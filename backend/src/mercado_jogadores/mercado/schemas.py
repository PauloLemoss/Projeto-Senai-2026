from datetime import datetime, timedelta
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from mercado_jogadores.core.datas import (
    FUSO_BRASILIA,
    formatar_datetime_rn01,
    parsear_datetime_rn01,
)
from mercado_jogadores.jogadores.schemas import InteiroDeQuery
from mercado_jogadores.mercado.models import Transacao
from mercado_jogadores.mercado.repository import FiltrosDeTransacao
from mercado_jogadores.mercado.service import (
    DadosDeCompra,
    HistoricoDeTransacoes,
    ResultadoDaCompra,
    ResultadoDaVenda,
)

LIMITE_DE_DIAS_DE_FIDELIDADE = 1095
_TIPOS_VALIDOS = frozenset(("COMPRA", "VENDA"))


class BuyRequest(BaseModel):
    """RN12, "Limites de cada campo" (`club_id`/`loyalty_until` da Compra)."""

    model_config = ConfigDict(extra="ignore")

    club_id: int = Field(gt=0, le=2_147_483_647)
    loyalty_until: datetime

    @field_validator("loyalty_until", mode="before")
    @classmethod
    def _parsear_loyalty_until(cls, v: object) -> object:
        return parsear_datetime_rn01(v) if isinstance(v, str) else v

    @model_validator(mode="after")
    def _validar_intervalo_de_loyalty_until(self) -> "BuyRequest":
        agora = datetime.now(FUSO_BRASILIA)
        if self.loyalty_until <= agora:
            raise ValueError("loyalty_until precisa ser uma data futura.")
        limite = agora + timedelta(days=LIMITE_DE_DIAS_DE_FIDELIDADE)
        if self.loyalty_until > limite:
            raise ValueError(
                f"loyalty_until não pode passar de {LIMITE_DE_DIAS_DE_FIDELIDADE} dias da compra."
            )
        return self

    def para_dados_de_compra(self) -> DadosDeCompra:
        return DadosDeCompra(club_id=self.club_id, loyalty_until=self.loyalty_until)


class TransactionRead(BaseModel):
    """Campos da transação (RN17), comuns a `COMPRA` e `VENDA`."""

    id: int
    club_id: int
    player_id: int
    player_name: str
    type: Literal["COMPRA", "VENDA"]
    value: Decimal
    fee: Decimal
    penalty: Decimal
    profit: Decimal | None
    cash_change: Decimal
    created_at: str

    @field_serializer("value", "fee", "penalty", "cash_change")
    def _serializar_moeda_como_numero(self, valor: Decimal) -> float:
        return float(valor)

    @field_serializer("profit")
    def _serializar_profit(self, valor: Decimal | None) -> float | None:
        return float(valor) if valor is not None else None

    @classmethod
    def a_partir_da_transacao(cls, transacao: Transacao) -> "TransactionRead":
        return cls(
            id=transacao.id,
            club_id=transacao.clube_id,
            player_id=transacao.jogador_id,
            player_name=transacao.nome_jogador,
            type=transacao.tipo,  # type: ignore[arg-type]
            value=transacao.valor,
            fee=transacao.taxa,
            penalty=transacao.multa,
            profit=transacao.lucro,
            cash_change=transacao.variacao_caixa,
            created_at=formatar_datetime_rn01(transacao.criado_em),
        )


class ContratoNaCompraRead(BaseModel):
    purchase_value: Decimal
    loyalty_until: str
    status: Literal["ATIVO"]

    @field_serializer("purchase_value")
    def _serializar_moeda_como_numero(self, valor: Decimal) -> float:
        return float(valor)


class BuyRead(TransactionRead):
    """Resposta de `POST /players/{id}/buy`: campos da transação + `contract` + `club_cash`."""

    contract: ContratoNaCompraRead
    club_cash: Decimal

    @field_serializer("club_cash")
    def _serializar_club_cash(self, valor: Decimal) -> float:
        return float(valor)

    @classmethod
    def a_partir_do_resultado(cls, resultado: ResultadoDaCompra) -> "BuyRead":
        transacao = resultado.transacao
        return cls(
            id=transacao.id,
            club_id=transacao.clube_id,
            player_id=transacao.jogador_id,
            player_name=transacao.nome_jogador,
            type=transacao.tipo,  # type: ignore[arg-type]
            value=transacao.valor,
            fee=transacao.taxa,
            penalty=transacao.multa,
            profit=transacao.lucro,
            cash_change=transacao.variacao_caixa,
            created_at=formatar_datetime_rn01(transacao.criado_em),
            contract=ContratoNaCompraRead(
                purchase_value=resultado.contrato.valor_compra,
                loyalty_until=formatar_datetime_rn01(resultado.contrato.fidelidade_ate),
                status=resultado.contrato.situacao,  # type: ignore[arg-type]
            ),
            club_cash=resultado.clube.caixa,
        )


class SellRead(TransactionRead):
    """Resposta de `POST /players/{id}/sell`: campos da transação + extras soltos (sem aninhar,
    diferente de `BuyRead.contract`)."""

    purchase_value: Decimal
    remaining_days: int
    penalty_rate: int
    contract_status: Literal["RESCINDIDO", "ENCERRADO"]
    club_cash: Decimal

    @field_serializer("purchase_value", "club_cash")
    def _serializar_extras_como_numero(self, valor: Decimal) -> float:
        return float(valor)

    @classmethod
    def a_partir_do_resultado(cls, resultado: ResultadoDaVenda) -> "SellRead":
        transacao = resultado.transacao
        return cls(
            id=transacao.id,
            club_id=transacao.clube_id,
            player_id=transacao.jogador_id,
            player_name=transacao.nome_jogador,
            type=transacao.tipo,  # type: ignore[arg-type]
            value=transacao.valor,
            fee=transacao.taxa,
            penalty=transacao.multa,
            profit=transacao.lucro,
            cash_change=transacao.variacao_caixa,
            created_at=formatar_datetime_rn01(transacao.criado_em),
            purchase_value=resultado.contrato.valor_compra,
            remaining_days=resultado.dias_restantes,
            penalty_rate=resultado.percentual_de_multa,
            contract_status=resultado.contrato.situacao,  # type: ignore[arg-type]
            club_cash=resultado.clube.caixa,
        )


class TransactionSummary(BaseModel):
    total_spent: Decimal
    total_received: Decimal
    total_fees: Decimal
    total_penalties: Decimal
    total_profit: Decimal

    @field_serializer(
        "total_spent", "total_received", "total_fees", "total_penalties", "total_profit"
    )
    def _serializar_moeda_como_numero(self, valor: Decimal) -> float:
        return float(valor)


class TransactionHistoryResponse(BaseModel):
    data: list[TransactionRead]
    summary: TransactionSummary

    @classmethod
    def a_partir_do_resultado(
        cls, resultado: HistoricoDeTransacoes
    ) -> "TransactionHistoryResponse":
        return cls(
            data=[TransactionRead.a_partir_da_transacao(t) for t in resultado.transacoes],
            summary=TransactionSummary(
                total_spent=resultado.resumo.total_spent,
                total_received=resultado.resumo.total_received,
                total_fees=resultado.resumo.total_fees,
                total_penalties=resultado.resumo.total_penalties,
                total_profit=resultado.resumo.total_profit,
            ),
        )


class TransactionListQuery(BaseModel):
    """`GET /clubs/{id}/transactions` e `/export`: filtros `type` e `player_id` (RN17, RN18)."""

    model_config = ConfigDict(extra="ignore")

    type: str | None = Field(default=None)
    player_id: InteiroDeQuery | None = Field(default=None, le=2_147_483_647)

    @field_validator("type", mode="before")
    @classmethod
    def _validar_type(cls, v: object) -> object:
        if v is None:
            return v
        if not isinstance(v, str) or v == "":
            raise ValueError("type inválido.")
        tokens = v.split(",")
        if len(set(tokens)) != len(tokens):
            raise ValueError("type não pode repetir o mesmo valor.")
        for token in tokens:
            if token not in _TIPOS_VALIDOS:
                raise ValueError(f"type inválido: {token}.")
        return v

    def para_filtros(self) -> FiltrosDeTransacao:
        tipos = self.type.split(",") if self.type is not None else None
        return FiltrosDeTransacao(tipos=tipos, jogador_id=self.player_id)
