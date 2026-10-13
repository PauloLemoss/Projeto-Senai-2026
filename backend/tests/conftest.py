from datetime import datetime

import pytest

from mercado_jogadores.jogadores.models import Jogador


class FakeJogadorRepository:
    """Implementa o mesmo `Protocol` de `JogadorRepository`, em memória — sem banco.

    Usado pelos testes do service layer (DIP): a regra de negócio é testada isolada da
    camada de persistência real.
    """

    def __init__(self) -> None:
        self._dados: dict[int, Jogador] = {}
        self._proximo_id = 1

    def obter(self, jogador_id: int) -> Jogador | None:
        jogador = self._dados.get(jogador_id)
        if jogador is None or jogador.excluido_em is not None:
            return None
        return jogador

    def salvar(self, jogador: Jogador) -> Jogador:
        if jogador.id is None:
            jogador.id = self._proximo_id
            self._proximo_id += 1
        self._dados[jogador.id] = jogador
        return jogador

    def excluir_logicamente(self, jogador_id: int, momento: datetime) -> None:
        jogador = self._dados.get(jogador_id)
        if jogador is not None:
            jogador.excluido_em = momento


@pytest.fixture
def fake_repo() -> FakeJogadorRepository:
    return FakeJogadorRepository()
