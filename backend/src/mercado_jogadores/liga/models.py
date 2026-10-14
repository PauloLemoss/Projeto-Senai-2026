from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mercado_jogadores.core.db import Base


class Escalacao(Base):
    """Tabela `escalacoes` — ver "3. Estrutura de tabelas" do enunciado.

    Única tabela do domínio com `DELETE` real (sai da escalação ao ser vendido ou ficar
    `DOENTE`, ou ao ser substituída por inteiro numa nova escalação). PK composta
    (`clube_id`, `jogador_id`); `jogador_id` também é único — um jogador está em no máximo uma
    escalação.
    """

    __tablename__ = "escalacoes"
    __table_args__ = (Index("ix_escalacoes_clube_id", "clube_id"),)

    clube_id: Mapped[int] = mapped_column(Integer, ForeignKey("clubes.id"), primary_key=True)
    jogador_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("jogadores.id"), primary_key=True, unique=True
    )
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Partida(Base):
    """Tabela `partidas` — log imutável (RN20.7), como `transacoes`: nunca é `UPDATE` nem
    `DELETE` depois de criada."""

    __tablename__ = "partidas"
    __table_args__ = (
        Index("ix_partidas_mandante_id", "mandante_id"),
        Index("ix_partidas_visitante_id", "visitante_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    mandante_id: Mapped[int] = mapped_column(Integer, ForeignKey("clubes.id"), nullable=False)
    visitante_id: Mapped[int] = mapped_column(Integer, ForeignKey("clubes.id"), nullable=False)
    gols_mandante: Mapped[int] = mapped_column(Integer, nullable=False)
    gols_visitante: Mapped[int] = mapped_column(Integer, nullable=False)
    formacao_mandante: Mapped[str] = mapped_column(String(5), nullable=False)
    formacao_visitante: Mapped[str] = mapped_column(String(5), nullable=False)
    jogada_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DueloPartida(Base):
    """Tabela `duelos_partida` — log imutável (RN20.7), 6 linhas por partida."""

    __tablename__ = "duelos_partida"
    __table_args__ = (Index("ix_duelos_partida_partida_id", "partida_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    partida_id: Mapped[int] = mapped_column(Integer, ForeignKey("partidas.id"), nullable=False)
    ordem: Mapped[int] = mapped_column(Integer, nullable=False)
    clube_atacante_id: Mapped[int] = mapped_column(Integer, ForeignKey("clubes.id"), nullable=False)
    atacante_id: Mapped[int] = mapped_column(Integer, ForeignKey("jogadores.id"), nullable=False)
    defensor_id: Mapped[int] = mapped_column(Integer, ForeignKey("jogadores.id"), nullable=False)
    nome_atacante: Mapped[str] = mapped_column(String(100), nullable=False)
    nome_defensor: Mapped[str] = mapped_column(String(100), nullable=False)
    posicao_atacante: Mapped[str] = mapped_column(String(3), nullable=False)
    posicao_defensor: Mapped[str] = mapped_column(String(3), nullable=False)
    condicao_atacante: Mapped[str] = mapped_column(String(20), nullable=False)
    condicao_defensor: Mapped[str] = mapped_column(String(20), nullable=False)
    atributo_ataque: Mapped[str] = mapped_column(String(10), nullable=False)
    atributo_defesa: Mapped[str] = mapped_column(String(10), nullable=False)
    valor_ataque: Mapped[int] = mapped_column(Integer, nullable=False)
    valor_defesa: Mapped[int] = mapped_column(Integer, nullable=False)
    gol: Mapped[bool] = mapped_column(Boolean, nullable=False)
