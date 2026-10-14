"""Testes das funções puras de RN02 a RN06, com os valores das tabelas de exemplo do enunciado
(README.md, seções "Cadastro de Jogadores" — essas tabelas foram conferidas pela banca e podem
ser usadas como casos de teste)."""

from decimal import Decimal

import pytest

from mercado_jogadores.jogadores.calculos import (
    arredondar,
    calcular_overall,
    calcular_valor_base,
    calcular_valor_de_mercado,
)


class TestArredondar:
    def test_meio_exato_arredonda_para_longe_do_zero(self) -> None:
        assert arredondar(Decimal("14.775")) == Decimal("14.78")
        assert arredondar(Decimal("0.385")) == Decimal("0.39")

    def test_nao_usa_banker_rounding(self) -> None:
        # round() nativo do Python daria 3.62 (par mais próximo); a regra exige 3.63.
        assert arredondar(Decimal("3.625")) == Decimal("3.63")


class TestCalcularOverall:
    @pytest.mark.parametrize(
        "atributos,posicao,esperado",
        [
            (
                {
                    "pace": 68,
                    "shooting": 65,
                    "passing": 80,
                    "dribbling": 78,
                    "defending": 52,
                    "physical": 60,
                },
                "MEI",
                73,
            ),
            (
                {
                    "pace": 78,
                    "shooting": 75,
                    "passing": 73,
                    "dribbling": 82,
                    "defending": 48,
                    "physical": 68,
                },
                "ATA",
                76,
            ),
            (
                {
                    "pace": 72,
                    "shooting": 70,
                    "passing": 78,
                    "dribbling": 76,
                    "defending": 70,
                    "physical": 66,
                },
                "LAT",
                72,
            ),
            (
                # soma ÷ 100 = 72,50 -> meio pra cima -> 73
                {
                    "pace": 50,
                    "shooting": 90,
                    "passing": 60,
                    "dribbling": 40,
                    "defending": 80,
                    "physical": 75,
                },
                "ZAG",
                73,
            ),
            (
                {
                    "pace": 55,
                    "shooting": 30,
                    "passing": 65,
                    "dribbling": 40,
                    "defending": 72,
                    "physical": 68,
                },
                "GOL",
                68,
            ),
        ],
    )
    def test_tabela_de_exemplo_do_enunciado(
        self, atributos: dict[str, int], posicao: str, esperado: int
    ) -> None:
        assert calcular_overall(atributos, posicao) == esperado


class TestCalcularValorBase:
    @pytest.mark.parametrize(
        "overall,potential,idade_cadastro,esperado",
        [
            (75, 86, 25, Decimal("40.00")),
            (60, 70, 30, Decimal("10.00")),
            (61, 70, 30, Decimal("12.00")),
            (76, 80, 22, Decimal("46.00")),
            (85, 92, 27, Decimal("100.00")),
            (70, 84, 21, Decimal("34.20")),  # jovem promessa
            (70, 84, 22, Decimal("30.00")),  # sem jovem promessa (22 anos)
            (45, 90, 18, Decimal("3.63")),  # 3,625 arredondado para longe do zero
            (40, 66, 36, Decimal("1.00")),  # piso
        ],
    )
    def test_tabela_de_exemplo_do_enunciado(
        self, overall: int, potential: int, idade_cadastro: int, esperado: Decimal
    ) -> None:
        assert calcular_valor_base(overall, potential, idade_cadastro) == esperado


class TestCalcularValorDeMercado:
    """RN02 a RN05 — este é o teste exigido pelo diferencial técnico B5 do barema."""

    @pytest.mark.parametrize(
        "valor_base,condicao,agilidade,idade,esperado",
        [
            (Decimal("82.00"), "APTO", 20, 25, Decimal("82.00")),
            (Decimal("82.00"), "APTO", 50, 19, Decimal("90.20")),
            (Decimal("82.00"), "MAL_CONDICIONADO", 50, 25, Decimal("69.70")),
            (Decimal("82.00"), "MAL_CONDICIONADO", 80, 21, Decimal("84.05")),
            (Decimal("82.00"), "MAL_CONDICIONADO", 30, 33, Decimal("53.30")),
            (Decimal("82.00"), "DOENTE", 90, 25, Decimal("69.70")),
            (Decimal("82.00"), "DOENTE", 30, 25, Decimal("49.20")),  # teto exatamente em -40%
            (Decimal("82.00"), "DOENTE", 10, 40, Decimal("49.20")),  # -50% limitado a -40%
            (Decimal("9.50"), "MAL_CONDICIONADO", 85, 25, Decimal("8.79")),  # 8,7875 arredondado
            (Decimal("1.00"), "MAL_CONDICIONADO", 50, 35, Decimal("1.00")),  # 0,75 sobe pro piso
        ],
    )
    def test_tabela_de_exemplo_do_enunciado(
        self,
        valor_base: Decimal,
        condicao: str,
        agilidade: int,
        idade: int,
        esperado: Decimal,
    ) -> None:
        assert calcular_valor_de_mercado(valor_base, condicao, agilidade, idade) == esperado
