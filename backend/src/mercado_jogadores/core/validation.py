"""Utilitários de validação compartilhados por toda a API (capability `api-conventions`)."""

import re

from mercado_jogadores.core.errors import NaoEncontradoError

_ESPACOS_REPETIDOS = re.compile(r" {2,}")
_CARACTERE_DE_CONTROLE = re.compile(r"[\x00-\x1f\x7f]")

_ID_VALIDO = re.compile(r"^[1-9][0-9]*$")
ID_MAXIMO = 2_147_483_647


def normalizar_texto(valor: str) -> str:
    """V4: remove espaços nas bordas, colapsa espaços repetidos, recusa caractere de controle."""
    if _CARACTERE_DE_CONTROLE.search(valor):
        raise ValueError("Texto contém caractere de controle.")
    sem_bordas = valor.strip(" ")
    return _ESPACOS_REPETIDOS.sub(" ", sem_bordas)


def validar_id_da_url(valor: str) -> int:
    """V8: id que não é inteiro positivo sem zeros à esquerda, ou acima do limite, é 404."""
    if not _ID_VALIDO.match(valor) or int(valor) > ID_MAXIMO:
        raise NaoEncontradoError("Identificador inválido.")
    return int(valor)
