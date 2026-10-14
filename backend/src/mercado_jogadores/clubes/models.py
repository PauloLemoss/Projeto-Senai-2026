from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, Index, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from mercado_jogadores.core.db import Base


class Clube(Base):
    """Tabela `clubes` — ver "3. Estrutura de tabelas" do enunciado.

    `nome_normalizado` não faz parte do enunciado: é a coluna (minúsculas, acento preservado)
    que garante no banco a unicidade de `nome` ignorando caixa, mas considerando acentos (RN10).
    """

    __tablename__ = "clubes"
    __table_args__ = (
        Index("ix_clubes_nome_normalizado", "nome_normalizado", unique=True),
        Index("ix_clubes_sigla", "sigla", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    nome: Mapped[str] = mapped_column(String(60), nullable=False)
    nome_normalizado: Mapped[str] = mapped_column(String(60), nullable=False)
    sigla: Mapped[str] = mapped_column(String(3), nullable=False)
    caixa: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False, server_default="300.00")
    formacao: Mapped[str | None] = mapped_column(String(5), nullable=True)

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
