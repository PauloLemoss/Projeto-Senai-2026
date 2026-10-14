## Purpose

Define o ciclo de criação e consulta de um clube: nome e sigla únicos, caixa inicial, listagem
ordenável e visão do elenco com valor e patrimônio calculados (RN10 e RN11). Depende da capability
`api-conventions` para as regras de validação e erro genéricas.

## ADDED Requirements

### Requirement: Criação de clube com nome e sigla únicos
O sistema SHALL criar um clube com `name` (3 a 60 caracteres após V4, de 2 a 5 palavras, só
letras com ou sem acento, espaços, hífen e ponto) e `acronym` (exatamente 3 letras de A a Z,
maiúsculas, sem acento). O clube SHALL nascer com `cash` 300,00 e sem jogadores. `name` SHALL ser
único ignorando maiúsculas e minúsculas, mas considerando acentos (RN10); `acronym` SHALL ser
único. A liga SHALL aceitar no máximo 20 clubes.

#### Scenario: Criação válida
- **WHEN** o cliente cria um clube com `name` "Águias FC" e `acronym` "AGU"
- **THEN** a API responde `201` com `Location` e o clube criado, com `cash` 300,00, `squad_value`
  0,00 e `net_worth` 300,00

#### Scenario: Nome duplicado ignorando caixa é recusado
- **WHEN** existe um clube "Águias FC" e o cliente tenta criar "  águias   fc " (minúsculo, com
  espaços redundantes que a normalização V4 remove)
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Nome com acento diferente é aceito
- **WHEN** existe um clube "Águias FC" e o cliente cria "Aguias FC" (sem acento)
- **THEN** a API responde `201` — nomes diferentes só pelo acento não são duplicados

#### Scenario: Sigla duplicada é recusada
- **WHEN** a sigla "AGU" já está cadastrada e o cliente tenta criar outro clube com essa sigla
- **THEN** a API responde `409` com `message`

#### Scenario: Limite de 20 clubes
- **WHEN** a liga já tem 20 clubes cadastrados e o cliente tenta criar o 21º
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Nome com caractere fora do permitido é recusado
- **WHEN** o cliente cria um clube com `name` "Clube 10" (contém dígito)
- **THEN** a API responde `400` com `message`

#### Scenario: Nome com uma palavra só é recusado
- **WHEN** o cliente cria um clube com `name` "Aguias" (uma palavra só)
- **THEN** a API responde `400` com `message`

#### Scenario: Nome com mais de cinco palavras é recusado
- **WHEN** o cliente cria um clube com `name` de seis palavras ou mais
- **THEN** a API responde `400` com `message`

#### Scenario: Sigla fora do formato básico é recusada
- **WHEN** o cliente cria um clube com `acronym` de 2 letras, ou em minúsculas, ou com acento
- **THEN** a API responde `400` com `message`, antes mesmo de verificar a correspondência com o
  nome

### Requirement: Sigla precisa corresponder ao nome do clube
`acronym` SHALL ser formado por três letras que aparecem no `name`, nessa ordem, ignorando
maiúsculas, minúsculas e acentos, sendo a primeira delas sempre a primeira letra do nome; as três
letras não podem ser todas iguais.

#### Scenario: Sigla que não começa pela primeira letra do nome é recusada
- **WHEN** o cliente cria um clube com `name` "Águias FC" e `acronym` "GUI" (não começa com "A")
- **THEN** a API responde `400` com `message`

#### Scenario: Sigla com as três letras iguais é recusada
- **WHEN** o cliente cria um clube com `acronym` "AAA"
- **THEN** a API responde `400` com `message`

#### Scenario: Sigla fora de ordem no nome é recusada
- **WHEN** o cliente cria um clube com `name` "Águias FC" e `acronym` "AUG" (letras existem no
  nome, mas fora da ordem em que aparecem)
- **THEN** a API responde `400` com `message`

### Requirement: Listagem de clubes ordenável por nome ou patrimônio
`GET /clubs` SHALL devolver todos os clubes com os campos mínimos (`id`, `name`, `acronym`,
`cash`, `squad_value`, `net_worth`), ordenados por `name` (padrão, ordem alfabética da regra
geral) ou por `net_worth` calculado (`sort=net_worth_asc` ou `net_worth_desc`), com empate
desfeito por nome e depois por id crescente. Um `sort` fora desses valores SHALL ser recusado com
`400`.

#### Scenario: Ordenação padrão por nome
- **WHEN** o cliente consulta `GET /clubs` sem `sort`
- **THEN** os clubes vêm em ordem alfabética pelo nome

#### Scenario: Ordenação por patrimônio
- **WHEN** o cliente consulta `GET /clubs?sort=net_worth_desc`
- **THEN** os clubes vêm do maior para o menor patrimônio, com empate desfeito por nome e depois id

#### Scenario: Valor de sort inválido é recusado
- **WHEN** o cliente consulta `GET /clubs?sort=cash`
- **THEN** a API responde `400` com `message`

### Requirement: Consulta de clube com elenco, valor do elenco e patrimônio
`GET /clubs/{id}` SHALL devolver o clube com `players` (o elenco), ordenado por posição (GOL,
ZAG, LAT, MEI, ATA), depois por nome e depois por id; `squad_value` (soma dos valores de mercado
dos jogadores do clube) e `net_worth` (`cash` + `squad_value`) SHALL ser calculados a cada
consulta, nunca gravados.

#### Scenario: Clube recém-criado tem elenco vazio
- **WHEN** consulta-se um clube que acabou de ser criado
- **THEN** `players` vem `[]`, `squad_value` é `0.00` e `net_worth` é igual ao `cash`

#### Scenario: Elenco ordenado por posição, depois nome, depois id
- **WHEN** um clube tem jogadores em mais de uma posição
- **THEN** `players` vem na ordem GOL, ZAG, LAT, MEI, ATA; dentro da mesma posição, por nome e
  depois por id

#### Scenario: Clube inexistente
- **WHEN** o cliente consulta `GET /clubs/{id}` para um id que não existe
- **THEN** a API responde `404` com `message`
