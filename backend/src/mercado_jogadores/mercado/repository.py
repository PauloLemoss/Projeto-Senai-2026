from dataclasses import dataclass
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from mercado_jogadores.mercado.models import Contrato, Transacao


@dataclass
class FiltrosDeTransacao:
    """Filtros de coluna direta do histórico (RN17) — aplicados em SQL, sem risco de duplicar
    regra de negócio."""

    tipos: list[str] | None = None
    jogador_id: int | None = None


class ContratoRepository(Protocol):
    """Abstração que o service depende (DIP) — nunca importa SQLAlchemy diretamente."""

    def obter_ativo_por_jogador(self, jogador_id: int) -> Contrato | None: ...

    def adicionar(self, contrato: Contrato) -> None: ...


class TransacaoRepository(Protocol):
    """Log imutável (RN17): não expõe nenhum método de update/delete."""

    def adicionar(self, transacao: Transacao) -> None: ...

    def existe_venda(self, clube_id: int, jogador_id: int) -> bool: ...

    def listar_por_clube(self, clube_id: int, filtros: FiltrosDeTransacao) -> list[Transacao]: ...


class SQLAlchemyContratoRepository:
    """Implementação real do `ContratoRepository`, usada em produção.

    `adicionar` só agenda a escrita (`session.add`); quem comita é a `UnidadeDeTrabalho` da
    operação composta (compra/venda), nunca o repositório.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def obter_ativo_por_jogador(self, jogador_id: int) -> Contrato | None:
        stmt = select(Contrato).where(
            Contrato.jogador_id == jogador_id, Contrato.situacao == "ATIVO"
        )
        return self._session.execute(stmt).scalar_one_or_none()

    def adicionar(self, contrato: Contrato) -> None:
        self._session.add(contrato)


class SQLAlchemyTransacaoRepository:
    """Implementação real do `TransacaoRepository`, usada em produção."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def adicionar(self, transacao: Transacao) -> None:
        self._session.add(transacao)

    def existe_venda(self, clube_id: int, jogador_id: int) -> bool:
        stmt = (
            select(Transacao.id)
            .where(
                Transacao.clube_id == clube_id,
                Transacao.jogador_id == jogador_id,
                Transacao.tipo == "VENDA",
            )
            .limit(1)
        )
        return self._session.execute(stmt).first() is not None

    def listar_por_clube(self, clube_id: int, filtros: FiltrosDeTransacao) -> list[Transacao]:
        stmt = select(Transacao).where(Transacao.clube_id == clube_id)

        if filtros.tipos is not None:
            stmt = stmt.where(Transacao.tipo.in_(filtros.tipos))
        if filtros.jogador_id is not None:
            stmt = stmt.where(Transacao.jogador_id == filtros.jogador_id)

        stmt = stmt.order_by(Transacao.criado_em.desc(), Transacao.id.desc())
        return list(self._session.execute(stmt).scalars().all())
