"""Regras de negócio do domínio jogador (RN02 a RN09). Único lugar onde essas regras vivem —
o router nunca as recalcula, só delega aqui."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal

from mercado_jogadores.clubes.repository import ClubeRepository
from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError
from mercado_jogadores.core.unidade_de_trabalho import UnidadeDeTrabalho
from mercado_jogadores.core.validation import normalizar_para_busca
from mercado_jogadores.jogadores.calculos import (
    ORDEM_DAS_POSICOES,
    calcular_overall,
    calcular_valor_base,
    calcular_valor_de_mercado,
)
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.repository import FiltrosSql, JogadorRepository
from mercado_jogadores.liga.repository import EscalacaoRepository

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


@dataclass
class FiltrosDeListagem:
    """Parâmetros de GET /players (RN07), já validados pelo schema da camada HTTP."""

    search: str | None = None
    position: str | None = None
    condition: str | None = None
    free: bool | None = None
    club_id: int | None = None
    min_age: int | None = None
    max_age: int | None = None
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    sort: list[str] = field(default_factory=lambda: ["name"])
    page: int = 1
    limit: int = 10


@dataclass
class ListaDeJogadores:
    itens: list[JogadorComCalculados]
    total_items: int
    page: int
    limit: int

    @property
    def total_pages(self) -> int:
        if self.total_items == 0:
            return 0
        return -(-self.total_items // self.limit)  # divisão arredondada para cima


def calcular_indicadores(jogador: Jogador) -> JogadorComCalculados:
    """Overall (RN06) e valor de mercado (RN05), calculados a cada consulta — usado também por
    `ClubeService` ao montar o elenco (RN11), sem duplicar a regra."""
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


class JogadorService:
    def __init__(
        self,
        repository: JogadorRepository,
        escalacao_repository: EscalacaoRepository,
        unidade_de_trabalho: UnidadeDeTrabalho,
        clube_repository: ClubeRepository,
    ) -> None:
        self._repository = repository
        self._escalacoes = escalacao_repository
        self._uot = unidade_de_trabalho
        self._clubes = clube_repository

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

        if nova_condicao == "DOENTE":
            return self._alterar_para_doente(jogador)

        jogador.condicao = nova_condicao
        jogador = self._repository.salvar(jogador)
        return self._com_calculados(jogador)

    def _alterar_para_doente(self, jogador: Jogador) -> JogadorComCalculados:
        """RN19.5: titular que fica DOENTE sai da escalação, na mesma operação atômica."""
        jogador.condicao = "DOENTE"
        self._escalacoes.remover_titular(jogador.id)
        try:
            self._uot.confirmar()
        except Exception:
            self._uot.desfazer()
            raise
        return self._com_calculados(jogador)

    def listar(self, filtros: FiltrosDeListagem) -> ListaDeJogadores:
        if filtros.club_id is not None and self._clubes.obter(filtros.club_id) is None:
            raise NaoEncontradoError("Clube não encontrado.")

        filtros_sql = FiltrosSql(
            position=filtros.position,
            condition=filtros.condition,
            free=filtros.free,
            club_id=filtros.club_id,
            min_age=filtros.min_age,
            max_age=filtros.max_age,
        )
        candidatos = self._repository.listar(filtros_sql)

        if filtros.search:
            termo = normalizar_para_busca(filtros.search)
            candidatos = [j for j in candidatos if termo in normalizar_para_busca(j.nome)]

        resultados = [self._com_calculados(j) for j in candidatos]

        if filtros.min_value is not None:
            resultados = [r for r in resultados if r.market_value >= filtros.min_value]
        if filtros.max_value is not None:
            resultados = [r for r in resultados if r.market_value <= filtros.max_value]

        resultados = self._ordenar(resultados, filtros.sort)

        inicio = (filtros.page - 1) * filtros.limit
        pagina = resultados[inicio : inicio + filtros.limit]

        return ListaDeJogadores(
            itens=pagina, total_items=len(resultados), page=filtros.page, limit=filtros.limit
        )

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

    def _ordenar(
        self, resultados: list[JogadorComCalculados], criterios: list[str]
    ) -> list[JogadorComCalculados]:
        """Ordena com múltiplas passadas de sort estável, da menos pra mais significativa:
        id crescente e nome (desempate final, RN07) primeiro, depois os critérios do usuário
        na ordem inversa — o último aplicado é o de maior prioridade."""
        resultados = sorted(resultados, key=lambda r: r.jogador.id)
        resultados = sorted(resultados, key=lambda r: normalizar_para_busca(r.jogador.nome))
        for campo in reversed(criterios):
            resultados = sorted(
                resultados, key=self._chave_de_ordenacao(campo), reverse=campo.endswith("_desc")
            )
        return resultados

    @staticmethod
    def _chave_de_ordenacao(campo: str):
        if campo in ("value_asc", "value_desc"):
            return lambda r: r.market_value
        if campo in ("age_asc", "age_desc"):
            return lambda r: r.jogador.idade
        if campo == "position":
            return lambda r: ORDEM_DAS_POSICOES.index(r.jogador.posicao)
        return lambda r: normalizar_para_busca(r.jogador.nome)

    def _com_calculados(self, jogador: Jogador) -> JogadorComCalculados:
        return calcular_indicadores(jogador)
