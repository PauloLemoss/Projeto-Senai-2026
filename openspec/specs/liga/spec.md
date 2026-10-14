# liga Specification

## Purpose

Define a escalação de titulares, as partidas com placar calculado pelos atributos dos jogadores e
o histórico de partidas e a classificação da liga (RN19 a RN21). Depende das capabilities
`jogadores`, `clubes` e `mercado` para os elencos e contratos que escalação e partidas referenciam.

## Requirements

### Requirement: Escalação substitui os titulares do clube numa única operação
`PUT /clubs/{id}/lineup` SHALL receber `formation` (`3-1`, `2-2`, `2-1-1` ou `1-2-1`) e `player_ids`
(exatamente 5 ids distintos e inteiros positivos) e substituir a escalação inteira do clube numa
única operação, sem mudar o caixa. Cada titular SHALL ser do elenco do clube e não estar `DOENTE`.
As posições dos 5 titulares SHALL fechar exatamente a formação: 1 GOL e, em cada setor (defesa:
ZAG ou LAT; meio: MEI; ataque: ATA), a quantidade de jogadores da formação escolhida. Jogador
`MAL_CONDICIONADO` SHALL poder ser escalado.

#### Scenario: Escalação válida substitui a anterior
- **WHEN** o cliente escala um clube com `formation` `2-1-1` e 5 `player_ids` do elenco que
  fecham a formação (1 GOL, 2 entre ZAG/LAT, 1 MEI, 1 ATA), nenhum `DOENTE`
- **THEN** a API responde `200` com a escalação criada, e uma escalação anterior (se houver) é
  totalmente substituída

#### Scenario: Jogador fora do elenco do clube é recusado
- **WHEN** um dos `player_ids` é de um jogador livre ou de outro clube
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Jogador DOENTE é recusado
- **WHEN** um dos `player_ids` é de um jogador `DOENTE`
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Posições que não fecham a formação são recusadas
- **WHEN** o cliente escala `formation` `2-1-1` (2 defesa, 1 meio, 1 ataque) com 2 goleiros, ou sem
  nenhum MEI, ou com 3 jogadores de defesa
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: formation fora da lista é recusada
- **WHEN** o cliente envia `formation` fora de `3-1`, `2-2`, `2-1-1` ou `1-2-1`
- **THEN** a API responde `400` com `message`

#### Scenario: player_ids fora do formato é recusado
- **WHEN** o cliente envia `player_ids` ausente, que não é lista, com tamanho diferente de 5, com
  ids repetidos ou que não são inteiros positivos
- **THEN** a API responde `400` com `message`

#### Scenario: Clube ou jogador inexistente
- **WHEN** o clube da URL não existe, ou um dos `player_ids` não existe (inclusive excluído
  logicamente)
- **THEN** a API responde `404` com `message`

### Requirement: Consulta da escalação atual do clube
`GET /clubs/{id}/lineup` SHALL devolver `club_id`, `formation`, `complete` e `players` (na ordem
do elenco, RN11, cada um com os campos de `GET /players/{id}`). Sem escalação, `formation` SHALL
vir `null`, `players` vazio e `complete` `false`.

#### Scenario: Clube sem escalação
- **WHEN** o cliente consulta a escalação de um clube que nunca escalou
- **THEN** a API responde `200` com `formation` `null`, `players` `[]` e `complete` `false`

#### Scenario: Clube com escalação completa
- **WHEN** o cliente consulta a escalação de um clube com os 5 titulares
- **THEN** a API responde `200` com `complete` `true` e os 5 `players` na ordem do elenco

#### Scenario: Clube inexistente
- **WHEN** o `id` do clube na URL não existe
- **THEN** a API responde `404` com `message`

### Requirement: Titular sai da escalação ao ser vendido ou ao ficar DOENTE
Quando um titular é vendido (RN16) ou tem a condição alterada para `DOENTE`, o sistema SHALL
removê-lo da escalação do clube na mesma operação da venda ou da alteração de condição. A
escalação SHALL ficar incompleta, mantendo a mesma `formation` e os titulares restantes, até uma
nova escalação completa ser enviada. Um jogador que deixa de estar `DOENTE` SHALL permanecer fora
da escalação até ser escalado de novo.

#### Scenario: Venda do titular deixa a escalação incompleta
- **WHEN** um clube tem escalação completa e um dos titulares é vendido
- **THEN** `GET /clubs/{id}/lineup` passa a trazer `complete` `false`, a mesma `formation` e os 4
  titulares restantes, e o clube não joga (RN20) até escalar de novo

#### Scenario: Titular que fica DOENTE sai da escalação
- **WHEN** um clube tem escalação completa e a condição de um titular é alterada para `DOENTE`
- **THEN** `GET /clubs/{id}/lineup` passa a trazer `complete` `false` e a mesma `formation`, sem
  esse jogador em `players`

#### Scenario: Jogador não volta sozinho ao deixar de estar DOENTE
- **WHEN** um jogador que saiu da escalação por estar `DOENTE` tem a condição alterada de volta
  para `APTO` ou `MAL_CONDICIONADO`
- **THEN** ele continua fora de `players` até ser escalado de novo explicitamente

### Requirement: Partida jogada na hora, com placar calculado pelos 6 duelos
`POST /matches` SHALL recusar com `400` quando o corpo ou um id for inválido (inclusive
`home_club_id`/`away_club_id` enviados como string ou com parte fracionária, em vez de inteiro) ou
`home_club_id` for igual a `away_club_id`; com `404` quando um dos clubes não existir; e com `409`
quando um dos
clubes não tiver escalação completa — nesses três casos, nada SHALL ser gravado. Caso contrário,
a partida SHALL ser jogada e gravada numa única operação: os titulares de cada clube, na ordem do
elenco (goleiro depois os 4 de linha, numerados do 1º ao 4º, do mais recuado ao mais avançado),
disputam 6 duelos (3 ataques do mandante, depois 3 do visitante); em cada duelo o atacante usa o
atributo da posição (finalização no ATA, passe no MEI, drible no ZAG/LAT) e o defensor usa sempre
a defesa, com o titular `MAL_CONDICIONADO` jogando com 15% a menos em cada atributo (arredondado
ao inteiro mais próximo, o meio para cima); o duelo vira gol quando o ataque é maior que a defesa.
O placar final (0 a 3 por clube) e o `result` (`MANDANTE`, `VISITANTE` ou `EMPATE`) SHALL ser
gravados com as formações dos dois clubes e os 6 duelos (nomes, posições, condições, atributo e
valor usados), sem recalcular depois. A partida SHALL poder ser jogada a qualquer momento, sem
limite por clube, inclusive repetindo o mesmo confronto; SHALL não mudar o caixa, a escalação nem
os jogadores.

#### Scenario: Partida de ponta a ponta com o exemplo do enunciado
- **WHEN** o Águias FC (mandante, `2-1-1`) enfrenta o Delta FC (visitante, `2-1-1`), com o LAT do
  Águias FC `MAL_CONDICIONADO` (drible 74 → 62,9 → 63; defesa 66 → 56,1 → 56)
- **THEN** a API responde `201` com `Location`, placar Águias FC 1 × 2 Delta FC, `result`
  `VISITANTE`, e os 6 duelos gravados na ordem (1 a 3 o mandante ataca, 4 a 6 o visitante)

#### Scenario: Mandante igual ao visitante é recusado
- **WHEN** o cliente envia `home_club_id` igual a `away_club_id`
- **THEN** a API responde `400` com `message`

#### Scenario: Clube inexistente
- **WHEN** `home_club_id` ou `away_club_id` não existe
- **THEN** a API responde `404` com `message`

#### Scenario: home_club_id ou away_club_id como string é recusado
- **WHEN** o cliente envia `home_club_id` ou `away_club_id` como string (ex.: `"1"`), em vez de um
  inteiro
- **THEN** a API responde `400` com `message`, e nada é gravado

#### Scenario: Escalação incompleta recusa a partida
- **WHEN** o mandante ou o visitante não tem escalação completa (nunca escalou, ou perdeu um
  titular por venda/DOENTE e não escalou de novo)
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Partida não muda caixa, escalação nem jogadores
- **WHEN** uma partida é jogada entre dois clubes
- **THEN** o `cash` dos dois clubes, as escalações e os atributos dos jogadores continuam
  exatamente os mesmos de antes da partida

### Requirement: Histórico de partidas e detalhe de uma partida
`GET /matches` SHALL devolver as partidas da mais recente para a mais antiga (empate pelo maior
id primeiro), com placar e `result`; o filtro opcional `club_id` SHALL trazer só as partidas em
que o clube foi mandante ou visitante. `GET /matches/{id}` SHALL devolver a partida com os 6
duelos, na mesma ordem da RN20.

#### Scenario: Histórico ordenado da mais recente para a mais antiga
- **WHEN** o cliente consulta `GET /matches` depois de várias partidas jogadas em momentos
  diferentes
- **THEN** elas vêm da mais recente para a mais antiga, sem `duels`

#### Scenario: Filtro por club_id
- **WHEN** o cliente consulta `GET /matches?club_id={id}`
- **THEN** só vêm as partidas em que esse clube foi mandante ou visitante

#### Scenario: Clube do filtro inexistente
- **WHEN** o `club_id` do filtro não existe
- **THEN** a API responde `404` com `message`

#### Scenario: Detalhe de uma partida traz os 6 duelos
- **WHEN** o cliente consulta `GET /matches/{id}` de uma partida existente
- **THEN** a API responde `200` com os 6 duelos, cada um com atacante, defensor, atributo, valor e
  se houve gol

#### Scenario: Partida inexistente
- **WHEN** o `id` da partida não existe
- **THEN** a API responde `404` com `message`

### Requirement: Classificação calculada a cada consulta
`GET /standings` SHALL devolver a classificação de todos os clubes cadastrados, inclusive os que
nunca jogaram (zerados): `position`, `club_id`, `club_name`, `played`, `wins`, `draws`, `losses`,
`goals_for`, `goals_against`, `goal_difference` e `points` (vitória 3, empate 1, derrota 0). A
ordem SHALL ser por mais pontos, depois maior saldo de gols, depois mais gols marcados, depois o
nome do clube em ordem alfabética; `position` SHALL ir de 1 ao total de clubes, sem repetir. A
classificação SHALL ser calculada a cada consulta, nunca gravada.

#### Scenario: Classificação com o exemplo do enunciado
- **WHEN** 6 clubes estão cadastrados e 4 partidas foram jogadas (Águias FC 1×2 Delta FC, Gama SC
  2×1 Épsilon EC, Épsilon EC 3×2 Águias FC, Delta FC 0×1 Gama SC), com Mangue FC e Tubarões EC sem
  jogar
- **THEN** `GET /standings` traz, na ordem: Gama SC (1º, 6 pontos), Épsilon EC (2º, 3 pontos,
  mais gols marcados que o Delta FC), Delta FC (3º, 3 pontos), Mangue FC (4º, 0 pontos, antes do
  Tubarões EC pelo nome), Tubarões EC (5º), Águias FC (6º, 0 pontos, saldo −2)

#### Scenario: Clube que nunca jogou aparece zerado
- **WHEN** um clube é consultado na classificação sem ter jogado nenhuma partida
- **THEN** ele aparece com `played`, `wins`, `draws`, `losses`, `goals_for`, `goals_against`,
  `goal_difference` e `points` todos `0`
