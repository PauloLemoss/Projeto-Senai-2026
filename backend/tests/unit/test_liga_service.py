from datetime import datetime
from decimal import Decimal

import pytest

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError, RequisicaoInvalidaError
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.repository import FiltrosSql
from mercado_jogadores.liga.models import Partida
from mercado_jogadores.liga.repository import FiltrosDePartida
from mercado_jogadores.liga.service import DadosDeEscalacao, DadosDePartida, LigaService
from tests.conftest import (
    FakeClubeRepository,
    FakeEscalacaoRepository,
    FakeJogadorRepository,
    FakePartidaRepository,
    FakeUnidadeDeTrabalho,
)

_MOMENTO = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)


def _novo_clube(fake_clube_repo: FakeClubeRepository, **sobrescritas: object) -> Clube:
    dados = {
        "nome": "Águias FC",
        "nome_normalizado": "águias fc",
        "sigla": "AGU",
        "caixa": Decimal("300.00"),
    }
    dados.update(sobrescritas)
    return fake_clube_repo.salvar(Clube(**dados))


def _novo_jogador(fake_repo: FakeJogadorRepository, **sobrescritas: object) -> Jogador:
    dados = {
        "nome": "Jogador Teste",
        "posicao": "MEI",
        "agilidade": 70,
        "idade": 25,
        "valor_base": Decimal("40.00"),
        "condicao": "APTO",
        "clube_id": None,
        "velocidade": 70,
        "finalizacao": 60,
        "passe": 70,
        "drible": 60,
        "defesa": 55,
        "fisico": 60,
        "potencial": 75,
    }
    dados.update(sobrescritas)
    return fake_repo.salvar(Jogador(**dados))


def _service(
    fake_clube_repo: FakeClubeRepository,
    fake_repo: FakeJogadorRepository,
    fake_escalacao_repo: FakeEscalacaoRepository,
    fake_partida_repo: FakePartidaRepository,
    fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
) -> LigaService:
    return LigaService(
        fake_clube_repo, fake_repo, fake_escalacao_repo, fake_partida_repo, fake_unidade_de_trabalho
    )


def _titulares_2_1_1(
    fake_repo: FakeJogadorRepository, clube_id: int, **sobrescritas_por_posicao: dict
) -> list[Jogador]:
    """5 titulares do elenco do clube que fecham a formação `2-1-1` (GOL, 2x defesa, 1 MEI, 1 ATA)."""
    posicoes = ["GOL", "ZAG", "LAT", "MEI", "ATA"]
    jogadores = []
    for i, posicao in enumerate(posicoes):
        overrides = dict(sobrescritas_por_posicao.get(posicao, {}))
        jogadores.append(
            _novo_jogador(
                fake_repo, nome=f"Jogador {i}", posicao=posicao, clube_id=clube_id, **overrides
            )
        )
    return jogadores


class TestEscalar:
    def test_escalacao_valida_substitui_a_anterior(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        titulares = _titulares_2_1_1(fake_repo, clube.id)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        # escalação anterior, com outro conjunto de titulares
        outro_jogador = _novo_jogador(fake_repo, nome="Reserva", posicao="GOL", clube_id=clube.id)
        fake_escalacao_repo.substituir_escalacao_do_clube(clube.id, [outro_jogador.id], _MOMENTO)

        resultado = service.escalar(
            clube.id,
            DadosDeEscalacao(formation="2-1-1", player_ids=[j.id for j in titulares]),
            _MOMENTO,
        )

        assert resultado.complete is True
        assert resultado.formation == "2-1-1"
        assert clube.formacao == "2-1-1"
        assert {t.jogador.id for t in resultado.titulares} == {j.id for j in titulares}
        assert outro_jogador.id not in fake_escalacao_repo.listar_titulares_do_clube(clube.id)

    def test_jogador_fora_do_elenco_do_clube_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        titulares = _titulares_2_1_1(fake_repo, clube.id)
        jogador_livre = _novo_jogador(fake_repo, nome="Livre", posicao="ATA", clube_id=None)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        ids = [j.id for j in titulares[:4]] + [jogador_livre.id]

        with pytest.raises(ConflitoError):
            service.escalar(clube.id, DadosDeEscalacao(formation="2-1-1", player_ids=ids), _MOMENTO)

        assert fake_escalacao_repo.listar_titulares_do_clube(clube.id) == []

    def test_jogador_doente_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        titulares = _titulares_2_1_1(fake_repo, clube.id, ATA={"condicao": "DOENTE"})
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(ConflitoError):
            service.escalar(
                clube.id,
                DadosDeEscalacao(formation="2-1-1", player_ids=[j.id for j in titulares]),
                _MOMENTO,
            )

    def test_posicoes_que_nao_fecham_a_formacao_sao_recusadas(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        # 2 goleiros, nenhum MEI -> não fecha 2-1-1
        jogadores = [
            _novo_jogador(fake_repo, nome=f"Jogador {i}", posicao=p, clube_id=clube.id)
            for i, p in enumerate(["GOL", "GOL", "ZAG", "LAT", "ATA"])
        ]
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(ConflitoError):
            service.escalar(
                clube.id,
                DadosDeEscalacao(formation="2-1-1", player_ids=[j.id for j in jogadores]),
                _MOMENTO,
            )

    def test_clube_inexistente_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.escalar(
                999, DadosDeEscalacao(formation="2-1-1", player_ids=[1, 2, 3, 4, 5]), _MOMENTO
            )

    def test_jogador_inexistente_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        titulares = _titulares_2_1_1(fake_repo, clube.id)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        ids = [j.id for j in titulares[:4]] + [999_999]

        with pytest.raises(NaoEncontradoError):
            service.escalar(clube.id, DadosDeEscalacao(formation="2-1-1", player_ids=ids), _MOMENTO)


class TestConsultarEscalacao:
    def test_clube_sem_escalacao(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        resultado = service.consultar_escalacao(clube.id)

        assert resultado.formation is None
        assert resultado.titulares == []
        assert resultado.complete is False

    def test_clube_com_escalacao_completa(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        titulares = _titulares_2_1_1(fake_repo, clube.id)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        service.escalar(
            clube.id,
            DadosDeEscalacao(formation="2-1-1", player_ids=[j.id for j in titulares]),
            _MOMENTO,
        )

        resultado = service.consultar_escalacao(clube.id)

        assert resultado.complete is True
        assert len(resultado.titulares) == 5
        # ordem do elenco: GOL, ZAG, LAT, MEI, ATA
        assert [t.jogador.posicao for t in resultado.titulares] == [
            "GOL",
            "ZAG",
            "LAT",
            "MEI",
            "ATA",
        ]

    def test_clube_com_escalacao_incompleta_depois_de_uma_venda(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        titulares = _titulares_2_1_1(fake_repo, clube.id)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        service.escalar(
            clube.id,
            DadosDeEscalacao(formation="2-1-1", player_ids=[j.id for j in titulares]),
            _MOMENTO,
        )

        fake_escalacao_repo.remover_titular(titulares[0].id)  # simula o efeito da venda/DOENTE

        resultado = service.consultar_escalacao(clube.id)

        assert resultado.complete is False
        assert resultado.formation == "2-1-1"
        assert len(resultado.titulares) == 4

    def test_clube_inexistente_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.consultar_escalacao(999)


def _jogador_do_exemplo(
    fake_repo: FakeJogadorRepository,
    jogador_id: int,
    clube_id: int,
    nome: str,
    posicao: str,
    condicao: str = "APTO",
    **atributos: int,
) -> Jogador:
    base = {
        "nome": nome,
        "posicao": posicao,
        "agilidade": 70,
        "idade": 25,
        "valor_base": Decimal("40.00"),
        "condicao": condicao,
        "clube_id": clube_id,
        "velocidade": 0,
        "finalizacao": 0,
        "passe": 0,
        "drible": 0,
        "defesa": 0,
        "fisico": 0,
        "potencial": 75,
    }
    base.update(atributos)
    return fake_repo.salvar(Jogador(id=jogador_id, **base))


def _escalar_aguias_e_delta(
    fake_clube_repo: FakeClubeRepository, fake_repo: FakeJogadorRepository, service: LigaService
) -> tuple[Clube, Clube]:
    """Reproduz de ponta a ponta o exemplo da RN20: Águias FC (mandante) × Delta FC (visitante),
    os dois no 2-1-1, com o LAT do Águias FC MAL_CONDICIONADO."""
    aguias = _novo_clube(fake_clube_repo)
    delta = _novo_clube(fake_clube_repo, nome="Delta FC", nome_normalizado="delta fc", sigla="DEL")

    titulares_aguias = [
        _jogador_do_exemplo(fake_repo, 30, aguias.id, "Rui Prado", "GOL", defesa=77),
        _jogador_do_exemplo(fake_repo, 32, aguias.id, "Téo Brandão", "ZAG", defesa=84),
        _jogador_do_exemplo(
            fake_repo,
            31,
            aguias.id,
            "Davi Lins",
            "LAT",
            condicao="MAL_CONDICIONADO",
            drible=74,
            defesa=66,
        ),
        _jogador_do_exemplo(fake_repo, 33, aguias.id, "Lauro Neves", "MEI", passe=82),
        _jogador_do_exemplo(fake_repo, 34, aguias.id, "Otto Rangel", "ATA", finalizacao=75),
    ]
    titulares_delta = [
        _jogador_do_exemplo(fake_repo, 40, delta.id, "Ivo Teles", "GOL", defesa=72),
        _jogador_do_exemplo(fake_repo, 41, delta.id, "Hugo Vaz", "ZAG", defesa=84),
        _jogador_do_exemplo(fake_repo, 42, delta.id, "Lino Matos", "LAT", drible=79, defesa=63),
        _jogador_do_exemplo(fake_repo, 43, delta.id, "Nei Soares", "MEI", passe=70),
        _jogador_do_exemplo(fake_repo, 44, delta.id, "Ugo Falcão", "ATA", finalizacao=81),
    ]

    service.escalar(
        aguias.id,
        DadosDeEscalacao(formation="2-1-1", player_ids=[j.id for j in titulares_aguias]),
        _MOMENTO,
    )
    service.escalar(
        delta.id,
        DadosDeEscalacao(formation="2-1-1", player_ids=[j.id for j in titulares_delta]),
        _MOMENTO,
    )
    return aguias, delta


class TestJogarPartida:
    def test_partida_de_ponta_a_ponta_com_o_exemplo_do_enunciado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        aguias, delta = _escalar_aguias_e_delta(fake_clube_repo, fake_repo, service)

        resultado = service.jogar_partida(
            DadosDePartida(home_club_id=aguias.id, away_club_id=delta.id), _MOMENTO
        )

        assert resultado.mandante.goals == 1
        assert resultado.visitante.goals == 2
        assert resultado.mandante.club_name == "Águias FC"
        assert resultado.visitante.club_name == "Delta FC"
        assert resultado.result == "VISITANTE"
        assert resultado.mandante.formation == "2-1-1"
        assert resultado.visitante.formation == "2-1-1"
        assert len(resultado.duelos) == 6
        tabela = [
            (
                d.ordem,
                d.clube_atacante_id,
                d.nome_atacante,
                d.valor_ataque,
                d.nome_defensor,
                d.valor_defesa,
                d.gol,
            )
            for d in resultado.duelos
        ]
        assert tabela == [
            (1, aguias.id, "Otto Rangel", 75, "Ivo Teles", 72, True),
            (2, aguias.id, "Lauro Neves", 82, "Hugo Vaz", 84, False),
            (3, aguias.id, "Davi Lins", 63, "Lino Matos", 63, False),
            (4, delta.id, "Ugo Falcão", 81, "Rui Prado", 77, True),
            (5, delta.id, "Nei Soares", 70, "Téo Brandão", 84, False),
            (6, delta.id, "Lino Matos", 79, "Davi Lins", 56, True),
        ]

    def test_mandante_igual_ao_visitante_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(RequisicaoInvalidaError):
            service.jogar_partida(
                DadosDePartida(home_club_id=clube.id, away_club_id=clube.id), _MOMENTO
            )

    def test_clube_inexistente_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.jogar_partida(DadosDePartida(home_club_id=clube.id, away_club_id=999), _MOMENTO)

    def test_escalacao_incompleta_recusa_a_partida(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        aguias, delta = _escalar_aguias_e_delta(fake_clube_repo, fake_repo, service)
        fake_escalacao_repo.remover_titular(30)  # Águias fica com só 4 titulares

        with pytest.raises(ConflitoError):
            service.jogar_partida(
                DadosDePartida(home_club_id=aguias.id, away_club_id=delta.id), _MOMENTO
            )

        assert fake_partida_repo.listar(FiltrosDePartida()) == []

    def test_partida_nao_muda_caixa_escalacao_nem_jogadores(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        aguias, delta = _escalar_aguias_e_delta(fake_clube_repo, fake_repo, service)
        caixa_aguias_antes = aguias.caixa
        caixa_delta_antes = delta.caixa
        titulares_aguias_antes = fake_escalacao_repo.listar_titulares_do_clube(aguias.id)
        atributos_antes = {j.id: j.defesa for j in fake_repo.listar(FiltrosSql())}

        service.jogar_partida(
            DadosDePartida(home_club_id=aguias.id, away_club_id=delta.id), _MOMENTO
        )

        assert aguias.caixa == caixa_aguias_antes
        assert delta.caixa == caixa_delta_antes
        assert fake_escalacao_repo.listar_titulares_do_clube(aguias.id) == titulares_aguias_antes
        for jogador in fake_repo.listar(FiltrosSql()):
            assert jogador.defesa == atributos_antes[jogador.id]


class TestHistoricoEConsultarPartida:
    def test_historico_ordena_mais_recente_primeiro_e_filtra_por_clube(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube_a = _novo_clube(fake_clube_repo)
        clube_b = _novo_clube(
            fake_clube_repo, nome="Delta FC", nome_normalizado="delta fc", sigla="DEL"
        )
        clube_c = _novo_clube(
            fake_clube_repo, nome="Gama SC", nome_normalizado="gama sc", sigla="GAM"
        )
        p1 = fake_partida_repo.adicionar(
            Partida(
                mandante_id=clube_a.id,
                visitante_id=clube_b.id,
                gols_mandante=1,
                gols_visitante=0,
                formacao_mandante="2-1-1",
                formacao_visitante="2-1-1",
                jogada_em=_MOMENTO,
            )
        )
        p2 = fake_partida_repo.adicionar(
            Partida(
                mandante_id=clube_b.id,
                visitante_id=clube_c.id,
                gols_mandante=0,
                gols_visitante=0,
                formacao_mandante="2-1-1",
                formacao_visitante="2-1-1",
                jogada_em=_MOMENTO,
            )
        )
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        todas = service.historico(FiltrosDePartida())
        assert [p.id for p in todas] == [p2.id, p1.id]

        do_clube_a = service.historico(FiltrosDePartida(clube_id=clube_a.id))
        assert [p.id for p in do_clube_a] == [p1.id]

    def test_historico_clube_do_filtro_inexistente_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.historico(FiltrosDePartida(clube_id=999))

    def test_consultar_partida_traz_os_6_duelos(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        aguias, delta = _escalar_aguias_e_delta(fake_clube_repo, fake_repo, service)
        jogada = service.jogar_partida(
            DadosDePartida(home_club_id=aguias.id, away_club_id=delta.id), _MOMENTO
        )

        resultado = service.consultar_partida(jogada.id)

        assert len(resultado.duelos) == 6
        assert resultado.result == "VISITANTE"

    def test_consultar_partida_inexistente_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.consultar_partida(999)


class TestClassificacao:
    def test_classificacao_com_o_exemplo_do_enunciado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        aguias = _novo_clube(
            fake_clube_repo, nome="Águias FC", nome_normalizado="águias fc", sigla="AGU"
        )
        delta = _novo_clube(
            fake_clube_repo, nome="Delta FC", nome_normalizado="delta fc", sigla="DEL"
        )
        gama = _novo_clube(fake_clube_repo, nome="Gama SC", nome_normalizado="gama sc", sigla="GAM")
        epsilon = _novo_clube(
            fake_clube_repo, nome="Épsilon EC", nome_normalizado="épsilon ec", sigla="EPS"
        )
        _novo_clube(fake_clube_repo, nome="Mangue FC", nome_normalizado="mangue fc", sigla="MAN")
        _novo_clube(
            fake_clube_repo, nome="Tubarões EC", nome_normalizado="tubarões ec", sigla="TUB"
        )

        def _partida(mandante: Clube, visitante: Clube, gm: int, gv: int) -> None:
            fake_partida_repo.adicionar(
                Partida(
                    mandante_id=mandante.id,
                    visitante_id=visitante.id,
                    gols_mandante=gm,
                    gols_visitante=gv,
                    formacao_mandante="2-1-1",
                    formacao_visitante="2-1-1",
                    jogada_em=_MOMENTO,
                )
            )

        _partida(aguias, delta, 1, 2)
        _partida(gama, epsilon, 2, 1)
        _partida(epsilon, aguias, 3, 2)
        _partida(delta, gama, 0, 1)

        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )
        classificacao = service.classificacao()

        assert [linha.club_name for linha in classificacao] == [
            "Gama SC",
            "Épsilon EC",
            "Delta FC",
            "Mangue FC",
            "Tubarões EC",
            "Águias FC",
        ]
        assert [linha.position for linha in classificacao] == [1, 2, 3, 4, 5, 6]
        gama_linha = classificacao[0]
        assert (gama_linha.played, gama_linha.wins, gama_linha.points) == (2, 2, 6)
        aguias_linha = classificacao[5]
        assert aguias_linha.points == 0
        assert aguias_linha.goal_difference == -2

    def test_clube_que_nunca_jogou_aparece_zerado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_partida_repo: FakePartidaRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        service = _service(
            fake_clube_repo,
            fake_repo,
            fake_escalacao_repo,
            fake_partida_repo,
            fake_unidade_de_trabalho,
        )

        classificacao = service.classificacao()

        linha = classificacao[0]
        assert linha.club_id == clube.id
        assert (
            linha.played,
            linha.wins,
            linha.draws,
            linha.losses,
            linha.goals_for,
            linha.goals_against,
            linha.goal_difference,
            linha.points,
        ) == (0, 0, 0, 0, 0, 0, 0, 0)


class _UnidadeDeTrabalhoQueFalhaAoConfirmar:
    """Simula uma falha de banco no commit, para testar que `jogar_partida` aciona o rollback e
    propaga o erro — ver `LigaService._confirmar_ou_desfazer`."""

    def __init__(self) -> None:
        self.desfez = False

    def confirmar(self) -> None:
        raise RuntimeError("falha simulada no commit")

    def desfazer(self) -> None:
        self.desfez = True


def test_falha_ao_confirmar_jogar_partida_aciona_o_rollback_e_propaga_o_erro(
    fake_clube_repo: FakeClubeRepository,
    fake_repo: FakeJogadorRepository,
    fake_escalacao_repo: FakeEscalacaoRepository,
    fake_partida_repo: FakePartidaRepository,
    fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
) -> None:
    service_para_escalar = LigaService(
        fake_clube_repo, fake_repo, fake_escalacao_repo, fake_partida_repo, fake_unidade_de_trabalho
    )
    aguias, delta = _escalar_aguias_e_delta(fake_clube_repo, fake_repo, service_para_escalar)

    uot_que_falha = _UnidadeDeTrabalhoQueFalhaAoConfirmar()
    service = LigaService(
        fake_clube_repo, fake_repo, fake_escalacao_repo, fake_partida_repo, uot_que_falha
    )

    with pytest.raises(RuntimeError):
        service.jogar_partida(
            DadosDePartida(home_club_id=aguias.id, away_club_id=delta.id), _MOMENTO
        )

    assert uot_que_falha.desfez is True
