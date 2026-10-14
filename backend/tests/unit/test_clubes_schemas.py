import pytest
from pydantic import ValidationError

from mercado_jogadores.clubes.schemas import ClubeCreate

_BASE = {"name": "Águias FC", "acronym": "AGU"}


def test_cadastro_valido_e_aceito() -> None:
    clube = ClubeCreate(**_BASE)
    assert clube.name == "Águias FC"
    assert clube.acronym == "AGU"


def test_espacos_redundantes_no_nome_sao_normalizados() -> None:
    clube = ClubeCreate(**{**_BASE, "name": "  Águias   FC "})
    assert clube.name == "Águias FC"


def test_nome_com_digito_e_recusado() -> None:
    with pytest.raises(ValidationError):
        ClubeCreate(**{**_BASE, "name": "Clube 10"})


def test_nome_com_uma_palavra_so_e_recusado() -> None:
    with pytest.raises(ValidationError):
        ClubeCreate(**{**_BASE, "name": "Aguias", "acronym": "AGU"})


def test_nome_com_mais_de_cinco_palavras_e_recusado() -> None:
    with pytest.raises(ValidationError):
        ClubeCreate(**{**_BASE, "name": "Um Dois Tres Quatro Cinco Seis"})


def test_nome_com_cinco_palavras_e_aceito() -> None:
    clube = ClubeCreate(**{**_BASE, "name": "Um Dois Tres Quatro Cinco", "acronym": "UDO"})
    assert clube.name == "Um Dois Tres Quatro Cinco"


def test_nome_com_menos_de_tres_caracteres_e_recusado() -> None:
    with pytest.raises(ValidationError):
        ClubeCreate(**{**_BASE, "name": "A"})


def test_nome_com_hifen_e_ponto_e_aceito() -> None:
    clube = ClubeCreate(**{"name": "F.C. Vento-Sul", "acronym": "FVS"})
    assert clube.name == "F.C. Vento-Sul"


@pytest.mark.parametrize("sigla", ["AG", "agu", "ÁGU"])
def test_sigla_fora_do_formato_basico_e_recusada(sigla: str) -> None:
    with pytest.raises(ValidationError):
        ClubeCreate(**{**_BASE, "acronym": sigla})


def test_sigla_que_nao_comeca_pela_primeira_letra_do_nome_e_recusada() -> None:
    with pytest.raises(ValidationError):
        ClubeCreate(**{**_BASE, "acronym": "GUI"})


def test_sigla_com_tres_letras_iguais_e_recusada() -> None:
    with pytest.raises(ValidationError):
        ClubeCreate(name="Ana Ana Ana", acronym="AAA")


def test_sigla_fora_de_ordem_no_nome_e_recusada() -> None:
    with pytest.raises(ValidationError):
        ClubeCreate(**{**_BASE, "acronym": "AUG"})
