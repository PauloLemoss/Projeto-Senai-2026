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
from mercado_jogadores.liga.repository import (
    SQLAlchemyEscalacaoRepository,
    SQLAlchemyPartidaRepository,
)
from mercado_jogadores.liga.schemas import (
    LineupRead,
    LineupUpdate,
    MatchCreate,
    MatchDetailRead,
    MatchListQuery,
    MatchRead,
    StandingRead,
)
from mercado_jogadores.liga.service import LigaService

router = APIRouter(tags=["liga"])


def get_liga_service(session: Session = Depends(get_session)) -> LigaService:
    return LigaService(
        SQLAlchemyClubeRepository(session),
        SQLAlchemyJogadorRepository(session),
        SQLAlchemyEscalacaoRepository(session),
        SQLAlchemyPartidaRepository(session),
        SQLAlchemyUnidadeDeTrabalho(session),
    )


@router.put("/clubs/{clube_id}/lineup", response_model=LineupRead)
def escalar_clube(
    clube_id: str,
    dados: LineupUpdate,
    service: LigaService = Depends(get_liga_service),
) -> LineupRead:
    id_valido = validar_id_da_url(clube_id)
    resultado = service.escalar(
        id_valido, dados.para_dados_de_escalacao(), datetime.now(FUSO_BRASILIA)
    )
    return LineupRead.a_partir_do_resultado(resultado)


@router.get("/clubs/{clube_id}/lineup", response_model=LineupRead)
def consultar_escalacao_do_clube(
    clube_id: str, service: LigaService = Depends(get_liga_service)
) -> LineupRead:
    id_valido = validar_id_da_url(clube_id)
    resultado = service.consultar_escalacao(id_valido)
    return LineupRead.a_partir_do_resultado(resultado)


@router.post("/matches", status_code=201, response_model=MatchDetailRead)
def jogar_partida(
    dados: MatchCreate, response: Response, service: LigaService = Depends(get_liga_service)
) -> MatchDetailRead:
    resultado = service.jogar_partida(dados.para_dados_de_partida(), datetime.now(FUSO_BRASILIA))
    response.headers["Location"] = f"/api/v1/matches/{resultado.id}"
    return MatchDetailRead.a_partir_do_resultado(resultado)


@router.get("/matches", response_model=list[MatchRead])
def historico_de_partidas(
    query: Annotated[MatchListQuery, Query()],
    service: LigaService = Depends(get_liga_service),
) -> list[MatchRead]:
    resultado = service.historico(query.para_filtros())
    return [MatchRead.a_partir_do_resultado(item) for item in resultado]


@router.get("/matches/{partida_id}", response_model=MatchDetailRead)
def consultar_partida(
    partida_id: str, service: LigaService = Depends(get_liga_service)
) -> MatchDetailRead:
    id_valido = validar_id_da_url(partida_id)
    resultado = service.consultar_partida(id_valido)
    return MatchDetailRead.a_partir_do_resultado(resultado)


@router.get("/standings", response_model=list[StandingRead])
def classificacao(service: LigaService = Depends(get_liga_service)) -> list[StandingRead]:
    resultado = service.classificacao()
    return [StandingRead.a_partir_da_linha(item) for item in resultado]
