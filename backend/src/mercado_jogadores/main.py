from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.exceptions import HTTPException as StarletteHTTPException

from mercado_jogadores.clubes.router import router as clubes_router
from mercado_jogadores.core.config import get_settings
from mercado_jogadores.core.db import get_session
from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError, RequisicaoInvalidaError
from mercado_jogadores.jogadores.router import router as jogadores_router
from mercado_jogadores.liga.router import router as liga_router
from mercado_jogadores.mercado.router import router as mercado_router


def create_app() -> FastAPI:
    app = FastAPI(title="Mercado de Jogadores", version="0.1.0")

    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.cors_origin],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(NaoEncontradoError)
    async def _tratar_nao_encontrado(request: Request, exc: NaoEncontradoError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"message": exc.message})

    @app.exception_handler(ConflitoError)
    async def _tratar_conflito(request: Request, exc: ConflitoError) -> JSONResponse:
        return JSONResponse(status_code=409, content={"message": exc.message})

    @app.exception_handler(RequisicaoInvalidaError)
    async def _tratar_requisicao_invalida(
        request: Request, exc: RequisicaoInvalidaError
    ) -> JSONResponse:
        return JSONResponse(status_code=400, content={"message": exc.message})

    @app.exception_handler(RequestValidationError)
    async def _tratar_erro_de_validacao(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        # V1/V2/V5/V6: corpo que não é objeto, tipo errado, enum fora da lista, campo ausente —
        # tudo isso o FastAPI detecta como RequestValidationError (422 por padrão); o enunciado
        # exige 400 (V9), nunca 422.
        return JSONResponse(status_code=400, content={"message": "Dado ou parâmetro inválido."})

    @app.exception_handler(StarletteHTTPException)
    async def _tratar_http_exception(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        # Cobre, entre outros, o 404 default do Starlette para caminho inexistente — garante
        # que toda recusa, mesmo a que o FastAPI gera sozinho, tem o campo `message` (V9).
        return JSONResponse(status_code=exc.status_code, content={"message": str(exc.detail)})

    @app.get("/health", tags=["health"])
    def verificar_saude(session: Session = Depends(get_session)) -> dict[str, str]:
        # Confere a conexão com o banco (não só "o processo subiu") — é o que o HEALTHCHECK do
        # Dockerfile e do docker-compose.yml usam para saber se a API está pronta de verdade.
        session.execute(text("SELECT 1"))
        return {"status": "ok"}

    app.include_router(jogadores_router, prefix="/api/v1")
    app.include_router(clubes_router, prefix="/api/v1")
    app.include_router(mercado_router, prefix="/api/v1")
    app.include_router(liga_router, prefix="/api/v1")
    return app


app = create_app()
