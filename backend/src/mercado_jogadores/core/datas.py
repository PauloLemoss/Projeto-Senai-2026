"""Data e hora no formato de Brasília (RN01), compartilhado por toda a API.

Fuso fixo (`-03:00`), não `ZoneInfo`: o enunciado exige "sem horário de verão" sempre, e um fuso
nomeado carregaria as regras históricas de DST do banco de fusos do sistema operacional.
"""

import re
from datetime import datetime, timedelta, timezone

FUSO_BRASILIA = timezone(timedelta(hours=-3))

_ENTRADA_RN01 = re.compile(r"^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})-03:00$")


def parsear_datetime_rn01(texto: str) -> datetime:
    """Só aceita `AAAA-MM-DDTHH:MM-03:00`; recusa outro formato ou data/hora inexistente."""
    match = _ENTRADA_RN01.match(texto)
    if not match:
        raise ValueError("Data e hora devem estar no formato AAAA-MM-DDTHH:MM-03:00.")

    ano, mes, dia, hora, minuto = (int(grupo) for grupo in match.groups())
    try:
        return datetime(ano, mes, dia, hora, minuto, tzinfo=FUSO_BRASILIA)
    except ValueError as erro:
        raise ValueError("Data ou hora inexistente.") from erro


def formatar_datetime_rn01(momento: datetime) -> str:
    """Resposta sempre em `AAAA-MM-DDTHH:MM:SS-03:00`; `momento` precisa ser timezone-aware."""
    return momento.astimezone(FUSO_BRASILIA).strftime("%Y-%m-%dT%H:%M:%S-03:00")
