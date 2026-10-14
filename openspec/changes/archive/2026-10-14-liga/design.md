## Context

Quarto e último módulo funcional, depois de `jogadores`, `clubes` e `mercado` (todos arquivados).
Duas diferenças em relação às changes anteriores:

1. **Efeitos colaterais entre módulos**: vender um jogador (`mercado`) ou marcá-lo `DOENTE`
   (`jogadores`) agora também precisa tirá-lo da escalação (`liga`), na mesma operação atômica
   (RN19.5, confirmado pelo glossário: "Operação atômica... assim como a alteração de condição que
   tira um titular da escalação").
2. **Um cálculo novo de arredondamento**: o efeito de `MAL_CONDICIONADO` na partida arredonda para
   **inteiro** (`74 × 0,85 = 62,9 → 63`), diferente do arredondamento de 2 casas usado em todo
   lugar em dinheiro.

## Goals / Non-Goals

**Goals:**
- Implementar RN19 (escalação), RN20 (partida) e RN21 (histórico e classificação).
- Fazer a venda e a alteração de condição para `DOENTE` tirarem o titular da escalação, na mesma
  transação de cada uma (sem duplicar essa regra nos dois lugares).
- Reaproveitar a ordem do elenco (GOL, ZAG, LAT, MEI, ATA, nome, id) já construída por
  `jogadores`/`clubes`, tanto para numerar os jogadores de linha quanto para a resposta de
  `GET /clubs/{id}/lineup`.

**Non-Goals:**
- Qualquer UI — este design cobre só o backend.
- Qualquer alteração de regra de negócio de `jogadores`/`clubes`/`mercado` além do efeito pontual
  "sai da escalação" (ver Decisions).

## Decisions

### `UnidadeDeTrabalho` sobe para `core/`, reaproveitada por `jogadores`, `mercado` e `liga`

Hoje ela vive em `mercado/unidade_de_trabalho.py`. Para `JogadorService.alterar_condicao` tirar o
titular da escalação na mesma transação (RN19.5), ele precisa do mesmo padrão de "mutar direto +
confirmar/desfazer no fim" já usado em `mercado`. Importar de `mercado` dentro de `jogadores`
inverteria a dependência natural entre capabilities (`jogadores` é a mais antiga e fundamental).
Decisão: mover `UnidadeDeTrabalho`/`SQLAlchemyUnidadeDeTrabalho` para `core/unidade_de_trabalho.py`
(puro infraestrutura, sem regra de negócio — no mesmo nível de `core/db.py`); `mercado` passa a
importar de lá, sem mudar de comportamento.

### `EscalacaoRepository` é composto por `JogadorService` e `MercadoService`, sem duplicar a regra

RN19.5 ("sai da escalação ao ser vendido ou ficar `DOENTE`") é uma regra só, mas tem dois
gatilhos. Em vez de duplicá-la, um único método, `EscalacaoRepository.remover_titular(jogador_id)`
(`DELETE` que só agenda a escrita, sem comitar — mesmo padrão de `ContratoRepository.adicionar`),
é chamado tanto por `MercadoService.vender` quanto por `JogadorService.alterar_condicao` (só
quando a nova condição é `DOENTE`), cada um confirmando pela própria `UnidadeDeTrabalho` já
existente (a de `mercado`) ou nova (a de `jogadores`, adicionada agora).

`JogadorService.__init__` ganha dois parâmetros novos (`escalacao_repository`,
`unidade_de_trabalho`), usados só por `alterar_condicao`; `cadastrar`/`editar`/`excluir` continuam
exatamente como estão (chamando `self._repository.salvar()`, que comita sozinho — não há operação
composta nesses casos).

**Alternativa considerada e rejeitada**: deixar o router, depois de chamar
`JogadorService.alterar_condicao`, chamar separadamente `EscalacaoRepository.remover_titular` e
comitar. Rejeitada porque são duas transações (duas chances de falha parcial), violando a regra
explícita de "operação atômica" do glossário.

### "Quem ataca e quem defende" é fixo pelo índice do jogador de linha, não pela posição

A tabela da RN20 (4º ataca o goleiro, 3º ataca o 1º, 2º ataca o 2º) não depende da formação nem da
posição de cada jogador — só da ordem dele entre os 4 jogadores de linha (já numerados pela ordem
do elenco). `liga/calculos.py::montar_duelos` implementa isso como três pares fixos de índice
(3º/0º-goleiro, 2º/1º, 1º/2º, zero-indexado), aplicados uma vez para o mandante atacando e outra
para o visitante — nenhuma tabela por formação é necessária aqui (a formação só entra na
*validação* da escalação, RN19, nunca no cálculo do duelo).

### Efeito de `MAL_CONDICIONADO` na partida: arredondamento para inteiro, função própria

`arredondar_inteiro` (`ROUND_HALF_UP` para 0 casas, igual em espírito ao `arredondar` de 2 casas
de `jogadores/calculos.py`, mas para atributos inteiros) vive em `liga/calculos.py`. O atributo
usado por cada titular (ataque pela posição; defesa sempre `defending`) já entra com esse efeito
aplicado — os atributos gravados no jogador nunca mudam (RN20.3).

### Classificação é calculada em memória, sem agregação em SQL

Com no máximo 20 clubes (RN10) e um volume de partidas pequeno para um estudo de caso, buscar
todas as partidas do banco e agregar em Python (`LigaService.classificacao`) é simples e correto,
sem risco de divergir de uma segunda implementação em SQL — mesmo critério já usado para valor de
mercado e patrimônio.

### Estrutura de pastas

```
backend/src/mercado_jogadores/liga/
├── __init__.py
├── models.py       # tabelas escalacoes, partidas, duelos_partida
├── calculos.py      # arredondar_inteiro, montar_duelos, placar/result
├── repository.py    # EscalacaoRepository, PartidaRepository (Protocol + SQLAlchemy)
├── service.py       # LigaService: escalar, consultar_escalacao, jogar_partida,
│                     # historico, consultar_partida, classificacao
├── schemas.py       # LineupUpdate, LineupRead, MatchCreate, MatchRead, StandingRead
└── router.py        # os 6 endpoints
```

`core/unidade_de_trabalho.py` (movido de `mercado/`) é reaproveitado por `jogadores`, `mercado` e
`liga`.

## Risks / Trade-offs

- **[Risco] `JogadorService` ganha uma dependência de `liga` (`EscalacaoRepository`), um módulo que
  nasce depois dele** → Mitigação: é só uma escrita de remoção (DIP via `Protocol`), no mesmo
  padrão de composição já usado em `clubes`→`mercado`; sem import circular (o `Protocol` de
  `EscalacaoRepository` não precisa importar nada de `jogadores`).
- **[Risco] Mover `UnidadeDeTrabalho` de `mercado/` para `core/` quebra o import existente** →
  Mitigação: é só um `Protocol` + uma implementação sobre `Session`, sem regra de negócio;
  `mercado/service.py` só troca o `import`, comportamento idêntico, suíte de `mercado` cobre a
  regressão.
- **[Risco] `POST /matches` grava 6 `duelos_partida` + 1 `partida` numa unica operação; qualquer
  falha no meio deixaria duelos órfãos** → Mitigação: mesmo padrão de `UnidadeDeTrabalho` das
  changes anteriores — tudo mutado/agendado antes de um único `confirmar()`.

## Migration Plan

Nova migration cria `escalacoes` (PK composta `clube_id`+`jogador_id`, sem `ON DELETE CASCADE`,
única tabela com `DELETE` real no domínio), `partidas` e `duelos_partida` (logs imutáveis, como
`transacoes`). `alembic downgrade base && alembic upgrade head` recria tudo do zero, como nas
changes anteriores.
