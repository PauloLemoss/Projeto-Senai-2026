from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.service import DadosCadastroJogador, JogadorService
from mercado_jogadores.mercado.models import Transacao
from mercado_jogadores.mercado.repository import FiltrosDeTransacao
from mercado_jogadores.mercado.service import DadosDeCompra, MercadoService, ResumoDeTransacoes
from tests.conftest import (
    FakeClubeRepository,
    FakeContratoRepository,
    FakeEscalacaoRepository,
    FakeJogadorRepository,
    FakeTransacaoRepository,
    FakeUnidadeDeTrabalho,
)

_MOMENTO = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)
_FIDELIDADE_ATE = _MOMENTO + timedelta(days=365)


def _cadastrar_jogador_com_valor_de_mercado(
    fake_repo: FakeJogadorRepository, valor: Decimal, **sobrescritas: object
) -> Jogador:
    dados = {
        "nome": "Meia Lua",
        "posicao": "MEI",
        "agilidade": 85,
        "idade": 25,
        "pace": 70,
        "shooting": 68,
        "passing": 82,
        "dribbling": 79,
        "defending": 55,
        "physical": 64,
        "potential": 86,
    }
    dados.update(sobrescritas)
    resultado = JogadorService(
        fake_repo, FakeEscalacaoRepository(), FakeUnidadeDeTrabalho(), FakeClubeRepository()
    ).cadastrar(DadosCadastroJogador(**dados))
    jogador = resultado.jogador
    # APTO + idade 22-31 não altera o valor de mercado (RN02-04): valor_base = valor de mercado.
    jogador.condicao = "APTO"
    jogador.valor_base = valor
    fake_repo.salvar(jogador)
    return jogador


def _novo_clube(fake_clube_repo: FakeClubeRepository, **sobrescritas: object) -> Clube:
    dados = {
        "nome": "Águias FC",
        "nome_normalizado": "águias fc",
        "sigla": "AGU",
        "caixa": Decimal("300.00"),
    }
    dados.update(sobrescritas)
    return fake_clube_repo.salvar(Clube(**dados))


def _dados_de_compra(club_id: int, **sobrescritas: object) -> DadosDeCompra:
    dados = {"club_id": club_id, "loyalty_until": _FIDELIDADE_ATE}
    dados.update(sobrescritas)
    return DadosDeCompra(**dados)


def _comprar_jogador(
    fake_repo: FakeJogadorRepository,
    fake_clube_repo: FakeClubeRepository,
    fake_contrato_repo: FakeContratoRepository,
    fake_transacao_repo: FakeTransacaoRepository,
    fake_escalacao_repo: FakeEscalacaoRepository,
    fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    valor_de_mercado: Decimal,
    fidelidade_ate: datetime,
    caixa_do_clube: Decimal = Decimal("1000.00"),
) -> tuple[Jogador, Clube, MercadoService]:
    jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, valor_de_mercado)
    clube = _novo_clube(fake_clube_repo, caixa=caixa_do_clube)
    service = MercadoService(
        fake_repo,
        fake_clube_repo,
        fake_contrato_repo,
        fake_transacao_repo,
        fake_escalacao_repo,
        fake_unidade_de_trabalho,
    )
    service.comprar(
        jogador.id, DadosDeCompra(club_id=clube.id, loyalty_until=fidelidade_ate), _MOMENTO
    )
    return jogador, clube, service


class TestComprar:
    def test_compra_aceita_abaixo_do_limite_sem_taxa(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("28.00"))
        clube = _novo_clube(fake_clube_repo, caixa=Decimal("300.00"))
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        resultado = service.comprar(jogador.id, _dados_de_compra(clube.id), _MOMENTO)

        assert resultado.transacao.taxa == Decimal("0.00")
        assert clube.caixa == Decimal("272.00")
        assert jogador.clube_id == clube.id
        assert resultado.contrato.situacao == "ATIVO"

    def test_custo_total_igual_ao_limite_e_aceito(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("47.62"))
        clube = _novo_clube(fake_clube_repo, caixa=Decimal("100.00"))
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        service.comprar(jogador.id, _dados_de_compra(clube.id), _MOMENTO)

        assert clube.caixa == Decimal("50.00")

    def test_custo_total_acima_do_limite_e_recusado_e_nada_e_gravado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("48.00"))
        clube = _novo_clube(fake_clube_repo, caixa=Decimal("100.00"))
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(ConflitoError):
            service.comprar(jogador.id, _dados_de_compra(clube.id), _MOMENTO)

        assert jogador.clube_id is None
        assert clube.caixa == Decimal("100.00")
        assert fake_contrato_repo.obter_ativo_por_jogador(jogador.id) is None

    def test_jogador_que_nao_esta_livre_e_recusado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("28.00"))
        clube = _novo_clube(fake_clube_repo)
        jogador.clube_id = clube.id
        fake_repo.salvar(jogador)
        outro_clube = _novo_clube(
            fake_clube_repo, nome="Leões FC", nome_normalizado="leões fc", sigla="LEO"
        )
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(ConflitoError):
            service.comprar(jogador.id, _dados_de_compra(outro_clube.id), _MOMENTO)

    def test_elenco_com_12_jogadores_recusa_a_13a_compra(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo, caixa=Decimal("1000.00"))
        for _ in range(12):
            titular = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("10.00"))
            titular.clube_id = clube.id
            fake_repo.salvar(titular)
        decimo_terceiro = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("10.00"))
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(ConflitoError):
            service.comprar(decimo_terceiro.id, _dados_de_compra(clube.id), _MOMENTO)

        assert decimo_terceiro.clube_id is None

    def test_clube_que_ja_vendeu_o_jogador_nao_pode_recompra_lo(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("28.00"))
        clube = _novo_clube(fake_clube_repo)
        fake_transacao_repo.adicionar(
            Transacao(
                clube_id=clube.id,
                jogador_id=jogador.id,
                nome_jogador=jogador.nome,
                tipo="VENDA",
                valor=Decimal("28.00"),
                taxa=Decimal("0.00"),
                multa=Decimal("0.00"),
                lucro=Decimal("0.00"),
                variacao_caixa=Decimal("28.00"),
                criado_em=_MOMENTO,
            )
        )
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(ConflitoError):
            service.comprar(jogador.id, _dados_de_compra(clube.id), _MOMENTO)

    def test_outro_clube_pode_comprar_o_jogador_vendido(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("28.00"))
        clube_a = _novo_clube(fake_clube_repo)
        clube_b = _novo_clube(
            fake_clube_repo, nome="Leões FC", nome_normalizado="leões fc", sigla="LEO"
        )
        fake_transacao_repo.adicionar(
            Transacao(
                clube_id=clube_a.id,
                jogador_id=jogador.id,
                nome_jogador=jogador.nome,
                tipo="VENDA",
                valor=Decimal("28.00"),
                taxa=Decimal("0.00"),
                multa=Decimal("0.00"),
                lucro=Decimal("0.00"),
                variacao_caixa=Decimal("28.00"),
                criado_em=_MOMENTO,
            )
        )
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        resultado = service.comprar(jogador.id, _dados_de_compra(clube_b.id), _MOMENTO)

        assert jogador.clube_id == clube_b.id
        assert resultado.transacao.clube_id == clube_b.id

    def test_jogador_inexistente_e_recusado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.comprar(999, _dados_de_compra(clube.id), _MOMENTO)

    def test_clube_inexistente_e_recusado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("28.00"))
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.comprar(jogador.id, _dados_de_compra(999), _MOMENTO)


_MOMENTO_VENDA = datetime(2026, 11, 5, 16, 40, tzinfo=FUSO_BRASILIA)


class TestVender:
    def test_fidelidade_ja_cumprida_nao_gera_multa(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, _clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("40.00"),
            _MOMENTO_VENDA - timedelta(days=1),
        )

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.dias_restantes == 0
        assert resultado.transacao.multa == Decimal("0.00")
        assert resultado.contrato.situacao == "ENCERRADO"
        assert jogador.clube_id is None

    def test_venda_de_titular_sai_da_escalacao(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("40.00"),
            _MOMENTO_VENDA - timedelta(days=1),
        )
        fake_escalacao_repo.substituir_escalacao_do_clube(clube.id, [jogador.id], _MOMENTO_VENDA)

        service.vender(jogador.id, _MOMENTO_VENDA)

        assert jogador.id not in fake_escalacao_repo.listar_titulares_do_clube(clube.id)

    def test_faixa_de_1_a_30_dias_restantes_gera_5_por_cento_de_multa(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, _clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("40.00"),
            _MOMENTO_VENDA + timedelta(days=30),
        )

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.dias_restantes == 30
        assert resultado.percentual_de_multa == 5
        assert resultado.transacao.multa == Decimal("2.00")
        assert resultado.contrato.situacao == "RESCINDIDO"

    def test_faixa_de_31_a_180_dias_restantes_gera_10_por_cento_de_multa(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, _clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("40.00"),
            _MOMENTO_VENDA + timedelta(days=30, minutes=1),
        )

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.dias_restantes == 31
        assert resultado.percentual_de_multa == 10
        assert resultado.transacao.multa == Decimal("4.00")

    def test_faixa_de_181_dias_ou_mais_gera_20_por_cento_de_multa(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, _clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("40.00"),
            _MOMENTO_VENDA + timedelta(days=180, minutes=1),
        )

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.dias_restantes == 181
        assert resultado.percentual_de_multa == 20
        assert resultado.transacao.multa == Decimal("8.00")

    def test_multa_e_limitada_a_dez(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, _clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("75.00"),
            _MOMENTO_VENDA + timedelta(days=200),
        )

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.percentual_de_multa == 20  # 20% de 75,00 seria 15,00
        assert resultado.transacao.multa == Decimal("10.00")

    def test_venda_de_ponta_a_ponta_do_exemplo_do_enunciado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        resultado_cadastro = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, fake_clube_repo
        ).cadastrar(
            DadosCadastroJogador(
                nome="Meia Lua",
                posicao="MEI",
                agilidade=85,
                idade=25,
                pace=70,
                shooting=68,
                passing=82,
                dribbling=79,
                defending=55,
                physical=64,
                potential=86,
            )
        )
        jogador = resultado_cadastro.jogador
        assert jogador.valor_base == Decimal("40.00")

        jogador.condicao = "MAL_CONDICIONADO"
        fake_repo.salvar(jogador)

        clube = _novo_clube(fake_clube_repo, caixa=Decimal("300.00"))
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )
        momento_compra = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)
        fidelidade_ate = datetime(2027, 3, 2, 10, 15, tzinfo=FUSO_BRASILIA)
        compra = service.comprar(
            jogador.id,
            DadosDeCompra(club_id=clube.id, loyalty_until=fidelidade_ate),
            momento_compra,
        )
        assert compra.transacao.valor == Decimal("37.00")
        assert clube.caixa == Decimal("261.15")

        jogador.condicao = "APTO"  # devolvido a APTO antes da venda
        fake_repo.salvar(jogador)

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.dias_restantes == 117
        assert resultado.percentual_de_multa == 10
        assert resultado.transacao.multa == Decimal("4.00")
        assert resultado.transacao.lucro == Decimal("3.00")
        assert resultado.transacao.taxa == Decimal("0.30")  # comissão
        assert resultado.transacao.variacao_caixa == Decimal("35.70")
        assert resultado.contrato.situacao == "RESCINDIDO"
        assert clube.caixa == Decimal("296.85")
        assert jogador.clube_id is None

    def test_jogador_livre_nao_pode_ser_vendido(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("40.00"))
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(ConflitoError):
            service.vender(jogador.id, _MOMENTO_VENDA)

    def test_jogador_inexistente_e_recusado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.vender(999, _MOMENTO_VENDA)


class TestComissaoProgressivaNaVenda:
    def test_lucro_simples_so_a_primeira_faixa(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, _clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("20.00"),
            _MOMENTO_VENDA - timedelta(days=1),
        )
        jogador.valor_base = Decimal("23.00")
        fake_repo.salvar(jogador)

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.transacao.lucro == Decimal("3.00")
        assert resultado.transacao.taxa == Decimal("0.30")
        assert resultado.transacao.variacao_caixa == Decimal("22.70")

    def test_lucro_cruzando_as_duas_faixas(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, _clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("20.00"),
            _MOMENTO_VENDA - timedelta(days=1),
        )
        jogador.valor_base = Decimal("35.00")
        fake_repo.salvar(jogador)

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.transacao.lucro == Decimal("15.00")
        assert resultado.transacao.taxa == Decimal("2.00")

    def test_prejuizo_nao_gera_comissao(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, _clube, service = _comprar_jogador(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
            Decimal("30.00"),
            _MOMENTO_VENDA - timedelta(days=1),
        )
        jogador.valor_base = Decimal("20.00")
        fake_repo.salvar(jogador)

        resultado = service.vender(jogador.id, _MOMENTO_VENDA)

        assert resultado.transacao.lucro == Decimal("-10.00")
        assert resultado.transacao.taxa == Decimal("0.00")
        assert resultado.transacao.variacao_caixa == Decimal("20.00")


def _comprar_e_vender_exemplo_do_enunciado(
    fake_repo: FakeJogadorRepository,
    fake_clube_repo: FakeClubeRepository,
    fake_contrato_repo: FakeContratoRepository,
    fake_transacao_repo: FakeTransacaoRepository,
    fake_escalacao_repo: FakeEscalacaoRepository,
    fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
) -> tuple[Jogador, Clube, MercadoService]:
    """Reproduz os exemplos 2.3.1/2.3.2 do enunciado: compra por 37,00 (fee 1,85), depois
    venda por 40,00 (multa 4,00, comissão 0,30, crédito 35,70)."""
    resultado_cadastro = JogadorService(
        fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, fake_clube_repo
    ).cadastrar(
        DadosCadastroJogador(
            nome="Meia Lua",
            posicao="MEI",
            agilidade=85,
            idade=25,
            pace=70,
            shooting=68,
            passing=82,
            dribbling=79,
            defending=55,
            physical=64,
            potential=86,
        )
    )
    jogador = resultado_cadastro.jogador
    jogador.condicao = "MAL_CONDICIONADO"
    fake_repo.salvar(jogador)

    clube = _novo_clube(fake_clube_repo, caixa=Decimal("300.00"))
    service = MercadoService(
        fake_repo,
        fake_clube_repo,
        fake_contrato_repo,
        fake_transacao_repo,
        fake_escalacao_repo,
        fake_unidade_de_trabalho,
    )
    momento_compra = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)
    fidelidade_ate = datetime(2027, 3, 2, 10, 15, tzinfo=FUSO_BRASILIA)
    service.comprar(
        jogador.id, DadosDeCompra(club_id=clube.id, loyalty_until=fidelidade_ate), momento_compra
    )

    jogador.condicao = "APTO"
    fake_repo.salvar(jogador)
    service.vender(jogador.id, _MOMENTO_VENDA)

    return jogador, clube, service


class TestHistorico:
    def test_sem_filtro_traz_compra_e_venda_com_os_totais_somados(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        _jogador, clube, service = _comprar_e_vender_exemplo_do_enunciado(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        historico = service.historico(clube.id, FiltrosDeTransacao())

        assert [t.tipo for t in historico.transacoes] == ["VENDA", "COMPRA"]
        assert historico.resumo.total_spent == Decimal("38.85")
        assert historico.resumo.total_received == Decimal("35.70")
        assert historico.resumo.total_fees == Decimal("2.15")
        assert historico.resumo.total_penalties == Decimal("4.00")
        assert historico.resumo.total_profit == Decimal("3.00")

    def test_filtro_por_type_restringe_data_e_summary(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        _jogador, clube, service = _comprar_e_vender_exemplo_do_enunciado(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        historico = service.historico(clube.id, FiltrosDeTransacao(tipos=["VENDA"]))

        assert [t.tipo for t in historico.transacoes] == ["VENDA"]
        assert historico.resumo.total_spent == Decimal("0.00")

    def test_jogador_sem_transacoes_no_clube(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("40.00"))
        clube = _novo_clube(fake_clube_repo)
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        historico = service.historico(clube.id, FiltrosDeTransacao(jogador_id=jogador.id))

        assert historico.transacoes == []
        assert historico.resumo == ResumoDeTransacoes(
            total_spent=Decimal("0.00"),
            total_received=Decimal("0.00"),
            total_fees=Decimal("0.00"),
            total_penalties=Decimal("0.00"),
            total_profit=Decimal("0.00"),
        )

    def test_jogador_do_filtro_inexistente_e_recusado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.historico(clube.id, FiltrosDeTransacao(jogador_id=999))

    def test_clube_inexistente(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        with pytest.raises(NaoEncontradoError):
            service.historico(999, FiltrosDeTransacao())

    def test_conciliacao_do_caixa_pelo_historico(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        _jogador, clube, service = _comprar_e_vender_exemplo_do_enunciado(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        historico = service.historico(clube.id, FiltrosDeTransacao())
        soma_variacao = sum((t.variacao_caixa for t in historico.transacoes), Decimal("0.00"))

        assert Decimal("300.00") + soma_variacao == clube.caixa

    def test_transacoes_de_jogador_excluido_permanecem_no_historico(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        jogador, clube, service = _comprar_e_vender_exemplo_do_enunciado(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        jogador.excluido_em = _MOMENTO_VENDA
        fake_repo.salvar(jogador)

        historico = service.historico(clube.id, FiltrosDeTransacao())

        assert len(historico.transacoes) == 2
        assert {t.nome_jogador for t in historico.transacoes} == {"Meia Lua"}


class TestExportarCsv:
    def test_exportacao_com_transacoes_bate_com_o_exemplo_do_enunciado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        _jogador, clube, service = _comprar_e_vender_exemplo_do_enunciado(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        csv_gerado = service.exportar_csv(clube.id, FiltrosDeTransacao())

        esperado = (
            "data_hora;tipo;jogador;valor;taxa_ou_comissao;multa;lucro;variacao_caixa\n"
            "2026-11-05T16:40:00-03:00;VENDA;Meia Lua;40,00;0,30;4,00;3,00;35,70\n"
            "2026-11-02T10:15:00-03:00;COMPRA;Meia Lua;37,00;1,85;0,00;;-38,85\n"
        )
        assert csv_gerado == esperado

    def test_exportacao_sem_transacoes_traz_so_o_cabecalho(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        csv_gerado = service.exportar_csv(clube.id, FiltrosDeTransacao())

        assert csv_gerado == (
            "data_hora;tipo;jogador;valor;taxa_ou_comissao;multa;lucro;variacao_caixa\n"
        )

    def test_nome_do_jogador_com_ponto_e_virgula_ou_aspas_e_escapado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_clube_repo: FakeClubeRepository,
        fake_contrato_repo: FakeContratoRepository,
        fake_transacao_repo: FakeTransacaoRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        clube = _novo_clube(fake_clube_repo)
        fake_transacao_repo.adicionar(
            Transacao(
                clube_id=clube.id,
                jogador_id=1,
                nome_jogador='Zé "Foguete" Lima',
                tipo="COMPRA",
                valor=Decimal("10.00"),
                taxa=Decimal("0.00"),
                multa=Decimal("0.00"),
                lucro=None,
                variacao_caixa=Decimal("-10.00"),
                criado_em=_MOMENTO,
            )
        )
        service = MercadoService(
            fake_repo,
            fake_clube_repo,
            fake_contrato_repo,
            fake_transacao_repo,
            fake_escalacao_repo,
            fake_unidade_de_trabalho,
        )

        csv_gerado = service.exportar_csv(clube.id, FiltrosDeTransacao())

        assert '"Zé ""Foguete"" Lima"' in csv_gerado


class _UnidadeDeTrabalhoQueFalhaAoConfirmar:
    """Simula uma falha de banco no commit (ex.: violação de constraint), para testar que o
    service aciona o rollback e propaga o erro — ver `MercadoService._confirmar_ou_desfazer`."""

    def __init__(self) -> None:
        self.desfez = False

    def confirmar(self) -> None:
        raise RuntimeError("falha simulada no commit")

    def desfazer(self) -> None:
        self.desfez = True


def test_falha_ao_confirmar_aciona_o_rollback_e_propaga_o_erro(
    fake_repo: FakeJogadorRepository,
    fake_clube_repo: FakeClubeRepository,
    fake_contrato_repo: FakeContratoRepository,
    fake_transacao_repo: FakeTransacaoRepository,
    fake_escalacao_repo: FakeEscalacaoRepository,
) -> None:
    jogador = _cadastrar_jogador_com_valor_de_mercado(fake_repo, Decimal("28.00"))
    clube = _novo_clube(fake_clube_repo)
    uot_que_falha = _UnidadeDeTrabalhoQueFalhaAoConfirmar()
    service = MercadoService(
        fake_repo,
        fake_clube_repo,
        fake_contrato_repo,
        fake_transacao_repo,
        fake_escalacao_repo,
        uot_que_falha,
    )

    with pytest.raises(RuntimeError):
        service.comprar(jogador.id, _dados_de_compra(clube.id), _MOMENTO)

    assert uot_que_falha.desfez is True
