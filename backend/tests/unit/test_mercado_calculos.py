from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.mercado.calculos import (
    calcular_comissao_de_venda,
    calcular_credito_na_venda,
    calcular_dias_restantes_e_percentual_de_multa,
    calcular_multa,
    calcular_taxa_de_compra,
    limite_de_compra,
)

_MOMENTO = datetime(2026, 11, 5, 16, 40, tzinfo=FUSO_BRASILIA)


class TestCalcularTaxaDeCompra:
    @pytest.mark.parametrize(
        "valor_de_mercado, taxa_esperada",
        [
            (Decimal("28.00"), Decimal("0.00")),
            (Decimal("30.00"), Decimal("0.00")),  # não é maior que 30,00
            (Decimal("30.01"), Decimal("1.50")),  # 1,5005 arredondado
            (Decimal("47.62"), Decimal("2.38")),
            (Decimal("48.00"), Decimal("2.40")),
        ],
    )
    def test_tabela_de_taxa_da_rn13(
        self, valor_de_mercado: Decimal, taxa_esperada: Decimal
    ) -> None:
        assert calcular_taxa_de_compra(valor_de_mercado) == taxa_esperada


class TestLimiteDeCompra:
    @pytest.mark.parametrize(
        "caixa, limite_esperado",
        [
            (Decimal("300.00"), Decimal("150.00")),
            (Decimal("100.00"), Decimal("50.00")),
        ],
    )
    def test_tabela_de_limite_da_rn13(self, caixa: Decimal, limite_esperado: Decimal) -> None:
        assert limite_de_compra(caixa) == limite_esperado

    def test_limite_exato_sem_arredondar(self) -> None:
        assert limite_de_compra(Decimal("261.15")) == Decimal("130.575")


class TestCalcularDiasRestantesEPercentualDeMulta:
    def test_fidelidade_ja_passada_nao_gera_multa(self) -> None:
        fidelidade_ate = _MOMENTO - timedelta(days=1)

        assert calcular_dias_restantes_e_percentual_de_multa(fidelidade_ate, _MOMENTO) == (0, 0)

    def test_fidelidade_no_proprio_momento_nao_gera_multa(self) -> None:
        assert calcular_dias_restantes_e_percentual_de_multa(_MOMENTO, _MOMENTO) == (0, 0)

    @pytest.mark.parametrize(
        "fim_da_fidelidade, dias_restantes_esperados, percentual_esperado",
        [
            (timedelta(days=10, hours=2), 11, 5),
            (timedelta(days=30), 30, 5),
            (timedelta(days=30, minutes=1), 31, 10),
            (timedelta(days=180), 180, 10),
            (timedelta(days=180, minutes=1), 181, 20),
            (timedelta(days=200), 200, 20),
        ],
    )
    def test_tabela_de_faixas_da_rn15(
        self,
        fim_da_fidelidade: timedelta,
        dias_restantes_esperados: int,
        percentual_esperado: int,
    ) -> None:
        fidelidade_ate = _MOMENTO + fim_da_fidelidade

        resultado = calcular_dias_restantes_e_percentual_de_multa(fidelidade_ate, _MOMENTO)

        assert resultado == (dias_restantes_esperados, percentual_esperado)


class TestCalcularMulta:
    def test_multa_de_ponta_a_ponta_do_exemplo_do_enunciado(self) -> None:
        assert calcular_multa(Decimal("40.00"), 10) == Decimal("4.00")

    def test_multa_e_limitada_a_dez(self) -> None:
        # 20% de 75,00 seria 15,00, acima do teto
        assert calcular_multa(Decimal("75.00"), 20) == Decimal("10.00")

    def test_sem_multa_quando_percentual_e_zero(self) -> None:
        assert calcular_multa(Decimal("40.00"), 0) == Decimal("0.00")


class TestCalcularComissaoDeVenda:
    @pytest.mark.parametrize(
        "lucro, comissao_esperada",
        [
            (Decimal("3.00"), Decimal("0.30")),
            (Decimal("3.85"), Decimal("0.39")),  # 0,385 arredondado
            (Decimal("10.00"), Decimal("1.00")),
            (Decimal("10.01"), Decimal("1.00")),  # 1,002 arredondado
            (Decimal("15.00"), Decimal("2.00")),
            (Decimal("-7.50"), Decimal("0.00")),
        ],
    )
    def test_tabela_de_comissao_da_rn16(self, lucro: Decimal, comissao_esperada: Decimal) -> None:
        assert calcular_comissao_de_venda(lucro) == comissao_esperada


class TestCalcularCreditoNaVenda:
    @pytest.mark.parametrize(
        "valor_de_compra, valor_na_venda, multa, comissao, credito_esperado",
        [
            (
                Decimal("37.00"),
                Decimal("40.00"),
                Decimal("4.00"),
                Decimal("0.30"),
                Decimal("35.70"),
            ),
            (
                Decimal("50.00"),
                Decimal("42.50"),
                Decimal("8.50"),
                Decimal("0.00"),
                Decimal("34.00"),
            ),
            (
                Decimal("26.15"),
                Decimal("30.00"),
                Decimal("1.50"),
                Decimal("0.39"),
                Decimal("28.11"),
            ),
            (
                Decimal("25.00"),
                Decimal("25.00"),
                Decimal("0.00"),
                Decimal("0.00"),
                Decimal("25.00"),
            ),
            (
                Decimal("60.00"),
                Decimal("75.00"),
                Decimal("10.00"),
                Decimal("2.00"),
                Decimal("63.00"),
            ),
        ],
    )
    def test_tabela_de_venda_de_ponta_a_ponta_da_rn16(
        self,
        valor_de_compra: Decimal,
        valor_na_venda: Decimal,
        multa: Decimal,
        comissao: Decimal,
        credito_esperado: Decimal,
    ) -> None:
        lucro = valor_na_venda - valor_de_compra
        assert calcular_comissao_de_venda(lucro) == comissao
        assert calcular_credito_na_venda(valor_na_venda, multa, comissao) == credito_esperado
