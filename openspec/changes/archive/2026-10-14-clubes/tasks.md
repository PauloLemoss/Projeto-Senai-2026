## 1. Banco de dados

- [x] 1.1 Criar `clubes/models.py` com a tabela `clubes` conforme "3. Estrutura de tabelas"
      (`nome`, `sigla`, `caixa` DECIMAL default 300.00, `formacao` nullable, `criado_em`), mais
      `nome_normalizado` (VARCHAR, não faz parte do enunciado, mas é a coluna que garante a RN10
      no banco) com índice único; `sigla` com índice único. Verificar com
      `alembic revision --autogenerate` detectando a tabela nova sem diffs espúrios.
- [x] 1.2 Migration adicionando a FK `jogadores.clube_id` → `clubes.id` (pendente desde
      `cadastro-jogadores`). Verificar com `alembic upgrade head` aplicando sem erro contra o
      banco de desenvolvimento (que não deve ter nenhum jogador com `clube_id` órfão) e
      `alembic downgrade base && alembic upgrade head` recriando do zero.

## 2. Validação da sigla

- [x] 2.1 Implementar `clubes/validacao.py::sigla_corresponde_ao_nome(nome, sigla) -> bool`
      (função pura, reaproveitando `normalizar_para_busca`). Verificar com testes unitários
      cobrindo os 3 cenários de recusa da spec (não começa pela primeira letra, três letras
      iguais, fora de ordem) e o caso de aceitação ("Águias FC" / "AGU").

## 3. Repositório e service

- [x] 3.1 Criar `clubes/repository.py` com `ClubeRepository` (`Protocol`: `obter`,
      `obter_por_nome_normalizado`, `obter_por_sigla`, `salvar`, `contar`, `listar`) e a
      implementação SQLAlchemy, usando o model `Clube` da task 1.1. Verificar com testes de
      integração contra o Postgres real: criar, obter por id, contar, e as duas buscas de
      unicidade.
- [x] 3.2 Criar um repositório de clubes fake (em memória) em `tests/conftest.py`, implementando
      o mesmo `Protocol`. Verificar com um teste de ida-e-volta.
- [x] 3.3 Implementar `clubes/service.py::ClubeService` com `cadastrar` (RN10: valida
      nome/sigla/unicidade/limite de 20, usando `sigla_corresponde_ao_nome`), `consultar`
      (monta o elenco chamando `jogador_repository.listar(FiltrosSql(club_id=...))` e
      `calculos.calcular_valor_de_mercado` de cada um) e `listar` (ordenação por nome ou
      patrimônio, com desempate). Recebe `ClubeRepository` e `JogadorRepository` por injeção.
      Verificar com testes unitários (repositórios fake) cobrindo cada `#### Scenario` das
      quatro requirements da spec `clubes`, incluindo a ordenação do elenco com `clube_id`
      atribuído manualmente nos dados de teste.

## 4. Schemas e router

- [x] 4.1 Criar `clubes/schemas.py` com `ClubeCreate` (valida nome e sigla, com
      `model_validator` chamando `sigla_corresponde_ao_nome`), `ClubeRead` (campos mínimos) e
      `ClubeComElencoRead` (adiciona `players`, sem o campo `contract` — ver design.md,
      Non-Goals). Verificar com testes unitários de schema cobrindo os limites de nome e sigla.
- [x] 4.2 Implementar os 3 endpoints em `clubes/router.py` (`POST /clubs`, `GET /clubs`,
      `GET /clubs/{id}`), incluído o parsing de `sort` (`name`, `net_worth_asc`,
      `net_worth_desc`). Verificar com `GET /docs` listando os 3 endpoints.
- [x] 4.3 Garantir `POST /clubs` com `201` e `Location`. Verificar com teste de integração.

## 5. Testes de integração de ponta a ponta

- [x] 5.1 Testes via `TestClient` cobrindo cada `#### Scenario` da spec `clubes` contra o
      Postgres real (criação, duplicidade de nome ignorando caixa, aceitar acento diferente,
      sigla duplicada, limite de 20 clubes, validação de sigla, listagem ordenada, consulta com
      elenco vazio, clube inexistente). Verificar rodando `poetry run pytest` com tudo passando.
- [x] 5.2 Medir a cobertura e fechar as lacunas que forem regra de negócio real, pelo mesmo
      critério das changes anteriores.

## 6. Documentação

- [x] 6.1 Atualizar o README: remover "Clubes" da lista de pendências e acrescentar uma decisão
      sobre a composição `ClubeService`/`JogadorRepository` e sobre o campo `contract` ainda não
      implementado.
