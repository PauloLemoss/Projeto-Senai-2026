from datetime import datetime

from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.liga.models import DueloPartida, Partida
from mercado_jogadores.liga.repository import FiltrosDePartida
from tests.conftest import FakeEscalacaoRepository, FakePartidaRepository

_MOMENTO = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)


class TestFakeEscalacaoRepository:
    def test_substituir_e_listar_titulares(
        self, fake_escalacao_repo: FakeEscalacaoRepository
    ) -> None:
        fake_escalacao_repo.substituir_escalacao_do_clube(1, [10, 20, 30], _MOMENTO)

        assert fake_escalacao_repo.listar_titulares_do_clube(1) == [10, 20, 30]

    def test_remover_titular(self, fake_escalacao_repo: FakeEscalacaoRepository) -> None:
        fake_escalacao_repo.substituir_escalacao_do_clube(1, [10, 20], _MOMENTO)

        fake_escalacao_repo.remover_titular(10)

        assert fake_escalacao_repo.listar_titulares_do_clube(1) == [20]


class TestFakePartidaRepository:
    def test_adicionar_atribui_id_e_obter_retorna_a_mesma_partida(
        self, fake_partida_repo: FakePartidaRepository
    ) -> None:
        partida = Partida(
            mandante_id=1,
            visitante_id=2,
            gols_mandante=1,
            gols_visitante=0,
            formacao_mandante="2-1-1",
            formacao_visitante="2-1-1",
            jogada_em=_MOMENTO,
        )

        salva = fake_partida_repo.adicionar(partida)

        assert salva.id is not None
        assert fake_partida_repo.obter(salva.id) is salva

    def test_adicionar_duelo_e_listar_duelos_na_ordem(
        self, fake_partida_repo: FakePartidaRepository
    ) -> None:
        partida = fake_partida_repo.adicionar(
            Partida(
                mandante_id=1,
                visitante_id=2,
                gols_mandante=0,
                gols_visitante=0,
                formacao_mandante="2-1-1",
                formacao_visitante="2-1-1",
                jogada_em=_MOMENTO,
            )
        )
        for ordem in (2, 1):
            fake_partida_repo.adicionar_duelo(
                DueloPartida(
                    partida_id=partida.id,
                    ordem=ordem,
                    clube_atacante_id=1,
                    atacante_id=1,
                    defensor_id=2,
                    nome_atacante="A",
                    nome_defensor="D",
                    posicao_atacante="ATA",
                    posicao_defensor="GOL",
                    condicao_atacante="APTO",
                    condicao_defensor="APTO",
                    atributo_ataque="shooting",
                    atributo_defesa="defending",
                    valor_ataque=75,
                    valor_defesa=72,
                    gol=True,
                )
            )

        duelos = fake_partida_repo.listar_duelos(partida.id)

        assert [d.ordem for d in duelos] == [1, 2]

    def test_listar_filtra_por_clube(self, fake_partida_repo: FakePartidaRepository) -> None:
        fake_partida_repo.adicionar(
            Partida(
                mandante_id=1,
                visitante_id=2,
                gols_mandante=1,
                gols_visitante=0,
                formacao_mandante="2-1-1",
                formacao_visitante="2-1-1",
                jogada_em=_MOMENTO,
            )
        )
        fake_partida_repo.adicionar(
            Partida(
                mandante_id=3,
                visitante_id=4,
                gols_mandante=0,
                gols_visitante=0,
                formacao_mandante="2-1-1",
                formacao_visitante="2-1-1",
                jogada_em=_MOMENTO,
            )
        )

        resultado = fake_partida_repo.listar(FiltrosDePartida(clube_id=1))

        assert len(resultado) == 1
        assert resultado[0].mandante_id == 1
