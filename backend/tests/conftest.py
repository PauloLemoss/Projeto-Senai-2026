from datetime import datetime

import pytest

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.repository import FiltrosSql
from mercado_jogadores.liga.models import DueloPartida, Partida
from mercado_jogadores.liga.repository import FiltrosDePartida
from mercado_jogadores.mercado.models import Contrato, Transacao
from mercado_jogadores.mercado.repository import FiltrosDeTransacao


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

    def listar(self, filtros: FiltrosSql) -> list[Jogador]:
        resultado = [j for j in self._dados.values() if j.excluido_em is None]

        if filtros.position is not None:
            resultado = [j for j in resultado if j.posicao == filtros.position]
        if filtros.condition is not None:
            resultado = [j for j in resultado if j.condicao == filtros.condition]
        if filtros.free is not None:
            resultado = [j for j in resultado if (j.clube_id is None) == filtros.free]
        if filtros.club_id is not None:
            resultado = [j for j in resultado if j.clube_id == filtros.club_id]
        if filtros.min_age is not None:
            resultado = [j for j in resultado if j.idade >= filtros.min_age]
        if filtros.max_age is not None:
            resultado = [j for j in resultado if j.idade <= filtros.max_age]

        return resultado


@pytest.fixture
def fake_repo() -> FakeJogadorRepository:
    return FakeJogadorRepository()


class FakeClubeRepository:
    """Implementa o mesmo `Protocol` de `ClubeRepository`, em memória — sem banco.

    Usado pelos testes do service layer (DIP): a regra de negócio é testada isolada da
    camada de persistência real.
    """

    def __init__(self) -> None:
        self._dados: dict[int, Clube] = {}
        self._proximo_id = 1

    def obter(self, clube_id: int) -> Clube | None:
        return self._dados.get(clube_id)

    def obter_por_nome_normalizado(self, nome_normalizado: str) -> Clube | None:
        for clube in self._dados.values():
            if clube.nome_normalizado == nome_normalizado:
                return clube
        return None

    def obter_por_sigla(self, sigla: str) -> Clube | None:
        for clube in self._dados.values():
            if clube.sigla == sigla:
                return clube
        return None

    def salvar(self, clube: Clube) -> Clube:
        if clube.id is None:
            clube.id = self._proximo_id
            self._proximo_id += 1
        self._dados[clube.id] = clube
        return clube

    def contar(self) -> int:
        return len(self._dados)

    def listar(self) -> list[Clube]:
        return list(self._dados.values())


@pytest.fixture
def fake_clube_repo() -> FakeClubeRepository:
    return FakeClubeRepository()


class FakeContratoRepository:
    """Implementa o mesmo `Protocol` de `ContratoRepository`, em memória — sem banco."""

    def __init__(self) -> None:
        self._dados: dict[int, Contrato] = {}
        self._proximo_id = 1

    def obter_ativo_por_jogador(self, jogador_id: int) -> Contrato | None:
        for contrato in self._dados.values():
            if contrato.jogador_id == jogador_id and contrato.situacao == "ATIVO":
                return contrato
        return None

    def adicionar(self, contrato: Contrato) -> None:
        if contrato.id is None:
            contrato.id = self._proximo_id
            self._proximo_id += 1
        self._dados[contrato.id] = contrato


@pytest.fixture
def fake_contrato_repo() -> FakeContratoRepository:
    return FakeContratoRepository()


class FakeTransacaoRepository:
    """Implementa o mesmo `Protocol` de `TransacaoRepository`, em memória — sem banco."""

    def __init__(self) -> None:
        self._dados: list[Transacao] = []
        self._proximo_id = 1

    def adicionar(self, transacao: Transacao) -> None:
        if transacao.id is None:
            transacao.id = self._proximo_id
            self._proximo_id += 1
        self._dados.append(transacao)

    def existe_venda(self, clube_id: int, jogador_id: int) -> bool:
        return any(
            t.clube_id == clube_id and t.jogador_id == jogador_id and t.tipo == "VENDA"
            for t in self._dados
        )

    def listar_por_clube(self, clube_id: int, filtros: FiltrosDeTransacao) -> list[Transacao]:
        resultado = [t for t in self._dados if t.clube_id == clube_id]
        if filtros.tipos is not None:
            resultado = [t for t in resultado if t.tipo in filtros.tipos]
        if filtros.jogador_id is not None:
            resultado = [t for t in resultado if t.jogador_id == filtros.jogador_id]
        resultado.sort(key=lambda t: (t.criado_em, t.id), reverse=True)
        return resultado


@pytest.fixture
def fake_transacao_repo() -> FakeTransacaoRepository:
    return FakeTransacaoRepository()


class FakeUnidadeDeTrabalho:
    """No-op: os repositórios fake já mutam objetos em memória, sem conceito de transação."""

    def confirmar(self) -> None:
        pass

    def desfazer(self) -> None:
        pass


@pytest.fixture
def fake_unidade_de_trabalho() -> FakeUnidadeDeTrabalho:
    return FakeUnidadeDeTrabalho()


class FakeEscalacaoRepository:
    """Implementa o mesmo `Protocol` de `EscalacaoRepository`, em memória — sem banco."""

    def __init__(self) -> None:
        self._titulares_por_clube: dict[int, list[int]] = {}

    def listar_titulares_do_clube(self, clube_id: int) -> list[int]:
        return list(self._titulares_por_clube.get(clube_id, []))

    def substituir_escalacao_do_clube(
        self, clube_id: int, jogador_ids: list[int], momento: datetime
    ) -> None:
        self._titulares_por_clube[clube_id] = list(jogador_ids)

    def remover_titular(self, jogador_id: int) -> None:
        for titulares in self._titulares_por_clube.values():
            if jogador_id in titulares:
                titulares.remove(jogador_id)
                return


@pytest.fixture
def fake_escalacao_repo() -> FakeEscalacaoRepository:
    return FakeEscalacaoRepository()


class FakePartidaRepository:
    """Implementa o mesmo `Protocol` de `PartidaRepository`, em memória — sem banco."""

    def __init__(self) -> None:
        self._partidas: dict[int, Partida] = {}
        self._duelos: dict[int, list[DueloPartida]] = {}
        self._proximo_id = 1

    def adicionar(self, partida: Partida) -> Partida:
        if partida.id is None:
            partida.id = self._proximo_id
            self._proximo_id += 1
        self._partidas[partida.id] = partida
        self._duelos.setdefault(partida.id, [])
        return partida

    def adicionar_duelo(self, duelo: DueloPartida) -> None:
        self._duelos.setdefault(duelo.partida_id, []).append(duelo)

    def listar(self, filtros: FiltrosDePartida) -> list[Partida]:
        resultado = list(self._partidas.values())
        if filtros.clube_id is not None:
            resultado = [
                p for p in resultado if filtros.clube_id in (p.mandante_id, p.visitante_id)
            ]
        resultado.sort(key=lambda p: (p.jogada_em, p.id), reverse=True)
        return resultado

    def obter(self, partida_id: int) -> Partida | None:
        return self._partidas.get(partida_id)

    def listar_duelos(self, partida_id: int) -> list[DueloPartida]:
        return sorted(self._duelos.get(partida_id, []), key=lambda d: d.ordem)


@pytest.fixture
def fake_partida_repo() -> FakePartidaRepository:
    return FakePartidaRepository()
