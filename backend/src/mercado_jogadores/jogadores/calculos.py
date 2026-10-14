"""Funções puras de cálculo do domínio jogador (RN02 a RN06).

Nenhuma função aqui sabe de HTTP, banco ou FastAPI — só matemática, com `Decimal` em toda
a parte monetária e arredondamento "para longe do zero" (ROUND_HALF_UP do módulo `decimal`
arredonda empates para longe do zero, inclusive em valores negativos), feito uma única vez
no resultado final de cada cálculo, como manda o enunciado.
"""

from decimal import ROUND_HALF_UP, Decimal

DOIS_CASAS = Decimal("0.01")
PISO_VALOR = Decimal("1.00")

PESOS_POR_POSICAO: dict[str, dict[str, int]] = {
    "GOL": {
        "pace": 10,
        "shooting": 0,
        "passing": 20,
        "dribbling": 0,
        "defending": 40,
        "physical": 30,
    },
    "ZAG": {
        "pace": 10,
        "shooting": 0,
        "passing": 15,
        "dribbling": 0,
        "defending": 45,
        "physical": 30,
    },
    "LAT": {
        "pace": 25,
        "shooting": 0,
        "passing": 20,
        "dribbling": 15,
        "defending": 25,
        "physical": 15,
    },
    "MEI": {
        "pace": 10,
        "shooting": 15,
        "passing": 35,
        "dribbling": 25,
        "defending": 5,
        "physical": 10,
    },
    "ATA": {
        "pace": 20,
        "shooting": 40,
        "passing": 10,
        "dribbling": 20,
        "defending": 0,
        "physical": 10,
    },
}

# Ordem fixa GOL, ZAG, LAT, MEI, ATA (RN06/RN07/RN11/RN19/RN20) — derivada da ordem de inserção
# de PESOS_POR_POSICAO, nunca duplicada como uma lista separada.
ORDEM_DAS_POSICOES: tuple[str, ...] = tuple(PESOS_POR_POSICAO.keys())

DESCONTO_POR_CONDICAO: dict[str, Decimal] = {
    "APTO": Decimal(0),
    "MAL_CONDICIONADO": Decimal(15),
    "DOENTE": Decimal(30),
}

TETO_DESCONTO = Decimal(-40)


def arredondar(valor: Decimal) -> Decimal:
    """Arredonda para 2 casas, empate para longe do zero (RN "Arredondamento")."""
    return valor.quantize(DOIS_CASAS, rounding=ROUND_HALF_UP)


def calcular_overall(atributos: dict[str, int], posicao: str) -> int:
    """RN06.2: overall = soma(atributo × peso da posição) ÷ 100, arredondado (meio pra cima)."""
    pesos = PESOS_POR_POSICAO[posicao]
    soma = sum(Decimal(atributos[nome]) * Decimal(peso) for nome, peso in pesos.items())
    resultado = soma / Decimal(100)
    return int(resultado.quantize(Decimal(1), rounding=ROUND_HALF_UP))


def _parte_do_overall(overall: int) -> Decimal:
    """RN06.3.1: parte progressiva — 0,50 (41-60) + 2,00 (61-75) + 6,00 (76-99) por ponto."""
    total = Decimal(0)
    if overall > 40:
        pontos_faixa1 = min(overall, 60) - 40
        total += Decimal(pontos_faixa1) * Decimal("0.50")
    if overall > 60:
        pontos_faixa2 = min(overall, 75) - 60
        total += Decimal(pontos_faixa2) * Decimal("2.00")
    if overall > 75:
        pontos_faixa3 = min(overall, 99) - 75
        total += Decimal(pontos_faixa3) * Decimal("6.00")
    return total


def calcular_valor_base(overall: int, potential: int, idade_cadastro: int) -> Decimal:
    """RN06.3: valor base, calculado uma única vez no cadastro."""
    parte_overall = _parte_do_overall(overall)

    if idade_cadastro <= 21:
        multiplicador = (Decimal(100) + Decimal(potential) - Decimal(overall)) / Decimal(100)
        parte_overall = parte_overall * multiplicador

    valor_base = arredondar(parte_overall)
    return max(valor_base, PISO_VALOR)


def _desconto_por_condicao_e_agilidade(condicao: str, agilidade: int) -> Decimal:
    """RN02 + RN03: desconto de condição, ajustado pela agilidade (só fora de APTO)."""
    desconto = DESCONTO_POR_CONDICAO[condicao]
    if condicao == "APTO":
        return desconto

    if 80 <= agilidade <= 100:
        desconto = desconto / Decimal(2)
    elif 1 <= agilidade <= 30:
        desconto = desconto + Decimal(10)
    # 31 a 79: sem efeito

    return desconto


def _ajuste_por_idade(idade: int) -> Decimal:
    """RN04: ajuste pela idade atual, vale para qualquer condição."""
    if idade <= 21:
        return Decimal(10)
    if idade >= 32:
        return Decimal(-10)
    return Decimal(0)


def calcular_valor_de_mercado(
    valor_base: Decimal, condicao: str, agilidade: int, idade: int
) -> Decimal:
    """RN05: valor de mercado, calculado a cada consulta."""
    desconto_condicao = _desconto_por_condicao_e_agilidade(condicao, agilidade)
    ajuste_idade = _ajuste_por_idade(idade)

    percentual_total = ajuste_idade - desconto_condicao
    percentual_total = max(percentual_total, TETO_DESCONTO)

    valor = valor_base * (Decimal(100) + percentual_total) / Decimal(100)
    valor = arredondar(valor)

    return max(valor, PISO_VALOR)
