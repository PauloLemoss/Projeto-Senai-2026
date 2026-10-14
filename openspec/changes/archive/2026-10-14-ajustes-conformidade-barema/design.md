## Context

Ver `proposal.md` - Why para a motivação (auditoria contra o enunciado/barema). Estado atual
relevante, confirmado lendo o código:

- `JogadorService.__init__` (`jogadores/service.py:107`) recebe `JogadorRepository`,
  `EscalacaoRepository` e `UnidadeDeTrabalho` — nenhuma dependência de `clubes`.
  `JogadorService.listar()` (linha 192) passa `filtros.club_id` direto pro `FiltrosSql` do
  repository, sem checar existência. `ClubeRepository.obter(clube_id) -> Clube | None`
  (`clubes/repository.py:12`) já existe e é exatamente o que falta injetar.
- O validador estrito de inteiro de corpo (V2/V3) já existe: `_validar_inteiro_json` e o tipo
  `InteiroEstrito = Annotated[int, BeforeValidator(_validar_inteiro_json)]`, definidos em
  `jogadores/schemas.py:39-53`. `liga/schemas.py` já importa `InteiroEstrito` de lá para
  `IdDeJogador` (`player_ids` da escalação). `BuyRequest.club_id` (`mercado/schemas.py:38`) e
  `MatchCreate.home_club_id`/`away_club_id` (`liga/schemas.py:76-77`) ainda usam `int` puro do
  Pydantic, que coage `"1"` → `1` silenciosamente em vez de recusar.
- `clubes/router.py` já compõe `ClubeService` com `SQLAlchemyJogadorRepository` importado de
  `jogadores.repository` (mesmo padrão de composição entre módulos que esta change replica, na
  direção oposta, em `jogadores/router.py`).
- Hoje não há nenhum logging próprio da aplicação: só a saída padrão do Uvicorn, sem timestamp.
- `pyproject.toml` (`[tool.poe.tasks]`) tem `format = "ruff format ."`, que altera arquivos; não
  existe nenhuma task de só-verificação.

## Goals / Non-Goals

- **Goal**: fechar os 3 gaps de comportamento observável (404 de `club_id`, tipo estrito nos 3
  campos, log por requisição) e o gap de tooling (format --check), sem mudar nenhum outro
  comportamento já correto.
- **Goal**: reaproveitar o que já existe (`InteiroEstrito`, `ClubeRepository`, o padrão de
  composição entre services) em vez de duplicar lógica de validação.
- **Non-goal**: não migrar o logging de requisições do Uvicorn para substituí-lo por completo;
  o objetivo é garantir que **existe** uma linha com timestamp/método/caminho/status por
  requisição, não reformatar toda a saída da aplicação.
- **Non-goal**: não mover `InteiroEstrito`/`core/validation.py` numa refatoração maior de módulo
  agora (ver "Decisions" abaixo) — risco maior que o benefício para o escopo desta change.

## Decisions

### 1. `JogadorService` ganha `ClubeRepository` como dependência nova (composição, não herança)
Mesmo padrão já usado por `ClubeService` (que recebe `JogadorRepository`): `JogadorService.listar()`
passa a checar `self._clubes.obter(filtros.club_id)` quando `filtros.club_id` não é `None`, e
levanta `NaoEncontradoError` se vier `None` — antes de montar `FiltrosSql` ou tocar no repositório
de jogadores. `jogadores/router.py` passa a importar `SQLAlchemyClubeRepository` de
`clubes.repository` e injetá-lo em `get_jogador_service`, assim como `clubes/router.py` já faz o
inverso.

**Alternativa considerada e rejeitada**: validar a existência do clube dentro do
`SQLAlchemyJogadorRepository.listar()` via um `JOIN`/subquery contra a tabela `clubes`. Rejeitada
porque o repository não deve decidir "existe ou não" como regra (isso é decisão do service, igual
a todo outro 404 do projeto), e porque um fake de teste do repository de jogadores não tem acesso
à tabela de clubes.

### 2. Reaproveitar `InteiroEstrito` de `jogadores/schemas.py` nos 3 campos, sem mover o código
`mercado/schemas.py` passa a importar `InteiroEstrito` de `jogadores.schemas` (mesmo import que
`liga/schemas.py` já faz) e troca `club_id: int = Field(...)` por
`club_id: InteiroEstrito = Field(...)`. `liga/schemas.py` troca `home_club_id`/`away_club_id: int`
pelo mesmo tipo.

**Alternativa considerada e rejeitada**: mover `_validar_inteiro_json`/`InteiroEstrito` para
`core/validation.py` (que já tem o docstring "compartilhado por toda a API"), eliminando o
cross-import de `liga`/`mercado` para dentro de `jogadores`. Seria mais correto a longo prazo, mas
troca import em 3 arquivos e tira o tipo do único lugar hoje testado — fora do escopo mínimo desta
correção. Fica registrado aqui como dívida técnica para uma change futura, não para agora.

### 3. Logging: `structlog`, configurado uma vez, com um middleware HTTP
Biblioteca nova (`structlog`, dependência de produção, não de dev) em vez de configurar o
`logging` padrão na mão: `structlog` já resolve timestamp + formatação legível de forma madura,
com uma chamada de configuração (`structlog.configure(...)`) e sem precisar escrever um
`logging.Formatter` customizado à mão. Formato de saída: texto legível (console), não JSON — o
requisito do barema é "legíveis", não "estruturados para agregador".

Implementação: um middleware HTTP do FastAPI (`@app.middleware("http")`) em `main.py` (ou
extraído para um módulo pequeno, ex. `core/logging.py`, se `main.py` ficar poluído) que, depois de
`call_next(request)`, loga uma linha com `method`, `path` e `status`; o `TimeStamper` do structlog
já inclui o timestamp automaticamente em cada linha. A configuração do structlog (processors,
formato, nível) roda uma vez, antes da criação do `FastAPI()`.

**Alternativa considerada e rejeitada**: configurar só o `logging.Formatter` padrão do Python.
Mais barato em dependência, mas o código de formatação (padding, cores opcionais, timestamp)
fica mais verboso para o mesmo resultado; como o projeto já aceita bibliotecas maduras para
outros diferenciais (ex. `ruff`), `structlog` é consistente com essa escolha.

**Decisão sobre o access log do próprio Uvicorn**: mantido como está (não desativado). O
requisito do barema pede que **exista** uma linha com timestamp/método/caminho/status por
requisição — não proíbe uma segunda linha adicional do Uvicorn sem timestamp coexistindo. Desativar
o access log do Uvicorn (`--no-access-log`) é cosmético, não necessário para atender ao requisito,
e fica fora do escopo mínimo desta correção.

### 4. Task `format-check` nova, task `format` sem mudança
`[tool.poe.tasks]` ganha `format-check = "ruff format --check ."`, sem alterar a task `format`
existente (que continua sendo o comando que *aplica* a formatação, útil no dia a dia). O README
passa a apontar `poe format-check` como o comando de "verificação de formatação" do diferencial
B5, e `poe lint` continua sendo o comando de lint.

## Risks / Trade-offs

- [Risco] Injetar `ClubeRepository` em `JogadorService` muda a assinatura pública do construtor →
  [Mitigação] é construído só via `get_jogador_service` (DI do FastAPI) e em testes via
  instanciação direta; os testes unitários existentes de `JogadorService` precisam passar a
  instanciar com um `FakeClubeRepository` novo (mesmo padrão dos fakes já existentes no projeto).
- [Risco] Nova dependência de produção (`structlog`) → [Mitigação] é uma lib madura e amplamente
  usada no ecossistema Python para exatamente esse problema; impacto de build é mínimo (pure
  Python, sem binário nativo).
- [Risco] Mudar `BuyRequest.club_id`/`MatchCreate.home_club_id`/`away_club_id` de `int` para
  `InteiroEstrito` pode quebrar algum teste existente que envia `club_id` como string esperando
  sucesso → [Mitigação] rodar a suíte completa depois da mudança; se algum teste hoje depende da
  coerção implícita, o teste está testando o comportamento errado (contrário ao V2 do enunciado) e
  deve ser corrigido, não a mudança revertida.

## Migration Plan

Mudança aditiva/corretiva em código já em produção interna (projeto ainda não entregue à banca) —
sem dado de usuário real, sem necessidade de migration de banco, sem rollback especial além de
reverter o commit caso algum teste quebre inesperadamente.

## Open Questions

Nenhuma — todas as decisões técnicas relevantes para implementar foram fechadas acima.
