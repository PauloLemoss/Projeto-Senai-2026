## Why

A change `cadastro-jogadores` entregou o ciclo de vida de um jogador isolado (cadastro, consulta
por id, edição, condição, exclusão), mas deixou de fora, de propósito, a listagem paginada com
busca, filtros e ordenação (RN07) — exatamente como registrado no "Fora de escopo" daquela
proposta. Sem isso, não dá pra navegar o cadastro de jogadores pela tela (quando o frontend for
implementado) nem completar a "Etapa 1: Jogadores" do barema (B07). Esta change fecha essa
lacuna.

## What Changes

- `GET /players` passa a aceitar: `search` (busca no nome, ignorando acentos/caixa), `position`,
  `condition`, `free`, `club_id`, `min_age`/`max_age`, `min_value`/`max_value`, `sort` (até dois
  critérios) e paginação (`page`, `limit`), combináveis entre si (RN07).
- Resposta passa a ser um objeto paginado (`data` + `meta`), em vez do array usado nos exemplos
  informais até aqui.
- Parâmetros inválidos, fora da lista aceita ou combinações contraditórias (ex.: `free=true`
  junto com `club_id`, `min_age` maior que `max_age`) são recusados com `400`.

**Fora de escopo nesta change**: filtro por `club_id` não valida que o clube existe de verdade
(a capability `clubes` ainda não existe) — por ora, qualquer `club_id` sintaticamente válido é
aceito como filtro; a validação de existência entra quando `clubes` for implementada.

## Capabilities

### New Capabilities
(nenhuma)

### Modified Capabilities
- `jogadores`: adiciona o requirement de listagem paginada, busca, filtros e ordenação de
  `GET /players` (RN07). Não altera nenhum requirement existente (cadastro, consulta por id,
  edição, condição e exclusão continuam exatamente como estão).

## Impact

- `backend/src/mercado_jogadores/jogadores/router.py`: novo handler `GET /players`.
- `backend/src/mercado_jogadores/jogadores/service.py`: nova operação de listagem (filtra, busca,
  ordena, pagina).
- `backend/src/mercado_jogadores/jogadores/repository.py`: o `Protocol` ganha um método de
  listagem com os critérios acima — a camada de dados monta a query (filtros/ordenação/paginação
  no banco), não o service.
- `backend/src/mercado_jogadores/jogadores/schemas.py`: novo schema de query params e de resposta
  paginada (`PlayerListResponse` com `data`/`meta`).
- Sem impacto em clubes, mercado ou liga (ainda não existem).
