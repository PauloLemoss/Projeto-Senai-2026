from typing import Protocol

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from mercado_jogadores.clubes.models import Clube


class ClubeRepository(Protocol):
    """Abstração que o service depende (DIP) — nunca importa SQLAlchemy diretamente."""

    def obter(self, clube_id: int) -> Clube | None: ...

    def obter_por_nome_normalizado(self, nome_normalizado: str) -> Clube | None: ...

    def obter_por_sigla(self, sigla: str) -> Clube | None: ...

    def salvar(self, clube: Clube) -> Clube: ...

    def contar(self) -> int: ...

    def listar(self) -> list[Clube]: ...


class SQLAlchemyClubeRepository:
    """Implementação real do `ClubeRepository`, usada em produção."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def obter(self, clube_id: int) -> Clube | None:
        stmt = select(Clube).where(Clube.id == clube_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def obter_por_nome_normalizado(self, nome_normalizado: str) -> Clube | None:
        stmt = select(Clube).where(Clube.nome_normalizado == nome_normalizado)
        return self._session.execute(stmt).scalar_one_or_none()

    def obter_por_sigla(self, sigla: str) -> Clube | None:
        stmt = select(Clube).where(Clube.sigla == sigla)
        return self._session.execute(stmt).scalar_one_or_none()

    def salvar(self, clube: Clube) -> Clube:
        self._session.add(clube)
        self._session.commit()
        self._session.refresh(clube)
        return clube

    def contar(self) -> int:
        stmt = select(func.count()).select_from(Clube)
        return self._session.execute(stmt).scalar_one()

    def listar(self) -> list[Clube]:
        stmt = select(Clube)
        return list(self._session.execute(stmt).scalars().all())
