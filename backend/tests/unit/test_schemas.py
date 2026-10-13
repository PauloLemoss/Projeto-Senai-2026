import pytest
from pydantic import ValidationError

from mercado_jogadores.jogadores.schemas import JogadorCreate

_BASE = {
    "name": "Meia Lua",
    "position": "MEI",
    "agility": 85,
    "age": 25,
    "pace": 70,
    "shooting": 68,
    "passing": 82,
    "dribbling": 79,
    "defending": 55,
    "physical": 64,
    "potential": 86,
}


def test_cadastro_valido_e_aceito() -> None:
    jogador = JogadorCreate(**_BASE)
    assert jogador.name == "Meia Lua"


def test_nome_com_menos_de_duas_palavras_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "name": "Lua"})


def test_nome_com_digito_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "name": "Jogador 10"})


def test_espacos_redundantes_no_nome_sao_normalizados() -> None:
    jogador = JogadorCreate(**{**_BASE, "name": "  Meia   Zeta "})
    assert jogador.name == "Meia Zeta"


def test_soma_dos_atributos_acima_de_480_e_recusada() -> None:
    dados = {**_BASE, "pace": 99, "shooting": 99, "passing": 99, "dribbling": 99, "defending": 99, "physical": 10}
    with pytest.raises(ValidationError):
        JogadorCreate(**dados)


def test_potential_menor_que_o_maior_atributo_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "potential": 50})


def test_jogador_com_33_anos_exige_potential_igual_ao_maior_atributo() -> None:
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "age": 33, "potential": 90})


def test_jogador_com_33_anos_aceita_potential_igual_ao_maior_atributo() -> None:
    dados = {**_BASE, "age": 33, "potential": 82}  # 82 é o maior dos seis atributos
    jogador = JogadorCreate(**dados)
    assert jogador.potential == 82


def test_agilidade_acima_de_85_com_35_anos_e_recusada() -> None:
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "age": 35, "agility": 90})


def test_campo_controlado_pelo_sistema_e_ignorado() -> None:
    jogador = JogadorCreate(**{**_BASE, "base_value": 999, "condition": "DOENTE", "club_id": 1})
    assert not hasattr(jogador, "base_value")
    assert not hasattr(jogador, "club_id")


def test_enum_em_minusculas_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "position": "mei"})


def test_numero_como_texto_e_recusado() -> None:
    """V2: `"85"` (texto) é recusado, mesmo parecendo um número válido."""
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "agility": "85"})


def test_inteiro_com_parte_fracionaria_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "agility": 85.5})


def test_float_sem_parte_fracionaria_e_aceito_como_inteiro() -> None:
    jogador = JogadorCreate(**{**_BASE, "agility": 85.0})
    assert jogador.agility == 85


def test_booleano_em_campo_inteiro_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorCreate(**{**_BASE, "agility": True})
