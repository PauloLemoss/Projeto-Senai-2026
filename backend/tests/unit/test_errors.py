import pytest

from mercado_jogadores.core.errors import (
    ConflitoError,
    ErroDeDominio,
    NaoEncontradoError,
    RequisicaoInvalidaError,
)


@pytest.mark.parametrize(
    "erro_cls",
    [ErroDeDominio, NaoEncontradoError, ConflitoError, RequisicaoInvalidaError],
)
def test_erro_carrega_a_mensagem(erro_cls: type[ErroDeDominio]) -> None:
    erro = erro_cls("algo deu errado")

    assert erro.message == "algo deu errado"
    assert str(erro) == "algo deu errado"
