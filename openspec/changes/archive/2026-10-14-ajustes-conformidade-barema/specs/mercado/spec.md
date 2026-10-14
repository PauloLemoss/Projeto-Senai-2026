## MODIFIED Requirements

### Requirement: Compra de jogador livre com taxa e limite de caixa
`POST /players/{id}/buy` SHALL comprar um jogador livre para o clube informado em `club_id`, pelo
`valor de mercado` no momento (nunca o valor base). `fee` (taxa) SHALL ser 5% do valor de mercado,
arredondada, cobrada somente quando o valor de mercado for maior que 30,00. O custo total (valor +
taxa) SHALL ser descontado do `cash` do clube e não pode passar de 50% do `cash` antes da compra
(o limite é exato, sem arredondar; pode ser igual ao limite). A operação SHALL, numa única
transação de banco: descontar o caixa, atribuir `club_id` ao jogador, criar o contrato `ATIVO`
(RN12) e gravar a transação `COMPRA` (RN17). Um clube SHALL ser impedido de comprar um jogador que
ele mesmo já vendeu (outro clube pode). A resposta SHALL trazer os campos da transação (RN17) mais
`contract` (`purchase_value`, `loyalty_until`, `status` sempre `ATIVO` nessa resposta) e
`club_cash` (o `cash` do clube depois da compra).

#### Scenario: Compra aceita abaixo do limite, sem taxa
- **WHEN** um clube com `cash` 300,00 compra um jogador livre com valor de mercado 28,00
- **THEN** a API responde `200`; `fee` é 0,00 (não é maior que 30,00); o caixa passa a 272,00

#### Scenario: Custo total igual ao limite de 50% do caixa é aceito
- **WHEN** um clube com `cash` 100,00 compra um jogador com valor de mercado 47,62 (`fee` 2,38,
  custo total 50,00 — exatamente 50% de 100,00)
- **THEN** a API responde `200`

#### Scenario: Custo total acima do limite de 50% do caixa é recusado
- **WHEN** um clube com `cash` 100,00 tenta comprar um jogador com valor de mercado 48,00 (`fee`
  2,40, custo total 50,40, acima do limite de 50,00)
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Jogador que não está livre é recusado
- **WHEN** o cliente tenta comprar um jogador que já tem `club_id`
- **THEN** a API responde `409` com `message`

#### Scenario: Elenco com 12 jogadores recusa a 13ª compra
- **WHEN** o clube comprador já tem 12 jogadores no elenco (RN14)
- **THEN** a API responde `409` com `message`, e nada é gravado

#### Scenario: Clube que já vendeu o jogador não pode recomprá-lo
- **WHEN** o clube A vende um jogador e depois tenta comprá-lo de volta
- **THEN** a API responde `409` com `message`

#### Scenario: Outro clube pode comprar o jogador vendido
- **WHEN** o clube A vende um jogador e o clube B tenta comprá-lo
- **THEN** a API responde `200`

#### Scenario: Jogador inexistente ou excluído é recusado
- **WHEN** o cliente compra um jogador cujo id não existe ou está excluído logicamente (RN09)
- **THEN** a API responde `404` com `message`

#### Scenario: Clube inexistente é recusado
- **WHEN** o cliente envia `club_id` de um clube que não existe
- **THEN** a API responde `404` com `message`

#### Scenario: Campo obrigatório ausente é recusado
- **WHEN** o cliente compra sem `club_id` ou sem `loyalty_until`
- **THEN** a API responde `400` com `message`

#### Scenario: club_id inválido é recusado
- **WHEN** o cliente envia `club_id` 0, negativo, ou como string (ex.: `"1"`), em vez de um
  inteiro positivo
- **THEN** a API responde `400` com `message` (diferente do clube inexistente, que é `404`)

#### Scenario: loyalty_until fora do formato da RN01 é recusado
- **WHEN** o cliente envia `loyalty_until` em outro formato, inclusive sem o `-03:00`
- **THEN** a API responde `400` com `message`

#### Scenario: loyalty_until que não é futuro é recusado
- **WHEN** o cliente envia `loyalty_until` igual ou anterior ao momento da compra
- **THEN** a API responde `400` com `message`

#### Scenario: loyalty_until acima de 1.095 dias é recusado
- **WHEN** o cliente envia `loyalty_until` mais de 1.095 dias depois do momento da compra
- **THEN** a API responde `400` com `message`
