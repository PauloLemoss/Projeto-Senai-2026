## 1. Infraestrutura e banco de dados

- [x] 1.1 Mover `mercado/unidade_de_trabalho.py` para `core/unidade_de_trabalho.py` (sem mudar o
      conteúdo), atualizar o import em `mercado/service.py`. Verificar rodando
      `poetry run pytest` da suíte de `mercado` inteira passando, sem nenhuma outra mudança.
- [x] 1.2 Criar `liga/models.py` com as tabelas `escalacoes` (PK composta `clube_id`+
      `jogador_id`), `partidas` e `duelos_partida`, conforme "3. Estrutura de tabelas", com as FKs
      para `clubes.id`/`jogadores.id`/`partidas.id` (sem `ON DELETE CASCADE`). Registrar os
      models em `alembic/env.py`. Verificar com `alembic revision --autogenerate` detectando as
      três tabelas novas sem diffs espúrios, e `alembic upgrade head` /
      `alembic downgrade base && alembic upgrade head` aplicando sem erro.

## 2. Cálculos puros (RN19, RN20)

- [x] 2.1 Criar `liga/calculos.py` com `FORMACOES` (mapa `formation -> {defesa, meio, ataque}`,
      as 4 formações da tabela da RN19) e
      `formacao_fecha_com_as_posicoes(formation, posicoes: list[str]) -> bool` (1 GOL + a
      contagem de cada setor bate exatamente). Verificar com testes unitários cobrindo as 4
      formações aceitas e pelo menos um caso de cada tipo de recusa (goleiro errado, setor a
      mais/a menos).
- [x] 2.2 Criar `arredondar_inteiro(valor: Decimal) -> int` (RN20.3: `ROUND_HALF_UP` para 0 casas)
      e `aplicar_efeito_de_condicao(atributo: int, condicao: str) -> int` (−15% só se
      `MAL_CONDICIONADO`, arredondado). Verificar com testes cobrindo os dois exemplos do
      enunciado (74×0,85=62,9→63; 50×0,85=42,5→43) e que `APTO` devolve o atributo sem mudança.
- [x] 2.3 Criar `montar_duelos(titulares_mandante, titulares_visitante) -> list[DueloCalculado]`
      (RN20.4-6): cada lista de titulares é `[goleiro, 1º, 2º, 3º, 4º]` (ordem do elenco); monta
      os 6 duelos fixos por índice (4º-vs-goleiro, 3º-vs-1º, 2º-vs-2º, uma vez pro mandante
      atacando e outra pro visitante), usando o atributo da posição do atacante
      (`finalizacao`/ATA, `passe`/MEI, `drible`/ZAG e LAT) e `defesa` do defensor, já com
      `aplicar_efeito_de_condicao`, decidindo `gol` (ataque > defesa). Verificar reproduzindo
      exatamente a tabela de exemplo da RN20 (Águias FC × Delta FC, os 6 duelos e os valores).
- [x] 2.4 Criar `calcular_placar_e_resultado(duelos) -> tuple[int, int, str]` (gols do mandante =
      duelos 1-3 com `gol`; gols do visitante = duelos 4-6; `result` `MANDANTE`/`VISITANTE`/
      `EMPATE`). Verificar com o placar do exemplo da RN20 (1×2, `VISITANTE`).

## 3. Repositórios

- [x] 3.1 Criar `liga/repository.py` com `EscalacaoRepository` (`Protocol`:
      `listar_titulares_do_clube`, `substituir_escalacao_do_clube`, `remover_titular`) e
      `PartidaRepository` (`Protocol`: `adicionar`, `listar`, `obter`), mais as implementações
      SQLAlchemy. `substituir_escalacao_do_clube`/`remover_titular`/`adicionar` SHALL só agendar
      a escrita, nunca comitar (mesmo padrão de `ContratoRepository`). Verificar com testes de
      integração contra o Postgres real: substituir escalação, listar titulares na ordem
      inserida, remover um titular, e `adicionar`/`listar`/`obter` de partidas.
- [x] 3.2 Criar os repositórios fake de escalação e partida em `tests/conftest.py`. Verificar com
      um teste de ida-e-volta de cada fake.

## 4. Service

- [x] 4.1 Modificar `JogadorService.__init__` para receber também `escalacao_repository` e
      `unidade_de_trabalho` (de `core/unidade_de_trabalho.py`); `alterar_condicao`, quando a nova
      condição é `DOENTE`, muta a condição diretamente, chama
      `escalacao_repository.remover_titular(jogador_id)` e confirma pela unidade de trabalho, na
      mesma operação (RN19.5). As demais operações (`cadastrar`, `editar`, `excluir`) continuam
      usando `self._repository.salvar()`. Verificar com um teste unitário (repositório fake)
      cobrindo "titular que fica DOENTE sai da escalação", e que os testes já existentes de
      `JogadorService` continuam passando com os fakes novos.
- [x] 4.2 Modificar `MercadoService.__init__` para receber também `escalacao_repository`;
      `vender` chama `escalacao_repository.remover_titular(jogador_id)` antes de confirmar (RN19.5).
      Verificar com um teste unitário cobrindo "venda de titular sai da escalação", e que os
      testes já existentes de `MercadoService` continuam passando.
- [x] 4.3 Implementar `LigaService.escalar` (RN19.1-4, 19.7): valida clube e os 5 jogadores
      existentes, cada um do elenco do clube e não `DOENTE`, e que as posições fecham a formação
      (`formacao_fecha_com_as_posicoes`); muta `clube.formacao` e chama
      `escalacao_repository.substituir_escalacao_do_clube`, confirmando pela unidade de trabalho.
      Verificar com testes unitários cobrindo cada `#### Scenario` da requirement "Escalação
      substitui os titulares do clube numa única operação".
- [x] 4.4 Implementar `LigaService.consultar_escalacao` (RN19.6), reaproveitando
      `jogador_repository.listar(FiltrosSql(club_id=...))` e a mesma ordenação do elenco já usada
      por `ClubeService` (GOL, ZAG, LAT, MEI, ATA, nome, id), filtrada pelos ids escalados.
      Verificar com testes cobrindo clube sem escalação, com escalação completa, e incompleta
      (depois de uma venda ou de um titular ficar `DOENTE`).
- [x] 4.5 Implementar `LigaService.jogar_partida` (RN20): valida mandante ≠ visitante, os dois
      clubes existem e têm escalação completa (5 titulares cada); monta os titulares de cada
      clube na ordem do elenco, calcula os 6 duelos e o placar (`liga/calculos.py`), grava
      `Partida` e os 6 `DueloPartida`, confirmando pela unidade de trabalho. Verificar com um
      teste unitário reproduzindo de ponta a ponta o exemplo da RN20 (placar, `result`, os 6
      duelos) e os `#### Scenario` de recusa (mandante=visitante, clube inexistente, escalação
      incompleta).
- [x] 4.6 Implementar `LigaService.historico`, `.consultar_partida` e `.classificacao` (RN21):
      histórico ordenado (mais recente primeiro, empate por id decrescente) com filtro opcional
      por `club_id`; classificação calculada em memória a partir de todas as partidas, com todos
      os clubes (inclusive zerados) e os desempates da RN21.4. Verificar com um teste unitário
      reproduzindo o exemplo de classificação do enunciado (6 clubes, 4 partidas).

## 5. Schemas e router

- [x] 5.1 Criar `liga/schemas.py` com `LineupUpdate` (`formation`, `player_ids`: exatamente 5
      inteiros positivos distintos), `LineupRead` (`club_id`, `formation`, `complete`, `players`
      reaproveitando `JogadorRead`), `MatchCreate` (`home_club_id`, `away_club_id`, distintos),
      `MatchRead` (com `duels` opcional para a listagem) e `StandingRead`. Verificar com testes
      unitários de schema cobrindo os limites de `player_ids` e de `home_club_id`/`away_club_id`.
- [x] 5.2 Implementar `PUT /clubs/{id}/lineup` e `GET /clubs/{id}/lineup` em `liga/router.py`.
      Verificar com `GET /docs` listando os 2 endpoints e um teste de integração de escalação
      feliz (`200`, corpo conforme o exemplo 2.4.1 do enunciado).
- [x] 5.3 Implementar `POST /matches`, `GET /matches`, `GET /matches/{id}` e `GET /standings`.
      Verificar com `GET /docs` listando os 4 endpoints e um teste de integração de partida feliz
      (`201` com `Location`, corpo conforme o exemplo 2.4.2 do enunciado).

## 6. Testes de integração de ponta a ponta

- [x] 6.1 Testes via `TestClient` cobrindo cada `#### Scenario` das requirements de escalação da
      spec `liga` contra o Postgres real (escalação válida substitui a anterior, jogador fora do
      elenco, jogador `DOENTE`, posições que não fecham a formação, `formation`/`player_ids` fora
      do formato, clube/jogador inexistente, consulta sem/com escalação). Verificar rodando
      `poetry run pytest` com tudo passando.
- [x] 6.2 Teste via `TestClient` cobrindo "titular sai da escalação ao ser vendido" (compra real,
      escala, vende, confere `GET /clubs/{id}/lineup` incompleta) e "titular sai da escalação ao
      ficar DOENTE" (idem, com `PATCH .../condition`), incluindo "o jogador não volta sozinho".
- [x] 6.3 Testes via `TestClient` cobrindo cada `#### Scenario` da requirement de partida contra o
      Postgres real, reproduzindo de ponta a ponta o exemplo da RN20 (placar, `result`, os 6
      duelos gravados), e os cenários de recusa (mandante=visitante, clube inexistente, escalação
      incompleta) e a checagem de "não muda caixa, escalação nem jogadores".
- [x] 6.4 Testes via `TestClient` cobrindo histórico (ordem, filtro por `club_id`, clube
      inexistente), detalhe de uma partida (os 6 duelos, partida inexistente) e classificação
      (reproduzindo o exemplo do enunciado com 6 clubes e 4 partidas, e um clube sem jogar
      aparecendo zerado).

## 7. Cobertura

- [x] 7.1 Medir a cobertura e fechar as lacunas que forem regra de negócio real, pelo mesmo
      critério das changes anteriores.

## 8. Documentação

- [x] 8.1 Atualizar o README: remover "Liga" da lista de pendências (o projeto passa a ter os 4
      módulos do backend completos) e acrescentar as decisões de `UnidadeDeTrabalho` em `core/`,
      do arredondamento inteiro do efeito de condição, e de como os duelos são montados por
      índice do jogador de linha, não por formação.
