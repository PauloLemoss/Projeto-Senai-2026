## Why

O sistema não existe ainda. Jogadores são a entidade raiz de todo o fluxo do estudo de caso
(README.md, "Como o sistema funciona"): clubes só compram jogadores já cadastrados, e o valor de
mercado deles é recalculado em todo o resto do sistema (compra, venda, histórico, escalação,
partidas). Sem o ciclo de vida básico do jogador — cadastro com cálculo do valor base, consulta
com valor de mercado e overall calculados, edição, alteração de condição física e exclusão lógica
— nenhum outro módulo (Clubes, Mercado, Liga) tem o que consumir. Esta é a primeira capability do
projeto.

## What Changes

- Cadastro de jogador (`POST /players`): recebe nome, posição, agilidade, idade e os sete
  indicadores (seis atributos + potencial); calcula e grava o **valor base** uma única vez
  (RN06); nasce `APTO` e livre (`club_id` nulo).
- Consulta de um jogador (`GET /players/{id}`): devolve o jogador com **overall** (RN06) e
  **valor de mercado** (RN02–RN05) calculados na hora da consulta, nunca gravados.
- Edição (`PUT /players/{id}`): altera nome, posição, agilidade e idade; indicadores, potencial e
  valor base continuam os do cadastro (RN08); idade não pode diminuir; jogador com clube não muda
  de posição.
- Alteração de condição física (`PATCH /players/{id}/condition`): `APTO`, `MAL_CONDICIONADO` ou
  `DOENTE`; de `DOENTE` não vai direto para `APTO`.
- Exclusão lógica (`DELETE /players/{id}`): só jogador livre; marca `excluido_em`, não apaga do
  banco; jogador excluído passa a contar como inexistente (404) em todos os endpoints.
- Validação de entrada compartilhada por todos os endpoints acima: corpo é objeto JSON (V1),
  tipos e limites de cada campo (V2, V6, "Limites de cada campo" do jogador), normalização de
  nome (V4), valores de lista exatos (V5), campos controlados pelo sistema ignorados sem erro
  (V7), id de URL fora do formato ou inexistente → 404 (V8), códigos de erro padronizados (V9).

**Fora de escopo nesta change** (fica para uma change futura, `listagem-jogadores`):
- `GET /players` paginado, busca por nome, filtros e ordenação (RN07).
- Qualquer coisa de Clubes, Mercado (compra/venda/histórico) ou Liga (escalação/partidas) — essas
  dependem de jogador existir, mas pertencem a capabilities próprias.

## Capabilities

### New Capabilities
- `api-conventions`: regras de validação, erro e convenções de resposta **compartilhadas por
  toda a API** (corpo precisa ser objeto JSON, normalização de texto, valores de lista exatos,
  campo obrigatório ausente, campos controlados pelo sistema ignorados, recurso/id inexistente ou
  malformado → 404, códigos de erro padronizados com `message`, criação → 201 com `Location`).
  Extraída como capability própria porque toda change futura (clubes, mercado, liga) depende
  dela — não deve ser redefinida em cada spec de domínio.
- `jogadores`: ciclo de vida de um jogador isolado — cadastro (com cálculo do valor base, RN06),
  consulta por id (com overall e valor de mercado calculados, RN02–RN06), edição (RN08),
  alteração de condição física, e exclusão lógica (RN09). Depende de `api-conventions` para as
  regras de validação/erro genéricas; aqui só entram os limites de campo e as regras específicas
  de jogador. Não inclui listagem/paginação (RN07), que fica para uma change futura que vai
  MODIFICAR esta mesma capability.

### Modified Capabilities
(nenhuma — primeira change do projeto)

## Impact

- Novo código: `backend/` inteiro (ainda não existe nenhuma linha) — router, service, repository
  e schemas Pydantic para jogador; modelo de dados da tabela `jogadores` (ver "3. Estrutura de
  tabelas" do enunciado).
- Sem impacto em frontend ou em outras capabilities ainda, por serem as primeiras linhas do
  projeto.
- Dependência nova: banco PostgreSQL (via Docker Compose) precisa existir para a camada de
  repositório, mesmo que os testes de regra de negócio (service) não dependam dele (repositório
  fake).
