from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from mercado_jogadores.jogadores.models import Jogador


class JogadorRepository(Protocol):
    """Abstração que o service depende (DIP) — nunca importa SQLAlchemy diretamente."""

    def obter(self, jogador_id: int) -> Jogador | None: ...

    def salvar(self, jogador: Jogador) -> Jogador: ...

    def excluir_logicamente(self, jogador_id: int, momento: datetime) -> None: ...


class SQLAlchemyJogadorRepository:
    """Implementação real do `JogadorRepository`, usada em produção."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def obter(self, jogador_id: int) -> Jogador | None:
        stmt = select(Jogador).where(
            Jogador.id == jogador_id, Jogador.excluido_em.is_(None)
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def salvar(self, jogador: Jogador) -> Jogador:
        self._session.add(jogador)
        self._session.commit()
        self._session.refresh(jogador)
        return jogador

    def excluir_logicamente(self, jogador_id: int, momento: datetime) -> None:
        jogador = self.obter(jogador_id)
        if jogador is None:
            return
        jogador.excluido_em = momento
        self._session.commit()
