from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from mercado_jogadores.jogadores.models import Jogador


@dataclass
class FiltrosSql:
    """Filtros de coluna direta de GET /players (RN07) — sem risco de duplicar regra de
    negócio, por isso aplicados em SQL. Busca por nome e valor de mercado não entram aqui
    (ver design.md da change listagem-jogadores)."""

    position: str | None = None
    condition: str | None = None
    free: bool | None = None
    club_id: int | None = None
    min_age: int | None = None
    max_age: int | None = None


class JogadorRepository(Protocol):
    """Abstração que o service depende (DIP) — nunca importa SQLAlchemy diretamente."""

    def obter(self, jogador_id: int) -> Jogador | None: ...

    def salvar(self, jogador: Jogador) -> Jogador: ...

    def excluir_logicamente(self, jogador_id: int, momento: datetime) -> None: ...

    def listar(self, filtros: FiltrosSql) -> list[Jogador]: ...


class SQLAlchemyJogadorRepository:
    """Implementação real do `JogadorRepository`, usada em produção."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def obter(self, jogador_id: int) -> Jogador | None:
        stmt = select(Jogador).where(Jogador.id == jogador_id, Jogador.excluido_em.is_(None))
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

    def listar(self, filtros: FiltrosSql) -> list[Jogador]:
        stmt = select(Jogador).where(Jogador.excluido_em.is_(None))

        if filtros.position is not None:
            stmt = stmt.where(Jogador.posicao == filtros.position)
        if filtros.condition is not None:
            stmt = stmt.where(Jogador.condicao == filtros.condition)
        if filtros.free is not None:
            stmt = stmt.where(
                Jogador.clube_id.is_(None) if filtros.free else Jogador.clube_id.is_not(None)
            )
        if filtros.club_id is not None:
            stmt = stmt.where(Jogador.clube_id == filtros.club_id)
        if filtros.min_age is not None:
            stmt = stmt.where(Jogador.idade >= filtros.min_age)
        if filtros.max_age is not None:
            stmt = stmt.where(Jogador.idade <= filtros.max_age)

        return list(self._session.execute(stmt).scalars().all())
