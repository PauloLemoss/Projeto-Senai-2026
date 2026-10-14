"""Funções puras de cálculo do domínio liga (RN19, RN20).

Nenhuma função aqui sabe de HTTP, banco ou FastAPI — só matemática e validação de formato.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

PERCENTUAL_MAL_CONDICIONADO = Decimal("0.85")

# RN20.5: atacante usa o atributo da posição (nome da API, nome do campo do titular).
_ATRIBUTO_DE_ATAQUE = {
    "ATA": ("shooting", "finalizacao"),
    "MEI": ("passing", "passe"),
    "ZAG": ("dribbling", "drible"),
    "LAT": ("dribbling", "drible"),
}

FORMACOES: dict[str, dict[str, int]] = {
    "3-1": {"defesa": 3, "meio": 0, "ataque": 1},
    "2-2": {"defesa": 2, "meio": 0, "ataque": 2},
    "2-1-1": {"defesa": 2, "meio": 1, "ataque": 1},
    "1-2-1": {"defesa": 1, "meio": 2, "ataque": 1},
}


def formacao_fecha_com_as_posicoes(formation: str, posicoes: list[str]) -> bool:
    """RN19.4: exatamente 1 GOL e, em cada setor (defesa: ZAG/LAT; meio: MEI; ataque: ATA), a
    quantidade de jogadores da formação. Assume que `posicoes` já tem exatamente 5 elementos."""
    setores_esperados = FORMACOES[formation]
    if posicoes.count("GOL") != 1:
        return False

    contagem = {
        "defesa": sum(1 for p in posicoes if p in ("ZAG", "LAT")),
        "meio": sum(1 for p in posicoes if p == "MEI"),
        "ataque": sum(1 for p in posicoes if p == "ATA"),
    }
    return contagem == setores_esperados


def arredondar_inteiro(valor: Decimal) -> int:
    """RN20.3: arredonda para o inteiro mais próximo, com o meio arredondado para cima."""
    return int(valor.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def aplicar_efeito_de_condicao(atributo: int, condicao: str) -> int:
    """RN20.3: titular `MAL_CONDICIONADO` joga com 15% a menos em cada atributo; `APTO` joga com
    o atributo do cadastro, sem mudança. O efeito vale só na partida — o atributo gravado no
    jogador nunca muda."""
    if condicao != "MAL_CONDICIONADO":
        return atributo
    return arredondar_inteiro(Decimal(atributo) * PERCENTUAL_MAL_CONDICIONADO)


@dataclass
class TitularEmCampo:
    """Os dados de um titular no momento da partida — função pura, por isso não depende do
    model `Jogador`; `LigaService` monta essa lista a partir do elenco real."""

    jogador_id: int
    nome: str
    posicao: str
    condicao: str
    finalizacao: int
    passe: int
    drible: int
    defesa: int


@dataclass
class DueloCalculado:
    ordem: int
    clube_atacante_id: int
    atacante: TitularEmCampo
    defensor: TitularEmCampo
    atributo: str
    valor_ataque: int
    valor_defesa: int
    gol: bool


def montar_duelos(
    clube_mandante_id: int,
    titulares_mandante: list[TitularEmCampo],
    clube_visitante_id: int,
    titulares_visitante: list[TitularEmCampo],
) -> list[DueloCalculado]:
    """RN20.4-6: 6 duelos (3 ataques do mandante, depois 3 do visitante). Cada lista de titulares
    é `[goleiro, 1º, 2º, 3º, 4º]` jogador de linha, na ordem do elenco. Atacam sempre o 4º, o 3º
    e o 2º; defendem sempre o goleiro, o 1º e o 2º do adversário — fixo pelo índice, não pela
    formação (ver design.md)."""
    duelos = _duelos_de_ataque(titulares_mandante, titulares_visitante, clube_mandante_id, 1)
    duelos += _duelos_de_ataque(titulares_visitante, titulares_mandante, clube_visitante_id, 4)
    return duelos


def _duelos_de_ataque(
    atacantes: list[TitularEmCampo],
    defensores: list[TitularEmCampo],
    clube_atacante_id: int,
    ordem_inicial: int,
) -> list[DueloCalculado]:
    goleiro_def, l1_def, l2_def, _l3_def, _l4_def = defensores
    _goleiro_ata, _l1_ata, l2_ata, l3_ata, l4_ata = atacantes
    pares = [(l4_ata, goleiro_def), (l3_ata, l1_def), (l2_ata, l2_def)]
    return [
        _resolver_duelo(ordem_inicial + indice, clube_atacante_id, atacante, defensor)
        for indice, (atacante, defensor) in enumerate(pares)
    ]


def _resolver_duelo(
    ordem: int, clube_atacante_id: int, atacante: TitularEmCampo, defensor: TitularEmCampo
) -> DueloCalculado:
    atributo_api, campo_do_atacante = _ATRIBUTO_DE_ATAQUE[atacante.posicao]
    valor_ataque = aplicar_efeito_de_condicao(
        getattr(atacante, campo_do_atacante), atacante.condicao
    )
    valor_defesa = aplicar_efeito_de_condicao(defensor.defesa, defensor.condicao)
    return DueloCalculado(
        ordem=ordem,
        clube_atacante_id=clube_atacante_id,
        atacante=atacante,
        defensor=defensor,
        atributo=atributo_api,
        valor_ataque=valor_ataque,
        valor_defesa=valor_defesa,
        gol=valor_ataque > valor_defesa,
    )


def resultado_por_placar(gols_mandante: int, gols_visitante: int) -> str:
    """RN21: `MANDANTE`/`VISITANTE` por quem fez mais gols, `EMPATE` se igual — usado tanto ao
    jogar a partida quanto ao reler o placar já gravado, sem duplicar a comparação."""
    if gols_mandante > gols_visitante:
        return "MANDANTE"
    if gols_visitante > gols_mandante:
        return "VISITANTE"
    return "EMPATE"


def calcular_placar_e_resultado(duelos: list[DueloCalculado]) -> tuple[int, int, str]:
    """RN20.6: gol quando o ataque é maior que a defesa; os duelos 1-3 são o mandante atacando,
    4-6 o visitante; `result` por quem fez mais gols."""
    gols_mandante = sum(1 for d in duelos if d.ordem <= 3 and d.gol)
    gols_visitante = sum(1 for d in duelos if d.ordem > 3 and d.gol)
    return gols_mandante, gols_visitante, resultado_por_placar(gols_mandante, gols_visitante)
