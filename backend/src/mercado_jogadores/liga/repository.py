from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session

from mercado_jogadores.liga.models import DueloPartida, Escalacao, Partida


class EscalacaoRepository(Protocol):
    """Abstração que `LigaService`, `JogadorService` e `MercadoService` dependem (DIP) — nunca
    importam SQLAlchemy diretamente."""

    def listar_titulares_do_clube(self, clube_id: int) -> list[int]: ...

    def substituir_escalacao_do_clube(
        self, clube_id: int, jogador_ids: list[int], momento: datetime
    ) -> None: ...

    def remover_titular(self, jogador_id: int) -> None: ...


@dataclass
class FiltrosDePartida:
    clube_id: int | None = None


class PartidaRepository(Protocol):
    """Log imutável (RN20.7): não expõe nenhum método de update/delete."""

    def adicionar(self, partida: Partida) -> Partida: ...

    def adicionar_duelo(self, duelo: DueloPartida) -> None: ...

    def listar(self, filtros: FiltrosDePartida) -> list[Partida]: ...

    def obter(self, partida_id: int) -> Partida | None: ...

    def listar_duelos(self, partida_id: int) -> list[DueloPartida]: ...


class SQLAlchemyEscalacaoRepository:
    """Implementação real do `EscalacaoRepository`, usada em produção.

    `substituir_escalacao_do_clube`/`remover_titular` só agendam a escrita (`delete`/`add`);
    quem comita é a `UnidadeDeTrabalho` da operação composta (escalar, vender, alterar
    condição), nunca o repositório.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def listar_titulares_do_clube(self, clube_id: int) -> list[int]:
        stmt = (
            select(Escalacao.jogador_id)
            .where(Escalacao.clube_id == clube_id)
            .order_by(Escalacao.jogador_id)
        )
        return list(self._session.execute(stmt).scalars().all())

    def substituir_escalacao_do_clube(
        self, clube_id: int, jogador_ids: list[int], momento: datetime
    ) -> None:
        self._session.execute(delete(Escalacao).where(Escalacao.clube_id == clube_id))
        for jogador_id in jogador_ids:
            self._session.add(
                Escalacao(clube_id=clube_id, jogador_id=jogador_id, criado_em=momento)
            )

    def remover_titular(self, jogador_id: int) -> None:
        self._session.execute(delete(Escalacao).where(Escalacao.jogador_id == jogador_id))


class SQLAlchemyPartidaRepository:
    """Implementação real do `PartidaRepository`, usada em produção."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def adicionar(self, partida: Partida) -> Partida:
        self._session.add(partida)
        self._session.flush()  # precisa do id gerado pros duelos; não comita
        return partida

    def adicionar_duelo(self, duelo: DueloPartida) -> None:
        self._session.add(duelo)

    def listar(self, filtros: FiltrosDePartida) -> list[Partida]:
        stmt = select(Partida)
        if filtros.clube_id is not None:
            stmt = stmt.where(
                or_(
                    Partida.mandante_id == filtros.clube_id,
                    Partida.visitante_id == filtros.clube_id,
                )
            )
        stmt = stmt.order_by(Partida.jogada_em.desc(), Partida.id.desc())
        return list(self._session.execute(stmt).scalars().all())

    def obter(self, partida_id: int) -> Partida | None:
        stmt = select(Partida).where(Partida.id == partida_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def listar_duelos(self, partida_id: int) -> list[DueloPartida]:
        stmt = (
            select(DueloPartida)
            .where(DueloPartida.partida_id == partida_id)
            .order_by(DueloPartida.ordem)
        )
        return list(self._session.execute(stmt).scalars().all())
