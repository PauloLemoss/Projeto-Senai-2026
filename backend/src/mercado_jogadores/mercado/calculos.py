"""Funções puras de cálculo do domínio mercado (RN13, RN15, RN16).

Nenhuma função aqui sabe de HTTP, banco ou FastAPI — só matemática, reaproveitando `arredondar`
de `jogadores/calculos.py` (mesmo arredondamento "para longe do zero", feito uma única vez no
resultado final de cada cálculo).
"""

from datetime import datetime, timedelta
from decimal import Decimal

from mercado_jogadores.jogadores.calculos import arredondar

TETO_PARA_COBRAR_TAXA = Decimal("30.00")
PERCENTUAL_DA_TAXA = Decimal("0.05")

MICROSSEGUNDOS_POR_DIA = 86_400_000_000
TETO_DA_MULTA = Decimal("10.00")

LIMITE_PRIMEIRA_FAIXA_DE_COMISSAO = Decimal("10.00")
PERCENTUAL_PRIMEIRA_FAIXA_DE_COMISSAO = Decimal("0.10")
PERCENTUAL_SEGUNDA_FAIXA_DE_COMISSAO = Decimal("0.20")


def calcular_taxa_de_compra(valor_de_mercado: Decimal) -> Decimal:
    """RN13: 5% do valor de mercado, arredondado, cobrado só quando maior que 30,00."""
    if valor_de_mercado <= TETO_PARA_COBRAR_TAXA:
        return Decimal("0.00")
    return arredondar(valor_de_mercado * PERCENTUAL_DA_TAXA)


def limite_de_compra(caixa: Decimal) -> Decimal:
    """RN13: metade do caixa antes da compra, sem arredondar (limite exato)."""
    return caixa / Decimal(2)


def calcular_dias_restantes_e_percentual_de_multa(
    fidelidade_ate: datetime, momento: datetime
) -> tuple[int, int]:
    """RN15.1-2: dias restantes (arredondados para cima, com fração) e o percentual de multa pela
    faixa: 0 dia -> 0%; 1 a 30 -> 5%; 31 a 180 -> 10%; 181 ou mais -> 20%."""
    diferenca = fidelidade_ate - momento
    if diferenca <= timedelta(0):
        return 0, 0

    microssegundos_restantes = (
        diferenca.days * 86_400_000_000 + diferenca.seconds * 1_000_000 + diferenca.microseconds
    )
    dias_restantes = -(-microssegundos_restantes // MICROSSEGUNDOS_POR_DIA)  # ceil sem float

    if dias_restantes <= 30:
        percentual = 5
    elif dias_restantes <= 180:
        percentual = 10
    else:
        percentual = 20
    return dias_restantes, percentual


def calcular_multa(valor_de_mercado: Decimal, percentual: int) -> Decimal:
    """RN15.3: multa = valor de mercado × percentual, arredondada e limitada a 10,00."""
    multa = arredondar(valor_de_mercado * Decimal(percentual) / Decimal(100))
    return min(multa, TETO_DA_MULTA)


def calcular_comissao_de_venda(lucro: Decimal) -> Decimal:
    """RN16.3: comissão progressiva, só quando o lucro é maior que zero: 10% sobre a parte até
    10,00 de lucro, mais 20% sobre a parte acima, somadas e arredondadas uma única vez."""
    if lucro <= Decimal(0):
        return Decimal("0.00")

    parte_ate_dez = min(lucro, LIMITE_PRIMEIRA_FAIXA_DE_COMISSAO)
    parte_acima_de_dez = max(lucro - LIMITE_PRIMEIRA_FAIXA_DE_COMISSAO, Decimal(0))
    comissao = (
        parte_ate_dez * PERCENTUAL_PRIMEIRA_FAIXA_DE_COMISSAO
        + parte_acima_de_dez * PERCENTUAL_SEGUNDA_FAIXA_DE_COMISSAO
    )
    return arredondar(comissao)


def calcular_credito_na_venda(valor: Decimal, multa: Decimal, comissao: Decimal) -> Decimal:
    """RN16.4: crédito no caixa = valor de mercado na venda − multa − comissão."""
    return valor - multa - comissao
