from datetime import datetime
from decimal import Decimal

from sqlalchemy import DECIMAL, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mercado_jogadores.core.db import Base


class Contrato(Base):
    """Tabela `contratos` — ver "3. Estrutura de tabelas" do enunciado.

    `iniciado_em`/`encerrado_em` nunca usam `server_default`: o `momento` de cada operação é
    calculado uma única vez em `MercadoService` e gravado igual em `contratos` e `transacoes`
    (RN12, RN15), nunca pelo relógio do banco.
    """

    __tablename__ = "contratos"
    __table_args__ = (Index("ix_contratos_jogador_id", "jogador_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    jogador_id: Mapped[int] = mapped_column(Integer, ForeignKey("jogadores.id"), nullable=False)
    clube_id: Mapped[int] = mapped_column(Integer, ForeignKey("clubes.id"), nullable=False)
    valor_compra: Mapped[Decimal] = mapped_column(DECIMAL(6, 2), nullable=False)
    fidelidade_ate: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    situacao: Mapped[str] = mapped_column(String(12), nullable=False)
    iniciado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    encerrado_em: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Transacao(Base):
    """Tabela `transacoes` — ver "3. Estrutura de tabelas" do enunciado.

    Log imutável (RN17): o repository não deve expor método de update/delete. `criado_em` nunca
    usa `server_default`, pelo mesmo motivo de `contratos.iniciado_em`.
    """

    __tablename__ = "transacoes"
    __table_args__ = (Index("ix_transacoes_clube_id", "clube_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    clube_id: Mapped[int] = mapped_column(Integer, ForeignKey("clubes.id"), nullable=False)
    jogador_id: Mapped[int] = mapped_column(Integer, ForeignKey("jogadores.id"), nullable=False)
    nome_jogador: Mapped[str] = mapped_column(String(100), nullable=False)
    tipo: Mapped[str] = mapped_column(String(6), nullable=False)
    valor: Mapped[Decimal] = mapped_column(DECIMAL(6, 2), nullable=False)
    taxa: Mapped[Decimal] = mapped_column(DECIMAL(6, 2), nullable=False)
    multa: Mapped[Decimal] = mapped_column(DECIMAL(6, 2), nullable=False)
    lucro: Mapped[Decimal | None] = mapped_column(DECIMAL(7, 2), nullable=True)
    variacao_caixa: Mapped[Decimal] = mapped_column(DECIMAL(8, 2), nullable=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
