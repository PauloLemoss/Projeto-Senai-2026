## 1. Data e hora (RN01) e banco de dados

- [x] 1.1 Criar `core/datas.py` com a constante `FUSO_BRASILIA` (`timezone(timedelta(hours=-3))`,
      não `ZoneInfo`), `parsear_datetime_rn01(texto: str) -> datetime` (aceita só
      `AAAA-MM-DDTHH:MM-03:00`, recusa outro formato e data/hora inexistente) e
      `formatar_datetime_rn01(momento: datetime) -> str` (`AAAA-MM-DDTHH:MM:SS-03:00`). Verificar
      com testes unitários cobrindo os 5 scenarios da requirement nova de `api-conventions`
      (formato válido, sem offset, data inexistente, hora inexistente, formato de saída).
- [x] 1.2 Criar `mercado/models.py` com as tabelas `contratos` e `transacoes` conforme "3.
      Estrutura de tabelas", com as FKs para `jogadores.id` e `clubes.id` (sem
      `ON DELETE CASCADE`). Registrar os models em `alembic/env.py`. Verificar com
      `alembic revision --autogenerate` detectando as duas tabelas novas sem diffs espúrios, e
      `alembic upgrade head` / `alembic downgrade base && alembic upgrade head` aplicando sem
      erro.

## 2. Cálculos puros (RN13, RN15, RN16)

- [x] 2.1 Criar `mercado/calculos.py::calcular_taxa_de_compra(valor_de_mercado) -> Decimal` (RN13:
      5% quando maior que 30,00, senão 0,00) e `limite_de_compra(caixa) -> Decimal` (RN13: metade
      do caixa, sem arredondar). Verificar com testes cobrindo as 5 linhas da tabela de RN13 do
      enunciado.
- [x] 2.2 Criar `calcular_dias_restantes_e_percentual_de_multa(fidelidade_ate, momento) ->
      tuple[int, int]` (RN15) e `calcular_multa(valor_de_mercado, percentual) -> Decimal` (teto
      10,00). Verificar com testes cobrindo as linhas da tabela de RN15 (já passou, 10d2h, 30d,
      30d1min, 180d, 180d1min, 200d) e o teto de 10,00.
- [x] 2.3 Criar `calcular_comissao_de_venda(lucro) -> Decimal` (RN16: 10% até 10,00 de lucro + 20%
      acima, só se lucro > 0) e `calcular_credito_na_venda(valor, multa, comissao) -> Decimal`.
      Verificar com testes cobrindo as 6 linhas da tabela de comissão e as 5 linhas da tabela de
      venda de ponta a ponta (RN16) do enunciado.

## 3. Repositórios e unidade de trabalho

- [x] 3.1 Criar `mercado/repository.py` com `ContratoRepository` (`Protocol`:
      `obter_ativo_por_jogador`, `adicionar`) e `TransacaoRepository` (`Protocol`: `adicionar`,
      `existe_venda`, `listar_por_clube`), mais as implementações SQLAlchemy. `adicionar` SHALL só
      agendar a escrita (`session.add`), nunca comitar. Verificar com testes de integração contra
      o Postgres real: criar contrato, obter o ativo, marcar `encerrado_em`/`situacao` (via
      mutação direta, sem método de update dedicado), e `existe_venda` antes/depois de uma
      transação `VENDA`.
- [x] 3.2 Criar `UnidadeDeTrabalho` em `mercado/unidade_de_trabalho.py` (`Protocol`:
      `confirmar`, `desfazer`), implementada sobre a `Session` (`commit`/`rollback`). Criar
      repositórios fake de contrato e transação e uma unidade de trabalho fake (no-op) em
      `tests/conftest.py`. Verificar com um teste de ida-e-volta de cada fake.

## 4. Service

- [x] 4.1 Implementar `mercado/service.py::MercadoService.comprar` (RN12, RN13, RN14): valida
      jogador livre, clube existente, `club_id`/`loyalty_until` (via `core/datas.py`), calcula
      taxa e custo total, recusa acima do limite de 50% do caixa, recusa elenco com 12 jogadores
      (reaproveitando `jogador_repository.listar`), recusa recompra do próprio clube
      (`TransacaoRepository.existe_venda`); muta `jogador.clube_id` e `clube.caixa`, cria
      `Contrato` `ATIVO` e `Transacao` `COMPRA`, confirma pela `UnidadeDeTrabalho`. Recebe
      `JogadorRepository`, `ClubeRepository`, `ContratoRepository`, `TransacaoRepository` e
      `UnidadeDeTrabalho` por injeção. Verificar com testes unitários (repositórios fake)
      cobrindo cada `#### Scenario` da requirement "Compra de jogador livre com taxa e limite de
      caixa" e o de "Elenco com 12 jogadores".
- [x] 4.2 Implementar `MercadoService.vender` (RN15, RN16): calcula dias restantes e percentual de
      multa (`calcular_dias_restantes_e_percentual_de_multa`), lucro, comissão
      (`calcular_comissao_de_venda`) e crédito; muta `jogador.clube_id = None` e `clube.caixa`,
      atualiza o contrato ativo para `RESCINDIDO`/`ENCERRADO` (com `encerrado_em`), cria
      `Transacao` `VENDA`, confirma pela `UnidadeDeTrabalho`. Recusa jogador livre. Verificar com
      testes unitários cobrindo cada `#### Scenario` das requirements "Venda de jogador com multa
      por fidelidade" e "Comissão progressiva sobre o lucro da venda".
- [x] 4.3 Implementar `MercadoService.historico(clube_id, filtros) -> HistoricoDeTransacoes` (RN17):
      lista as transações do clube (mais recente primeiro, empate por id decrescente), aplica
      filtros `type`/`player_id`, monta o `summary` (5 totais). Verificar com testes unitários
      cobrindo cada `#### Scenario` da requirement "Histórico de transações do clube com filtros e
      totais".
- [x] 4.4 Implementar `MercadoService.exportar_csv(clube_id, filtros) -> str` (RN18), reaproveitando
      `historico` para os dados e o módulo `csv` da biblioteca padrão para a formatação
      (`delimiter=";"`, `quotechar='"'`, `lineterminator="\n"`). Verificar com testes unitários
      cobrindo cabeçalho, linha de dados, CSV vazio (só cabeçalho) e nome de jogador com `;`/aspas
      escapado.
- [x] 4.5 Modificar `clubes/service.py::ClubeService` para receber também um `ContratoRepository` e
      incluir `contract` (via `calcular_dias_restantes_e_percentual_de_multa`) em cada
      `JogadorComCalculados` do elenco montado por `_com_elenco`. Verificar com um teste unitário
      cobrindo o `#### Scenario` novo da requirement modificada de `clubes` ("Jogador do elenco
      mostra o contrato calculado na hora"), e que os testes já existentes de `ClubeService`
      continuam passando com um `ContratoRepository` fake sem contratos.

## 5. Schemas e router

- [x] 5.1 Criar `mercado/schemas.py` com `BuyRequest` (`club_id`, `loyalty_until` via
      `core/datas.py`, validando o intervalo "depois da compra e até 1.095 dias depois"),
      `TransactionRead` (campos da tabela "Campos da transação"), `TransactionHistoryResponse`
      (`data` + `summary`) e `TransactionListQuery` (`type` um-ou-mais, `player_id`). Mais dois
      schemas de resposta que ESTENDEM `TransactionRead` com campos extras só da operação, não
      gravados em `transacoes` — não confundir com o `contract` do elenco de `clubes` (task 5.2),
      que não tem `status`: `BuyRead` (+ `contract` aninhado com `purchase_value`,
      `loyalty_until`, `status` sempre `ATIVO`, e `club_cash`) e `SellRead` (+ `purchase_value`,
      `remaining_days`, `penalty_rate`, `contract_status`, `club_cash`, soltos, sem aninhar).
      Verificar com testes unitários de schema cobrindo os limites de `loyalty_until`, de `type`,
      e o formato de `BuyRead`/`SellRead` contra os exemplos 2.3.1/2.3.2 do enunciado.
- [x] 5.2 Atualizar `clubes/schemas.py::ClubeComElencoRead`/`JogadorRead` (ou um novo
      `JogadorDoElencoRead`) para incluir `contract` (`purchase_value`, `loyalty_until`,
      `remaining_days`, `penalty_rate`), usando `core/datas.py` para formatar `loyalty_until`.
      Verificar com teste unitário de schema.
- [x] 5.3 Implementar `POST /players/{id}/buy` e `POST /players/{id}/sell` em `mercado/router.py`.
      Verificar com `GET /docs` listando os 2 endpoints e um teste de integração de compra feliz
      (`200`, corpo conforme o exemplo 2.3.1 do enunciado).
- [x] 5.4 Implementar `GET /clubs/{id}/transactions` e `GET /clubs/{id}/transactions/export`
      (`Content-Type: text/csv` no segundo). Verificar com `GET /docs` listando os 2 endpoints.

## 6. Testes de integração de ponta a ponta

- [x] 6.1 Testes via `TestClient` cobrindo cada `#### Scenario` das requirements de compra da spec
      `mercado` contra o Postgres real (aceita abaixo do limite, custo igual ao limite, acima do
      limite, jogador não livre, elenco com 12, recompra pelo mesmo clube, outro clube pode
      comprar, jogador/clube inexistente, campo ausente, `club_id` inválido vs. inexistente,
      `loyalty_until` fora do formato/não futuro/acima de 1.095 dias), incluindo o formato da
      resposta (`contract` aninhado com `status`, `club_cash`). Verificar rodando
      `poetry run pytest` com tudo passando.
- [x] 6.2 Testes via `TestClient` cobrindo cada `#### Scenario` das requirements de venda e
      comissão da spec `mercado` contra o Postgres real (cada faixa de multa, teto de 10,00, venda
      de ponta a ponta com os valores do exemplo 2.3.2, lucro em duas faixas, prejuízo sem
      comissão, jogador livre recusado, jogador inexistente). Verificar rodando
      `poetry run pytest` com tudo passando.
- [x] 6.3 Testes via `TestClient` cobrindo cada `#### Scenario` das requirements de histórico e
      exportação CSV contra o Postgres real (sem filtro, filtro por `type`, filtro por
      `player_id` sem transações, filtro inválido, jogador/clube inexistente, conciliação do
      caixa, transações de jogador excluído mantidas, CSV com e sem transações, nome escapado).
      Verificar o CSV byte a byte (separador, LF, UTF-8 sem BOM).
- [x] 6.4 Teste via `TestClient` cobrindo o `#### Scenario` novo de `clubes` ("Jogador do elenco
      mostra o contrato calculado na hora"), reproduzindo os valores do exemplo 2.2.2 do
      enunciado (`cash` 261,15, `squad_value` 37,00, `contract.remaining_days` 120,
      `penalty_rate` 10) depois de uma compra real via `POST /players/{id}/buy`.

## 7. Cobertura

- [x] 7.1 Medir a cobertura e fechar as lacunas que forem regra de negócio real, pelo mesmo
      critério das changes anteriores.

## 8. Documentação

- [x] 8.1 Atualizar o README: remover "Mercado" da lista de pendências e acrescentar as decisões
      de `UnidadeDeTrabalho`, do fuso fixo de `core/datas.py` e do reaproveitamento de RN15 entre
      `mercado` e `clubes`.
