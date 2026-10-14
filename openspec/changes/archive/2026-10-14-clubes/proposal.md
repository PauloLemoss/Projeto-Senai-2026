## Why

O Mercado (compra/venda de jogadores) precisa que clubes existam antes de poder funcionar: toda
compra indica um `club_id`, e sem a tabela `clubes` nem o endpoint de criação, não há o que
referenciar. Esta change implementa o módulo Clubes (RN10 e RN11) isoladamente, como o próprio
"Como o sistema funciona" do enunciado descreve (clubes nascem depois dos jogadores e antes da
compra).

## What Changes

- Criação de clube (`POST /clubs`): nome e sigla, com as validações de formato e unicidade da
  RN10; nasce com 300,00 em caixa e sem jogadores; limite de 20 clubes na liga.
- Listagem de clubes (`GET /clubs`): ordenável por nome (padrão) ou por patrimônio calculado
  (RN11), com empate desfeito por nome e depois id.
- Consulta de um clube (`GET /clubs/{id}`): caixa, valor do elenco, patrimônio e elenco ordenado
  (GOL, ZAG, LAT, MEI, ATA, depois nome, depois id).

**Fora de escopo nesta change**: o campo `contract` de cada jogador do elenco (fim da fidelidade,
dias restantes, % de multa) — isso depende da tabela `contratos`, que só existe quando a compra
(capability `mercado`, ainda não implementada) a criar. Até lá, qualquer clube consultado tem o
elenco vazio por construção (não existe forma de um jogador ganhar `club_id` sem a compra), então
a ordenação e os valores do elenco (`squad_value`, `net_worth`) já são implementados e testados
agora — a parte que falta é só o campo `contract`, adicionado numa change futura que vai MODIFICAR
esta mesma capability `clubes`.

## Capabilities

### New Capabilities
- `clubes`: criação com validação de nome/sigla e unicidade (RN10), listagem ordenável e consulta
  com elenco, valor do elenco e patrimônio (RN11).

### Modified Capabilities
(nenhuma)

## Impact

- `backend/src/mercado_jogadores/clubes/`: novo módulo (models, schemas, service, repository,
  router), seguindo o mesmo padrão de camadas de `jogadores`.
- Migration: cria a tabela `clubes` (com `nome_normalizado` para a unicidade case-insensitive da
  RN10) e **adiciona a FK de `jogadores.clube_id` para `clubes.id`**, que ficou pendente desde a
  change `cadastro-jogadores`.
- Sem impacto na capability `jogadores` nem em `api-conventions`.
