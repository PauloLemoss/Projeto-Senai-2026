## Why

`jogadores`, `clubes` e `mercado` fecham os três primeiros módulos do enunciado; falta o quarto e
último: a Liga. Com `contratos`/`transacoes` já existindo (change `mercado`), os clubes já têm
elenco de verdade (via compra), o que permite escalar titulares e jogar partidas pela primeira
vez. Esta change implementa escalação, partidas (com o placar calculado pelos 6 duelos) e o
histórico/classificação (RN19 a RN21) — o último módulo funcional da aplicação.

## What Changes

- Escalação de titulares (`PUT /clubs/{id}/lineup`): substitui a escalação inteira numa única
  operação — 1 goleiro e 4 jogadores de linha, distribuídos numa das 4 formações aceitas; cada
  titular precisa ser do elenco do clube e não estar `DOENTE`; não muda o caixa (RN19).
- Consulta da escalação atual (`GET /clubs/{id}/lineup`): `formation`, `complete` e `players` na
  ordem do elenco; sem escalação, tudo vazio/`null`/`false` (RN19).
- Titular sai da escalação automaticamente quando é vendido ou passa a `DOENTE` — na mesma
  operação da venda ou da alteração de condição; a escalação fica incompleta (mesma formação) até
  escalar de novo; o jogador não volta sozinho ao deixar de estar `DOENTE` (RN19).
- Partida entre dois clubes com escalação completa (`POST /matches`): placar calculado pelos 6
  duelos entre os titulares (3 ataques de cada lado), com o efeito de −15% por atributo do titular
  `MAL_CONDICIONADO`; grava a partida, as formações e os 6 duelos com os valores do momento, numa
  única operação; não muda caixa, escalação nem jogadores (RN20).
- Histórico de partidas (`GET /matches`, com filtro `club_id`) e detalhe de uma partida com os 6
  duelos (`GET /matches/{id}`) (RN21).
- Classificação de todos os clubes (`GET /standings`), calculada a cada consulta, nunca gravada:
  pontos, saldo de gols, gols marcados, com os desempates da RN21.

**Fora de escopo nesta change**: qualquer UI (frontend ainda não iniciado). Com `liga`, os quatro
módulos funcionais do enunciado estarão implementados.

## Capabilities

### New Capabilities
- `liga`: escalação de titulares, partidas com placar calculado pelos duelos, histórico de
  partidas e classificação (RN19 a RN21).

### Modified Capabilities
(nenhuma) — a saída automática da escalação (RN19.5), embora disparada pela venda (`mercado`) e
pela alteração de condição (`jogadores`), é descrita inteiramente como comportamento de `liga`
(o único efeito observável dela é em `GET /clubs/{id}/lineup`, que pertence a `liga`); as
specs de `jogadores` e `mercado` continuam corretas como estão, sem precisar de delta. A
implementação de `MercadoService.vender` e `JogadorService.alterar_condicao`, sim, muda (ver
design.md) — isso é impacto de código, não de comportamento documentado nessas capabilities.

## Impact

- `backend/src/mercado_jogadores/liga/`: novo módulo (models, schemas, service, repository,
  router), seguindo o mesmo padrão de camadas de `jogadores`/`clubes`/`mercado`.
- Migration: cria as tabelas `escalacoes`, `partidas` e `duelos_partida` (RN19, RN20).
- `MercadoService.vender` e `JogadorService.alterar_condicao`: passam a remover o titular da
  escalação (se houver) na mesma operação atômica, via um novo `EscalacaoRepository` (leitura e
  remoção), composição análoga à de `ClubeService` com `ContratoRepository`.
- Sem impacto em `clubes` (o campo `formacao`, que já existe na tabela desde a change `clubes`
  mas nunca foi lido/escrito, passa a ser usado pela escalação) nem em `api-conventions`.
