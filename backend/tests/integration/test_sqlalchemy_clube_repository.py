from sqlalchemy.orm import Session

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.clubes.repository import SQLAlchemyClubeRepository


def _novo_clube(**sobrescritas: object) -> Clube:
    base = {"nome": "Águias FC", "nome_normalizado": "águias fc", "sigla": "AGU"}
    base.update(sobrescritas)
    return Clube(**base)


def test_salvar_e_obter_contra_o_postgres_real(db_session: Session) -> None:
    repo = SQLAlchemyClubeRepository(db_session)

    salvo = repo.salvar(_novo_clube())
    assert salvo.id is not None
    assert salvo.caixa == 300

    obtido = repo.obter(salvo.id)
    assert obtido is not None
    assert obtido.nome == "Águias FC"


def test_obter_clube_inexistente_retorna_none(db_session: Session) -> None:
    repo = SQLAlchemyClubeRepository(db_session)

    assert repo.obter(999_999) is None


def test_contar_reflete_quantidade_de_clubes(db_session: Session) -> None:
    repo = SQLAlchemyClubeRepository(db_session)
    assert repo.contar() == 0

    repo.salvar(_novo_clube())
    repo.salvar(_novo_clube(nome="Leões FC", nome_normalizado="leões fc", sigla="LEO"))

    assert repo.contar() == 2


def test_obter_por_nome_normalizado_encontra_ignorando_caixa(db_session: Session) -> None:
    repo = SQLAlchemyClubeRepository(db_session)
    repo.salvar(_novo_clube())

    encontrado = repo.obter_por_nome_normalizado("águias fc")

    assert encontrado is not None
    assert encontrado.sigla == "AGU"
    assert repo.obter_por_nome_normalizado("leões fc") is None


def test_obter_por_sigla_encontra(db_session: Session) -> None:
    repo = SQLAlchemyClubeRepository(db_session)
    repo.salvar(_novo_clube())

    encontrado = repo.obter_por_sigla("AGU")

    assert encontrado is not None
    assert encontrado.nome == "Águias FC"
    assert repo.obter_por_sigla("LEO") is None


def test_listar_devolve_todos_os_clubes(db_session: Session) -> None:
    repo = SQLAlchemyClubeRepository(db_session)
    repo.salvar(_novo_clube())
    repo.salvar(_novo_clube(nome="Leões FC", nome_normalizado="leões fc", sigla="LEO"))

    resultado = repo.listar()

    assert {c.nome for c in resultado} == {"Águias FC", "Leões FC"}
