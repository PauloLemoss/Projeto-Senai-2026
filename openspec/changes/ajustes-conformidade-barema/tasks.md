## 1. GET /players com club_id inexistente → 404 (jogadores)

- [x] 1.1 Injetar `ClubeRepository` em `JogadorService.__init__` e validar `filtros.club_id` em
      `listar()` (levantar `NaoEncontradoError` quando o clube não existir), antes de montar
      `FiltrosSql`; atualizar `jogadores/router.py` (`get_jogador_service`) para injetar
      `SQLAlchemyClubeRepository` — verificar rodando `poetry run poe test` (suíte inteira ainda
      passa, nenhum teste quebrado pela mudança de assinatura do construtor).
- [x] 1.2 Adicionar teste unitário (service, com `FakeClubeRepository`) e teste de integração
      (`GET /players?club_id=<inexistente>` → `404` com `message`) cobrindo o scenario novo da
      spec `jogadores` — verificar que os dois testes novos passam e que o caso de `club_id`
      existente continua `200` com os jogadores do elenco.

## 2. Validação estrita de club_id/home_club_id/away_club_id (api-conventions, mercado, liga)

- [x] 2.1 Trocar `BuyRequest.club_id: int` por `InteiroEstrito` em `mercado/schemas.py` (import de
      `jogadores.schemas`, mesmo padrão já usado por `liga/schemas.py`) — verificar com um teste
      que `POST /players/{id}/buy` com `{"club_id": "1", ...}` responde `400`.
- [x] 2.2 Trocar `MatchCreate.home_club_id`/`away_club_id: int` por `InteiroEstrito` em
      `liga/schemas.py` — verificar com um teste que `POST /matches` com `home_club_id` ou
      `away_club_id` como string responde `400`.
- [x] 2.3 Rodar a suíte completa (`poetry run poe test`) e conferir que nenhum teste existente
      dependia da coerção implícita de string para os três campos (se algum depender, corrigir o
      teste para enviar o tipo certo, não reverter a validação).

## 3. Registro de logs por requisição (diferenciais-tecnicos)

- [x] 3.1 Adicionar `structlog` como dependência de produção (`poetry add structlog`) — verificar
      que `poetry.lock` é atualizado e `poetry install` roda sem erro.
- [x] 3.2 Configurar o `structlog` (processors incluindo `TimeStamper` com formato legível,
      renderer de console) uma vez, antes da criação do `FastAPI()` em `main.py` (extrair para
      `core/logging.py` se `main.py` ficar poluído) — verificar lendo a configuração no código.
- [x] 3.3 Adicionar um middleware HTTP que loga, depois de cada requisição, uma linha com
      `method`, `path` e `status` — verificar manualmente: subir a aplicação
      (`docker compose up -d` ou `poe dev`), fazer uma requisição (`GET /api/v1/players`) e
      conferir no `docker compose logs api` (ou saída do terminal) que aparece uma linha com
      data/hora legível, método, caminho e status.

## 4. Lint e verificação de formatação (diferenciais-tecnicos)

- [x] 4.1 Adicionar a task `format-check = "ruff format --check ."` em
      `backend/pyproject.toml` (`[tool.poe.tasks]`), sem alterar a task `format` existente —
      verificar rodando `poetry run poe format-check` sobre o código já formatado: termina com
      código `0` e nenhum arquivo é alterado (`git status` limpo antes e depois).
- [x] 4.2 Atualizar o README (seção de testes/diferenciais) para citar `poe format-check` como o
      comando de verificação de formatação e `poe lint` como o comando de lint — verificar lendo
      o README atualizado.

## 5. Fechamento

- [x] 5.1 Rodar a suíte completa uma última vez com o banco subido
      (`docker compose up -d db && poetry run poe migrate && poetry run poe test`) e `poetry run
      poe lint`/`poetry run poe format-check` — verificar que tudo passa (0 erros, 0 arquivos
      alterados pelo format-check).
- [x] 5.2 Rebuildar e subir a imagem Docker (`docker compose up -d --build`) e conferir que
      `docker compose ps` mostra `api` `(healthy)` e que uma requisição real gera uma linha de log
      com timestamp/método/caminho/status na saída do contêiner.
