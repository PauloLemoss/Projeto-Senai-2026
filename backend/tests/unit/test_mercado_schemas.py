from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from pydantic import ValidationError

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.mercado.models import Contrato, Transacao
from mercado_jogadores.mercado.schemas import (
    BuyRead,
    BuyRequest,
    SellRead,
    TransactionListQuery,
)
from mercado_jogadores.mercado.service import ResultadoDaCompra, ResultadoDaVenda


def _loyalty_until_daqui_a(dias: int) -> str:
    momento = datetime.now(FUSO_BRASILIA) + timedelta(days=dias)
    return momento.strftime("%Y-%m-%dT%H:%M") + "-03:00"


class TestBuyRequest:
    def test_requisicao_valida_e_aceita(self) -> None:
        dados = BuyRequest(club_id=1, loyalty_until=_loyalty_until_daqui_a(365))
        assert dados.club_id == 1

    def test_club_id_zero_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            BuyRequest(club_id=0, loyalty_until=_loyalty_until_daqui_a(365))

    def test_club_id_negativo_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            BuyRequest(club_id=-5, loyalty_until=_loyalty_until_daqui_a(365))

    def test_loyalty_until_que_nao_e_futuro_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            BuyRequest(club_id=1, loyalty_until=_loyalty_until_daqui_a(-1))

    def test_loyalty_until_acima_de_1095_dias_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            BuyRequest(club_id=1, loyalty_until=_loyalty_until_daqui_a(1096))

    def test_loyalty_until_dentro_do_limite_e_aceito(self) -> None:
        dados = BuyRequest(club_id=1, loyalty_until=_loyalty_until_daqui_a(1090))
        assert dados.club_id == 1


class TestBuyReadESellRead:
    def test_buy_read_bate_com_o_exemplo_2_3_1_do_enunciado(self) -> None:
        transacao = Transacao(
            id=10,
            clube_id=1,
            jogador_id=2,
            nome_jogador="Meia Lua",
            tipo="COMPRA",
            valor=Decimal("37.00"),
            taxa=Decimal("1.85"),
            multa=Decimal("0.00"),
            lucro=None,
            variacao_caixa=Decimal("-38.85"),
            criado_em=datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA),
        )
        contrato = Contrato(
            jogador_id=2,
            clube_id=1,
            valor_compra=Decimal("37.00"),
            fidelidade_ate=datetime(2027, 3, 2, 10, 15, tzinfo=FUSO_BRASILIA),
            situacao="ATIVO",
            iniciado_em=datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA),
        )
        clube = Clube(
            id=1,
            nome="Águias FC",
            nome_normalizado="águias fc",
            sigla="AGU",
            caixa=Decimal("261.15"),
        )
        resultado = ResultadoDaCompra(transacao=transacao, contrato=contrato, clube=clube)

        corpo = BuyRead.a_partir_do_resultado(resultado).model_dump()

        assert corpo == {
            "id": 10,
            "club_id": 1,
            "player_id": 2,
            "player_name": "Meia Lua",
            "type": "COMPRA",
            "value": 37.00,
            "fee": 1.85,
            "penalty": 0.00,
            "profit": None,
            "cash_change": -38.85,
            "created_at": "2026-11-02T10:15:00-03:00",
            "contract": {
                "purchase_value": 37.00,
                "loyalty_until": "2027-03-02T10:15:00-03:00",
                "status": "ATIVO",
            },
            "club_cash": 261.15,
        }

    def test_sell_read_bate_com_o_exemplo_2_3_2_do_enunciado(self) -> None:
        transacao = Transacao(
            id=11,
            clube_id=1,
            jogador_id=2,
            nome_jogador="Meia Lua",
            tipo="VENDA",
            valor=Decimal("40.00"),
            taxa=Decimal("0.30"),
            multa=Decimal("4.00"),
            lucro=Decimal("3.00"),
            variacao_caixa=Decimal("35.70"),
            criado_em=datetime(2026, 11, 5, 16, 40, tzinfo=FUSO_BRASILIA),
        )
        contrato = Contrato(
            jogador_id=2,
            clube_id=1,
            valor_compra=Decimal("37.00"),
            fidelidade_ate=datetime(2027, 3, 2, 10, 15, tzinfo=FUSO_BRASILIA),
            situacao="RESCINDIDO",
            iniciado_em=datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA),
            encerrado_em=datetime(2026, 11, 5, 16, 40, tzinfo=FUSO_BRASILIA),
        )
        clube = Clube(
            id=1,
            nome="Águias FC",
            nome_normalizado="águias fc",
            sigla="AGU",
            caixa=Decimal("296.85"),
        )
        resultado = ResultadoDaVenda(
            transacao=transacao,
            contrato=contrato,
            clube=clube,
            dias_restantes=117,
            percentual_de_multa=10,
        )

        corpo = SellRead.a_partir_do_resultado(resultado).model_dump()

        assert corpo == {
            "id": 11,
            "club_id": 1,
            "player_id": 2,
            "player_name": "Meia Lua",
            "type": "VENDA",
            "value": 40.00,
            "fee": 0.30,
            "penalty": 4.00,
            "profit": 3.00,
            "cash_change": 35.70,
            "created_at": "2026-11-05T16:40:00-03:00",
            "purchase_value": 37.00,
            "remaining_days": 117,
            "penalty_rate": 10,
            "contract_status": "RESCINDIDO",
            "club_cash": 296.85,
        }


class TestTransactionListQuery:
    def test_sem_filtro_e_aceito(self) -> None:
        query = TransactionListQuery()
        assert query.para_filtros().tipos is None
        assert query.para_filtros().jogador_id is None

    def test_um_tipo_e_aceito(self) -> None:
        query = TransactionListQuery(type="VENDA")
        assert query.para_filtros().tipos == ["VENDA"]

    def test_dois_tipos_sao_aceitos(self) -> None:
        query = TransactionListQuery(type="COMPRA,VENDA")
        assert query.para_filtros().tipos == ["COMPRA", "VENDA"]

    def test_tipo_invalido_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            TransactionListQuery(type="venda")

    def test_tipo_repetido_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            TransactionListQuery(type="VENDA,VENDA")

    def test_player_id_valido_e_aceito(self) -> None:
        query = TransactionListQuery(player_id="5")
        assert query.para_filtros().jogador_id == 5

    def test_player_id_com_zero_a_esquerda_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            TransactionListQuery(player_id="05")

    def test_type_explicitamente_nulo_e_aceito_como_sem_filtro(self) -> None:
        query = TransactionListQuery(type=None)
        assert query.para_filtros().tipos is None

    def test_type_vazio_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            TransactionListQuery(type="")
