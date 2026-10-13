from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from mercado_jogadores.core.db import SessionLocal
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.repository import SQLAlchemyJogadorRepository


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Sessão real contra o Postgres do docker-compose, revertida ao final do teste."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def _novo_jogador() -> Jogador:
    return Jogador(
        nome="Teste Integração",
        posicao="ATA",
        agilidade=70,
        idade=25,
        valor_base=Decimal("50.00"),
        condicao="APTO",
        velocidade=70,
        finalizacao=70,
        passe=70,
        drible=70,
        defesa=70,
        fisico=70,
        potencial=75,
    )


def test_salvar_e_obter_contra_o_postgres_real(db_session: Session) -> None:
    repo = SQLAlchemyJogadorRepository(db_session)

    salvo = repo.salvar(_novo_jogador())
    assert salvo.id is not None

    obtido = repo.obter(salvo.id)
    assert obtido is not None
    assert obtido.nome == "Teste Integração"


def test_excluir_logicamente_marca_excluido_em_e_some_do_obter(db_session: Session) -> None:
    repo = SQLAlchemyJogadorRepository(db_session)
    jogador = repo.salvar(_novo_jogador())

    repo.excluir_logicamente(jogador.id, datetime.now(UTC))

    assert repo.obter(jogador.id) is None
