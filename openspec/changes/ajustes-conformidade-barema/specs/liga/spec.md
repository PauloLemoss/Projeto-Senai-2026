## MODIFIED Requirements

### Requirement: Partida jogada na hora, com placar calculado pelos 6 duelos
`POST /matches` SHALL recusar com `400` quando o corpo ou um id for inválido (inclusive
`home_club_id`/`away_club_id` enviados como string ou com parte fracionária, em vez de inteiro) ou
`home_club_id` for igual a `away_club_id`; com `404` quando um dos clubes não existir; e com `409`
quando um dos clubes não tiver escalação completa — nesses três casos, nada SHALL ser gravado.
Caso contrário, a partida SHALL ser jogada e gravada numa única operação: os titulares de cada
clube, na ordem do elenco (goleiro depois os 4 de linha, numerados do 1º ao 4º, do mais recuado ao
mais avançado), disputam 6 duelos (3 ataques do mandante, depois 3 do visitante); em cada duelo o
atacante usa o atributo da posição (finalização no ATA, passe no MEI, drible no ZAG/LAT) e o
defensor usa sempre a defesa, com o titular `MAL_CONDICIONADO` jogando com 15% a menos em cada
atributo (arredondado ao inteiro mais próximo, o meio para cima); o duelo vira gol quando o ataque
é maior que a defesa. O placar final (0 a 3 por clube) e o `result` (`MANDANTE`, `VISITANTE` ou
`EMPATE`) SHALL ser gravados com as formações dos dois clubes e os 6 duelos (nomes, posições,
condições, atributo e valor usados), sem recalcular depois. A partida SHALL poder ser jogada a
qualquer momento, sem limite por clube, inclusive repetindo o mesmo confronto; SHALL não mudar o
caixa, a escalação nem os jogadores.

#### Scenario: Partida de ponta a ponta com o exemplo do enunciado
- **WHEN** o Águias FC (mandante, `2-1-1`) enfrenta o Delta FC (visitante, `2-1-1`), com o LAT do
  Águias FC `MAL_CONDICIONADO` (drible 74 → 62,9 → 63; defesa 66 → 56,1 → 56)
- **THEN** a API responde `201` com `Location`, placar Águias FC 1 × 2 Delta FC, `result`
  `VISITANTE`, e os 6 duelos gravados na ordem (1 a 3 o mandante ataca, 4 a 6 o visitante)

#### Scenario: Mandante igual ao visitante é recusado
- **WHEN** o cliente envia `home_club_id` igual a `away_club_id`
- **THEN** a API responde `400` com `message`

#### Scenario: home_club_id ou away_club_id como string é recusado
- **WHEN** o cliente envia `home_club_id` ou `away_club_id` como string (ex.: `"1"`), em vez de um
  inteiro
- **THEN** a API responde `400` com `message`, e nada é gravado

#### Scenario: Clube inexistente
- **WHEN** `home_club_id` ou `away_club_id` não existe
- **THEN** a API responde `404` com `message`

#### Scenario: Escalação incompleta recusa a partida
- **WHEN** o mandante ou o visitante não tem escalação completa (nunca escalou, ou perdeu um
  titular por venda/DOENTE e não escalou de novo)
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Partida não muda caixa, escalação nem jogadores
- **WHEN** uma partida é jogada entre dois clubes
- **THEN** o `cash` dos dois clubes, as escalações e os atributos dos jogadores continuam
  exatamente os mesmos de antes da partida
