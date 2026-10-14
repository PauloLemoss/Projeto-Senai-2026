from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from mercado_jogadores.clubes.repository import SQLAlchemyClubeRepository
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.core.db import get_session
from mercado_jogadores.core.unidade_de_trabalho import SQLAlchemyUnidadeDeTrabalho
from mercado_jogadores.core.validation import validar_id_da_url
from mercado_jogadores.jogadores.repository import SQLAlchemyJogadorRepository
from mercado_jogadores.liga.repository import SQLAlchemyEscalacaoRepository
from mercado_jogadores.mercado.repository import (
    SQLAlchemyContratoRepository,
    SQLAlchemyTransacaoRepository,
)
from mercado_jogadores.mercado.schemas import (
    BuyRead,
    BuyRequest,
    SellRead,
    TransactionHistoryResponse,
    TransactionListQuery,
)
from mercado_jogadores.mercado.service import MercadoService

router = APIRouter(tags=["mercado"])


def get_mercado_service(session: Session = Depends(get_session)) -> MercadoService:
    return MercadoService(
        SQLAlchemyJogadorRepository(session),
        SQLAlchemyClubeRepository(session),
        SQLAlchemyContratoRepository(session),
        SQLAlchemyTransacaoRepository(session),
        SQLAlchemyEscalacaoRepository(session),
        SQLAlchemyUnidadeDeTrabalho(session),
    )


@router.post("/players/{jogador_id}/buy", response_model=BuyRead)
def comprar_jogador(
    jogador_id: str,
    dados: BuyRequest,
    service: MercadoService = Depends(get_mercado_service),
) -> BuyRead:
    id_valido = validar_id_da_url(jogador_id)
    resultado = service.comprar(
        id_valido, dados.para_dados_de_compra(), datetime.now(FUSO_BRASILIA)
    )
    return BuyRead.a_partir_do_resultado(resultado)


@router.post("/players/{jogador_id}/sell", response_model=SellRead)
def vender_jogador(
    jogador_id: str, service: MercadoService = Depends(get_mercado_service)
) -> SellRead:
    id_valido = validar_id_da_url(jogador_id)
    resultado = service.vender(id_valido, datetime.now(FUSO_BRASILIA))
    return SellRead.a_partir_do_resultado(resultado)


@router.get("/clubs/{clube_id}/transactions", response_model=TransactionHistoryResponse)
def historico_de_transacoes_do_clube(
    clube_id: str,
    query: Annotated[TransactionListQuery, Query()],
    service: MercadoService = Depends(get_mercado_service),
) -> TransactionHistoryResponse:
    id_valido = validar_id_da_url(clube_id)
    resultado = service.historico(id_valido, query.para_filtros())
    return TransactionHistoryResponse.a_partir_do_resultado(resultado)


@router.get("/clubs/{clube_id}/transactions/export")
def exportar_historico_de_transacoes_do_clube(
    clube_id: str,
    query: Annotated[TransactionListQuery, Query()],
    service: MercadoService = Depends(get_mercado_service),
) -> Response:
    id_valido = validar_id_da_url(clube_id)
    csv_texto = service.exportar_csv(id_valido, query.para_filtros())
    return Response(content=csv_texto, media_type="text/csv")
