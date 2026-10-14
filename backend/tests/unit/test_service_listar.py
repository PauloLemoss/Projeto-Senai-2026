from decimal import Decimal

import pytest

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.core.errors import NaoEncontradoError
from mercado_jogadores.jogadores.service import (
    DadosCadastroJogador,
    FiltrosDeListagem,
    JogadorService,
)
from tests.conftest import (
    FakeClubeRepository,
    FakeEscalacaoRepository,
    FakeJogadorRepository,
    FakeUnidadeDeTrabalho,
)


def _dados(nome: str = "Jogador Teste", **sobrescritas: object) -> DadosCadastroJogador:
    base = {
        "nome": nome,
        "posicao": "MEI",
        "agilidade": 70,
        "idade": 25,
        "pace": 70,
        "shooting": 60,
        "passing": 60,
        "dribbling": 60,
        "defending": 60,
        "physical": 60,
        "potential": 75,
    }
    base.update(sobrescritas)
    return DadosCadastroJogador(**base)


@pytest.fixture
def service(
    fake_repo: FakeJogadorRepository,
    fake_escalacao_repo: FakeEscalacaoRepository,
    fake_unidade_de_trabalho: FakeUnidadeDeTrabalho,
    fake_clube_repo: FakeClubeRepository,
) -> JogadorService:
    return JogadorService(fake_repo, fake_escalacao_repo, fake_unidade_de_trabalho, fake_clube_repo)


class TestListagemPaginadaBuscaEFiltros:
    def test_busca_ignora_acentos_e_caixa(self, service: JogadorService) -> None:
        service.cadastrar(_dados(nome="João Silva"))
        resultado = service.listar(FiltrosDeListagem(search="joao"))
        assert len(resultado.itens) == 1

    def test_busca_segundo_exemplo(self, service: JogadorService) -> None:
        service.cadastrar(_dados(nome="Meia Lua"))
        resultado = service.listar(FiltrosDeListagem(search="LUA"))
        assert len(resultado.itens) == 1

    def test_paginacao_intermediaria(self, service: JogadorService) -> None:
        for i in range(23):
            service.cadastrar(_dados(nome=f"Jogador Numero {i:02d}"))

        resultado = service.listar(FiltrosDeListagem(limit=10, page=1))

        assert len(resultado.itens) == 10
        assert resultado.total_items == 23
        assert resultado.total_pages == 3

    def test_ultima_pagina_parcial(self, service: JogadorService) -> None:
        for i in range(23):
            service.cadastrar(_dados(nome=f"Jogador Numero {i:02d}"))

        resultado = service.listar(FiltrosDeListagem(limit=10, page=3))

        assert len(resultado.itens) == 3
        assert resultado.total_items == 23
        assert resultado.total_pages == 3

    def test_pagina_alem_da_ultima(self, service: JogadorService) -> None:
        for i in range(23):
            service.cadastrar(_dados(nome=f"Jogador Numero {i:02d}"))

        resultado = service.listar(FiltrosDeListagem(limit=10, page=4))

        assert resultado.itens == []
        assert resultado.total_items == 23
        assert resultado.total_pages == 3

    def test_sem_jogadores_que_atendam_ao_filtro(self, service: JogadorService) -> None:
        resultado = service.listar(FiltrosDeListagem())
        assert resultado.itens == []
        assert resultado.total_items == 0
        assert resultado.total_pages == 0

    @pytest.mark.parametrize(
        "total_cadastrados,limit,page,itens_esperados,total_items,total_pages",
        [
            (23, 10, 1, 10, 23, 3),
            (23, 10, 3, 3, 23, 3),
            (23, 10, 4, 0, 23, 3),
            (23, 50, 1, 23, 23, 1),
            (0, 10, 1, 0, 0, 0),
        ],
    )
    def test_tabela_de_paginacao_do_rn07(
        self,
        service: JogadorService,
        total_cadastrados: int,
        limit: int,
        page: int,
        itens_esperados: int,
        total_items: int,
        total_pages: int,
    ) -> None:
        for i in range(total_cadastrados):
            service.cadastrar(_dados(nome=f"Jogador Numero {i:02d}"))

        resultado = service.listar(FiltrosDeListagem(limit=limit, page=page))

        assert len(resultado.itens) == itens_esperados
        assert resultado.total_items == total_items
        assert resultado.total_pages == total_pages

    def test_filtro_min_value_usa_o_valor_de_mercado(self, service: JogadorService) -> None:
        # overall baixo -> valor base pequeno; usamos min_value acima do valor base, mas dentro
        # do valor de mercado ajustado por idade pra confirmar que o filtro usa o calculado.
        cadastrado = service.cadastrar(_dados(idade=20))  # idade <=21 -> +10% no valor de mercado
        valor_base = cadastrado.jogador.valor_base
        resultado = service.listar(FiltrosDeListagem(min_value=valor_base + Decimal("0.01")))
        assert len(resultado.itens) == 1

    def test_filtro_max_value_usa_o_valor_de_mercado(self, service: JogadorService) -> None:
        caro = service.cadastrar(_dados(idade=20))  # +10% no valor de mercado
        barato = service.cadastrar(_dados(idade=35))  # -10% no valor de mercado

        resultado = service.listar(FiltrosDeListagem(max_value=barato.market_value))

        ids = {item.jogador.id for item in resultado.itens}
        assert barato.jogador.id in ids
        assert caro.jogador.id not in ids

    def test_faixa_com_um_so_limite_assume_o_extremo(self, service: JogadorService) -> None:
        service.cadastrar(_dados(idade=20))
        service.cadastrar(_dados(idade=44))

        resultado = service.listar(FiltrosDeListagem(min_age=30))

        assert len(resultado.itens) == 1
        assert resultado.itens[0].jogador.idade == 44


class TestOrdenacao:
    def test_ordenacao_por_posicao_usa_ordem_fixa(self, service: JogadorService) -> None:
        service.cadastrar(_dados(nome="Zagueiro Um", posicao="ZAG"))
        service.cadastrar(_dados(nome="Atacante Um", posicao="ATA"))
        service.cadastrar(_dados(nome="Goleiro Um", posicao="GOL"))

        resultado = service.listar(FiltrosDeListagem(sort=["position"]))

        posicoes = [item.jogador.posicao for item in resultado.itens]
        assert posicoes == ["GOL", "ZAG", "ATA"]

    def test_ordenacao_por_valor_de_mercado(self, service: JogadorService) -> None:
        caro = service.cadastrar(_dados(nome="Jogador Caro", idade=20))  # +10%
        barato = service.cadastrar(_dados(nome="Jogador Barato", idade=35))  # -10%

        asc = service.listar(FiltrosDeListagem(sort=["value_asc"]))
        assert [i.jogador.id for i in asc.itens] == [barato.jogador.id, caro.jogador.id]

        desc = service.listar(FiltrosDeListagem(sort=["value_desc"]))
        assert [i.jogador.id for i in desc.itens] == [caro.jogador.id, barato.jogador.id]

    def test_empate_e_desfeito_por_nome_e_depois_id(self, service: JogadorService) -> None:
        service.cadastrar(_dados(nome="Beta Jogador", idade=25))
        service.cadastrar(_dados(nome="Alfa Jogador", idade=25))

        resultado = service.listar(FiltrosDeListagem(sort=["age_asc"]))

        nomes = [item.jogador.nome for item in resultado.itens]
        assert nomes == ["Alfa Jogador", "Beta Jogador"]

    def test_repetir_o_mesmo_campo_e_recusado_pelo_service_nao_e_tratado_aqui(self) -> None:
        """A validação de 'sort=value_asc,value_desc' é responsabilidade do schema (400, antes
        de chegar ao service) — ver tests/unit/test_schemas.py."""


class TestValidacaoDosParametros:
    def test_so_livres_com_clube_false_e_aceito_e_aplica_os_dois_filtros(
        self, service: JogadorService, fake_clube_repo: FakeClubeRepository
    ) -> None:
        fake_clube_repo.salvar(Clube(nome="Águias FC", nome_normalizado="águias fc", sigla="AGU"))
        livre = service.cadastrar(_dados(nome="Jogador Livre"))
        com_clube = service.cadastrar(_dados(nome="Jogador Com Clube"))
        com_clube.jogador.clube_id = 1

        resultado = service.listar(FiltrosDeListagem(free=False, club_id=1))

        ids = {item.jogador.id for item in resultado.itens}
        assert com_clube.jogador.id in ids
        assert livre.jogador.id not in ids

    def test_filtro_por_club_id_de_clube_inexistente_e_recusado(
        self, service: JogadorService
    ) -> None:
        service.cadastrar(_dados(nome="Jogador Livre"))

        with pytest.raises(NaoEncontradoError):
            service.listar(FiltrosDeListagem(club_id=999))
