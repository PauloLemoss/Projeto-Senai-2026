## Purpose

Define as regras de validação de entrada, os códigos de erro e as convenções de resposta que
valem para **todos** os endpoints da API (`/api/v1`), independente do domínio (jogadores,
clubes, mercado ou liga), conforme "📏 Premissas e regras gerais" do enunciado.

## ADDED Requirements

### Requirement: Corpo da requisição deve ser um objeto JSON
O sistema SHALL recusar com `400` qualquer corpo de requisição que não seja um objeto JSON válido
(RN/V1). Em pedidos sem corpo (consultas, exclusão), um corpo enviado SHALL ser ignorado.

#### Scenario: Corpo é um array
- **WHEN** o cliente envia `POST /players` com corpo `[]`
- **THEN** a API responde `400` com um objeto JSON contendo `message` não vazio, e nada é gravado

#### Scenario: Corpo é um valor simples
- **WHEN** o cliente envia `POST /players` com corpo `"x"` ou `10`
- **THEN** a API responde `400` com `message`, e nada é gravado

#### Scenario: JSON malformado
- **WHEN** o cliente envia um corpo que não é JSON válido (sintaxe quebrada)
- **THEN** a API responde `400` com `message`, e nada é gravado

### Requirement: Normalização de campos de texto antes de validar e gravar
Em todo campo de texto livre (nome, busca), o sistema SHALL remover espaços no início e no fim e
colapsar espaços repetidos em um só, antes de validar o tamanho e gravar (V4). Caracteres de
controle (tabulação, quebra de linha) SHALL ser recusados com `400`. Texto que fica vazio depois
da normalização conta como ausente.

#### Scenario: Espaços redundantes são normalizados
- **WHEN** o cliente envia o campo de nome como `"  Meia   Zeta "`
- **THEN** o valor é gravado como `"Meia Zeta"`

#### Scenario: Caractere de controle é recusado
- **WHEN** o cliente envia um campo de texto contendo um caractere de tabulação ou quebra de linha
- **THEN** a API responde `400` com `message`

#### Scenario: Texto vazio após normalização conta como ausente
- **WHEN** o cliente envia um campo de nome obrigatório como `"   "`
- **THEN** a API trata o campo como ausente e responde conforme a regra de campo obrigatório

### Requirement: Valores de lista são comparados exatamente, sem normalizar caixa
O sistema SHALL aceitar valores de enum (lista) exatamente como definidos no enunciado, com a
mesma caixa (maiúsculas/minúsculas) exigida (V5). Um valor com caixa diferente SHALL ser
recusado com `400`, nunca convertido.

#### Scenario: Valor de enum em minúsculas é recusado
- **WHEN** o cliente envia um campo de enum como `"ata"` em vez de `"ATA"`
- **THEN** a API responde `400` com `message`

### Requirement: Campo obrigatório ausente ou nulo é recusado
O sistema SHALL recusar com `400` qualquer requisição em que um campo obrigatório esteja ausente
ou seja `null` (V6).

#### Scenario: Campo obrigatório ausente
- **WHEN** o cliente envia um corpo sem um campo obrigatório do endpoint
- **THEN** a API responde `400` com `message`, e nada é gravado

#### Scenario: Campo obrigatório nulo
- **WHEN** o cliente envia um campo obrigatório explicitamente como `null`
- **THEN** a API responde `400` com `message`, e nada é gravado

### Requirement: Campos controlados pelo sistema são ignorados sem erro
O sistema SHALL ignorar, sem gerar erro, qualquer campo que o próprio sistema calcule ou controle
(como `id`, valores em moeda, indicadores calculados) e qualquer campo que não pertença ao
endpoint, inclusive campos com nome fora do snake_case esperado (V7). Se o campo obrigatório
correspondente não vier por causa disso, a requisição SHALL ser recusada pela regra de campo
obrigatório (V6).

#### Scenario: Campo calculado enviado no corpo é ignorado
- **WHEN** o cliente envia um campo controlado pelo sistema (ex.: um valor em moeda) no corpo de
  uma requisição de criação ou edição
- **THEN** a API ignora esse campo sem erro e calcula/gravação segue a regra de negócio do
  endpoint, não o valor enviado

#### Scenario: Nome de campo fora do snake_case é tratado como inexistente
- **WHEN** o cliente envia um campo com nome em outro formato (ex.: camelCase) no lugar de um
  campo esperado em snake_case
- **THEN** a API ignora o campo enviado e, se o campo esperado correspondente não vier, recusa a
  requisição pela regra de campo obrigatório ausente

### Requirement: Recurso ou id inexistente responde 404
O sistema SHALL responder `404` quando o caminho da URL não corresponder a um endpoint do
enunciado, ou quando o id de um recurso na URL não existir (V8). Um id na URL que não seja um
inteiro positivo escrito só com dígitos, sem zeros à esquerda, ou que passe de 2.147.483.647,
SHALL também contar como inexistente (`404`).

#### Scenario: Caminho inexistente
- **WHEN** o cliente faz uma requisição a um caminho que não existe no enunciado
- **THEN** a API responde `404` com `message`

#### Scenario: Id na URL em formato inválido
- **WHEN** o cliente faz uma requisição com um id na URL que não é um inteiro positivo sem zeros
  à esquerda (ex.: `abc`, `0`, `-1`, `1.5`, `01`)
- **THEN** a API responde `404` com `message`

#### Scenario: Id na URL acima do limite
- **WHEN** o cliente faz uma requisição com um id na URL maior que 2.147.483.647
- **THEN** a API responde `404` com `message`

### Requirement: Códigos de erro e corpo de recusa padronizados
O sistema SHALL usar `400` para dado, formato ou parâmetro inválido, `404` para recurso
inexistente e `409` para regra de negócio violada (V9), nunca combinando dois motivos de erro na
mesma resposta. Toda recusa SHALL responder com um objeto JSON contendo o campo `message` (texto
não vazio), sem stack trace, com o cabeçalho `Content-Type: application/json`. Nenhuma recusa
SHALL gravar qualquer dado.

#### Scenario: Recusa de regra de negócio
- **WHEN** uma requisição viola uma regra de negócio do domínio (ex.: limite de caixa, estado de
  contrato)
- **THEN** a API responde `409` com um objeto JSON contendo `message` não vazio, e nada é gravado

#### Scenario: Nenhuma informação de implementação vaza na recusa
- **WHEN** qualquer requisição é recusada (`400`, `404` ou `409`)
- **THEN** o corpo da resposta não contém stack trace nem detalhes internos de implementação

### Requirement: Criação de recurso responde 201 com Location
O sistema SHALL responder `201` em toda criação bem-sucedida de recurso, com o cabeçalho
`Location` apontando para o recurso criado (como caminho a partir da raiz do servidor, com o
prefixo `/api/v1`, ou como URL absoluta).

#### Scenario: Criação bem-sucedida
- **WHEN** um recurso é criado com sucesso
- **THEN** a resposta tem status `201` e o cabeçalho `Location` aponta para o recurso criado
