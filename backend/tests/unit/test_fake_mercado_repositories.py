from datetime import datetime, timedelta
from decimal import Decimal

from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.mercado.models import Contrato, Transacao
from mercado_jogadores.mercado.repository import FiltrosDeTransacao
from tests.conftest import FakeContratoRepository, FakeTransacaoRepository, FakeUnidadeDeTrabalho

_MOMENTO = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)


def _novo_contrato(**sobrescritas: object) -> Contrato:
    base = {
        "jogador_id": 1,
        "clube_id": 1,
        "valor_compra": Decimal("37.00"),
        "fidelidade_ate": _MOMENTO + timedelta(days=365),
        "situacao": "ATIVO",
        "iniciado_em": _MOMENTO,
    }
    base.update(sobrescritas)
    return Contrato(**base)


def _nova_transacao(**sobrescritas: object) -> Transacao:
    base = {
        "clube_id": 1,
        "jogador_id": 1,
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


class TestFakeContratoRepository:
    def test_adicionar_atribui_id_e_obter_ativo_retorna_o_mesmo_contrato(
        self, fake_contrato_repo: FakeContratoRepository
    ) -> None:
        contrato = _novo_contrato()

        fake_contrato_repo.adicionar(contrato)

        assert contrato.id is not None
        obtido = fake_contrato_repo.obter_ativo_por_jogador(1)
        assert obtido is contrato

    def test_obter_ativo_nao_retorna_contrato_encerrado(
        self, fake_contrato_repo: FakeContratoRepository
    ) -> None:
        fake_contrato_repo.adicionar(_novo_contrato(situacao="ENCERRADO"))

        assert fake_contrato_repo.obter_ativo_por_jogador(1) is None


class TestFakeTransacaoRepository:
    def test_adicionar_atribui_id_e_existe_venda_reflete_o_tipo(
        self, fake_transacao_repo: FakeTransacaoRepository
    ) -> None:
        transacao = _nova_transacao(tipo="VENDA")

        fake_transacao_repo.adicionar(transacao)

        assert transacao.id is not None
        assert fake_transacao_repo.existe_venda(clube_id=1, jogador_id=1) is True
        assert fake_transacao_repo.existe_venda(clube_id=2, jogador_id=1) is False

    def test_listar_por_clube_ordena_mais_recente_primeiro_e_filtra(
        self, fake_transacao_repo: FakeTransacaoRepository
    ) -> None:
        compra = _nova_transacao(tipo="COMPRA", criado_em=_MOMENTO)
        venda = _nova_transacao(tipo="VENDA", criado_em=_MOMENTO + timedelta(days=1))
        fake_transacao_repo.adicionar(compra)
        fake_transacao_repo.adicionar(venda)

        resultado = fake_transacao_repo.listar_por_clube(1, FiltrosDeTransacao())
        assert [t.tipo for t in resultado] == ["VENDA", "COMPRA"]

        so_venda = fake_transacao_repo.listar_por_clube(1, FiltrosDeTransacao(tipos=["VENDA"]))
        assert [t.tipo for t in so_venda] == ["VENDA"]


class TestFakeUnidadeDeTrabalho:
    def test_confirmar_e_desfazer_nao_levantam_erro(
        self, fake_unidade_de_trabalho: FakeUnidadeDeTrabalho
    ) -> None:
        fake_unidade_de_trabalho.confirmar()
        fake_unidade_de_trabalho.desfazer()
