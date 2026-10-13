## Purpose

Define o ciclo de vida de um jogador isolado: cadastro com cálculo do valor base, consulta com
overall e valor de mercado calculados, edição, alteração de condição física e exclusão lógica.
Depende da capability `api-conventions` para as regras de validação e erro genéricas; aqui só
entram os limites de campo e as regras específicas de jogador do enunciado (RN02 a RN09).

## ADDED Requirements

### Requirement: Limites de campo do cadastro de jogador
O sistema SHALL validar, no cadastro (`POST /players`), os seguintes campos obrigatórios, cada um
recusado com `400` fora do limite (inclusive): `name` (3 a 100 caracteres após normalização, pelo
menos duas palavras, nenhum dígito), `position` (`GOL`, `ZAG`, `LAT`, `MEI` ou `ATA`), `agility`
(inteiro de 1 a 100, no máximo 85 se `age` for 35 ou mais), `age` (inteiro de 16 a 45),
`pace`/`shooting`/`passing`/`dribbling`/`defending`/`physical` (inteiros de 1 a 99 cada, soma dos
seis não pode passar de 480) e `potential` (inteiro de 1 a 99, maior ou igual ao maior dos seis
atributos; igual ao maior deles se `age` for 33 ou mais).

#### Scenario: Nome com menos de duas palavras é recusado
- **WHEN** o cliente cadastra um jogador com `name` de uma palavra só (ex.: `"Lua"`)
- **THEN** a API responde `400` com `message`

#### Scenario: Soma dos seis atributos acima do limite é recusada
- **WHEN** o cliente cadastra um jogador cuja soma de `pace`+`shooting`+`passing`+`dribbling`+
  `defending`+`physical` passa de 480
- **THEN** a API responde `400` com `message`

#### Scenario: Potential menor que o maior atributo é recusado
- **WHEN** o cliente cadastra um jogador com `potential` menor que o maior dos seis atributos
- **THEN** a API responde `400` com `message`

#### Scenario: Jogador com 33 anos ou mais exige potential igual ao maior atributo
- **WHEN** o cliente cadastra um jogador com `age` 33 e `potential` diferente do maior dos seis
  atributos
- **THEN** a API responde `400` com `message`

### Requirement: Cadastro calcula e grava o valor base uma única vez
O sistema SHALL calcular o `overall` a partir dos seis atributos e dos pesos da posição (RN06),
depois calcular o `valor base` em duas etapas — parte progressiva do overall (0,50 por ponto de
41 a 60, 2,00 por ponto de 61 a 75, 6,00 por ponto de 76 a 99) e, se a idade do cadastro for até
21 anos, multiplicar essa parte por `(100 + potential − overall) ÷ 100` — arredondar o resultado
uma única vez para 2 casas, com piso de 1,00. O valor base SHALL ser gravado no cadastro e não
muda depois, mesmo que o `PUT` altere a posição ou a idade.

#### Scenario: Cadastro sem jovem promessa
- **WHEN** um jogador é cadastrado com atributos que resultam em overall 75, `potential` 86 e
  `age` 25
- **THEN** o valor base calculado e gravado é `40.00`

#### Scenario: Cadastro com jovem promessa
- **WHEN** um jogador é cadastrado com atributos que resultam em overall 70, `potential` 84 e
  `age` 21
- **THEN** o valor base calculado e gravado é `34.20`

#### Scenario: Cadastro no piso do valor base
- **WHEN** um jogador é cadastrado com atributos que resultam em overall 40, `potential` 66 e
  `age` 36 (parte do overall 0,00)
- **THEN** o valor base calculado e gravado é `1.00`

### Requirement: Jogador nasce livre e APTO
O sistema SHALL cadastrar todo jogador com `condition` `APTO` e `club_id` nulo, independente do
que for enviado no corpo (V7).

#### Scenario: Cadastro básico
- **WHEN** um jogador é cadastrado com dados válidos
- **THEN** a resposta traz `condition: "APTO"` e `club_id: null`

### Requirement: Consulta calcula overall e valor de mercado a cada acesso
O sistema SHALL calcular `overall` (RN06, pelos pesos da posição) e `market_value` (RN02 a RN05,
a partir do valor base, da condição física, da agilidade e da idade atuais) a cada consulta do
jogador, nunca gravando esses valores. O cálculo do valor de mercado segue, nesta ordem: desconto
por condição ajustado pela agilidade (RN02/RN03), percentual total (ajuste por idade RN04 menos o
desconto), teto de −40% no percentual total, valor de mercado = valor base × (100 + percentual) ÷
100 arredondado, com piso de 1,00.

#### Scenario: Jogador APTO sem ajuste de idade
- **WHEN** consulta-se um jogador com valor base 82,00, condição `APTO`, agilidade 20 e idade 25
- **THEN** `market_value` é `82.00`

#### Scenario: Desconto reduzido pela metade por alta agilidade
- **WHEN** consulta-se um jogador com valor base 82,00, condição `MAL_CONDICIONADO`, agilidade 80
  e idade 21 (desconto de condição 7,5%, ajuste de idade +10%)
- **THEN** `market_value` é `84.05`

#### Scenario: Teto de desconto aplicado
- **WHEN** consulta-se um jogador com valor base 82,00, condição `DOENTE`, agilidade 10 e idade 40
  (percentual total calculado ficaria em −50%)
- **THEN** o desconto é limitado a −40% e `market_value` é `49.20`

#### Scenario: Piso do valor de mercado aplicado
- **WHEN** consulta-se um jogador com valor base 1,00, condição `MAL_CONDICIONADO`, agilidade 50 e
  idade 35 (resultado do cálculo ficaria em 0,75)
- **THEN** `market_value` sobe para o piso de `1.00`

### Requirement: Edição altera só nome, posição, agilidade e idade
O sistema SHALL permitir, via `PUT /players/{id}`, alterar apenas `name`, `position`, `agility` e
`age`, exigindo os quatro campos mesmo que só um mude; os seis atributos, o `potential` e o valor
base SHALL continuar os do cadastro (RN08, V7). Jogador com `club_id` não nulo SHALL recusar
mudança de posição com `409`. A idade enviada SHALL ser recusada com `409` se for menor que a
idade atual.

#### Scenario: Edição válida não muda indicadores nem valor base
- **WHEN** o cliente envia `PUT /players/{id}` alterando só `agility`, mantendo os demais campos
- **THEN** a resposta traz os seis atributos, o `potential` e o `base_value` iguais aos do
  cadastro, com a `agility` atualizada

#### Scenario: Mudança de posição de jogador com clube é recusada
- **WHEN** o cliente envia `PUT /players/{id}` com `position` diferente para um jogador cujo
  `club_id` não é nulo
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Redução de idade é recusada
- **WHEN** o cliente envia `PUT /players/{id}` com `age` menor que a idade atual do jogador
- **THEN** a API responde `409` com `message`, e nada é gravado

### Requirement: Alteração de condição física segue uma máquina de estados
O sistema SHALL permitir, via `PATCH /players/{id}/condition`, alterar `condition` para `APTO`,
`MAL_CONDICIONADO` ou `DOENTE`, exceto a transição direta de `DOENTE` para `APTO`, que SHALL ser
recusada com `409`. Enviar a condição já atual SHALL ser aceito com `200`, sem mudança.

#### Scenario: Transição direta de DOENTE para APTO é recusada
- **WHEN** o cliente envia `PATCH /players/{id}/condition` com `{"condition": "APTO"}` para um
  jogador atualmente `DOENTE`
- **THEN** a API responde `409` com `message`, e a condição não muda

#### Scenario: Enviar a condição atual é aceito sem mudança
- **WHEN** o cliente envia `PATCH /players/{id}/condition` com a condição que o jogador já tem
- **THEN** a API responde `200` e a condição permanece a mesma

#### Scenario: Condição fora da lista é recusada
- **WHEN** o cliente envia `PATCH /players/{id}/condition` com um valor fora de `APTO`,
  `MAL_CONDICIONADO` ou `DOENTE`
- **THEN** a API responde `400` com `message`

### Requirement: Exclusão lógica de jogador livre
O sistema SHALL permitir `DELETE /players/{id}` apenas para jogador **livre** (`club_id` nulo),
respondendo `204` sem corpo e marcando o momento da exclusão sem apagar o registro (RN09).
Jogador com clube SHALL ser recusado com `409`. Depois da exclusão, o jogador SHALL contar como
inexistente (`404`) em toda consulta, edição, alteração de condição e nova exclusão por esse id.

#### Scenario: Exclusão de jogador livre
- **WHEN** o cliente envia `DELETE /players/{id}` para um jogador livre
- **THEN** a API responde `204` sem corpo

#### Scenario: Exclusão de jogador com clube é recusada
- **WHEN** o cliente envia `DELETE /players/{id}` para um jogador cujo `club_id` não é nulo
- **THEN** a API responde `409` com `message`, e o jogador não é excluído

#### Scenario: Jogador excluído conta como inexistente
- **WHEN** o cliente consulta, edita, altera a condição ou tenta excluir de novo um jogador já
  excluído
- **THEN** a API responde `404` com `message` em qualquer um desses casos
