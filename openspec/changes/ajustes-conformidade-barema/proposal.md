## Why

Uma auditoria comparando o enunciado oficial e o barema de avaliação contra o backend implementado
encontrou 3 divergências reais: duas são regras do enunciado que o código (e, em dois casos, a
própria spec) não cobre — `GET /players?club_id=<inexistente>` deveria responder `404` e responde
`200` com lista vazia; três campos inteiros do corpo (`club_id` na compra, `home_club_id` e
`away_club_id` na partida) aceitam `"15"` (texto) quando o enunciado exige recusar com `400`
(V2) — e a terceira é um diferencial técnico do barema (B5, "Registro de logs") hoje não atendido:
a aplicação não emite nenhuma linha de log com data/hora, método, caminho e status por requisição.
Corrigir agora evita perder pontos de B07/B11/B20/B21 (roteiro da API) e B5 (diferenciais) numa
avaliação real.

## What Changes

- `GET /players` passa a validar a existência do clube quando `club_id` é informado, respondendo
  `404` se o clube não existir (hoje devolve `200` com `data: []`).
- A capability `api-conventions` ganha uma regra geral (hoje ausente) para V2/V3: todo campo
  inteiro do corpo SHALL ser recusado com `400` quando vier como string (mesmo uma string
  numérica, tipo `"15"`) ou como número com parte fracionária não nula.
- `BuyRequest.club_id` (mercado) e `MatchCreate.home_club_id`/`away_club_id` (liga) passam a usar
  o validador estrito de inteiro já usado em outros campos do projeto (reaproveitado, não
  duplicado), em vez do `int` puro do Pydantic (que hoje converte string numérica silenciosamente).
- A aplicação passa a emitir, para cada requisição HTTP, uma única linha de log legível com
  data/hora, método, caminho e status — via biblioteca de log (não `print`), atendendo ao
  diferencial B5 "Registro de logs".
- O comando de formatação do backend informado no README passa a ser um comando que só **verifica**
  (sem alterar arquivos), atendendo ao diferencial B5 "Lint e formatação" (hoje `poe format`
  altera os arquivos).

## Capabilities

### New Capabilities
- `diferenciais-tecnicos`: cobre os diferenciais técnicos do backend que não são regra de negócio
  de nenhuma capability de domínio (B5 do barema) — registro de logs por requisição e os comandos
  de lint/formatação informados no README.

### Modified Capabilities
- `api-conventions`: nova regra geral de validação de campo inteiro no corpo (V2/V3) — hoje a spec
  só cobre V1, V4-V9 e o formato de data, nunca formalizou a rejeição de string/fracionário em
  campo inteiro, apesar de o enunciado exigir isso em todo campo (e o projeto já implementar via
  um validador reaproveitado na maioria dos campos).
- `jogadores`: o requirement de `GET /players` (filtros combinados, RN07) passa a exigir `404`
  quando `club_id` referenciar um clube inexistente — hoje o requirement nem menciona esse caso.
- `mercado`: o scenario "club_id inválido é recusado" (compra) passa a cobrir também o caso de
  `club_id` enviado como string, não só "0 ou negativo".
- `liga`: o requirement de `POST /matches` ganha um scenario novo para `home_club_id`/
  `away_club_id` enviados como string (tipo inválido), distinto do scenario já existente de
  "mandante igual ao visitante".

## Impact

- Código: `backend/src/mercado_jogadores/jogadores/service.py` (nova dependência de
  `ClubeRepository`), `backend/src/mercado_jogadores/jogadores/router.py` (injeção da dependência
  nova), `backend/src/mercado_jogadores/mercado/schemas.py`, `backend/src/mercado_jogadores/liga/
  schemas.py`, `backend/src/mercado_jogadores/core/validation.py` (validador reaproveitado),
  `backend/src/mercado_jogadores/main.py` (middleware/handler de log), `backend/pyproject.toml`
  (task de formatação só-verificação), `README.md` (comando de verificação de formatação).
- Testes: novos testes unitários (jogadores: 404 por clube inexistente no filtro; mercado e liga:
  tipo inválido nos campos de id) e, para logs, um teste manual (não dá para asserir em teste
  automatizado o formato exato da saída de log sem acoplar ao backend de log escolhido).
- Nenhuma mudança de schema de banco, nenhuma migration nova.
