from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.repository import FiltrosSql, SQLAlchemyJogadorRepository


def _novo_jogador(**sobrescritas: object) -> Jogador:
    base = dict(
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
    base.update(sobrescritas)
    return Jogador(**base)


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


def test_listar_filtra_por_posicao_e_exclui_jogador_excluido(db_session: Session) -> None:
    repo = SQLAlchemyJogadorRepository(db_session)
    ata = repo.salvar(_novo_jogador(posicao="ATA"))
    mei = repo.salvar(_novo_jogador(posicao="MEI"))
    excluido = repo.salvar(_novo_jogador(posicao="ATA"))
    repo.excluir_logicamente(excluido.id, datetime.now(UTC))

    resultado = repo.listar(FiltrosSql(position="ATA"))

    ids = {j.id for j in resultado}
    assert ata.id in ids
    assert mei.id not in ids
    assert excluido.id not in ids


def test_listar_filtra_por_condicao(db_session: Session) -> None:
    repo = SQLAlchemyJogadorRepository(db_session)
    apto = repo.salvar(_novo_jogador(condicao="APTO"))
    doente = repo.salvar(_novo_jogador(condicao="DOENTE"))

    resultado = repo.listar(FiltrosSql(condition="DOENTE"))

    ids = {j.id for j in resultado}
    assert doente.id in ids
    assert apto.id not in ids


def test_listar_filtra_por_livre(db_session: Session) -> None:
    repo = SQLAlchemyJogadorRepository(db_session)
    livre = repo.salvar(_novo_jogador(clube_id=None))
    com_clube = repo.salvar(_novo_jogador(clube_id=1))

    resultado = repo.listar(FiltrosSql(free=True))

    ids = {j.id for j in resultado}
    assert livre.id in ids
    assert com_clube.id not in ids


def test_listar_filtra_por_club_id(db_session: Session) -> None:
    repo = SQLAlchemyJogadorRepository(db_session)
    do_clube_2 = repo.salvar(_novo_jogador(clube_id=2))
    do_clube_1 = repo.salvar(_novo_jogador(clube_id=1))

    resultado = repo.listar(FiltrosSql(club_id=2))

    ids = {j.id for j in resultado}
    assert do_clube_2.id in ids
    assert do_clube_1.id not in ids


def test_listar_filtra_por_faixa_de_idade(db_session: Session) -> None:
    repo = SQLAlchemyJogadorRepository(db_session)
    jovem = repo.salvar(_novo_jogador(idade=18))
    na_faixa = repo.salvar(_novo_jogador(idade=30))
    velho = repo.salvar(_novo_jogador(idade=40))

    resultado = repo.listar(FiltrosSql(min_age=20, max_age=35))

    ids = {j.id for j in resultado}
    assert na_faixa.id in ids
    assert jovem.id not in ids
    assert velho.id not in ids
