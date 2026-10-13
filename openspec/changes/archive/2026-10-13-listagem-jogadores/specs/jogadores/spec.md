## ADDED Requirements

### Requirement: Listagem paginada de jogadores com busca e filtros
`GET /players` SHALL devolver um objeto paginado (`data` e `meta`) com os jogadores que atendem à
busca e aos filtros combinados (RN07). `search` SHALL procurar o texto dentro do nome, ignorando
maiúsculas, minúsculas e acentos. Os filtros disponíveis — `position`, `condition`, `free`,
`club_id`, faixa de idade (`min_age`/`max_age`, 16 a 45) e faixa de **valor de mercado**
(`min_value`/`max_value`, 0 a 550, nunca o valor base) — SHALL ser combináveis entre si, aplicados
antes da paginação. Quando só um dos limites de uma faixa (`min_age`/`max_age` ou
`min_value`/`max_value`) for enviado, o outro SHALL assumir o extremo correspondente da faixa
aceita (ex.: só `min_age` enviado equivale a `max_age=45`). `meta.total_items` SHALL contar todos
os jogadores que atendem à busca e aos filtros (não só os da página atual), e `meta.total_pages`
SHALL ser `total_items ÷ limit`, arredondado para cima (`0` quando não houver itens). Uma página
além da última SHALL responder `200` com `data: []` e o `meta` correto, nunca `404`.

#### Scenario: Busca ignora acentos e caixa
- **WHEN** o cliente busca `search=joao`
- **THEN** jogadores com nome "João Silva" aparecem no resultado

#### Scenario: Busca ignora acentos e caixa (segundo exemplo)
- **WHEN** o cliente busca `search=LUA`
- **THEN** jogadores com nome "Meia Lua" aparecem no resultado

#### Scenario: Paginação intermediária
- **WHEN** 23 jogadores atendem aos filtros e o cliente pede `limit=10&page=1`
- **THEN** `data` tem 10 itens (do 1º ao 10º), `meta.total_items` é 23 e `meta.total_pages` é 3

#### Scenario: Última página parcial
- **WHEN** 23 jogadores atendem aos filtros e o cliente pede `limit=10&page=3`
- **THEN** `data` tem 3 itens (do 21º ao 23º), `meta.total_items` é 23 e `meta.total_pages` é 3

#### Scenario: Página além da última
- **WHEN** 23 jogadores atendem aos filtros e o cliente pede `limit=10&page=4`
- **THEN** a API responde `200` com `data: []`, `meta.total_items` 23 e `meta.total_pages` 3

#### Scenario: Sem jogadores que atendam ao filtro
- **WHEN** nenhum jogador atende aos filtros aplicados
- **THEN** a API responde `200` com `data: []`, `meta.total_items` 0 e `meta.total_pages` 0

#### Scenario: Filtro de valor usa o valor de mercado, nunca o valor base
- **WHEN** o cliente filtra por `min_value` e `max_value`
- **THEN** o filtro é aplicado sobre o `market_value` calculado de cada jogador, não sobre o
  `base_value`

#### Scenario: Faixa com um só limite assume o extremo correspondente
- **WHEN** o cliente envia só `min_age=30`, sem `max_age`
- **THEN** o filtro é aplicado como se `max_age` fosse `45` (o extremo superior aceito)

### Requirement: Ordenação da listagem de jogadores
`sort` SHALL aceitar `name` (padrão), `value_asc`, `value_desc`, `age_asc`, `age_desc` e
`position`, no máximo dois critérios separados por vírgula, sem repetir o mesmo campo mesmo com
sentidos diferentes (`value_asc,value_desc` ou `age_asc,age_desc` SHALL ser recusado, por
repetirem o campo `value`/`age`); com dois critérios de campos diferentes, o segundo desempata o
primeiro, e depois disso o desempate final SHALL ser sempre pelo nome e, por último, pelo id
crescente. `sort=position` SHALL ordenar na ordem fixa **GOL, ZAG, LAT, MEI, ATA** (RN07/RN11),
não alfabética.

#### Scenario: Ordenação por posição usa a ordem fixa, não alfabética
- **WHEN** o cliente pede `sort=position`
- **THEN** os jogadores aparecem na ordem GOL, ZAG, LAT, MEI, ATA, nunca em ordem alfabética das
  siglas

#### Scenario: Empate de ordenação é desfeito pelo nome e depois pelo id
- **WHEN** dois ou mais jogadores empatam no critério de `sort` pedido
- **THEN** o desempate segue pelo nome (ordem alfabética da regra geral) e, se ainda empatado,
  pelo id crescente

#### Scenario: Repetir o mesmo campo com sentidos diferentes é recusado
- **WHEN** o cliente pede `sort=value_asc,value_desc`
- **THEN** a API responde `400` com `message`, por repetir o campo `value`

### Requirement: Validação dos parâmetros de consulta de GET /players
Os parâmetros de `GET /players` SHALL seguir os formatos e faixas de "1. Filtros e query params
aceitos": `search` de 2 a 100 caracteres; inteiros (`club_id`, `page`, `limit`, `min_age`,
`max_age`) só positivos, sem zeros à esquerda, sem sinal e sem ponto, com `min_age`/`max_age` de
16 a 45, `limit` de 1 a 50 (padrão 10) e `page` a partir de 1 (padrão 1); decimais (`min_value`,
`max_value`) na forma `10`, `10.5` ou `10.55`, sem sinal, vírgula ou zeros à esquerda, de 0 a 550.
Um parâmetro com valor fora do aceito ou da faixa, vazio, ou uma combinação contraditória
(`min_age` > `max_age`, `min_value` > `max_value`, ou `free=true` junto com `club_id`) SHALL ser
recusado com `400`. `free=false` junto com `club_id` SHALL ser aceito. Um parâmetro com nome fora
da tabela SHALL ser ignorado.

#### Scenario: Valor de enum com caixa trocada é recusado
- **WHEN** o cliente envia `position=mei` (minúsculo)
- **THEN** a API responde `400` com `message`

#### Scenario: Combinação contraditória de idade é recusada
- **WHEN** o cliente envia `min_age` maior que `max_age`
- **THEN** a API responde `400` com `message`

#### Scenario: Combinação contraditória de só-livres com clube é recusada
- **WHEN** o cliente envia `free=true` junto com `club_id`
- **THEN** a API responde `400` com `message`

#### Scenario: Só-livres com clube=false é aceito
- **WHEN** o cliente envia `free=false` junto com `club_id`
- **THEN** a API aceita a combinação e aplica os dois filtros

#### Scenario: Parâmetro com valor vazio é recusado
- **WHEN** o cliente envia `position=` (presente, mas vazio)
- **THEN** a API responde `400` com `message`

#### Scenario: Parâmetro de nome desconhecido é ignorado
- **WHEN** o cliente envia um parâmetro que não está na tabela de filtros aceitos
- **THEN** a API ignora esse parâmetro e processa a requisição normalmente

#### Scenario: Busca fora do tamanho aceito é recusada
- **WHEN** o cliente envia `search` com 1 caractere (abaixo do mínimo de 2)
- **THEN** a API responde `400` com `message`

#### Scenario: Limit fora da faixa aceita é recusado
- **WHEN** o cliente envia `limit=51` (acima do máximo de 50)
- **THEN** a API responde `400` com `message`

#### Scenario: Valor de filtro acima do limite aceito é recusado
- **WHEN** o cliente envia `max_value=551` (acima do máximo de 550)
- **THEN** a API responde `400` com `message`
