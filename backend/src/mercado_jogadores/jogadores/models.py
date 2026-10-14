from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Index, Integer, String, func, text
from sqlalchemy.orm import Mapped, mapped_column

from mercado_jogadores.core.db import Base


class Jogador(Base):
    """Tabela `jogadores` — ver "3. Estrutura de tabelas" do enunciado.

    Índices (RN07, listagem): `clube_id`, `posicao` e `condicao` atendem os filtros de coluna
    direta de `GET /players`; o índice parcial em `excluido_em` atende toda consulta (não só a
    listagem), que sempre filtra `excluido_em IS NULL`. Busca por nome e valor de mercado não têm
    índice aqui de propósito — ver design.md da change `listagem-jogadores`.
    """

    __tablename__ = "jogadores"
    __table_args__ = (
        Index("ix_jogadores_clube_id", "clube_id"),
        Index("ix_jogadores_posicao", "posicao"),
        Index("ix_jogadores_condicao", "condicao"),
        Index(
            "ix_jogadores_ativos",
            "excluido_em",
            postgresql_where=text("excluido_em IS NULL"),
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(100), nullable=False)
    posicao: Mapped[str] = mapped_column(String(3), nullable=False)
    agilidade: Mapped[int] = mapped_column(Integer, nullable=False)
    idade: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_base: Mapped[Decimal] = mapped_column(DECIMAL(6, 2), nullable=False)
    condicao: Mapped[str] = mapped_column(String(20), nullable=False, default="APTO")
    clube_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("clubes.id"), nullable=True)

    velocidade: Mapped[int] = mapped_column(Integer, nullable=False)
    finalizacao: Mapped[int] = mapped_column(Integer, nullable=False)
    passe: Mapped[int] = mapped_column(Integer, nullable=False)
    drible: Mapped[int] = mapped_column(Integer, nullable=False)
    defesa: Mapped[int] = mapped_column(Integer, nullable=False)
    fisico: Mapped[int] = mapped_column(Integer, nullable=False)
    potencial: Mapped[int] = mapped_column(Integer, nullable=False)

    excluido_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
