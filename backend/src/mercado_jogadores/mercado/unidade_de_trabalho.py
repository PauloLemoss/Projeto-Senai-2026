"""Unidade de trabalho das operações compostas de mercado (compra, venda) — ver design.md.

Compra e venda escrevem em jogador, clube, contrato e transação; o commit (ou rollback, se uma
regra de negócio falhar no meio) acontece uma única vez, no fim, por esta abstração — o service
continua dependendo só de um `Protocol`, nunca do SQLAlchemy diretamente (DIP).
"""

from typing import Protocol

from sqlalchemy.orm import Session


class UnidadeDeTrabalho(Protocol):
    def confirmar(self) -> None: ...

    def desfazer(self) -> None: ...


class SQLAlchemyUnidadeDeTrabalho:
    """Implementação real, usada em produção: `commit`/`rollback` sobre a `Session`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def confirmar(self) -> None:
        self._session.commit()

    def desfazer(self) -> None:
        self._session.rollback()
