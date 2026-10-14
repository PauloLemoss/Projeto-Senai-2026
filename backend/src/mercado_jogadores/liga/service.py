"""Regras de negócio do domínio liga (RN19 a RN21). Único lugar onde essas regras vivem —
o router nunca as recalcula, só delega aqui.

A validação de formato de `formation`/`player_ids`/`home_club_id`/`away_club_id` (RN01) fica nos
schemas da camada HTTP — ver design.md. Aqui só as regras que dependem de persistência e do
estado de clube/jogador/escalação.
"""

from dataclasses import dataclass
from datetime import datetime

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.clubes.repository import ClubeRepository
from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError, RequisicaoInvalidaError
from mercado_jogadores.core.unidade_de_trabalho import UnidadeDeTrabalho
from mercado_jogadores.core.validation import normalizar_para_busca
from mercado_jogadores.jogadores.calculos import ORDEM_DAS_POSICOES
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.jogadores.repository import FiltrosSql, JogadorRepository
from mercado_jogadores.jogadores.service import JogadorComCalculados, calcular_indicadores
from mercado_jogadores.liga.calculos import (
    DueloCalculado,
    TitularEmCampo,
    calcular_placar_e_resultado,
    formacao_fecha_com_as_posicoes,
    montar_duelos,
    resultado_por_placar,
)
from mercado_jogadores.liga.models import DueloPartida, Partida
from mercado_jogadores.liga.repository import (
    EscalacaoRepository,
    FiltrosDePartida,
    PartidaRepository,
)

TITULARES_POR_ESCALACAO = 5


@dataclass
class DadosDeEscalacao:
    formation: str
    player_ids: list[int]


@dataclass
class EscalacaoDoClube:
    clube: Clube
    formation: str | None
    complete: bool
    titulares: list[JogadorComCalculados]


@dataclass
class DadosDePartida:
    home_club_id: int
    away_club_id: int


@dataclass
class LadoDaPartida:
    club_id: int
    club_name: str
    formation: str
    goals: int


@dataclass
class ResultadoDaPartida:
    id: int
    jogada_em: datetime
    mandante: LadoDaPartida
    visitante: LadoDaPartida
    duelos: list[DueloPartida]

    @property
    def result(self) -> str:
        return resultado_por_placar(self.mandante.goals, self.visitante.goals)


@dataclass
class LinhaDeClassificacao:
    club_id: int
    club_name: str
    played: int = 0
    wins: int = 0
    draws: int = 0
    losses: int = 0
    goals_for: int = 0
    goals_against: int = 0
    position: int = 0

    @property
    def goal_difference(self) -> int:
        return self.goals_for - self.goals_against

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws


class LigaService:
    def __init__(
        self,
        clube_repository: ClubeRepository,
        jogador_repository: JogadorRepository,
        escalacao_repository: EscalacaoRepository,
        partida_repository: PartidaRepository,
        unidade_de_trabalho: UnidadeDeTrabalho,
    ) -> None:
        self._clubes = clube_repository
        self._jogadores = jogador_repository
        self._escalacoes = escalacao_repository
        self._partidas = partida_repository
        self._uot = unidade_de_trabalho

    def escalar(
        self, clube_id: int, dados: DadosDeEscalacao, momento: datetime
    ) -> EscalacaoDoClube:
        clube = self._obter_clube_ou_falhar(clube_id)

        titulares = []
        for jogador_id in dados.player_ids:
            jogador = self._jogadores.obter(jogador_id)
            if jogador is None:
                raise NaoEncontradoError("Jogador não encontrado.")
            titulares.append(jogador)

        for jogador in titulares:
            if jogador.clube_id != clube_id:
                raise ConflitoError("Jogador fora do elenco do clube.")
            if jogador.condicao == "DOENTE":
                raise ConflitoError("Jogador DOENTE não pode ser escalado.")

        posicoes = [jogador.posicao for jogador in titulares]
        if not formacao_fecha_com_as_posicoes(dados.formation, posicoes):
            raise ConflitoError("As posições escaladas não fecham a formação.")

        clube.formacao = dados.formation
        self._escalacoes.substituir_escalacao_do_clube(clube_id, dados.player_ids, momento)
        self._confirmar_ou_desfazer()

        return self.consultar_escalacao(clube_id)

    def consultar_escalacao(self, clube_id: int) -> EscalacaoDoClube:
        clube = self._obter_clube_ou_falhar(clube_id)

        titulares_ids = set(self._escalacoes.listar_titulares_do_clube(clube_id))
        elenco_ordenado = self._elenco_ordenado(clube_id)
        titulares = [jogador for jogador in elenco_ordenado if jogador.id in titulares_ids]

        return EscalacaoDoClube(
            clube=clube,
            formation=clube.formacao,
            complete=len(titulares_ids) == TITULARES_POR_ESCALACAO,
            titulares=[calcular_indicadores(jogador) for jogador in titulares],
        )

    def jogar_partida(self, dados: DadosDePartida, momento: datetime) -> ResultadoDaPartida:
        if dados.home_club_id == dados.away_club_id:
            raise RequisicaoInvalidaError("O clube mandante não pode ser igual ao visitante.")

        mandante = self._obter_clube_ou_falhar(dados.home_club_id)
        visitante = self._obter_clube_ou_falhar(dados.away_club_id)

        titulares_mandante = self._titulares_em_campo(mandante)
        titulares_visitante = self._titulares_em_campo(visitante)

        duelos_calculados = montar_duelos(
            mandante.id, titulares_mandante, visitante.id, titulares_visitante
        )
        gols_mandante, gols_visitante, _resultado = calcular_placar_e_resultado(duelos_calculados)

        partida = self._partidas.adicionar(
            Partida(
                mandante_id=mandante.id,
                visitante_id=visitante.id,
                gols_mandante=gols_mandante,
                gols_visitante=gols_visitante,
                formacao_mandante=mandante.formacao,
                formacao_visitante=visitante.formacao,
                jogada_em=momento,
            )
        )

        duelos_gravados = [
            self._gravar_duelo(partida.id, duelo_calculado) for duelo_calculado in duelos_calculados
        ]

        self._confirmar_ou_desfazer()
        return ResultadoDaPartida(
            id=partida.id,
            jogada_em=partida.jogada_em,
            mandante=LadoDaPartida(
                club_id=mandante.id,
                club_name=mandante.nome,
                formation=mandante.formacao,
                goals=gols_mandante,
            ),
            visitante=LadoDaPartida(
                club_id=visitante.id,
                club_name=visitante.nome,
                formation=visitante.formacao,
                goals=gols_visitante,
            ),
            duelos=duelos_gravados,
        )

    def historico(self, filtros: FiltrosDePartida) -> list[ResultadoDaPartida]:
        if filtros.clube_id is not None and self._clubes.obter(filtros.clube_id) is None:
            raise NaoEncontradoError("Clube não encontrado.")
        # RN21: a listagem não traz os duelos (só `GET /matches/{id}`) — evita buscá-los à toa.
        return [self._resultado_a_partir_da_partida(p, []) for p in self._partidas.listar(filtros)]

    def consultar_partida(self, partida_id: int) -> ResultadoDaPartida:
        partida = self._partidas.obter(partida_id)
        if partida is None:
            raise NaoEncontradoError("Partida não encontrada.")
        duelos = self._partidas.listar_duelos(partida_id)
        return self._resultado_a_partir_da_partida(partida, duelos)

    def _resultado_a_partir_da_partida(
        self, partida: Partida, duelos: list[DueloPartida]
    ) -> ResultadoDaPartida:
        return ResultadoDaPartida(
            id=partida.id,
            jogada_em=partida.jogada_em,
            mandante=self._lado(
                partida.mandante_id, partida.formacao_mandante, partida.gols_mandante
            ),
            visitante=self._lado(
                partida.visitante_id, partida.formacao_visitante, partida.gols_visitante
            ),
            duelos=duelos,
        )

    def _lado(self, clube_id: int, formacao: str, gols: int) -> LadoDaPartida:
        clube = self._clubes.obter(clube_id)
        return LadoDaPartida(club_id=clube_id, club_name=clube.nome, formation=formacao, goals=gols)

    def classificacao(self) -> list[LinhaDeClassificacao]:
        linhas = {
            clube.id: LinhaDeClassificacao(club_id=clube.id, club_name=clube.nome)
            for clube in self._clubes.listar()
        }
        for partida in self._partidas.listar(FiltrosDePartida()):
            self._atualizar_linha(
                linhas[partida.mandante_id], partida.gols_mandante, partida.gols_visitante
            )
            self._atualizar_linha(
                linhas[partida.visitante_id], partida.gols_visitante, partida.gols_mandante
            )

        ordenadas = sorted(
            linhas.values(), key=lambda linha: normalizar_para_busca(linha.club_name)
        )
        ordenadas = sorted(ordenadas, key=lambda linha: linha.goals_for, reverse=True)
        ordenadas = sorted(ordenadas, key=lambda linha: linha.goal_difference, reverse=True)
        ordenadas = sorted(ordenadas, key=lambda linha: linha.points, reverse=True)
        for posicao, linha in enumerate(ordenadas, start=1):
            linha.position = posicao
        return ordenadas

    @staticmethod
    def _atualizar_linha(linha: LinhaDeClassificacao, gols_pro: int, gols_contra: int) -> None:
        linha.played += 1
        linha.goals_for += gols_pro
        linha.goals_against += gols_contra
        if gols_pro > gols_contra:
            linha.wins += 1
        elif gols_pro < gols_contra:
            linha.losses += 1
        else:
            linha.draws += 1

    def _obter_clube_ou_falhar(self, clube_id: int) -> Clube:
        clube = self._clubes.obter(clube_id)
        if clube is None:
            raise NaoEncontradoError("Clube não encontrado.")
        return clube

    def _elenco_ordenado(self, clube_id: int) -> list[Jogador]:
        elenco = self._jogadores.listar(FiltrosSql(club_id=clube_id))
        elenco = sorted(elenco, key=lambda jogador: jogador.id)
        elenco = sorted(elenco, key=lambda jogador: normalizar_para_busca(jogador.nome))
        elenco = sorted(elenco, key=lambda jogador: ORDEM_DAS_POSICOES.index(jogador.posicao))
        return elenco

    def _titulares_em_campo(self, clube: Clube) -> list[TitularEmCampo]:
        titulares_ids = set(self._escalacoes.listar_titulares_do_clube(clube.id))
        if len(titulares_ids) != TITULARES_POR_ESCALACAO:
            raise ConflitoError(f"O clube {clube.nome} não tem escalação completa.")

        elenco_ordenado = self._elenco_ordenado(clube.id)
        titulares = [jogador for jogador in elenco_ordenado if jogador.id in titulares_ids]
        return [
            TitularEmCampo(
                jogador_id=jogador.id,
                nome=jogador.nome,
                posicao=jogador.posicao,
                condicao=jogador.condicao,
                finalizacao=jogador.finalizacao,
                passe=jogador.passe,
                drible=jogador.drible,
                defesa=jogador.defesa,
            )
            for jogador in titulares
        ]

    def _gravar_duelo(self, partida_id: int, duelo: DueloCalculado) -> DueloPartida:
        registro = DueloPartida(
            partida_id=partida_id,
            ordem=duelo.ordem,
            clube_atacante_id=duelo.clube_atacante_id,
            atacante_id=duelo.atacante.jogador_id,
            defensor_id=duelo.defensor.jogador_id,
            nome_atacante=duelo.atacante.nome,
            nome_defensor=duelo.defensor.nome,
            posicao_atacante=duelo.atacante.posicao,
            posicao_defensor=duelo.defensor.posicao,
            condicao_atacante=duelo.atacante.condicao,
            condicao_defensor=duelo.defensor.condicao,
            atributo_ataque=duelo.atributo,
            atributo_defesa="defending",
            valor_ataque=duelo.valor_ataque,
            valor_defesa=duelo.valor_defesa,
            gol=duelo.gol,
        )
        self._partidas.adicionar_duelo(registro)
        return registro

    def _confirmar_ou_desfazer(self) -> None:
        try:
            self._uot.confirmar()
        except Exception:
            self._uot.desfazer()
            raise
