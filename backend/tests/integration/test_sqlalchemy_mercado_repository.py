from datetime import datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.core.unidade_de_trabalho import SQLAlchemyUnidadeDeTrabalho
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.mercado.models import Contrato, Transacao
from mercado_jogadores.mercado.repository import (
    FiltrosDeTransacao,
    SQLAlchemyContratoRepository,
    SQLAlchemyTransacaoRepository,
)

_MOMENTO = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)


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


def _novo_clube(**sobrescritas: object) -> Clube:
    base = {"nome": "Águias FC", "nome_normalizado": "águias fc", "sigla": "AGU"}
    base.update(sobrescritas)
    return Clube(**base)


def _novo_contrato(jogador_id: int, clube_id: int, **sobrescritas: object) -> Contrato:
    base = {
        "jogador_id": jogador_id,
        "clube_id": clube_id,
        "valor_compra": Decimal("37.00"),
        "fidelidade_ate": _MOMENTO + timedelta(days=365),
        "situacao": "ATIVO",
        "iniciado_em": _MOMENTO,
    }
    base.update(sobrescritas)
    return Contrato(**base)


def _nova_transacao(clube_id: int, jogador_id: int, **sobrescritas: object) -> Transacao:
    base = {
        "clube_id": clube_id,
        "jogador_id": jogador_id,
        "nome_jogador": "Meia Lua",
        "tipo": "COMPRA",
        "valor": Decimal("37.00"),
        "taxa": Decimal("1.85"),
        "multa": Decimal("0.00"),
        "lucro": None,
        "variacao_caixa": Decimal("-38.85"),
        "criado_em": _MOMENTO,
    }
    base.update(sobrescritas)
    return Transacao(**base)


def _novo_jogador_e_clube(db_session: Session) -> tuple[Jogador, Clube]:
    jogador = _novo_jogador()
    clube = _novo_clube()
    db_session.add_all([jogador, clube])
    db_session.commit()
    return jogador, clube


def test_adicionar_contrato_e_obter_o_ativo(db_session: Session) -> None:
    jogador, clube = _novo_jogador_e_clube(db_session)
    repo = SQLAlchemyContratoRepository(db_session)

    repo.adicionar(_novo_contrato(jogador.id, clube.id))
    db_session.commit()

    ativo = repo.obter_ativo_por_jogador(jogador.id)
    assert ativo is not None
    assert ativo.situacao == "ATIVO"
    assert ativo.valor_compra == Decimal("37.00")


def test_obter_ativo_por_jogador_sem_contrato_retorna_none(db_session: Session) -> None:
    repo = SQLAlchemyContratoRepository(db_session)
    assert repo.obter_ativo_por_jogador(999_999) is None


def test_mutar_contrato_diretamente_persiste_sem_metodo_de_update(db_session: Session) -> None:
    jogador, clube = _novo_jogador_e_clube(db_session)
    repo = SQLAlchemyContratoRepository(db_session)
    repo.adicionar(_novo_contrato(jogador.id, clube.id))
    db_session.commit()

    contrato = repo.obter_ativo_por_jogador(jogador.id)
    assert contrato is not None
    contrato.situacao = "RESCINDIDO"
    contrato.encerrado_em = _MOMENTO + timedelta(days=10)
    db_session.commit()

    assert repo.obter_ativo_por_jogador(jogador.id) is None  # não é mais ATIVO
    assert contrato.situacao == "RESCINDIDO"
    assert contrato.encerrado_em is not None


def test_existe_venda_antes_e_depois_de_uma_transacao_de_venda(db_session: Session) -> None:
    jogador, clube = _novo_jogador_e_clube(db_session)
    repo = SQLAlchemyTransacaoRepository(db_session)

    assert repo.existe_venda(clube.id, jogador.id) is False

    repo.adicionar(_nova_transacao(clube.id, jogador.id, tipo="VENDA", valor=Decimal("40.00")))
    db_session.commit()

    assert repo.existe_venda(clube.id, jogador.id) is True


def test_listar_por_clube_ordena_mais_recente_primeiro_e_filtra(db_session: Session) -> None:
    jogador, clube = _novo_jogador_e_clube(db_session)
    repo = SQLAlchemyTransacaoRepository(db_session)

    compra = _nova_transacao(clube.id, jogador.id, tipo="COMPRA", criado_em=_MOMENTO)
    venda = _nova_transacao(
        clube.id,
        jogador.id,
        tipo="VENDA",
        criado_em=_MOMENTO + timedelta(days=1),
        valor=Decimal("40.00"),
        taxa=Decimal("0.30"),
        lucro=Decimal("3.00"),
        variacao_caixa=Decimal("35.70"),
    )
    repo.adicionar(compra)
    repo.adicionar(venda)
    db_session.commit()

    resultado = repo.listar_por_clube(clube.id, FiltrosDeTransacao())
    assert [t.tipo for t in resultado] == ["VENDA", "COMPRA"]

    so_venda = repo.listar_por_clube(clube.id, FiltrosDeTransacao(tipos=["VENDA"]))
    assert [t.tipo for t in so_venda] == ["VENDA"]

    por_jogador = repo.listar_por_clube(clube.id, FiltrosDeTransacao(jogador_id=jogador.id))
    assert len(por_jogador) == 2


def test_unidade_de_trabalho_confirmar_persiste_e_desfazer_reverte(db_session: Session) -> None:
    clube = _novo_clube()
    db_session.add(clube)
    uot = SQLAlchemyUnidadeDeTrabalho(db_session)
    uot.confirmar()
    assert clube.id is not None

    clube.caixa = Decimal("999.00")
    uot.desfazer()

    db_session.refresh(clube)
    assert clube.caixa == Decimal("300.00")
