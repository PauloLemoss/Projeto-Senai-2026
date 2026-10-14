# Mercado de Jogadores

Estudo de caso SENAI/PE – CÓD. 237 DESENVOLVEDOR I (FULLSTACK).

> O frontend ainda não foi implementado (change futura). Este README cobre, por enquanto, só o
> backend, que já tem os 4 módulos completos: cadastro, consulta, edição, alteração de condição,
> exclusão lógica e listagem paginada (com busca, filtros e ordenação) de jogadores; cadastro,
> listagem ordenável e consulta (com elenco, valor do elenco e patrimônio) de clubes; compra,
> venda, histórico de transações e exportação em CSV (mercado); e escalação de titulares,
> partidas com placar calculado pelos atributos dos jogadores, histórico de partidas e
> classificação da liga (liga).

## Estrutura

- `backend/` — API REST (Python + FastAPI)
- `frontend/` — Interface (React) — ainda não implementada
- `openspec/` — Especificações (SDD, via [OpenSpec](https://github.com/Fission-AI/OpenSpec)) que guiam a implementação

## 1. Pré-requisitos

Há dois jeitos de rodar a aplicação — escolha um:

| Jeito | O que precisa instalar |
| --- | --- |
| **Docker (recomendado)** | Só Docker + Docker Compose. A API e o Postgres rodam inteiramente em contêiner; não precisa instalar Python nem Poetry na máquina. |
| **Local (Poetry)** | Python 3.12, [Poetry](https://python-poetry.org) 2.5+, e Docker + Docker Compose (só para o Postgres, que continua em contêiner nos dois casos). |

| Ferramenta | Versão usada no desenvolvimento |
| --- | --- |
| Python | 3.12 |
| [Poetry](https://python-poetry.org) | 2.5 |
| Docker + Docker Compose | Docker 29, Compose v2 |

Funciona em Linux, macOS e Windows (via WSL2, que é o jeito recomendado de rodar Docker no
Windows). O Postgres sempre roda em contêiner, nos dois jeitos acima — não precisa instalar
localmente.

## 2. Criar e recriar o banco de dados

O banco é gerenciado por migrations do [Alembic](https://alembic.sqlalchemy.org), versionadas em
`backend/alembic/versions/`.

> Rodando via Docker (seção 3, opção A)? Pode pular esta seção — o contêiner `api` roda
> `alembic upgrade head` sozinho toda vez que sobe.

```bash
# Na raiz do repositório: sobe o Postgres
docker compose up -d db

# Na pasta backend: cria as tabelas
cd backend
poetry run poe migrate
```

Para recriar o banco do zero (apagar e criar de novo):

```bash
# Na pasta backend
poetry run poe migrate-reset
```

O banco criado por esses passos começa vazio, sem jogadores.

## 3. Instalar e executar

### Opção A: Docker (recomendado — API e Postgres em contêiner)

```bash
# Na raiz do repositório
cp .env.example .env
cp backend/.env.example backend/.env
docker compose up -d --build
# API em http://localhost:8000 (o script da banca acrescenta /api/v1)
# Documentação interativa (Swagger) em http://localhost:8000/docs
```

O contêiner `api` espera o Postgres ficar saudável, aplica as migrations (`alembic upgrade head`)
e só então sobe o Uvicorn — não precisa nenhum passo manual além do `docker compose up`. Para
reconstruir a imagem depois de alterar dependências (`pyproject.toml`), rode o mesmo comando de
novo (o `--build` força o rebuild).

Parar tudo: `docker compose down` (os dados do Postgres ficam no volume `db_data`; para apagar
também o volume, `docker compose down -v`).

**Como saber se subiu tudo certo:** `docker compose ps` mostra `(healthy)` ao lado do contêiner
`api` quando a aplicação está de pé *e* conectando no banco (não só o processo rodando) — isso
usa o endpoint `GET /health`, que faz um `SELECT 1` real no Postgres a cada checagem. Enquanto
estiver `(unhealthy)` ou sem essa coluna, a API ainda não está pronta para receber requisições.

### Opção B: Local com Poetry (API fora de contêiner, Postgres em contêiner)

```bash
# Banco de dados (na raiz do repositório)
cp .env.example .env
docker compose up -d db

# Backend (na pasta backend)
cd backend
cp .env.example .env
poetry install
poetry run poe migrate
poetry run poe dev
# API em http://localhost:8000 (o script da banca acrescenta /api/v1)
# Documentação interativa (Swagger) em http://localhost:8000/docs
```

O frontend ainda não existe nesta entrega.

### Rodar os testes

As tasks abaixo usam o [poethepoet](https://poethepoet.natn.io) (`poe`), que roda igual em
Linux, macOS e Windows — os comandos `poetry run poe <task>` dispensam `make` ou qualquer outra
ferramenta além do próprio Poetry.

```bash
# Na pasta backend, com o banco subido (docker compose up -d db) e migrado
# (poetry run poe migrate) — os testes de integração usam o Postgres real
cd backend
poetry run poe test          # roda a suíte inteira (unit + integration)
poetry run poe test-cov      # idem, com relatório de cobertura
poetry run poe lint          # ruff check
poetry run poe format        # ruff format
```

Lista completa de tasks disponíveis em `backend/pyproject.toml` (seção `[tool.poe.tasks]`):
`install`, `dev`, `test`, `test-cov`, `lint`, `format`, `migrate`, `migrate-reset`, `db-up`,
`docker-up`, `docker-down`.

## 4. Variáveis de ambiente

Dois arquivos `.env.example`, cada um na pasta do serviço que o usa:

- **`/.env.example`** (raiz): credenciais do Postgres, lidas pelo `docker-compose.yml`.
- **`backend/.env.example`**: `DATABASE_URL` (string de conexão do backend com o Postgres acima)
  e `CORS_ORIGIN` (origem do frontend liberada no CORS).

As portas e credenciais padrão (porta `5433` para o Postgres, em vez da `5432` padrão) evitam
colisão com outros serviços que já possam estar rodando na máquina; não há necessidade de mudar
nada para a aplicação funcionar.

> **Nota (Docker):** o `DATABASE_URL` de `backend/.env` aponta para `localhost:5433` (pensado para
> a API rodar fora de contêiner, opção B). Dentro da rede do `docker-compose.yml` esse host não
> existe; por isso o serviço `api` sobrescreve `DATABASE_URL` para apontar ao serviço `db` na
> porta interna `5432` — isso é automático, não precisa editar nada à mão.

## 5. Estrutura e bibliotecas (backend)

```
backend/
├── Dockerfile            # build multi-stage (Poetry) da imagem da API
├── alembic/              # migrations do banco
├── src/mercado_jogadores/
│   ├── core/             # config, sessão do banco, exceções de domínio, validações comuns,
│   │                     # unidade_de_trabalho (operações atômicas, reaproveitada por
│   │                     # jogadores/mercado/liga)
│   ├── jogadores/        # capability "jogadores": models, schemas, service, repository, router
│   ├── clubes/           # capability "clubes": models, schemas, service, repository, router
│   ├── mercado/          # capability "mercado": models, schemas, service, repository, router
│   │                     # e calculos (RN13/15/16)
│   └── liga/             # capability "liga": models, schemas, service, repository, router e
│                         # calculos (RN19/20: formação, duelos, placar)
└── tests/
    ├── unit/             # cálculos, schemas e service, sem banco (repositório fake)
    └── integration/      # endpoints HTTP via TestClient, contra o Postgres real
```

Bibliotecas além da stack obrigatória do enunciado, com o motivo de cada uma:

| Biblioteca | Motivo |
| --- | --- |
| `pydantic-settings` | Carrega as variáveis de ambiente (`.env`) de forma tipada e validada. |
| `alembic` | Migrations do banco — criação e recriação reprodutíveis (exigência do README). |
| `psycopg[binary]` | Driver do PostgreSQL para o SQLAlchemy. |
| `pytest-asyncio` | Suporte a testes assíncronos do pytest (usado pela suíte de testes do FastAPI). |
| `httpx` | Cliente HTTP usado pelo `TestClient` do FastAPI nos testes de integração. |
| `ruff` | Lint e formatação do backend (diferencial técnico). |
| `poethepoet` | Executa as tasks (`poetry run poe test`, `poe lint`, `poe migrate`, etc.) — alternativa a um Makefile que roda igual em Linux/macOS/Windows, sem depender de `make` estar instalado. |

## 6. Decisões e premissas

- **Arquitetura em camadas** (Router → Service → Repository): o service nunca importa
  SQLAlchemy diretamente, só a abstração `JogadorRepository` (um `Protocol`), para poder ser
  testado com um repositório fake, sem banco.
- **`ClubeService` compõe com `JogadorRepository`**, em vez de o `ClubeRepository` fazer um JOIN
  direto `clubes`/`jogadores`: para montar o elenco e o `squad_value` de um clube, o service
  reaproveita `jogador_repository.listar(FiltrosSql(club_id=...))`, o mesmo método que a
  capability `jogadores` já construiu e testou para a listagem (RN07), em vez de duplicar essa
  busca. O cálculo de `overall` e `market_value` de cada jogador também é reaproveitado (função
  `calcular_indicadores`, extraída de `JogadorService` para uso dos dois services).
- **Operações compostas (compra e venda) são atômicas via uma `UnidadeDeTrabalho`**: em vez de
  cada `Repository.salvar()` comitar sozinho (o que permitiria um estado parcial se uma escrita
  seguinte falhasse), `MercadoService.comprar`/`vender` mutam `Jogador`/`Clube` diretamente (já
  anexados à mesma `Session`), agendam `Contrato`/`Transacao` via `adicionar()` (sem comitar), e
  só no fim chamam uma `UnidadeDeTrabalho` (`Protocol` com `confirmar`/`desfazer`) que comita ou
  desfaz tudo de uma vez — sem precisar mudar a interface já testada de `jogadores`/`clubes`.
- **Data e hora (RN01): fuso fixo, não biblioteca de timezone**: `core/datas.py` usa
  `timezone(timedelta(hours=-3))` em vez de `ZoneInfo("America/Sao_Paulo")`, porque o enunciado
  exige `-03:00` sempre, "sem horário de verão" — um fuso nomeado carregaria regras históricas de
  DST do banco de fusos do sistema operacional.
- **RN15 (dias restantes e % de multa) é reaproveitada entre `mercado` e `clubes`**: a mesma
  função pura (`calcular_dias_restantes_e_percentual_de_multa`) calcula a multa na venda e o
  `contract` de cada jogador do elenco em `GET /clubs/{id}` ("como se fosse vendido agora") — o
  próprio barema cita essa regra como exemplo do que não pode ser cálculo duplicado.
- **Exportação CSV usa vírgula decimal**, diferente da convenção de números JSON da API (RN18
  pede "2 casas e vírgula decimal"): `mercado/service.py` tem um formatador próprio
  (`_formatar_valor_csv`) só para a exportação, via módulo `csv` da biblioteca padrão.
- **Arredondamento monetário**: `Decimal` com `ROUND_HALF_UP` em todo lugar (nunca `float` nem o
  `round()` nativo do Python, que arredonda "para o par mais próximo" em empates — o enunciado
  exige "para longe do zero").
- **Serialização de `Decimal` como número JSON**: o Pydantic, por padrão, serializa `Decimal`
  como string (`"40.00"`); isso violaria a convenção "valores são números JSON" do enunciado, e
  foi corrigido com um `field_serializer` explícito em `JogadorRead`.
- **Mensagens de erro**: em português, e o texto delas não segue nenhuma convenção fixa (o
  enunciado deixa o texto livre, só exige o campo `message`).
- **Filtros de `GET /players`**: posição, condição, livre/clube e faixa de idade são aplicados em
  SQL (com índice); busca por nome e tudo que envolve valor de mercado (filtro e ordenação) são
  calculados em Python, reaproveitando a mesma função de RN02–RN05 usada na consulta de um
  jogador — mesmo o barema permitindo reimplementar essa fórmula em SQL sem penalidade, optamos
  por não ter duas versões da mesma regra (motivo: evitar o tipo de divergência silenciosa do
  exemplo de ficha de avaliação, onde a multa foi implementada duas vezes e só uma arredondava
  certo).
- **Query params em string**: a validação de `GET /players` não reaproveita o `BeforeValidator`
  usado nos corpos JSON, porque query params chegam sempre como string — os formatos (inteiro
  sem zeros à esquerda, decimal com até 2 casas) são validados por regex própria.
- **`UnidadeDeTrabalho` mora em `core/`, não em `mercado/`**: ela nasceu em `mercado` (compra e
  venda), mas a change `liga` precisou do mesmo padrão em `jogadores` (uma mudança de condição
  para `DOENTE` tira o titular da escalação, na mesma transação) — como `jogadores` é a
  capability mais antiga e fundamental, importar de `mercado` inverteria a dependência natural
  entre capabilities. A abstração não tem nenhuma regra de negócio (só `confirmar`/`desfazer`
  sobre uma `Session`), então subiu para `core/unidade_de_trabalho.py`, no mesmo nível de
  `core/db.py`, e passou a ser reaproveitada por `jogadores`, `mercado` e `liga`.
- **"Sai da escalação" é uma regra só, chamada de dois lugares**: em vez de duplicar RN19.5 em
  `MercadoService.vender` e em `JogadorService.alterar_condicao`, as duas chamam
  `EscalacaoRepository.remover_titular(jogador_id)` (que só agenda a escrita, nunca comita) antes
  de confirmar pela própria `UnidadeDeTrabalho` de cada operação — mesmo padrão de composição já
  usado por `ClubeService`, que depende do `ContratoRepository` de `mercado`.
- **Efeito de `MAL_CONDICIONADO` na partida arredonda para inteiro, não para 2 casas**: o -15% nos
  atributos (RN20.3) usa `arredondar_inteiro` (`ROUND_HALF_UP` para 0 casas), uma função própria
  de `liga/calculos.py`, diferente do `arredondar` de 2 casas usado em todo valor monetário do
  projeto — são conceitos diferentes (atributo de jogador em partida vs. dinheiro), por isso não
  reaproveitam a mesma função nem a mesma precisão.
- **Quem ataca e quem defende em cada duelo é fixo pelo índice do jogador de linha, não pela
  formação**: a tabela da RN20 (o 4º jogador de linha ataca o goleiro, o 3º ataca o 1º, o 2º ataca
  o 2º) depende só da posição de cada titular na ordem do elenco (RN11: GOL, ZAG, LAT, MEI, ATA,
  depois nome, depois id) — nunca da formação escolhida, que só entra na validação da escalação
  (RN19). Isso evita uma tabela de pareamento por formação, que seria mais uma regra para manter
  sincronizada sem necessidade.

- **Dockerfile multi-stage, não single-stage**: o estágio `builder` instala o Poetry e as
  dependências; o estágio final (`runtime`) só copia a `venv` já pronta e o código — a imagem
  final não carrega o Poetry nem o cache de instalação, só o necessário para rodar o Uvicorn.
- **`poethepoet` em vez de Makefile**: as tasks (`test`, `lint`, `migrate`, etc.) precisavam rodar
  igual em Linux e Windows. Um Makefile exigiria `make` instalado à parte no Windows (não vem por
  padrão); o `poethepoet` é uma dependência de desenvolvimento Python comum (`poetry run poe
  <task>`), então já funciona em qualquer SO que já tenha Poetry — sem instalar mais nada.
- **`DATABASE_URL` sobrescrito no `docker-compose.yml`, não hardcoded no `backend/.env`**: o
  mesmo `backend/.env` precisa servir tanto a opção B (API local, Postgres em `localhost:5433`)
  quanto a opção A (API em contêiner, Postgres no host interno `db:5432`) — em vez de manter dois
  arquivos de env por ambiente, o serviço `api` do compose sobrescreve só essa variável.
- **`GET /health` confere o banco, não só o processo**: um healthcheck que só confirma "o Uvicorn
  está de pé" mentiria se o Postgres caísse (a API continuaria respondendo erro 500 em tudo, mas o
  Docker reportaria "healthy"). Por isso o endpoint faz um `SELECT 1` real a cada checagem — o
  `HEALTHCHECK` do Dockerfile e o `healthcheck` do serviço `api` no compose usam esse mesmo
  endpoint, e é ele que aparece como `(healthy)`/`(unhealthy)` no `docker compose ps`.
- **Correções de lint aceitas no código inteiro**: ao configurar o `ruff` via `poe lint`, 113
  avisos pré-existentes apareceram. A maioria era modernização de sintaxe sem risco (`Union[X, Y]`
  → `X | Y`, `Decimal("0")` → `Decimal(0)`, `dict(...)` → literal em testes, import não usado) e
  foi corrigida. Duas regras viraram exceção de configuração, não mudança de código, por serem
  falso-positivo para os frameworks usados: `B008` (Depends()/Query() como default de parâmetro é
  o padrão do FastAPI) e `TRY004` (validators do Pydantic levantam `ValueError` de propósito,
  mesmo para erro de tipo — é assim que o Pydantic converte em erro de validação).

## 7. Funcionalidades não implementadas

- Frontend (React) — ainda não iniciado.

## 8. Uso de inteligência artificial

Usei o Claude Code (Anthropic) durante todo o desenvolvimento desta entrega, com a seguinte
abordagem:

- **Onde**: todo o backend desenvolvido até aqui (arquitetura, regras de negócio, testes,
  migrations, README).
- **Como e por quê**: o projeto foi conduzido por SDD (Spec-Driven Development) com a ferramenta
  [OpenSpec](https://github.com/Fission-AI/OpenSpec) — cada funcionalidade nasce como uma
  especificação (`openspec/changes/<nome>/`), com requisitos e cenários rastreados às regras de
  negócio do enunciado (RN01–RN21), antes de qualquer código ser escrito. A IA gerou specs,
  design técnico, plano de tarefas e a implementação linha a linha a partir disso, incluindo os
  testes automatizados que conferem as tabelas de exemplo do próprio enunciado.
- **O que foi aceito, alterado ou descartado**: todas as decisões de arquitetura (camadas,
  padrão de repositório, escolha de bibliotecas, versões exatas) foram revisadas e aprovadas
  por mim antes da implementação. Durante a implementação, dois problemas reais de serialização
  foram encontrados e corrigidos — importante separar dois conceitos aqui: internamente, todo
  valor monetário é sempre `Decimal` (nunca `float`), para não perder precisão nos cálculos; o
  problema era só no **formato do JSON da resposta HTTP**, uma camada depois. O Pydantic, quando
  nenhum `field_serializer` customizado intercepta um campo `Decimal`, serializa esse campo como
  **string** no JSON (`"fee": "1.85"`, com aspas) — o enunciado exige número puro
  (`"fee": 1.85`). A correção é um `field_serializer` que converte `Decimal` para `float` só na
  hora de montar a resposta (`float(Decimal("1.85"))`), sem nenhuma perda de precisão porque o
  cálculo já tinha terminado em `Decimal`.
  1. Esse comportamento padrão (sem o `field_serializer`) foi descoberto logo na capability
     `jogadores`, pelos próprios testes de integração (a resposta vinha com valores entre aspas).
  2. Na capability `mercado`, o bug voltou de um jeito mais sutil: um `field_serializer` de uma
     subclasse (`SellRead`) usava o mesmo nome de método de um já definido na classe-mãe
     (`TransactionRead`), atropelando silenciosamente o serializer herdado — dois campos
     voltaram a cair no comportamento padrão do Pydantic (viraram string em vez de número) sem
     que o `Decimal` em si estivesse errado em nenhum momento. Só foi detectado porque o teste
     comparava a resposta inteira contra o exemplo exato do enunciado, não campo a campo.
