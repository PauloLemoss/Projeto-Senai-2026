from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from mercado_jogadores.clubes.repository import SQLAlchemyClubeRepository
from mercado_jogadores.core.db import get_session
from mercado_jogadores.core.unidade_de_trabalho import SQLAlchemyUnidadeDeTrabalho
from mercado_jogadores.core.validation import validar_id_da_url
from mercado_jogadores.jogadores.repository import SQLAlchemyJogadorRepository
from mercado_jogadores.jogadores.schemas import (
    CondicaoUpdate,
    JogadorCreate,
    JogadorListQuery,
    JogadorRead,
    JogadorUpdate,
    PlayerListResponse,
)
from mercado_jogadores.jogadores.service import JogadorService
from mercado_jogadores.liga.repository import SQLAlchemyEscalacaoRepository

router = APIRouter(prefix="/players", tags=["jogadores"])


def get_jogador_service(session: Session = Depends(get_session)) -> JogadorService:
    return JogadorService(
        SQLAlchemyJogadorRepository(session),
        SQLAlchemyEscalacaoRepository(session),
        SQLAlchemyUnidadeDeTrabalho(session),
        SQLAlchemyClubeRepository(session),
    )


@router.get("", response_model=PlayerListResponse)
def listar_jogadores(
    query: Annotated[JogadorListQuery, Query()],
    service: JogadorService = Depends(get_jogador_service),
) -> PlayerListResponse:
    resultado = service.listar(query.para_filtros_de_listagem())
    return PlayerListResponse.a_partir_do_resultado(resultado)


@router.post("", status_code=201, response_model=JogadorRead)
def cadastrar_jogador(
    dados: JogadorCreate,
    response: Response,
    service: JogadorService = Depends(get_jogador_service),
) -> JogadorRead:
    resultado = service.cadastrar(dados.para_dados_de_cadastro())
    response.headers["Location"] = f"/api/v1/players/{resultado.jogador.id}"
    return JogadorRead.a_partir_do_resultado(resultado)


@router.get("/{jogador_id}", response_model=JogadorRead)
def consultar_jogador(
    jogador_id: str, service: JogadorService = Depends(get_jogador_service)
) -> JogadorRead:
    id_valido = validar_id_da_url(jogador_id)
    resultado = service.consultar(id_valido)
    return JogadorRead.a_partir_do_resultado(resultado)


@router.put("/{jogador_id}", response_model=JogadorRead)
def editar_jogador(
    jogador_id: str,
    dados: JogadorUpdate,
    service: JogadorService = Depends(get_jogador_service),
) -> JogadorRead:
    id_valido = validar_id_da_url(jogador_id)
    resultado = service.editar(id_valido, dados.para_dados_de_edicao())
    return JogadorRead.a_partir_do_resultado(resultado)


@router.patch("/{jogador_id}/condition", response_model=JogadorRead)
def alterar_condicao_do_jogador(
    jogador_id: str,
    dados: CondicaoUpdate,
    service: JogadorService = Depends(get_jogador_service),
) -> JogadorRead:
    id_valido = validar_id_da_url(jogador_id)
    resultado = service.alterar_condicao(id_valido, dados.condition)
    return JogadorRead.a_partir_do_resultado(resultado)


@router.delete("/{jogador_id}", status_code=204)
def excluir_jogador(
    jogador_id: str, service: JogadorService = Depends(get_jogador_service)
) -> Response:
    id_valido = validar_id_da_url(jogador_id)
    service.excluir(id_valido)
    return Response(status_code=204)
