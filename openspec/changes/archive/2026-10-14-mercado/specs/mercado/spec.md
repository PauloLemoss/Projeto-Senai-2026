## Purpose

Define a compra e a venda de jogadores entre clubes e a liga, com contrato de fidelidade, multa,
comissão progressiva, histórico de transações e exportação em CSV (RN12 a RN18). Depende das
capabilities `jogadores` e `clubes` para os cadastros que compra e venda referenciam.

## ADDED Requirements

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
- **WHEN** o cliente envia `club_id` 0 ou negativo
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

### Requirement: Venda de jogador com multa por fidelidade
`POST /players/{id}/sell` (sem corpo) SHALL vender, pelo `cash` do clube atual, um jogador do
elenco, pelo valor de mercado no momento. Dias restantes SHALL ser a diferença entre o fim da
fidelidade e o momento da venda, em dias com fração arredondados para cima (0 se o fim já passou).
O percentual da multa SHALL ser 0% (0 dias), 5% (1 a 30 dias), 10% (31 a 180 dias) ou 20% (181 dias
ou mais); a multa SHALL ser o valor de mercado × percentual, arredondada e limitada a 10,00. Com
multa, o contrato SHALL passar a `RESCINDIDO`; sem multa, a `ENCERRADO`. Um jogador livre (sem
clube) SHALL ser recusado. A resposta SHALL trazer os campos da transação (RN17) mais
`purchase_value` (valor gravado no contrato), `remaining_days`, `penalty_rate`, `contract_status`
(`RESCINDIDO` ou `ENCERRADO`) e `club_cash` (o `cash` do clube depois da venda).

#### Scenario: Fidelidade já cumprida não gera multa
- **WHEN** o fim da fidelidade já passou no momento da venda
- **THEN** `remaining_days` é 0, `penalty` é 0,00 e o contrato passa a `ENCERRADO`

#### Scenario: Faixa de 1 a 30 dias restantes gera 5% de multa
- **WHEN** faltam exatamente 30 dias para o fim da fidelidade
- **THEN** a multa é 5% do valor de mercado no momento da venda

#### Scenario: Faixa de 31 a 180 dias restantes gera 10% de multa
- **WHEN** faltam 30 dias e 1 minuto para o fim da fidelidade (arredonda para 31 dias restantes)
- **THEN** a multa é 10% do valor de mercado no momento da venda

#### Scenario: Faixa de 181 dias ou mais gera 20% de multa
- **WHEN** faltam 180 dias e 1 minuto para o fim da fidelidade (arredonda para 181 dias restantes)
- **THEN** a multa é 20% do valor de mercado no momento da venda

#### Scenario: Multa é limitada a 10,00
- **WHEN** 20% do valor de mercado no momento da venda passa de 10,00 (ex.: valor de mercado
  75,00, 20% = 15,00)
- **THEN** a multa gravada é 10,00

#### Scenario: Venda de ponta a ponta com multa, comissão e crédito
- **WHEN** um jogador comprado por 37,00 é vendido por 40,00, com 117 dias restantes de fidelidade
  (multa 10% = 4,00)
- **THEN** o lucro é 3,00, a comissão é 0,30 (10% do lucro), o crédito no caixa é 35,70 e o
  contrato passa a `RESCINDIDO`

#### Scenario: Jogador livre não pode ser vendido
- **WHEN** o cliente tenta vender um jogador sem clube
- **THEN** a API responde `409` com `message`

#### Scenario: Jogador inexistente ou excluído é recusado
- **WHEN** o cliente vende um jogador cujo id não existe ou está excluído logicamente (RN09)
- **THEN** a API responde `404` com `message`

### Requirement: Comissão progressiva sobre o lucro da venda
A comissão SHALL ser cobrada somente quando o lucro (valor de mercado na venda − valor de compra
gravado no contrato) for maior que zero: 10% sobre a parte do lucro até 10,00, mais 20% sobre a
parte acima de 10,00, somadas e arredondadas uma única vez no final. O crédito no caixa SHALL ser
o valor de mercado − multa − comissão.

#### Scenario: Lucro simples, só a primeira faixa
- **WHEN** o lucro da venda é 3,00
- **THEN** a comissão é 0,30 (10% de 3,00)

#### Scenario: Lucro cruzando as duas faixas
- **WHEN** o lucro da venda é 15,00
- **THEN** a comissão é 2,00 (10% de 10,00 + 20% de 5,00)

#### Scenario: Prejuízo não gera comissão
- **WHEN** o valor de mercado na venda é menor que o valor de compra (lucro negativo)
- **THEN** a comissão é 0,00

### Requirement: Histórico de transações do clube com filtros e totais
`GET /clubs/{id}/transactions` SHALL devolver `data` (as transações `COMPRA` e `VENDA` do clube,
da mais recente para a mais antiga, empate desfeito por id decrescente) e `summary` com os totais
das transações filtradas: `total_spent` (`value` + `fee` das `COMPRA`), `total_received`
(`cash_change` das `VENDA`), `total_fees` (`fee` de todas), `total_penalties` (`penalty` das
`VENDA`) e `total_profit` (`profit` das `VENDA`). Os filtros opcionais `type` (um ou mais,
separados por vírgula) e `player_id` SHALL poder ser combinados; a transação guarda os valores e o
nome do jogador no momento da operação, nunca recalculados.

#### Scenario: Histórico sem filtro traz compra e venda com os totais somados
- **WHEN** o cliente consulta o histórico de um clube que comprou e depois vendeu um jogador
- **THEN** `data` traz as duas transações (venda primeiro) e `summary` soma `total_spent`,
  `total_received`, `total_fees`, `total_penalties` e `total_profit` de ambas

#### Scenario: Filtro por type restringe data e summary
- **WHEN** o cliente consulta o histórico com `type=VENDA`
- **THEN** `data` só traz a venda e `summary.total_spent` é 0,00

#### Scenario: Jogador sem transações no clube
- **WHEN** o cliente filtra por `player_id` de um jogador sem transações nesse clube
- **THEN** a API responde `200` com `data` vazio e todos os totais de `summary` em 0,00

#### Scenario: Filtro inválido é recusado
- **WHEN** o cliente envia `type` fora da lista (`COMPRA`, `VENDA`) ou repetido
- **THEN** a API responde `400` com `message`

#### Scenario: Jogador do filtro inexistente ou excluído
- **WHEN** `player_id` não existe ou está excluído logicamente
- **THEN** a API responde `404` com `message`

#### Scenario: Clube inexistente
- **WHEN** o `id` do clube na URL não existe
- **THEN** a API responde `404` com `message`

#### Scenario: Conciliação do caixa pelo histórico
- **WHEN** se soma 300,00 (caixa inicial, RN10) com a `cash_change` de todas as transações do
  clube, sem filtro
- **THEN** o resultado é igual ao `cash` atual do clube

#### Scenario: Transações de jogador excluído permanecem no histórico
- **WHEN** um jogador com transações num clube é excluído logicamente (RN09) e o histórico desse
  clube é consultado depois
- **THEN** as transações dele continuam aparecendo, com o nome e os valores gravados no momento de
  cada operação, sem recalcular

### Requirement: Exportação do histórico em CSV
`GET /clubs/{id}/transactions/export` SHALL aceitar os mesmos filtros do histórico e responder
`200` com um arquivo `text/csv`, UTF-8 sem BOM, linhas terminadas em LF: a primeira linha é o
cabeçalho `data_hora;tipo;jogador;valor;taxa_ou_comissao;multa;lucro;variacao_caixa`; uma linha por
transação, na mesma ordem do histórico; valores com 2 casas e vírgula decimal, negativo com `-`;
`lucro` vazio quando nulo (na compra); nome do jogador com `;` ou aspas vai entre aspas duplas, com
cada aspa interna duplicada.

#### Scenario: Exportação com transações
- **WHEN** o cliente exporta o histórico de um clube com uma venda registrada
- **THEN** a API responde `200` com `Content-Type: text/csv` e uma linha de dados depois do
  cabeçalho, com os mesmos valores do histórico em JSON

#### Scenario: Exportação sem transações
- **WHEN** o cliente exporta o histórico de um clube sem transações
- **THEN** a API responde `200` com um CSV contendo só a linha de cabeçalho

#### Scenario: Nome do jogador com ponto e vírgula ou aspas é escapado
- **WHEN** a transação gravou o nome do jogador com `;` ou `"` no momento da operação
- **THEN** a linha do CSV traz o nome entre aspas duplas, com cada aspa interna duplicada

#### Scenario: Filtro inválido ou recurso inexistente
- **WHEN** o filtro é inválido, ou o clube ou o jogador do filtro não existem
- **THEN** a API responde com o mesmo código e `message` em JSON do histórico (`400` ou `404`)
