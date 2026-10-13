## Context

A capability `jogadores` já existe (change `cadastro-jogadores`, arquivada), com
Router → Service → Repository e os cálculos de RN02–RN06 isolados em `calculos.py`. Esta change
só adiciona um novo caso de uso (`listar`) a essa mesma capability — não há mudança de
arquitetura.

Achado relevante do barema (B2, "Como contar" de "Cálculo duplicado"): a correção **não conta
como duplicação** reescrever a fórmula do valor de mercado em SQL, só para filtrar/ordenar a
listagem. Ou seja, a banca permite esse atalho — mas, como ele cria duas implementações da mesma
fórmula (Python e SQL) que podem divergir silenciosamente (foi exatamente isso que aconteceu com
a multa, RN15, no exemplo de ficha de avaliação: duas implementações do mesmo cálculo, uma
arredondando certo e outra não), a decisão abaixo evita esse atalho deliberadamente.

## Goals / Non-Goals

**Goals:**
- Implementar RN07 (busca, filtros, ordenação, paginação) sem introduzir uma segunda
  implementação da fórmula do valor de mercado.
- Manter o service testável com repositório fake, como as demais operações de `jogadores`.

**Non-Goals:**
- Performance em escala (milhares de jogadores): fora do escopo deste estudo de caso — o limite
  de resposta da banca é 10s por requisição, e a listagem opera sobre o cadastro de uma liga
  fictícia, não um volume de produção.
- Validar que `club_id` do filtro corresponde a um clube existente de verdade — a capability
  `clubes` ainda não existe (ver proposal.md, "Fora de escopo").

## Decisions

### Filtros diretos em SQL (com índice); valor de mercado e busca por nome em Python

Dividido em dois grupos, por motivo diferente cada um:

- **Filtros de coluna direta** (`position`, `condition`, `free`/`club_id`, faixa de idade) **vão
  para a cláusula `WHERE` do repositório**, com índice (ver "Índices", abaixo). Não há cálculo de
  regra de negócio aqui — é comparação direta de coluna, sem risco de duplicar fórmula nenhuma, e
  reduz o conjunto de linhas antes de qualquer processamento em Python.
- **Busca por nome** (`search`) é feita em Python, sobre o conjunto já filtrado por SQL: reusa a
  mesma normalização de acentos/caixa de `core/validation.py`, em vez de depender da extensão
  `unaccent` do Postgres (que exigiria uma migration própria e um índice funcional/trigram só pra
  isso — desproporcional ao volume de dados deste projeto).
- **Filtro e ordenação por valor de mercado** (`min_value`/`max_value`, `value_asc`/`value_desc`)
  continuam em Python, reaproveitando `calculos.calcular_valor_de_mercado` — a mesma função usada
  por `consultar()`. Mesmo o barema permitindo reimplementar RN02–RN05 em SQL sem penalidade
  (B2, "Cálculo duplicado"), a decisão é **não usar esse atalho**: criar uma segunda
  implementação da mesma fórmula (Python e SQL) é exatamente o padrão que gerou o bug da multa
  (RN15) no exemplo de ficha de avaliação — duas versões da mesma regra, uma arredondando certo e
  outra não. Como o filtro de coluna direta já reduz bastante o conjunto antes desse ponto,
  calcular o valor de mercado em Python para o que sobrou é barato.

A ordenação final (incluindo os dois critérios combináveis, com `position` na ordem fixa e
`value_*` calculado) é sempre feita em Python, depois da busca e dos filtros — assim não existe
lógica de ordenação partida entre SQL e Python para o mesmo `sort`.

### Índices para os filtros de coluna direta

Nova migration adiciona índices em `jogadores`:
- `clube_id` — usado pelo filtro `club_id`/`free`, e vai ser reaproveitado pelas consultas de
  elenco quando a capability `clubes` existir (`GET /clubs/{id}` lista o elenco pelo clube).
- `posicao` — usado pelo filtro `position` e por `sort=position`.
- `condicao` — usado pelo filtro `condition`.
- `excluido_em` — toda consulta de jogador (não só a listagem) filtra `excluido_em IS NULL`; um
  índice parcial (`WHERE excluido_em IS NULL`) é mais enxuto que um índice completo, já que só
  precisamos buscar rápido os jogadores ativos.

Não cria índice em `nome` (a busca é feita em Python sobre o conjunto já filtrado, não por `LIKE`
no banco — um índice B-tree comum não ajudaria em "contém" de qualquer forma, só um índice
trigram, que é o overhead que a decisão acima evitou) nem em `idade` (faixa pequena de 16 a 45,
baixa seletividade, não compensa o custo de escrita do índice na escala deste projeto).

### `sort=position` usa a mesma ordem fixa do `calculos.py`, não uma nova constante

A ordem GOL, ZAG, LAT, MEI, ATA já existe como chave de `PESOS_POR_POSICAO` em `calculos.py`
(RN06). A ordenação por posição reusa a ordem das chaves desse dicionário, em vez de declarar uma
segunda lista de posições em outro arquivo.

### Paginação é um dataclass de retorno do service, não um schema Pydantic

Seguindo o padrão já usado (`JogadorComCalculados`): `service.listar()` devolve uma
`ListaDeJogadores` (dataclass com `itens: list[JogadorComCalculados]`, `total_items: int`,
`page: int`, `limit: int`), e o schema Pydantic de resposta (`PlayerListResponse`, com `data` e
`meta`) só mapeia esse resultado — igual já fazemos com `JogadorRead.a_partir_do_resultado`.

### Query params validados por um schema Pydantic próprio

Um `JogadorListQuery` (Pydantic) com todos os parâmetros de `GET /players`, usando o mesmo
`InteiroEstrito` já existente para os inteiros e um tipo similar para os decimais
(`min_value`/`max_value`), e `model_validator` para as combinações contraditórias (`min_age` >
`max_age`, `min_value` > `max_value`, `free=true` com `club_id`). Os `Literal` de `sort` aceitam
até dois valores separados por vírgula — validados como lista de enum, não como string livre.

## Risks / Trade-offs

- **[Risco] Filtro por valor e busca por nome ainda processam em Python o que sobrar depois do
  SQL** → Mitigação: aceitável na escala deste projeto (ver Non-Goals); os filtros de coluna
  direta (posição, condição, clube, idade) já reduzem o conjunto antes desse ponto, e o teto de
  jogadores de uma liga fictícia está longe de justificar `unaccent`/trigram no banco.
- **[Risco] Pydantic exige parsing de `sort` com até dois valores em uma string separada por
  vírgula** → Mitigação: um `field_validator` dedicado faz o split e valida cada parte contra o
  enum, rejeitando repetição do mesmo campo.
- **[Risco] Índice parcial em `excluido_em` é sintaxe específica do Postgres** (`CREATE INDEX ...
  WHERE excluido_em IS NULL`) → Mitigação: sem problema aqui, porque o banco da aplicação é
  Postgres (decisão já fechada); só importaria se o projeto precisasse suportar múltiplos bancos.
