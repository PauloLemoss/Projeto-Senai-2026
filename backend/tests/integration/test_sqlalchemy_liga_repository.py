from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.liga.models import DueloPartida, Partida
from mercado_jogadores.liga.repository import (
    FiltrosDePartida,
    SQLAlchemyEscalacaoRepository,
    SQLAlchemyPartidaRepository,
)

_MOMENTO = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)


def _novo_clube(**sobrescritas: object) -> Clube:
    base = {
        "nome": "Águias FC",
        "nome_normalizado": "águias fc",
        "sigla": "AGU",
        "caixa": Decimal("300.00"),
    }
    base.update(sobrescritas)
    return Clube(**base)


def _novo_jogador(**sobrescritas: object) -> Jogador:
    base = {
        "nome": "Meia Lua",
        "posicao": "MEI",
        "agilidade": 85,
        "idade": 25,
        "valor_base": Decimal("40.00"),
        "condicao": "APTO",
        "velocidade": 70,
        "finalizacao": 68,
        "passe": 82,
        "drible": 79,
        "defesa": 55,
        "fisico": 64,
        "potencial": 86,
    }
    base.update(sobrescritas)
    return Jogador(**base)


def test_substituir_escalacao_do_clube_grava_e_substitui(db_session: Session) -> None:
    clube = _novo_clube()
    jogadores = [_novo_jogador(nome=f"Jogador {i}", clube_id=None) for i in range(3)]
    db_session.add(clube)
    db_session.add_all(jogadores)
    db_session.commit()
    for j in jogadores:
        j.clube_id = clube.id
    db_session.commit()

    repo = SQLAlchemyEscalacaoRepository(db_session)
    repo.substituir_escalacao_do_clube(clube.id, [j.id for j in jogadores[:2]], _MOMENTO)
    db_session.commit()

    assert repo.listar_titulares_do_clube(clube.id) == sorted(j.id for j in jogadores[:2])

    # substitui por inteiro: só o terceiro jogador fica escalado
    repo.substituir_escalacao_do_clube(clube.id, [jogadores[2].id], _MOMENTO)
    db_session.commit()

    assert repo.listar_titulares_do_clube(clube.id) == [jogadores[2].id]


def test_remover_titular(db_session: Session) -> None:
    clube = _novo_clube()
    jogador = _novo_jogador()
    db_session.add_all([clube, jogador])
    db_session.commit()
    jogador.clube_id = clube.id
    db_session.commit()

    repo = SQLAlchemyEscalacaoRepository(db_session)
    repo.substituir_escalacao_do_clube(clube.id, [jogador.id], _MOMENTO)
    db_session.commit()
    assert repo.listar_titulares_do_clube(clube.id) == [jogador.id]

    repo.remover_titular(jogador.id)
    db_session.commit()

    assert repo.listar_titulares_do_clube(clube.id) == []


def test_adicionar_obter_e_listar_duelos_de_uma_partida(db_session: Session) -> None:
    mandante = _novo_clube()
    visitante = _novo_clube(nome="Leões FC", nome_normalizado="leões fc", sigla="LEO")
    jogador = _novo_jogador()
    db_session.add_all([mandante, visitante, jogador])
    db_session.commit()

    repo = SQLAlchemyPartidaRepository(db_session)
    partida = repo.adicionar(
        Partida(
            mandante_id=mandante.id,
            visitante_id=visitante.id,
            gols_mandante=1,
            gols_visitante=2,
            formacao_mandante="2-1-1",
            formacao_visitante="2-1-1",
            jogada_em=_MOMENTO,
        )
    )
    assert partida.id is not None

    for ordem in range(1, 7):
        repo.adicionar_duelo(
            DueloPartida(
                partida_id=partida.id,
                ordem=ordem,
                clube_atacante_id=mandante.id if ordem <= 3 else visitante.id,
                atacante_id=jogador.id,
                defensor_id=jogador.id,
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
                gol=(ordem in (1, 4, 6)),
            )
        )
    db_session.commit()

    obtida = repo.obter(partida.id)
    assert obtida is not None
    assert obtida.gols_mandante == 1

    duelos = repo.listar_duelos(partida.id)
    assert [d.ordem for d in duelos] == [1, 2, 3, 4, 5, 6]
    assert [d.gol for d in duelos] == [True, False, False, True, False, True]


def test_obter_partida_inexistente_retorna_none(db_session: Session) -> None:
    repo = SQLAlchemyPartidaRepository(db_session)
    assert repo.obter(999_999) is None


def test_listar_filtra_por_clube_e_ordena_mais_recente_primeiro(db_session: Session) -> None:
    clube_a = _novo_clube()
    clube_b = _novo_clube(nome="Leões FC", nome_normalizado="leões fc", sigla="LEO")
    clube_c = _novo_clube(nome="Gama SC", nome_normalizado="gama sc", sigla="GSC")
    db_session.add_all([clube_a, clube_b, clube_c])
    db_session.commit()

    repo = SQLAlchemyPartidaRepository(db_session)
    p1 = repo.adicionar(
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
    p2 = repo.adicionar(
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
    db_session.commit()

    do_clube_a = repo.listar(FiltrosDePartida(clube_id=clube_a.id))
    assert [p.id for p in do_clube_a] == [p1.id]

    todas = repo.listar(FiltrosDePartida())
    assert [p.id for p in todas] == [p2.id, p1.id]  # mais recente primeiro (empate por id)
