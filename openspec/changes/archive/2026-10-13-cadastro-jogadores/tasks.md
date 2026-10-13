## 1. Setup do backend

- [x] 1.1 Inicializar `backend/` com Poetry (`poetry init` ou `pyproject.toml` manual) fixando
      Python `^3.12`; adicionar `fastapi^0.143.0`, `uvicorn`, `sqlalchemy^2`, `psycopg[binary]`,
      `pydantic-settings`, `alembic`; em dev: `pytest`, `pytest-asyncio`, `httpx`, `ruff`. Verificar
      com `poetry install` concluindo sem erro e `poetry.lock` sendo gerado.
- [x] 1.2 Criar `docker-compose.yml` na raiz do monorepo subindo só o Postgres (serviço `db`), com
      variáveis via `.env`/`.env.example`. Verificar com `docker compose up -d db` seguido de
      `docker compose ps` mostrando o serviço saudável.
- [x] 1.3 Configurar Alembic (`alembic init`) apontando para a `DATABASE_URL` do `.env`. Verificar
      com `alembic current` rodando sem erro contra o banco subido na tarefa 1.2.
- [x] 1.4 Criar o esqueleto de pastas de `src/mercado_jogadores/` (`core/`, `jogadores/`) descrito
      em design.md. Verificar com `poetry run python -c "import mercado_jogadores"` sem erro.

## 2. Convenções da API (capability `api-conventions`)

- [x] 2.1 Criar `core/errors.py` com as exceções de domínio (`NaoEncontradoError`,
      `ConflitoError`, `RequisicaoInvalidaError`). Verificar com um teste unitário que cada uma
      carrega a `message`.
- [x] 2.2 Registrar exception handlers em `main.py` traduzindo cada exceção para 404/409/400 com
      corpo `{"message": ...}` e `Content-Type: application/json`. Verificar com um teste de
      integração que dispara cada exceção a partir de uma rota de teste e confere o status e o
      corpo.
- [x] 2.3 Configurar handler para corpo que não é objeto JSON (array, string, número) responder
      `400` (sobrescrevendo o handler default do FastAPI para `RequestValidationError` quando
      necessário). Verificar com teste de integração enviando `[]`, `"x"` e `10` como corpo de
      `POST /players` e conferindo `400` em todos.
- [x] 2.4 Implementar função utilitária de normalização de texto (trim + colapso de espaços,
      rejeição de caracteres de controle) reutilizável por qualquer schema Pydantic de texto livre.
      Verificar com teste unitário cobrindo os cenários da spec `api-conventions`
      (`"  Meia   Zeta "` → `"Meia Zeta"`; caractere de tabulação → erro).
- [x] 2.5 Configurar CORS (`CORSMiddleware`) restrito à origem do frontend, lida de variável de
      ambiente (nunca `*`). Verificar com teste de integração conferindo o cabeçalho
      `Access-Control-Allow-Origin` na origem configurada.

## 3. Modelo de dados e migration (`jogadores`)

- [x] 3.1 Criar `jogadores/models.py` com a tabela `jogadores` conforme "3. Estrutura de tabelas"
      do enunciado (`nome`, `posicao`, `agilidade`, `idade`, `valor_base` DECIMAL, `condicao`,
      `clube_id`, os seis atributos, `potencial`, `excluido_em`, `criado_em`, `atualizado_em`).
      Verificar com `alembic revision --autogenerate` detectando a tabela sem diffs espúrios.
- [x] 3.2 Gerar e aplicar a migration inicial. Verificar com `alembic upgrade head` criando a
      tabela no Postgres de desenvolvimento, e `alembic downgrade base && alembic upgrade head`
      recriando do zero sem erro (isso vira o comando de "recriar o banco" do README).

## 4. Cálculos puros (RN02–RN06)

- [x] 4.1 Implementar `jogadores/calculos.py::calcular_overall(atributos, posicao) -> int` com a
      tabela de pesos por posição. Verificar com teste unitário cobrindo as 5 linhas da tabela de
      exemplo do RN06 (MEI→73, ATA→76, LAT→72, ZAG→73 com meio-pra-cima, GOL→68).
- [x] 4.2 Implementar `calcular_valor_base(overall, potential, idade_cadastro) -> Decimal` (partes
      progressivas + jovem promessa + piso). Verificar com teste unitário cobrindo as 9 linhas da
      tabela de exemplo do RN06, incluindo o caso de meio-pra-longe-do-zero (3,625 → 3,63) e o
      piso (40/66/36 → 1,00).
- [x] 4.3 Implementar `calcular_valor_de_mercado(valor_base, condicao, agilidade, idade) ->
      Decimal` (RN02 a RN05, com teto de −40% e piso de 1,00). Verificar com teste unitário
      cobrindo as 10 linhas da tabela de exemplo do RN05 — **este é o teste exigido pelo
      diferencial técnico B5 do barema**.
- [x] 4.4 Confirmar que o arredondamento usa `Decimal` com `ROUND_HALF_UP` (nunca `round()`
      nativo nem `float`). Verificar com um teste dedicado ao caso de empate exato (`14,775` →
      `14,78`, para longe do zero).

## 5. Repositório e service (`jogadores`)

- [x] 5.1 Definir `jogadores/repository.py::JogadorRepository` como `Protocol` (métodos: obter,
      listar_por_id, salvar, excluir_logicamente) e sua implementação SQLAlchemy. Verificar com
      `mypy`/type-checking passando (ou, na ausência de mypy configurado, com um teste de
      integração exercitando a implementação contra o Postgres de teste).
- [x] 5.2 Criar um repositório fake (dicionário em memória) em `tests/conftest.py`, implementando
      o mesmo `Protocol`. Verificar com um teste simples de ida-e-volta (salvar + obter).
- [x] 5.3 Implementar `jogadores/service.py` com as operações: cadastrar, consultar, editar,
      alterar_condicao, excluir — cada uma recebendo o repositório por injeção (construtor),
      nunca importando SQLAlchemy. Cobrir: RN06 no cadastro, RN08 na edição (posição/idade),
      transição de condição (DOENTE→APTO recusado), RN09 na exclusão. Verificar com testes
      unitários do service usando o repositório fake da tarefa 5.2 para cada cenário das specs
      `jogadores` (edição recusada por posição, por idade, condição DOENTE→APTO, exclusão de
      jogador com clube).

## 6. Schemas e router (API HTTP)

- [x] 6.1 Criar `jogadores/schemas.py` com `JogadorCreate`, `JogadorUpdate`, `CondicaoUpdate` e
      `JogadorRead` (Pydantic v2), aplicando os limites de campo da spec `jogadores` e a
      normalização de texto da tarefa 2.4. Verificar com testes unitários de schema cobrindo os
      limites (nome < 3 chars, atributo fora de 1–99, soma > 480).
- [x] 6.2 Implementar `jogadores/router.py` com os 5 endpoints (`POST /players`,
      `GET /players/{id}`, `PUT /players/{id}`, `PATCH /players/{id}/condition`,
      `DELETE /players/{id}`), cada handler só chamando o service e devolvendo o schema de
      resposta. Verificar com `GET /docs` (Swagger) listando os 5 endpoints corretamente.
- [x] 6.3 Garantir que `POST /players` responde `201` com header `Location` e que `DELETE
      /players/{id}` responde `204` sem corpo. Verificar com teste de integração conferindo
      status e headers.
- [x] 6.4 Testes de integração de ponta a ponta (via `TestClient`/`httpx`) para cada cenário das
      duas specs desta change (`api-conventions` e `jogadores`): pelo menos um teste por
      `#### Scenario` escrito. Verificar rodando `poetry run pytest` e conferindo que todos
      passam.

## 7. Documentação

- [x] 7.1 Preencher o `README.md` da raiz com os itens 1 a 3 (pré-requisitos com versão exata:
      Python 3.12, Poetry, Docker; criação/recriação do banco via Alembic; passo a passo de
      instalar e rodar o backend) cobrindo só o que esta change entrega. Verificar seguindo os
      comandos do zero numa pasta limpa e confirmando que a API sobe e responde em `/docs`.
- [x] 7.2 Criar `.env.example` com as variáveis usadas (`DATABASE_URL`, origem do CORS).
      Verificar que `cp .env.example .env` seguido dos comandos do item 7.1 funciona sem edição
      manual de valores.
