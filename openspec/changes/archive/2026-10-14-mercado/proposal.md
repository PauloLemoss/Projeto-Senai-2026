## Why

Com `jogadores` e `clubes` prontos, o enunciado descreve a sequência natural: "os clubes compram
(assinando um contrato de fidelidade) e vendem, e tudo fica no histórico". Sem o Mercado, um
jogador nunca ganha `club_id` de verdade (só por manipulação direta de teste) e o campo `contract`
do elenco de `GET /clubs/{id}`, deixado de fora na change `clubes` por depender da tabela
`contratos`, continua sem poder ser implementado. Esta change implementa compra, venda, histórico
de transações e a exportação em CSV (RN12 a RN18).

## What Changes

- Compra de jogador livre (`POST /players/{id}/buy`): preço pelo valor de mercado do momento,
  taxa de 5% acima de 30,00, limite de 50% do caixa (sem arredondar o limite), contrato `ATIVO`,
  transação `COMPRA` e jogador no elenco — tudo numa única transação de banco (RN12, RN13).
  Limite de 12 jogadores por elenco (RN14). Um clube não pode recomprar um jogador que ele mesmo
  já vendeu.
- Venda de jogador do elenco (`POST /players/{id}/sell`, sem corpo): multa por fidelidade pelos
  dias restantes (0%/5%/10%/20%, teto 10,00), comissão progressiva sobre o lucro (10% até 10,00
  de lucro + 20% acima), contrato `RESCINDIDO` ou `ENCERRADO`, crédito no caixa, jogador volta a
  livre e transação `VENDA` gravada — também numa única transação (RN15, RN16).
- Histórico de transações do clube (`GET /clubs/{id}/transactions`): filtros por `type` (um ou
  mais) e `player_id`, com `summary` dos totais filtrados (RN17).
- Exportação do histórico em CSV (`GET /clubs/{id}/transactions/export`): mesmos filtros, mesma
  ordem, arquivo `text/csv` UTF-8 sem BOM (RN18).

**Fora de escopo nesta change**: escalação e partidas (capability `liga`, que depende de
`contratos` e `transacoes` já existirem).

## Capabilities

### New Capabilities
- `mercado`: compra, venda, histórico de transações e exportação CSV (RN12 a RN18).

### Modified Capabilities
- `clubes`: a requirement "Consulta de clube com elenco, valor do elenco e patrimônio" passa a
  exigir o campo `contract` (fim da fidelidade, dias restantes, percentual de multa) em cada
  jogador do elenco de `GET /clubs/{id}` — deixado de fora na change `clubes` porque a tabela
  `contratos` só nasce aqui.
- `api-conventions`: acrescenta a requirement de formato de data e hora (RN01) — nenhuma
  capability anterior expunha campo de data/hora na API (`criado_em`/`atualizado_em` de
  `jogadores`/`clubes` nunca aparecem numa resposta); `loyalty_until` e `created_at` do Mercado
  são os primeiros, e a regra vale igualmente para a futura `liga` (`jogada_em` de partidas).

## Impact

- `backend/src/mercado_jogadores/mercado/`: novo módulo (models, schemas, service, repository,
  router), seguindo o mesmo padrão de camadas de `jogadores` e `clubes`.
- Migration: cria as tabelas `contratos` e `transacoes` (RN12, RN17), com as FKs para `jogadores`
  e `clubes`.
- `clubes/service.py` e `clubes/schemas.py`: o elenco de `ClubeComElenco` passa a incluir o
  contrato de cada jogador (dependência de leitura em `ContratoRepository`, análoga à composição
  já existente com `JogadorRepository`).
- `core/`: novo utilitário de data/hora (fuso de Brasília fixo, parsing e formatação RN01),
  reaproveitado por `mercado` e, depois, por `liga`.
- Sem impacto em `jogadores`.
