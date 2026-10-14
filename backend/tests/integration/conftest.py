from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.orm import Session

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.core.db import SessionLocal, get_session
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.liga.models import DueloPartida, Escalacao, Partida
from mercado_jogadores.main import app
from mercado_jogadores.mercado.models import Contrato, Transacao


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Sessão real contra o Postgres do docker-compose.

    O repositório comita internamente (salvar/excluir_logicamente), então isolamento por
    rollback não funciona aqui — a limpeza é feita apagando as tabelas ao final do teste, sempre
    filhas antes de pais (FK): `duelos_partida` antes de `partidas`; `escalacoes`,
    `contratos`/`transacoes` antes de `jogadores`/`clubes`; `jogadores` antes de `clubes`.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.execute(delete(DueloPartida))
        session.execute(delete(Partida))
        session.execute(delete(Escalacao))
        session.execute(delete(Contrato))
        session.execute(delete(Transacao))
        session.execute(delete(Jogador))
        session.execute(delete(Clube))
        session.commit()
        session.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def _sessao_de_teste() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_session] = _sessao_de_teste
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
