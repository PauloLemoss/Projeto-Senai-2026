## ADDED Requirements

### Requirement: Campo inteiro do corpo recusa texto e fração (V2/V3)
Em todo campo do corpo de uma requisição documentado como inteiro em "Limites de cada campo", o
sistema SHALL recusar com `400` um valor que não seja um número JSON (ex.: uma string, mesmo que
só com dígitos, como `"15"`) e SHALL recusar com `400` um número com parte fracionária não nula
(ex.: `50.5`); um número com parte fracionária nula (ex.: `50.0`) SHALL ser aceito como o inteiro
correspondente (`50`). Esta regra vale para todo campo inteiro de corpo, inclusive os que
referenciam outro recurso por id (`club_id`, `player_ids`, `home_club_id`, `away_club_id`).

#### Scenario: String numérica em campo inteiro do corpo é recusada
- **WHEN** o cliente envia um campo inteiro do corpo como string, mesmo só com dígitos (ex.:
  `"club_id": "1"`)
- **THEN** a API responde `400` com `message`, e nada é gravado

#### Scenario: Número com parte fracionária não nula é recusado
- **WHEN** o cliente envia um campo inteiro do corpo como `50.5`
- **THEN** a API responde `400` com `message`

#### Scenario: Número com parte fracionária nula é aceito
- **WHEN** o cliente envia um campo inteiro do corpo como `50.0`
- **THEN** o valor é aceito como `50`
