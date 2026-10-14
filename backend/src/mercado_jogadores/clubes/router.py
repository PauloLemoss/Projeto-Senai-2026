from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from mercado_jogadores.clubes.repository import SQLAlchemyClubeRepository
from mercado_jogadores.clubes.schemas import ClubeComElencoRead, ClubeCreate, ClubeRead
from mercado_jogadores.clubes.service import ClubeService
from mercado_jogadores.core.db import get_session
from mercado_jogadores.core.validation import validar_id_da_url
from mercado_jogadores.jogadores.repository import SQLAlchemyJogadorRepository

router = APIRouter(prefix="/clubs", tags=["clubes"])

SortDeClubes = Literal["name", "net_worth_asc", "net_worth_desc"]


def get_clube_service(session: Session = Depends(get_session)) -> ClubeService:
    return ClubeService(
        SQLAlchemyClubeRepository(session), SQLAlchemyJogadorRepository(session)
    )


@router.get("", response_model=list[ClubeRead])
def listar_clubes(
    sort: SortDeClubes = Query(default="name"),
    service: ClubeService = Depends(get_clube_service),
) -> list[ClubeRead]:
    resultado = service.listar(sort)
    return [ClubeRead.a_partir_do_resultado(item) for item in resultado]


@router.post("", status_code=201, response_model=ClubeRead)
def cadastrar_clube(
    dados: ClubeCreate,
    response: Response,
    service: ClubeService = Depends(get_clube_service),
) -> ClubeRead:
    resultado = service.cadastrar(dados.para_dados_de_cadastro())
    response.headers["Location"] = f"/api/v1/clubs/{resultado.clube.id}"
    return ClubeRead.a_partir_do_resultado(resultado)


@router.get("/{clube_id}", response_model=ClubeComElencoRead)
def consultar_clube(
    clube_id: str, service: ClubeService = Depends(get_clube_service)
) -> ClubeComElencoRead:
    id_valido = validar_id_da_url(clube_id)
    resultado = service.consultar(id_valido)
    return ClubeComElencoRead.a_partir_do_resultado(resultado)
