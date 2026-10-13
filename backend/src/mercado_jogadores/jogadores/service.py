"""Regras de negócio do domínio jogador (RN02 a RN09). Único lugar onde essas regras vivem —
o router nunca as recalcula, só delega aqui."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError
from mercado_jogadores.jogadores.calculos import calcular_overall, calcular_valor_base, calcular_valor_de_mercado
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.repository import JogadorRepository

CONDICOES_VALIDAS = ("APTO", "MAL_CONDICIONADO", "DOENTE")


@dataclass
class DadosCadastroJogador:
    nome: str
    posicao: str
    agilidade: int
    idade: int
    pace: int
    shooting: int
    passing: int
    dribbling: int
    defending: int
    physical: int
    potential: int


@dataclass
class DadosEdicaoJogador:
    nome: str
    posicao: str
    agilidade: int
    idade: int


@dataclass
class JogadorComCalculados:
    """Jogador persistido + os campos calculados a cada consulta (RN02–RN06), nunca gravados."""

    jogador: Jogador
    overall: int
    market_value: Decimal


class JogadorService:
    def __init__(self, repository: JogadorRepository) -> None:
        self._repository = repository

    def cadastrar(self, dados: DadosCadastroJogador) -> JogadorComCalculados:
        atributos = {
            "pace": dados.pace,
            "shooting": dados.shooting,
            "passing": dados.passing,
            "dribbling": dados.dribbling,
            "defending": dados.defending,
            "physical": dados.physical,
        }
        overall_no_cadastro = calcular_overall(atributos, dados.posicao)
        valor_base = calcular_valor_base(overall_no_cadastro, dados.potential, dados.idade)

        jogador = Jogador(
            nome=dados.nome,
            posicao=dados.posicao,
            agilidade=dados.agilidade,
            idade=dados.idade,
            valor_base=valor_base,
            condicao="APTO",
            clube_id=None,
            velocidade=dados.pace,
            finalizacao=dados.shooting,
            passe=dados.passing,
            drible=dados.dribbling,
            defesa=dados.defending,
            fisico=dados.physical,
            potencial=dados.potential,
        )
        jogador = self._repository.salvar(jogador)
        return self._com_calculados(jogador)

    def consultar(self, jogador_id: int) -> JogadorComCalculados:
        jogador = self._obter_ou_falhar(jogador_id)
        return self._com_calculados(jogador)

    def editar(self, jogador_id: int, dados: DadosEdicaoJogador) -> JogadorComCalculados:
        jogador = self._obter_ou_falhar(jogador_id)

        if dados.posicao != jogador.posicao and jogador.clube_id is not None:
            raise ConflitoError("Jogador com clube não muda de posição.")
        if dados.idade < jogador.idade:
            raise ConflitoError("A idade não pode diminuir.")

        jogador.nome = dados.nome
        jogador.posicao = dados.posicao
        jogador.agilidade = dados.agilidade
        jogador.idade = dados.idade

        jogador = self._repository.salvar(jogador)
        return self._com_calculados(jogador)

    def alterar_condicao(self, jogador_id: int, nova_condicao: str) -> JogadorComCalculados:
        jogador = self._obter_ou_falhar(jogador_id)

        if jogador.condicao == "DOENTE" and nova_condicao == "APTO":
            raise ConflitoError("Jogador DOENTE não pode passar direto para APTO.")

        jogador.condicao = nova_condicao
        jogador = self._repository.salvar(jogador)
        return self._com_calculados(jogador)

    def excluir(self, jogador_id: int) -> None:
        jogador = self._obter_ou_falhar(jogador_id)

        if jogador.clube_id is not None:
            raise ConflitoError("Só jogador livre pode ser excluído.")

        self._repository.excluir_logicamente(jogador_id, datetime.now(UTC))

    def _obter_ou_falhar(self, jogador_id: int) -> Jogador:
        jogador = self._repository.obter(jogador_id)
        if jogador is None:
            raise NaoEncontradoError("Jogador não encontrado.")
        return jogador

    def _com_calculados(self, jogador: Jogador) -> JogadorComCalculados:
        atributos = {
            "pace": jogador.velocidade,
            "shooting": jogador.finalizacao,
            "passing": jogador.passe,
            "dribbling": jogador.drible,
            "defending": jogador.defesa,
            "physical": jogador.fisico,
        }
        overall = calcular_overall(atributos, jogador.posicao)
        market_value = calcular_valor_de_mercado(
            jogador.valor_base, jogador.condicao, jogador.agilidade, jogador.idade
        )
        return JogadorComCalculados(jogador=jogador, overall=overall, market_value=market_value)
