## Context

Segundo módulo do backend, depois de `jogadores` (arquivada). Mesma arquitetura em camadas
(Router → Service → Repository), agora com um segundo módulo de domínio (`clubes/`) que precisa
compor com `jogadores` para calcular o elenco — ver "Decisions" abaixo.

## Goals / Non-Goals

**Goals:**
- Implementar RN10 (criação, unicidade) e a parte de RN11 que já dá pra testar sem o módulo
  Mercado (listagem, elenco vazio, valor do elenco e patrimônio calculados corretamente).
- Reaproveitar o que `jogadores` já construiu (cálculo de valor de mercado, ordem das posições,
  filtro por `club_id`) em vez de duplicar.
- Adicionar a FK pendente de `jogadores.clube_id` para `clubes.id`.

**Non-Goals:**
- Campo `contract` no elenco de `GET /clubs/{id}` — depende da tabela `contratos`, que só existe
  quando a capability `mercado` (compra) for implementada.
- Qualquer endpoint de compra/venda, ou o campo `formacao` sendo de fato usado (existe na tabela,
  mas só a capability `liga` futura vai lê-lo/escrevê-lo).

## Decisions

### `ClubeService` compõe com `JogadorRepository`, não duplica a busca do elenco

Para montar `squad_value` e o elenco ordenado, o `ClubeService` recebe, além do
`ClubeRepository`, o mesmo `JogadorRepository` já existente — e chama
`jogador_repository.listar(FiltrosSql(club_id=clube_id))`, o método que a capability `jogadores`
já construiu e testou para a listagem (RN07). O valor de mercado de cada jogador do elenco é
calculado com `calculos.calcular_valor_de_mercado`, a mesma função de sempre — nenhuma fórmula
nova, nenhuma query nova.

**Alternativa considerada e rejeitada**: o `ClubeRepository` fazer um JOIN direto
`clubes`/`jogadores` e devolver tudo numa consulta só. Mais "eficiente" numa única query, mas
criaria uma segunda forma de buscar "jogadores de um clube" (a primeira já existe em
`JogadorRepository.listar`), com risco de as duas divergirem se uma regra de filtro mudar (ex.:
jogador excluído não deve aparecer) e só uma delas for atualizada.

### Unicidade do nome: coluna `nome_normalizado` com índice único (RN10)

RN10 exige unicidade **ignorando maiúsculas e minúsculas, mas considerando acentos** — não é a
mesma comparação do SQL `LOWER()` puro em todo banco (colation sensível a acento varia por
instalação). A aplicação grava `nome_normalizado` (o nome em minúsculas, sem mexer em acento) a
cada criação, e a coluna tem `UNIQUE` no banco — exigência explícita do barema (B3, "a unicidade
do nome deve ser garantida também no banco").

### Validação da sigla: função pura, não expressão regular

A regra ("três letras que aparecem no nome, nessa ordem, a primeira sendo a primeira letra do
nome") não é uma regex simples de escrever nem de ler depois. Vira uma função pura em
`clubes/validacao.py`: reduz o nome às letras (sem espaço/hífen/ponto), ignora acento e caixa, e
confere que a sigla é uma subsequência que começa no índice 0.

```python
def sigla_corresponde_ao_nome(nome: str, sigla: str) -> bool:
    alvo = sigla.lower()
    if len(set(alvo)) == 1:  # as três letras não podem ser todas iguais
        return False
    letras = [c for c in normalizar_para_busca(nome) if c.isalpha()]
    if not letras or letras[0] != alvo[0]:
        return False
    resto = iter(letras[1:])
    return all(c in resto for c in alvo[1:])
```

Reaproveita `normalizar_para_busca` (`core/validation.py`, já usada pela busca de RN07) em vez de
reimplementar remoção de acento.

### Estrutura de pastas

```
backend/src/mercado_jogadores/clubes/
├── __init__.py
├── models.py       # tabela clubes (nome, nome_normalizado, sigla, caixa, formacao, criado_em)
├── validacao.py     # sigla_corresponde_ao_nome (função pura, sem HTTP nem banco)
├── repository.py    # Protocol + implementação SQLAlchemy
├── service.py       # ClubeService: cadastrar, consultar, listar
├── schemas.py       # ClubeCreate, ClubeRead, ClubeListQuery
└── router.py        # os 3 endpoints
```

## Risks / Trade-offs

- **[Risco] `ClubeService` depender de `JogadorRepository` cria acoplamento entre módulos** →
  Mitigação: é uma dependência de leitura só (`listar`), já existente e testada; a alternativa
  (JOIN direto ou duplicar a query) é pior pelos motivos acima.
- **[Risco] Elenco sempre vazio nesta change torna a ordenação (GOL/ZAG/LAT/MEI/ATA, nome, id)
  impossível de testar via API de ponta a ponta** → Mitigação: testada diretamente no
  `ClubeService` com um repositório de jogadores fake, atribuindo `clube_id` manualmente nos
  dados de teste (sem precisar de endpoint de compra) — mesma técnica já usada nos testes de
  "jogador com clube" da capability `jogadores`.
- **[Risco] Migration adiciona uma FK (`jogadores.clube_id` → `clubes.id`) numa tabela que já tem
  dados em produção/desenvolvimento** → Mitigação: sem risco aqui porque não há ambiente de
  produção; no pior caso, um jogador de teste com `clube_id` apontando para um clube inexistente
  (não deveria existir, já que só a compra define `clube_id`, e compra ainda não existe) quebraria
  a migration — o passo de verificação da task confere isso antes de aplicar.
