from decimal import Decimal

from mercado_jogadores.jogadores.models import Jogador
from tests.conftest import FakeJogadorRepository


def _novo_jogador() -> Jogador:
    return Jogador(
        nome="Meia Lua",
        posicao="MEI",
        agilidade=85,
        idade=25,
        valor_base=Decimal("40.00"),
        condicao="APTO",
        velocidade=70,
        finalizacao=68,
        passe=82,
        drible=79,
        defesa=55,
        fisico=64,
        potencial=86,
    )


def test_salvar_atribui_id_e_obter_retorna_o_mesmo_jogador(
    fake_repo: FakeJogadorRepository,
) -> None:
    jogador = _novo_jogador()

    salvo = fake_repo.salvar(jogador)
    assert salvo.id is not None

    obtido = fake_repo.obter(salvo.id)
    assert obtido is not None
    assert obtido.nome == "Meia Lua"


def test_obter_retorna_none_para_jogador_inexistente(
    fake_repo: FakeJogadorRepository,
) -> None:
    assert fake_repo.obter(999) is None
