from mercado_jogadores.clubes.models import Clube
from tests.conftest import FakeClubeRepository


def _novo_clube() -> Clube:
    return Clube(nome="Águias FC", nome_normalizado="águias fc", sigla="AGU")


def test_salvar_atribui_id_e_obter_retorna_o_mesmo_clube(
    fake_clube_repo: FakeClubeRepository,
) -> None:
    clube = _novo_clube()

    salvo = fake_clube_repo.salvar(clube)
    assert salvo.id is not None

    obtido = fake_clube_repo.obter(salvo.id)
    assert obtido is not None
    assert obtido.nome == "Águias FC"


def test_obter_retorna_none_para_clube_inexistente(
    fake_clube_repo: FakeClubeRepository,
) -> None:
    assert fake_clube_repo.obter(999) is None
