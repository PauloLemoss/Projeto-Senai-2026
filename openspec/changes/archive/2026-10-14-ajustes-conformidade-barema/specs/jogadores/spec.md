## MODIFIED Requirements

### Requirement: Listagem paginada de jogadores com busca e filtros
`GET /players` SHALL devolver um objeto paginado (`data` e `meta`) com os jogadores que atendem à
busca e aos filtros combinados (RN07). `search` SHALL procurar o texto dentro do nome, ignorando
maiúsculas, minúsculas e acentos. Os filtros disponíveis — `position`, `condition`, `free`,
`club_id`, faixa de idade (`min_age`/`max_age`, 16 a 45) e faixa de **valor de mercado**
(`min_value`/`max_value`, 0 a 550, nunca o valor base) — SHALL ser combináveis entre si, aplicados
antes da paginação. Quando só um dos limites de uma faixa (`min_age`/`max_age` ou
`min_value`/`max_value`) for enviado, o outro SHALL assumir o extremo correspondente da faixa
aceita (ex.: só `min_age` enviado equivale a `max_age=45`). Quando `club_id` for informado, o
sistema SHALL responder `404` se o clube não existir, antes de aplicar qualquer outro filtro.
`meta.total_items` SHALL contar todos os jogadores que atendem à busca e aos filtros (não só os da
página atual), e `meta.total_pages` SHALL ser `total_items ÷ limit`, arredondado para cima (`0`
quando não houver itens). Uma página além da última SHALL responder `200` com `data: []` e o
`meta` correto, nunca `404`.

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

#### Scenario: Filtro por club_id de clube inexistente é recusado
- **WHEN** o cliente filtra `GET /players?club_id=<id>` com um `club_id` de clube que não existe
- **THEN** a API responde `404` com `message`, mesmo que algum jogador atenda aos demais filtros
