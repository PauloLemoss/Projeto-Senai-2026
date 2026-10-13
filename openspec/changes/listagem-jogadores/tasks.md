## 1. Banco de dados e repositório

- [x] 1.1 Migration adicionando índices em `jogadores`: `clube_id`, `posicao`, `condicao`, e um
      índice parcial em `excluido_em` (`WHERE excluido_em IS NULL`). Verificar com
      `alembic upgrade head` aplicando sem erro e `alembic downgrade base && alembic upgrade head`
      recriando do zero.
- [x] 1.2 Adicionar `listar(filtros: FiltrosSql) -> list[Jogador]` ao `Protocol
      JogadorRepository` e às implementações (SQLAlchemy e fake): aplica no SQL só os filtros de
      coluna direta (`position`, `condition`, `free`/`club_id`, faixa de idade) e sempre
      `excluido_em IS NULL`; não inclui busca por nome nem filtro de valor de mercado (ficam no
      service, em Python — ver design.md). Verificar com teste unitário do repositório fake e de
      integração do repositório real, incluindo um teste que cada filtro de coluna direta
      realmente restringe o resultado.

## 2. Cálculos e ordenação

- [x] 2.1 Expor a ordem fixa de posições (`GOL, ZAG, LAT, MEI, ATA`) a partir de
      `calculos.PESOS_POR_POSICAO.keys()` (ou constante equivalente), sem duplicar a lista em
      outro arquivo. Verificar com teste unitário conferindo a ordem exata.

## 3. Service: caso de uso de listagem

- [x] 3.1 Implementar `JogadorService.listar(filtros: FiltrosDeListagem) -> ListaDeJogadores`:
      chama `repository.listar()` com os filtros de coluna direta (SQL), depois em Python aplica
      busca por nome (ignorando acentos/caixa, reusando `core/validation.py`), calcula o valor de
      mercado de cada candidato (`calculos.calcular_valor_de_mercado`) pra aplicar
      `min_value`/`max_value`, ordena (até dois critérios, com `position` na ordem fixa e
      desempate final por nome e id) e pagina por último. Verificar com testes unitários
      (repositório fake) cobrindo cada `#### Scenario` do requirement de listagem e do de
      ordenação na spec `jogadores`.
- [x] 3.2 Cobrir a tabela de paginação do RN07 (23/10/1, 23/10/3, 23/10/4, 23/50/1, 0/10/1) com
      testes parametrizados. Verificar que `total_items` e `total_pages` batem exatamente com a
      tabela do enunciado.

## 4. Query params e resposta HTTP

- [x] 4.1 Criar `JogadorListQuery` (Pydantic) com todos os parâmetros de `GET /players`
      ("1. Filtros e query params aceitos"), incluindo o parser de `sort` (até dois critérios) e
      o `model_validator` das combinações contraditórias (`min_age`/`max_age`,
      `min_value`/`max_value`, `free=true` com `club_id`). Verificar com testes unitários de
      schema cobrindo os cenários de validação do requirement "Validação dos parâmetros" da spec.
- [x] 4.2 Criar `PlayerListResponse` (`data: list[JogadorRead]`, `meta: PaginationMeta`) e o
      mapeamento a partir de `ListaDeJogadores`. Verificar com teste unitário do mapeamento.
- [x] 4.3 Implementar `GET /players` no router, delegando ao service e devolvendo
      `PlayerListResponse`. Verificar com `GET /docs` listando o novo endpoint com os query
      params documentados.

## 5. Testes de integração de ponta a ponta

- [x] 5.1 Testes via `TestClient` cobrindo cada `#### Scenario` dos três requirements adicionados
      (listagem paginada, ordenação, validação de parâmetros) contra o Postgres real, com uma
      carga de jogadores variados criada no início de cada teste. Verificar rodando
      `poetry run pytest` com todos os testes passando.
- [x] 5.2 Medir a cobertura (`poetry run pytest --cov=mercado_jogadores --cov-report=term-missing`)
      e revisar linhas não cobertas do código novo desta change, fechando as lacunas que forem
      regra de negócio real (seguindo o mesmo critério usado em `cadastro-jogadores`: não forçar
      teste em código defensivo inalcançável).

## 6. Documentação

- [x] 6.1 Atualizar o README com o novo endpoint na lista de funcionalidades entregues (seção
      "Funcionalidades não implementadas" deixa de citar RN07). Verificar lendo o README depois
      da edição: a lista de pendências deve refletir só o que ainda falta (clubes, mercado, liga,
      frontend).
