# Mercado de Jogadores

Estudo de caso SENAI/PE – CÓD. 237 DESENVOLVEDOR I (FULLSTACK).

> O frontend ainda não foi implementado (change futura). Este README cobre, por enquanto, só o
> backend, na parte entregue até aqui: cadastro, consulta, edição, alteração de condição,
> exclusão lógica e listagem paginada (com busca, filtros e ordenação) de jogadores.

## Estrutura

- `backend/` — API REST (Python + FastAPI)
- `frontend/` — Interface (React) — ainda não implementada
- `openspec/` — Especificações (SDD, via [OpenSpec](https://github.com/Fission-AI/OpenSpec)) que guiam a implementação

## 1. Pré-requisitos

| Ferramenta | Versão usada no desenvolvimento |
| --- | --- |
| Python | 3.12 |
| [Poetry](https://python-poetry.org) | 2.5 |
| Docker + Docker Compose | Docker 29, Compose v2 |

O Postgres roda em contêiner (não precisa instalar localmente).

## 2. Criar e recriar o banco de dados

O banco é gerenciado por migrations do [Alembic](https://alembic.sqlalchemy.org), versionadas em
`backend/alembic/versions/`.

```bash
# Na raiz do repositório: sobe o Postgres
docker compose up -d db

# Na pasta backend: cria as tabelas
cd backend
poetry run alembic upgrade head
```

Para recriar o banco do zero (apagar e criar de novo):

```bash
# Na pasta backend
poetry run alembic downgrade base
poetry run alembic upgrade head
```

O banco criado por esses passos começa vazio, sem jogadores.

## 3. Instalar e executar

```bash
# Banco de dados (na raiz do repositório)
cp .env.example .env
docker compose up -d db

# Backend (na pasta backend)
cd backend
cp .env.example .env
poetry install
poetry run alembic upgrade head
poetry run uvicorn mercado_jogadores.main:app --reload
# API em http://localhost:8000 (o script da banca acrescenta /api/v1)
# Documentação interativa (Swagger) em http://localhost:8000/docs
```

O frontend ainda não existe nesta entrega.

### Rodar os testes

```bash
# Na pasta backend, com o banco subido (docker compose up -d db) e migrado
# (poetry run alembic upgrade head) — os testes de integração usam o Postgres real
cd backend
poetry run pytest
```

## 4. Variáveis de ambiente

Dois arquivos `.env.example`, cada um na pasta do serviço que o usa:

- **`/.env.example`** (raiz): credenciais do Postgres, lidas pelo `docker-compose.yml`.
- **`backend/.env.example`**: `DATABASE_URL` (string de conexão do backend com o Postgres acima)
  e `CORS_ORIGIN` (origem do frontend liberada no CORS).

As portas e credenciais padrão (porta `5433` para o Postgres, em vez da `5432` padrão) evitam
colisão com outros serviços que já possam estar rodando na máquina; não há necessidade de mudar
nada para a aplicação funcionar.

## 5. Estrutura e bibliotecas (backend)

```
backend/
├── alembic/              # migrations do banco
├── src/mercado_jogadores/
│   ├── core/             # config, sessão do banco, exceções de domínio, validações comuns
│   └── jogadores/        # capability "jogadores": models, schemas, service, repository, router
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

## 6. Decisões e premissas

- **Arquitetura em camadas** (Router → Service → Repository): o service nunca importa
  SQLAlchemy diretamente, só a abstração `JogadorRepository` (um `Protocol`), para poder ser
  testado com um repositório fake, sem banco.
- **`clube_id` na tabela `jogadores`** ainda não tem chave estrangeira para `clubes.id`: essa
  tabela nasce numa change futura (capability `clubes`), que vai adicionar a constraint.
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

## 7. Funcionalidades não implementadas

- Frontend (React) — ainda não iniciado.
- Módulos de Clubes, Mercado (compra/venda/histórico) e Liga (escalação/partidas) — ainda não
  implementados.

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
  por mim antes da implementação. Durante a implementação, um problema real foi encontrado e
  corrigido no processo: a serialização padrão do Pydantic devolvia valores monetários como
  string em vez de número JSON, o que foi detectado pelos próprios testes de integração e
  corrigido.
