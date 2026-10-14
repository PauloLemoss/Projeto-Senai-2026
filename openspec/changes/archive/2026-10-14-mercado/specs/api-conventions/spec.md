## ADDED Requirements

### Requirement: Datas e horas no formato de Brasília (RN01)
Toda data e hora enviada à API SHALL usar o horário de Brasília, timezone-aware, no formato
`AAAA-MM-DDTHH:MM-03:00` (minutos, sem segundos). Um formato diferente, inclusive sem o `-03:00`,
SHALL ser recusado com `400`. Uma data ou hora inexistente, mesmo no formato certo (como
`2027-02-30T10:15-03:00` ou `2027-03-02T24:00-03:00`), SHALL também ser recusada com `400`, nunca
ajustada. As respostas SHALL trazer o formato `AAAA-MM-DDTHH:MM:SS-03:00` (com segundos). O
horário de Brasília SHALL ser sempre `-03:00`, sem horário de verão.

#### Scenario: Formato de entrada válido é aceito
- **WHEN** o cliente envia uma data e hora como `2027-03-02T10:15-03:00`
- **THEN** o valor é aceito e interpretado como aquele instante no horário de Brasília

#### Scenario: Entrada sem o offset -03:00 é recusada
- **WHEN** o cliente envia uma data e hora sem o sufixo `-03:00` (ex.: `2027-03-02T10:15`, ou com
  outro offset)
- **THEN** a API responde `400` com `message`

#### Scenario: Data inexistente é recusada
- **WHEN** o cliente envia `2027-02-30T10:15-03:00` (30 de fevereiro não existe)
- **THEN** a API responde `400` com `message`, nunca ajustando para outra data

#### Scenario: Hora inexistente é recusada
- **WHEN** o cliente envia `2027-03-02T24:00-03:00` (hora 24 não existe)
- **THEN** a API responde `400` com `message`

#### Scenario: Resposta traz o formato com segundos
- **WHEN** a API devolve uma data e hora gravada ou calculada
- **THEN** o valor vem no formato `AAAA-MM-DDTHH:MM:SS-03:00`, sempre com o offset `-03:00`
