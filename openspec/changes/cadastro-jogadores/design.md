## Context

Primeiro código do projeto: não existe backend ainda. Ver proposal.md para a motivação. As
specs (`api-conventions`, `jogadores`) definem o comportamento; este documento define como
implementá-lo em Python/FastAPI.

## Goals / Non-Goals

**Goals:**
- Estabelecer o esqueleto de camadas (router → service → repository) que todas as changes
  futuras (clubes, mercado, liga) vão seguir, sem retrabalho de arquitetura.
- Deixar o service layer testável sem banco (repositório fake), já com o primeiro teste
  automatizado real (cálculo de valor de mercado).
- Entregar algo rodável de ponta a ponta (API + Postgres via Docker Compose) mesmo sendo o
  primeiro change.

**Non-Goals:**
- Paginação/busca/filtros de `GET /players` (RN07) — change futura.
- Qualquer endpoint de clube, mercado ou liga.
- Frontend — fica para quando houver algo pra consumir.
- Autenticação (fora do escopo do projeto inteiro, ver Constituição).

## Decisions

### Estrutura de pastas do backend
```
backend/
├── pyproject.toml          # Poetry: dependências + poetry.lock
├── poetry.lock
├── .env.example
├── alembic/                 # migrations (criação/recriação do banco via README)
│   └── versions/
├── alembic.ini
├── src/
│   └── mercado_jogadores/
│       ├── main.py                    # cria o app FastAPI, inclui routers, CORS, exception handlers
│       ├── core/
│       │   ├── config.py              # Settings via pydantic-settings (lê .env)
│       │   ├── errors.py              # exceções de domínio (NotFoundError, ConflictError, ValidationError) + handlers
│       │   └── db.py                  # engine/session factory do SQLAlchemy
│       └── jogadores/
│           ├── router.py              # endpoints FastAPI, só valida (Pydantic) e chama o service
│           ├── schemas.py             # Pydantic: JogadorCreate, JogadorUpdate, CondicaoUpdate, JogadorRead
│           ├── models.py              # SQLAlchemy: tabela `jogadores`
│           ├── service.py             # regras de negócio: RN02–RN09, recebe repository por injeção
│           ├── repository.py          # Protocol (interface) + implementação SQLAlchemy
│           └── calculos.py            # funções puras: overall, valor_base, valor_de_mercado (Decimal)
└── tests/
    ├── conftest.py                     # fixtures: repositório fake, client de teste
    ├── unit/
    │   └── test_calculos.py           # testes do service com repositório fake (sem banco)
    └── integration/
        └── test_jogadores_api.py      # testes via TestClient + banco de teste (opcional nesta change)
```

**Por que separar `calculos.py` do `service.py`**: RN02–RN06 são funções matemáticas puras
(entrada → saída, sem efeito colateral). Isolá-las facilita testar exaustivamente contra as
tabelas de exemplo do enunciado sem precisar montar um jogador completo ou um repositório a cada
teste. O `service.py` orquestra (busca no repositório, chama `calculos.py`, decide o código de
erro); `calculos.py` não sabe de HTTP nem de banco.

### Repository como `Protocol`, não ABC
```python
class JogadorRepository(Protocol):
    def obter(self, jogador_id: int) -> Jogador | None: ...
    def salvar(self, jogador: Jogador) -> Jogador: ...
    def excluir_logicamente(self, jogador_id: int, momento: datetime) -> None: ...
```
Alternativa considerada: `abc.ABC` com métodos abstratos. Optei por `Protocol` (PEP 544,
structural typing) porque não precisamos de uma classe-base compartilhada nem de registro
explícito — o repositório fake de teste só precisa ter os mesmos métodos, sem herdar de nada.
Isso é o DIP da Constituição aplicado da forma mais simples possível em Python.

### Decimal em toda a camada de cálculo e persistência
Todos os campos de moeda (`valor_base`, `market_value` na resposta) usam `decimal.Decimal`,
nunca `float`. Arredondamento usa `Decimal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` —
`ROUND_HALF_UP` do módulo `decimal` arredonda o `.5` para longe do zero em valores positivos
(coincide com a regra do enunciado), diferente do `round()` nativo do Python (banker's rounding).
Alternativa considerada: inteiro em centavos. Rejeitada para Postgres (não é SQLite) — `NUMERIC`
já guarda sem perda de precisão, então converter para centavos só adicionaria complexidade sem
necessidade (a conversão para centavos é exigida pelo enunciado só quando o banco é SQLite).

### Exceções de domínio mapeadas por um exception handler central
`service.py` levanta `NaoEncontradoError`, `ConflitoError` ou `RequisicaoInvalidaError` (definidas
em `core/errors.py`); um `@app.exception_handler` em `main.py` traduz cada uma para o status HTTP
(404/409/400) e monta o corpo `{"message": ...}`. O router nunca captura exceção nem monta
resposta de erro — isso é o que a Constituição chama de "tratamento central de erros" (critério
B2 do barema).

### Migrations com Alembic
Alternativa considerada: deixar o SQLAlchemy criar as tabelas com `Base.metadata.create_all()` no
startup. Rejeitada porque o README precisa de um comando explícito de "recriar o banco do zero"
(exigência do barema, B3 "Criação reprodutível") — Alembic dá isso de graça (`alembic upgrade
head` / `downgrade base` + `upgrade head`), e documenta o histórico de mudanças do schema à
medida que outras capabilities (clubes, contratos, etc.) forem adicionando tabelas.

## Risks / Trade-offs

- **[Risco] Arredondamento divergente entre `Decimal` e o que o enunciado espera em casos de
  "meio" exato** → Mitigação: todo caso de "meio exato" das tabelas do enunciado (RN06: 72,50 →
  73; RN06 valor base: 3,625 → 3,63) vira um teste unitário de `calculos.py` nomeado pelo valor
  exato, antes de qualquer outra regra ser implementada.
- **[Risco] `Protocol` do Python não impõe implementação em tempo de execução (só type-checking
  estático)** → Mitigação: cobertura de teste do repositório fake e do repositório real contra o
  mesmo conjunto de testes de contrato (reexecutar os testes do service com os dois repositórios)
  fica registrada como tarefa de melhoria futura, não bloqueia esta change.
- **[Risco] Alembic adiciona uma ferramenta a mais para o avaliador (júnior fora do time)
  entender** → Mitigação: README documenta o comando exato (`alembic upgrade head`,
  `alembic downgrade base && alembic upgrade head` para recriar), testado literalmente como a
  banca vai executar.

## Migration Plan

Não aplicável — não há dado em produção nem versão anterior do sistema. A primeira migration do
Alembic cria a tabela `jogadores` do zero.
