from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from mercado_jogadores.clubes.service import ClubeService, DadosCadastroClube
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.service import DadosCadastroJogador, JogadorService
from mercado_jogadores.mercado.models import Contrato
from tests.conftest import FakeClubeRepository, FakeContratoRepository, FakeJogadorRepository

_MOMENTO = datetime(2026, 11, 2, 10, 15, tzinfo=FUSO_BRASILIA)


def _dados_cadastro_clube(**sobrescritas: object) -> DadosCadastroClube:
    base = dict(nome="Águias FC", sigla="AGU")
    base.update(sobrescritas)
    return DadosCadastroClube(**base)


def _cadastrar_jogador(fake_repo: FakeJogadorRepository, **sobrescritas: object) -> Jogador:
    dados = dict(
        nome="Jogador Teste",
        posicao="ATA",
        agilidade=70,
        idade=25,
        pace=70,
        shooting=70,
        passing=70,
        dribbling=70,
        defending=70,
        physical=70,
        potential=75,
    )
    dados.update(sobrescritas)
    resultado = JogadorService(fake_repo).cadastrar(DadosCadastroJogador(**dados))
    return resultado.jogador


class TestCadastrar:
    def test_clube_nasce_com_caixa_300_e_sem_jogadores(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)

        resultado = service.cadastrar(_dados_cadastro_clube())

        assert resultado.clube.caixa == Decimal("300.00")
        assert resultado.squad_value == Decimal("0.00")
        assert resultado.net_worth == Decimal("300.00")
        assert resultado.elenco == []

    def test_nome_duplicado_ignorando_caixa_e_recusado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        service.cadastrar(_dados_cadastro_clube(nome="Águias FC", sigla="AGU"))

        with pytest.raises(ConflitoError):
            service.cadastrar(_dados_cadastro_clube(nome="águias fc", sigla="AGF"))

    def test_nome_com_acento_diferente_e_aceito(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        service.cadastrar(_dados_cadastro_clube(nome="Águias FC", sigla="AGU"))

        resultado = service.cadastrar(_dados_cadastro_clube(nome="Aguias FC", sigla="AGF"))

        assert resultado.clube.id is not None

    def test_sigla_duplicada_e_recusada(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        service.cadastrar(_dados_cadastro_clube(nome="Águias FC", sigla="AGU"))

        with pytest.raises(ConflitoError):
            service.cadastrar(_dados_cadastro_clube(nome="Leões FC", sigla="AGU"))

    def test_limite_de_20_clubes(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        for i in range(20):
            service.cadastrar(
                _dados_cadastro_clube(nome=f"Clube {i:02d} FC", sigla=f"C{i:02d}")
            )

        with pytest.raises(ConflitoError):
            service.cadastrar(_dados_cadastro_clube(nome="Clube Extra FC", sigla="C20"))


class TestConsultar:
    def test_clube_inexistente_levanta_nao_encontrado(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)

        with pytest.raises(NaoEncontradoError):
            service.consultar(999, _MOMENTO)

    def test_clube_recem_criado_tem_elenco_vazio(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        clube = service.cadastrar(_dados_cadastro_clube()).clube

        resultado = service.consultar(clube.id, _MOMENTO)

        assert resultado.elenco == []
        assert resultado.squad_value == Decimal("0.00")
        assert resultado.net_worth == resultado.clube.caixa

    def test_elenco_ordenado_por_posicao_depois_nome_depois_id(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        clube = service.cadastrar(_dados_cadastro_clube()).clube

        meia = _cadastrar_jogador(fake_repo, nome="Zeta Meia", posicao="MEI")
        atacante = _cadastrar_jogador(fake_repo, nome="Ana Ataque", posicao="ATA")
        goleiro = _cadastrar_jogador(fake_repo, nome="Beto Gol", posicao="GOL")
        zagueiro_b = _cadastrar_jogador(fake_repo, nome="Zagueiro B", posicao="ZAG")
        zagueiro_a = _cadastrar_jogador(fake_repo, nome="Zagueiro A", posicao="ZAG")

        for jogador in (meia, atacante, goleiro, zagueiro_b, zagueiro_a):
            jogador.clube_id = clube.id
            fake_repo.salvar(jogador)

        resultado = service.consultar(clube.id, _MOMENTO)

        nomes_em_ordem = [item.calculados.jogador.nome for item in resultado.elenco]
        assert nomes_em_ordem == [
            "Beto Gol",
            "Zagueiro A",
            "Zagueiro B",
            "Zeta Meia",
            "Ana Ataque",
        ]

    def test_squad_value_e_net_worth_somam_o_valor_de_mercado_do_elenco(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        clube = service.cadastrar(_dados_cadastro_clube()).clube

        jogador = _cadastrar_jogador(fake_repo, idade=25, agilidade=50, potential=75)
        jogador.clube_id = clube.id
        fake_repo.salvar(jogador)

        resultado = service.consultar(clube.id, _MOMENTO)

        valor_esperado = resultado.elenco[0].calculados.market_value
        assert resultado.squad_value == valor_esperado
        assert resultado.net_worth == clube.caixa + valor_esperado

    def test_jogador_sem_contrato_nao_quebra_e_contract_e_none(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        """Compatibilidade com testes/estados anteriores à change `mercado`: um jogador com
        `clube_id` atribuído manualmente (sem passar por `MercadoService.comprar`) não tem
        contrato nenhum — o elenco não deve quebrar, só mostrar `contract=None`."""
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        clube = service.cadastrar(_dados_cadastro_clube()).clube
        jogador = _cadastrar_jogador(fake_repo)
        jogador.clube_id = clube.id
        fake_repo.salvar(jogador)

        resultado = service.consultar(clube.id, _MOMENTO)

        assert resultado.elenco[0].contract is None

    def test_jogador_do_elenco_mostra_o_contrato_calculado_na_hora(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        clube = service.cadastrar(_dados_cadastro_clube()).clube
        jogador = _cadastrar_jogador(fake_repo)
        jogador.clube_id = clube.id
        fake_repo.salvar(jogador)

        fidelidade_ate = _MOMENTO + timedelta(days=120)
        fake_contrato_repo.adicionar(
            Contrato(
                jogador_id=jogador.id,
                clube_id=clube.id,
                valor_compra=Decimal("37.00"),
                fidelidade_ate=fidelidade_ate,
                situacao="ATIVO",
                iniciado_em=_MOMENTO,
            )
        )

        resultado = service.consultar(clube.id, _MOMENTO)

        contrato = resultado.elenco[0].contract
        assert contrato is not None
        assert contrato.purchase_value == Decimal("37.00")
        assert contrato.loyalty_until == fidelidade_ate
        assert contrato.remaining_days == 120
        assert contrato.penalty_rate == 10


class TestListar:
    def test_ordenacao_padrao_por_nome(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        service.cadastrar(_dados_cadastro_clube(nome="Zebras FC", sigla="ZEB"))
        service.cadastrar(_dados_cadastro_clube(nome="Águias FC", sigla="AGU"))

        resultado = service.listar()

        assert [c.clube.nome for c in resultado] == ["Águias FC", "Zebras FC"]

    def test_ordenacao_por_patrimonio_com_desempate_por_nome(
        self,
        fake_clube_repo: FakeClubeRepository,
        fake_repo: FakeJogadorRepository,
        fake_contrato_repo: FakeContratoRepository,
    ) -> None:
        service = ClubeService(fake_clube_repo, fake_repo, fake_contrato_repo)
        rico = service.cadastrar(_dados_cadastro_clube(nome="Rico FC", sigla="RIC")).clube
        service.cadastrar(_dados_cadastro_clube(nome="Pobre FC", sigla="POB"))
        service.cadastrar(_dados_cadastro_clube(nome="Empate A FC", sigla="EMA"))
        service.cadastrar(_dados_cadastro_clube(nome="Empate B FC", sigla="EMB"))

        jogador = _cadastrar_jogador(fake_repo, nome="Craque", posicao="ATA")
        jogador.clube_id = rico.id
        fake_repo.salvar(jogador)

        resultado = service.listar(sort="net_worth_desc")

        nomes = [c.clube.nome for c in resultado]
        assert nomes[0] == "Rico FC"
        assert nomes[1:] == ["Empate A FC", "Empate B FC", "Pobre FC"]
