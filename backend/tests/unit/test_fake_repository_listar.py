from datetime import UTC, datetime
from decimal import Decimal

from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.repository import FiltrosSql
from tests.conftest import FakeJogadorRepository


def _jogador(**sobrescritas: object) -> Jogador:
    base = {
        "nome": "Jogador Teste",
        "posicao": "MEI",
        "agilidade": 70,
        "idade": 25,
        "valor_base": Decimal("50.00"),
        "condicao": "APTO",
        "clube_id": None,
        "velocidade": 70,
        "finalizacao": 70,
        "passe": 70,
        "drible": 70,
        "defesa": 70,
        "fisico": 70,
        "potencial": 75,
    }
    base.update(sobrescritas)
    return Jogador(**base)


def test_listar_sem_filtro_devolve_todos_os_ativos(fake_repo: FakeJogadorRepository) -> None:
    fake_repo.salvar(_jogador())
    fake_repo.salvar(_jogador())

    assert len(fake_repo.listar(FiltrosSql())) == 2


def test_listar_exclui_jogador_excluido(fake_repo: FakeJogadorRepository) -> None:
    jogador = fake_repo.salvar(_jogador())
    fake_repo.excluir_logicamente(jogador.id, momento=datetime.now(UTC))

    assert fake_repo.listar(FiltrosSql()) == []


def test_listar_filtra_por_posicao(fake_repo: FakeJogadorRepository) -> None:
    fake_repo.salvar(_jogador(posicao="MEI"))
    fake_repo.salvar(_jogador(posicao="ATA"))

    resultado = fake_repo.listar(FiltrosSql(position="ATA"))

    assert len(resultado) == 1
    assert resultado[0].posicao == "ATA"


def test_listar_filtra_por_condicao(fake_repo: FakeJogadorRepository) -> None:
    fake_repo.salvar(_jogador(condicao="APTO"))
    fake_repo.salvar(_jogador(condicao="DOENTE"))

    resultado = fake_repo.listar(FiltrosSql(condition="DOENTE"))

    assert len(resultado) == 1
    assert resultado[0].condicao == "DOENTE"


def test_listar_filtra_por_livre(fake_repo: FakeJogadorRepository) -> None:
    fake_repo.salvar(_jogador(clube_id=None))
    fake_repo.salvar(_jogador(clube_id=1))

    resultado = fake_repo.listar(FiltrosSql(free=True))

    assert len(resultado) == 1
    assert resultado[0].clube_id is None


def test_listar_filtra_por_club_id(fake_repo: FakeJogadorRepository) -> None:
    fake_repo.salvar(_jogador(clube_id=1))
    fake_repo.salvar(_jogador(clube_id=2))

    resultado = fake_repo.listar(FiltrosSql(club_id=2))

    assert len(resultado) == 1
    assert resultado[0].clube_id == 2


def test_listar_filtra_por_faixa_de_idade(fake_repo: FakeJogadorRepository) -> None:
    fake_repo.salvar(_jogador(idade=18))
    fake_repo.salvar(_jogador(idade=30))
    fake_repo.salvar(_jogador(idade=40))

    resultado = fake_repo.listar(FiltrosSql(min_age=20, max_age=35))

    assert len(resultado) == 1
    assert resultado[0].idade == 30
