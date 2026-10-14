from datetime import datetime
from decimal import Decimal

import pytest
from pydantic import ValidationError

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.clubes.schemas import ClubeComElencoRead, ClubeCreate
from mercado_jogadores.clubes.service import ClubeComElenco, ContratoDoElenco, JogadorDoElenco
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.service import JogadorComCalculados

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


def test_clube_com_elenco_read_bate_com_o_exemplo_2_2_2_do_enunciado() -> None:
    jogador = Jogador(
        id=2,
        nome="Meia Lua",
        posicao="MEI",
        agilidade=85,
        idade=25,
        valor_base=Decimal("40.00"),
        condicao="MAL_CONDICIONADO",
        clube_id=1,
        velocidade=70,
        finalizacao=68,
        passe=82,
        drible=79,
        defesa=55,
        fisico=64,
        potencial=86,
    )
    calculados = JogadorComCalculados(jogador=jogador, overall=75, market_value=Decimal("37.00"))
    contrato = ContratoDoElenco(
        purchase_value=Decimal("37.00"),
        loyalty_until=datetime(2027, 3, 2, 10, 15, tzinfo=FUSO_BRASILIA),
        remaining_days=120,
        penalty_rate=10,
    )
    clube = Clube(
        id=1, nome="Águias FC", nome_normalizado="águias fc", sigla="AGU", caixa=Decimal("261.15")
    )
    resultado = ClubeComElenco(
        clube=clube,
        elenco=[JogadorDoElenco(calculados=calculados, contract=contrato)],
        squad_value=Decimal("37.00"),
        net_worth=Decimal("298.15"),
    )

    corpo = ClubeComElencoRead.a_partir_do_resultado(resultado).model_dump()

    assert corpo == {
        "id": 1,
        "name": "Águias FC",
        "acronym": "AGU",
        "cash": 261.15,
        "squad_value": 37.00,
        "net_worth": 298.15,
        "players": [
            {
                "id": 2,
                "name": "Meia Lua",
                "position": "MEI",
                "agility": 85,
                "age": 25,
                "condition": "MAL_CONDICIONADO",
                "base_value": 40.00,
                "market_value": 37.00,
                "pace": 70,
                "shooting": 68,
                "passing": 82,
                "dribbling": 79,
                "defending": 55,
                "physical": 64,
                "potential": 86,
                "overall": 75,
                "club_id": 1,
                "contract": {
                    "purchase_value": 37.00,
                    "loyalty_until": "2027-03-02T10:15:00-03:00",
                    "remaining_days": 120,
                    "penalty_rate": 10,
                },
            }
        ],
    }


def test_jogador_sem_contrato_mostra_contract_nulo() -> None:
    jogador = Jogador(
        id=2, nome="Meia Lua", posicao="MEI", agilidade=85, idade=25,
        valor_base=Decimal("40.00"), condicao="APTO", clube_id=1, velocidade=70,
        finalizacao=68, passe=82, drible=79, defesa=55, fisico=64, potencial=86,
    )
    calculados = JogadorComCalculados(jogador=jogador, overall=75, market_value=Decimal("40.00"))
    clube = Clube(
        id=1, nome="Águias FC", nome_normalizado="águias fc", sigla="AGU", caixa=Decimal("300.00")
    )
    resultado = ClubeComElenco(
        clube=clube,
        elenco=[JogadorDoElenco(calculados=calculados, contract=None)],
        squad_value=Decimal("40.00"),
        net_worth=Decimal("340.00"),
    )

    corpo = ClubeComElencoRead.a_partir_do_resultado(resultado).model_dump()

    assert corpo["players"][0]["contract"] is None
