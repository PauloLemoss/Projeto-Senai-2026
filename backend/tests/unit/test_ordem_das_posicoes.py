from mercado_jogadores.jogadores.calculos import ORDEM_DAS_POSICOES


def test_ordem_fixa_das_posicoes() -> None:
    assert ORDEM_DAS_POSICOES == ("GOL", "ZAG", "LAT", "MEI", "ATA")
