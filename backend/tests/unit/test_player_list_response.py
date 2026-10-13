from decimal import Decimal

from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.schemas import PlayerListResponse
from mercado_jogadores.jogadores.service import JogadorComCalculados, ListaDeJogadores


def test_mapeamento_de_lista_de_jogadores_para_player_list_response() -> None:
    jogador = Jogador(
        id=1,
        nome="Meia Lua",
        posicao="MEI",
        agilidade=85,
        idade=25,
        valor_base=Decimal("40.00"),
        condicao="APTO",
        clube_id=None,
        velocidade=70,
        finalizacao=68,
        passe=82,
        drible=79,
        defesa=55,
        fisico=64,
        potencial=86,
    )
    resultado = ListaDeJogadores(
        itens=[JogadorComCalculados(jogador=jogador, overall=75, market_value=Decimal("40.00"))],
        total_items=1,
        page=1,
        limit=10,
    )

    resposta = PlayerListResponse.a_partir_do_resultado(resultado)

    assert len(resposta.data) == 1
    assert resposta.data[0].name == "Meia Lua"
    assert resposta.meta.total_items == 1
    assert resposta.meta.total_pages == 1
    assert resposta.meta.page == 1
    assert resposta.meta.limit == 10
