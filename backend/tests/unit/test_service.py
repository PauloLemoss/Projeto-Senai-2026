from datetime import datetime
from decimal import Decimal

import pytest

from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError
from mercado_jogadores.jogadores.service import (
    DadosCadastroJogador,
    DadosEdicaoJogador,
    JogadorService,
)
from tests.conftest import (
    FakeClubeRepository,
    FakeEscalacaoRepository,
    FakeJogadorRepository,
    FakeUnidadeDeTrabalho,
)


def _dados_cadastro_validos() -> DadosCadastroJogador:
    return DadosCadastroJogador(
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


class TestCadastrar:
    def test_calcula_e_grava_o_valor_base_uma_unica_vez(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )

        resultado = service.cadastrar(_dados_cadastro_validos())

        assert resultado.jogador.valor_base == Decimal("40.00")  # RN06, tabela do enunciado
        assert resultado.overall == 75

    def test_jogador_nasce_livre_e_apto(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )

        resultado = service.cadastrar(_dados_cadastro_validos())

        assert resultado.jogador.condicao == "APTO"
        assert resultado.jogador.clube_id is None


class TestConsultar:
    def test_jogador_inexistente_levanta_nao_encontrado(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )

        with pytest.raises(NaoEncontradoError):
            service.consultar(999)

    def test_valor_de_mercado_calculado_a_cada_consulta(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())

        service.alterar_condicao(cadastrado.jogador.id, "MAL_CONDICIONADO")
        resultado = service.consultar(cadastrado.jogador.id)

        # agilidade 85 (80-100: desconto pela metade) -> 7,5%; idade 25 (22-31: 0%)
        assert resultado.market_value == Decimal("37.00")


class TestEditar:
    def test_edicao_nao_muda_indicadores_nem_valor_base(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())

        resultado = service.editar(
            cadastrado.jogador.id,
            DadosEdicaoJogador(nome="Meia Lua", posicao="MEI", agilidade=90, idade=25),
        )

        assert resultado.jogador.agilidade == 90
        assert resultado.jogador.valor_base == Decimal("40.00")
        assert resultado.jogador.potencial == 86

    def test_mudanca_de_posicao_com_clube_e_recusada(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())
        cadastrado.jogador.clube_id = 1  # simula jogador já comprado por um clube
        fake_repo.salvar(cadastrado.jogador)

        with pytest.raises(ConflitoError):
            service.editar(
                cadastrado.jogador.id,
                DadosEdicaoJogador(nome="Meia Lua", posicao="ATA", agilidade=85, idade=25),
            )

    def test_reducao_de_idade_e_recusada(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())

        with pytest.raises(ConflitoError):
            service.editar(
                cadastrado.jogador.id,
                DadosEdicaoJogador(nome="Meia Lua", posicao="MEI", agilidade=85, idade=24),
            )


class TestAlterarCondicao:
    def test_transicao_direta_de_doente_para_apto_e_recusada(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())
        service.alterar_condicao(cadastrado.jogador.id, "DOENTE")

        with pytest.raises(ConflitoError):
            service.alterar_condicao(cadastrado.jogador.id, "APTO")

    def test_enviar_a_condicao_atual_e_aceito_sem_erro(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())

        resultado = service.alterar_condicao(cadastrado.jogador.id, "APTO")

        assert resultado.jogador.condicao == "APTO"

    def test_titular_que_fica_doente_sai_da_escalacao(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())
        fake_escalacao_repo.substituir_escalacao_do_clube(
            1, [cadastrado.jogador.id], datetime.now()
        )

        service.alterar_condicao(cadastrado.jogador.id, "DOENTE")

        assert cadastrado.jogador.id not in fake_escalacao_repo.listar_titulares_do_clube(1)


class TestExcluir:
    def test_exclusao_de_jogador_com_clube_e_recusada(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())
        cadastrado.jogador.clube_id = 1
        fake_repo.salvar(cadastrado.jogador)

        with pytest.raises(ConflitoError):
            service.excluir(cadastrado.jogador.id)

    def test_exclusao_de_jogador_livre_marca_excluido_e_some_da_consulta(
        self,
        fake_repo: FakeJogadorRepository,
        fake_escalacao_repo: FakeEscalacaoRepository,
        fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    ) -> None:
        service = JogadorService(
            fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, FakeClubeRepository()
        )
        cadastrado = service.cadastrar(_dados_cadastro_validos())

        service.excluir(cadastrado.jogador.id)

        with pytest.raises(NaoEncontradoError):
            service.consultar(cadastrado.jogador.id)


class _UnidadeDeTrabalhoQueFalhaAoConfirmar:
    """Simula uma falha de banco no commit, para testar que `_alterar_para_doente` aciona o
    rollback e propaga o erro — ver `JogadorService._alterar_para_doente`."""

    def __init__(self) -> None:
        self.desfez = False

    def confirmar(self) -> None:
        raise RuntimeError("falha simulada no commit")

    def desfazer(self) -> None:
        self.desfez = True


def test_falha_ao_confirmar_doente_aciona_o_rollback_e_propaga_o_erro(
    fake_repo: FakeJogadorRepository, fake_escalacao_repo: FakeEscalacaoRepository
) -> None:
    uot_que_falha = _UnidadeDeTrabalhoQueFalhaAoConfirmar()
    service = JogadorService(fake_repo, fake_escalacao_repo, uot_que_falha, FakeClubeRepository())
    cadastrado = service.cadastrar(_dados_cadastro_validos())

    with pytest.raises(RuntimeError):
        service.alterar_condicao(cadastrado.jogador.id, "DOENTE")

    assert uot_que_falha.desfez is True
