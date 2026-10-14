## Context

Terceiro módulo do backend, depois de `jogadores` e `clubes` (ambos arquivados). Mesma
arquitetura em camadas (Router → Service → Repository). Duas diferenças novas em relação às
changes anteriores:

1. **Operações compostas**: compra e venda escrevem em quatro lugares cada (jogador, clube,
   contrato, transação) e precisam rodar numa única transação de banco — nenhuma capability
   anterior precisou disso (`jogadores`/`clubes` só escrevem uma linha por operação).
2. **Datas na API**: `loyalty_until` (entrada) e `created_at`/`loyalty_until` (saída) são os
   primeiros campos de data/hora que a API aceita ou devolve — `criado_em`/`atualizado_em` de
   `jogadores`/`clubes` são só colunas internas, nunca aparecem numa resposta.

## Goals / Non-Goals

**Goals:**
- Implementar RN12 a RN18 (compra, venda, histórico, exportação CSV).
- Garantir que compra e venda sejam atômicas (barema exige "cada uma numa transação do banco").
- Acrescentar o campo `contract` ao elenco de `GET /clubs/{id}` (capability `clubes`), reaproveitando
  o mesmo cálculo de dias restantes/percentual de multa usado na venda — o barema trata isso
  explicitamente como "não pode ser cálculo duplicado".
- Resolver o formato de data/hora (RN01) de forma reaproveitável pela futura `liga`.

**Non-Goals:**
- Escalação, partidas, classificação (capability `liga` futura) — só nasce depois de `contratos`
  e `transacoes` existirem, mas o fluxo de escalação em si é outra change.
- Qualquer UI — este design cobre só o backend.

## Decisions

### Operações compostas são atômicas via uma pequena abstração de unidade de trabalho

Compra toca `jogadores.clube_id`, `clubes.caixa`, `contratos` (insert) e `transacoes` (insert);
venda toca as mesmas quatro, em sentido inverso. O padrão já usado por `JogadorRepository.salvar`
e `ClubeRepository.salvar` (cada chamada comita sozinha) não serve aqui: comitar a cada escrita
permitiria um estado parcial (ex.: caixa debitado sem o contrato criado) se uma escrita seguinte
falhar.

`MercadoService.comprar`/`vender` ficam donos da transação:
- `Jogador` e `Clube`, já anexados à mesma `Session` pelos `obter()` existentes de
  `JogadorRepository`/`ClubeRepository`, são mutados diretamente (`jogador.clube_id = ...`,
  `clube.caixa -= ...`) em vez de passar pelo `salvar()` que comita sozinho.
- `ContratoRepository`/`TransacaoRepository` ganham um método `adicionar(...)` que só agenda a
  escrita (equivalente a `session.add`), sem comitar.
- O commit (ou rollback, se uma regra de negócio for violada no meio da operação) acontece uma
  única vez, no fim, por uma abstração `UnidadeDeTrabalho` (`Protocol` com `confirmar`/`desfazer`,
  implementada sobre a `Session` do SQLAlchemy) injetada no `MercadoService` — o service continua
  dependendo só de abstrações (DIP), nunca do SQLAlchemy diretamente. O fake de teste é um no-op
  (os repositórios fake já mutam objetos em memória sem conceito de transação).

**Alternativa considerada e rejeitada**: acrescentar um parâmetro `commit=False` em
`JogadorRepository.salvar`/`ClubeRepository.salvar`. Rejeitada porque mistura duas
responsabilidades (persistir uma entidade vs. participar de uma transação maior) na mesma
assinatura, e exigiria mudar a interface já implementada e testada de `jogadores`/`clubes` só
para um caso de uso que apenas `mercado` tem.

### RN15 (dias restantes e percentual de multa) é função pura, reaproveitada por `clubes`

A regra "dias restantes = fim da fidelidade − momento, arredondado pra cima; percentual pela
faixa" é usada duas vezes: na venda (para calcular a multa) e na consulta do clube (para mostrar
`remaining_days`/`penalty_rate` de cada jogador do elenco, "como se fosse vendido agora"). O
próprio barema cita essa regra como exemplo do que não pode ser cálculo duplicado.

Decisão: `calcular_dias_restantes_e_percentual_de_multa(fidelidade_ate, momento) -> (int, int)`
vive em `mercado/calculos.py` (função pura, sem HTTP nem banco, no mesmo espírito de
`jogadores/calculos.py`). `ClubeService` passa a receber também um `ContratoRepository` (a mesma
composição por injeção já usada com `JogadorRepository` desde a change `clubes`) e chama essa
função para montar `contract` de cada jogador do elenco. Não há import circular: `mercado.calculos`
não importa nada de `clubes`, só `datetime`/`decimal`.

### Recompra do mesmo clube: consulta ao histórico de transações

RN12 proíbe um clube comprar de volta um jogador que ele mesmo vendeu (outro clube pode).
`TransacaoRepository` ganha `existe_venda(clube_id, jogador_id) -> bool`, consultando se há uma
transação `VENDA` daquele clube para aquele jogador — reaproveita a tabela que já é a fonte da
verdade do histórico, em vez de uma coluna ou flag nova.

### Limite de elenco (RN14): reaproveita a mesma listagem de `jogadores`

Para contar o elenco antes da compra, `MercadoService` chama
`jogador_repository.listar(FiltrosSql(club_id=clube_id))` — o mesmo método que `clubes` já usa
para montar o elenco — em vez de um `COUNT` próprio.

### RN01 (data e hora): fuso fixo, não biblioteca de timezone

O enunciado exige `-03:00` sempre, "sem horário de verão" — é mais seguro fixar o offset
(`timezone(timedelta(hours=-3))`) do que depender de um fuso nomeado (`ZoneInfo("America/
Sao_Paulo")`), que carrega regras históricas de horário de verão no banco de dados de fusos do
sistema operacional. Um módulo novo, `core/datas.py`, concentra: a constante do fuso, o parser de
entrada (`AAAA-MM-DDTHH:MM-03:00`, rejeitando outro formato ou data/hora inexistente) e o
formatador de saída (`AAAA-MM-DDTHH:MM:SS-03:00`). Isso é o que a requirement nova de
`api-conventions` (RN01) formaliza, e o que `mercado` consome para `loyalty_until`/`created_at` —
a mesma função que a futura `liga` vai usar para `jogada_em`.

### Exportação CSV: biblioteca padrão `csv`, sem dependência nova

O formato pedido pela RN18 (separador `;`, aspas duplas quando o campo tem `;` ou `"`, aspa
interna duplicada) é exatamente o comportamento padrão do módulo `csv` da biblioteca padrão do
Python com `delimiter=";"`, `quotechar='"'` e `quoting=csv.QUOTE_MINIMAL` — não precisa de
escaping escrito à mão. `lineterminator="\n"` força LF (o padrão do módulo é `\r\n`). O volume por
clube é pequeno (histórico de transações de um único clube), então o CSV inteiro é montado em
memória (`io.StringIO`), sem streaming.

### Estrutura de pastas

```
backend/src/mercado_jogadores/mercado/
├── __init__.py
├── models.py       # tabelas contratos e transacoes
├── calculos.py      # taxa, multa (RN15), comissão (RN16); reaproveita arredondar de jogadores
├── repository.py    # ContratoRepository, TransacaoRepository (Protocol + SQLAlchemy)
├── unidade_de_trabalho.py  # UnidadeDeTrabalho (Protocol + implementação sobre a Session)
├── service.py       # MercadoService: comprar, vender, historico, exportar_csv
├── schemas.py       # BuyRequest, SellRequest/TransactionRead, TransactionHistoryResponse
└── router.py        # POST /players/{id}/buy, /sell; GET /clubs/{id}/transactions[/export]
```

`core/datas.py` concentra o utilitário de data/hora (RN01), reaproveitado por `mercado` e, depois,
por `liga`.

## Risks / Trade-offs

- **[Risco] `UnidadeDeTrabalho` é um conceito novo no projeto, não usado por `jogadores`/`clubes`**
  → Mitigação: Protocol mínimo (`confirmar`/`desfazer`), implementação real é só
  `session.commit()`/`session.rollback()`; o fake de teste é um no-op, sem lógica a testar à
  parte.
- **[Risco] `ClubeService` passa a depender de `mercado.calculos` e `ContratoRepository`,
  invertendo a direção "intuitiva" (clubes nasceu antes de mercado)** → Mitigação: é só uma
  função pura e uma leitura (Protocol), no mesmo padrão de composição já usado com
  `JogadorRepository`; sem import circular real (`mercado.calculos` não importa `clubes`).
- **[Risco] Falha no meio de uma compra/venda deixar o objeto `Jogador`/`Clube` mutado em memória,
  mesmo sem commit** → Mitigação: toda regra de negócio que pode recusar a operação (RN12 a RN16)
  é checada **antes** de qualquer mutação nos objetos; a única escrita que pode falhar depois das
  mutações é a do próprio banco (violação de constraint), e aí o rollback da `UnidadeDeTrabalho`
  desfaz tudo.
- **[Risco] Fuso fixo (`timezone(timedelta(hours=-3))`) diverge de `ZoneInfo("America/Sao_Paulo")`
  se o Brasil reintroduzir horário de verão** → Aceito: o enunciado é explícito ("sem horário de
  verão"), então o fuso fixo é o comportamento exigido, não uma simplificação.

## Migration Plan

Nova migration cria `contratos` e `transacoes` (tabelas novas, sem dado existente para migrar);
FKs para `jogadores.id` e `clubes.id`, sem `ON DELETE CASCADE` (política já adotada — nenhuma das
duas tabelas é deletada). `alembic downgrade base && alembic upgrade head` recria tudo do zero,
como nas changes anteriores.
