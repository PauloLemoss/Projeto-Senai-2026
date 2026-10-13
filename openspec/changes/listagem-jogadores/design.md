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

### Filtrar e ordenar por valor de mercado em Python, não em SQL

Mesmo o barema permitindo a fórmula duplicada em SQL sem penalidade, a decisão é **não usar esse
atalho**: o repositório busca todos os jogadores ativos (`excluido_em IS NULL`) com um único
`SELECT`, e o `service.listar()` aplica busca, filtros, ordenação e paginação inteiramente em
Python, reaproveitando `calculos.calcular_valor_de_mercado` — a mesma função usada por
`consultar()`. Isso elimina de vez a possibilidade de `GET /players?min_value=...` filtrar por um
número e `GET /players/{id}` devolver outro para o mesmo jogador.

**Alternativa considerada e rejeitada**: reimplementar RN02–RN05 como expressão SQL (`CASE WHEN`)
para filtrar/ordenar no banco. Mais eficiente, mas motivo de rejeição é equivalente ao do exemplo
de ficha de avaliação (B14): duas implementações da mesma regra divergem silenciosamente, e só a
automação de teste pega isso tarde. Com o volume de dados deste projeto (dezenas a poucas
centenas de jogadores), buscar tudo e processar em Python no service é instantâneo e sem risco de
divergência.

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

- **[Risco] Buscar todos os jogadores ativos a cada listagem** → Mitigação: aceitável na escala
  deste projeto (ver Non-Goals); se o volume crescesse, o próximo passo seria mover só os filtros
  "baratos" (posição, condição, livre/clube, idade — colunas diretas, sem cálculo) para o SQL,
  mantendo busca por valor em Python.
- **[Risco] Pydantic exige parsing de `sort` com até dois valores em uma string separada por
  vírgula** → Mitigação: um `field_validator` dedicado faz o split e valida cada parte contra o
  enum, rejeitando repetição do mesmo campo.
