from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from mercado_jogadores.core.datas import formatar_datetime_rn01
from mercado_jogadores.core.validation import ID_MAXIMO
from mercado_jogadores.jogadores.schemas import (
    Condicao,
    InteiroDeQuery,
    InteiroEstrito,
    JogadorRead,
    Posicao,
)
from mercado_jogadores.liga.models import DueloPartida
from mercado_jogadores.liga.repository import FiltrosDePartida
from mercado_jogadores.liga.service import (
    DadosDeEscalacao,
    DadosDePartida,
    EscalacaoDoClube,
    LinhaDeClassificacao,
    ResultadoDaPartida,
)

Formacao = Literal["3-1", "2-2", "2-1-1", "1-2-1"]
Resultado = Literal["MANDANTE", "VISITANTE", "EMPATE"]
AtributoDeDuelo = Literal["shooting", "passing", "dribbling", "defending"]

IdDeJogador = Annotated[InteiroEstrito, Field(gt=0, le=ID_MAXIMO)]
TITULARES_POR_ESCALACAO = 5


class LineupUpdate(BaseModel):
    """RN19, "1. Campos aceitos" (`formation`/`player_ids` de `PUT /clubs/{id}/lineup`)."""

    model_config = ConfigDict(extra="ignore")

    formation: Formacao
    player_ids: list[IdDeJogador] = Field(
        min_length=TITULARES_POR_ESCALACAO, max_length=TITULARES_POR_ESCALACAO
    )

    @field_validator("player_ids")
    @classmethod
    def _sem_ids_repetidos(cls, v: list[int]) -> list[int]:
        if len(set(v)) != len(v):
            raise ValueError("player_ids não pode repetir ids.")
        return v

    def para_dados_de_escalacao(self) -> DadosDeEscalacao:
        return DadosDeEscalacao(formation=self.formation, player_ids=self.player_ids)


class LineupRead(BaseModel):
    """Formato de resposta de `PUT`/`GET /clubs/{id}/lineup` (2.4.1 do enunciado)."""

    club_id: int
    formation: Formacao | None
    complete: bool
    players: list[JogadorRead]

    @classmethod
    def a_partir_do_resultado(cls, resultado: EscalacaoDoClube) -> "LineupRead":
        return cls(
            club_id=resultado.clube.id,
            formation=resultado.formation,  # type: ignore[arg-type]
            complete=resultado.complete,
            players=[JogadorRead.a_partir_do_resultado(item) for item in resultado.titulares],
        )


class MatchCreate(BaseModel):
    """RN20, "1. Campos aceitos" (`home_club_id`/`away_club_id` de `POST /matches`)."""

    model_config = ConfigDict(extra="ignore")

    home_club_id: InteiroEstrito = Field(gt=0, le=ID_MAXIMO)
    away_club_id: InteiroEstrito = Field(gt=0, le=ID_MAXIMO)

    def para_dados_de_partida(self) -> DadosDePartida:
        return DadosDePartida(home_club_id=self.home_club_id, away_club_id=self.away_club_id)


class MatchSideRead(BaseModel):
    club_id: int
    club_name: str
    formation: str
    goals: int


class DuelPlayerRead(BaseModel):
    player_id: int
    player_name: str
    position: Posicao
    condition: Condicao
    attribute: AtributoDeDuelo
    value: int


class DuelRead(BaseModel):
    order: int
    attacking_club_id: int
    attacker: DuelPlayerRead
    defender: DuelPlayerRead
    goal: bool

    @classmethod
    def a_partir_do_duelo(cls, duelo: DueloPartida) -> "DuelRead":
        return cls(
            order=duelo.ordem,
            attacking_club_id=duelo.clube_atacante_id,
            attacker=DuelPlayerRead(
                player_id=duelo.atacante_id,
                player_name=duelo.nome_atacante,
                position=duelo.posicao_atacante,  # type: ignore[arg-type]
                condition=duelo.condicao_atacante,  # type: ignore[arg-type]
                attribute=duelo.atributo_ataque,  # type: ignore[arg-type]
                value=duelo.valor_ataque,
            ),
            defender=DuelPlayerRead(
                player_id=duelo.defensor_id,
                player_name=duelo.nome_defensor,
                position=duelo.posicao_defensor,  # type: ignore[arg-type]
                condition=duelo.condicao_defensor,  # type: ignore[arg-type]
                attribute=duelo.atributo_defesa,  # type: ignore[arg-type]
                value=duelo.valor_defesa,
            ),
            goal=duelo.gol,
        )


class MatchRead(BaseModel):
    """Formato de `GET /matches` (sem `duels`) — `MatchDetailRead` adiciona `duels` para
    `POST /matches` e `GET /matches/{id}` (2.4.2 do enunciado)."""

    id: int
    played_at: str
    home: MatchSideRead
    away: MatchSideRead
    result: Resultado

    @classmethod
    def a_partir_do_resultado(cls, resultado: ResultadoDaPartida) -> "MatchRead":
        return cls(
            id=resultado.id,
            played_at=formatar_datetime_rn01(resultado.jogada_em),
            home=MatchSideRead(
                club_id=resultado.mandante.club_id,
                club_name=resultado.mandante.club_name,
                formation=resultado.mandante.formation,
                goals=resultado.mandante.goals,
            ),
            away=MatchSideRead(
                club_id=resultado.visitante.club_id,
                club_name=resultado.visitante.club_name,
                formation=resultado.visitante.formation,
                goals=resultado.visitante.goals,
            ),
            result=resultado.result,  # type: ignore[arg-type]
        )


class MatchDetailRead(MatchRead):
    duels: list[DuelRead]

    @classmethod
    def a_partir_do_resultado(cls, resultado: ResultadoDaPartida) -> "MatchDetailRead":
        return cls(
            id=resultado.id,
            played_at=formatar_datetime_rn01(resultado.jogada_em),
            home=MatchSideRead(
                club_id=resultado.mandante.club_id,
                club_name=resultado.mandante.club_name,
                formation=resultado.mandante.formation,
                goals=resultado.mandante.goals,
            ),
            away=MatchSideRead(
                club_id=resultado.visitante.club_id,
                club_name=resultado.visitante.club_name,
                formation=resultado.visitante.formation,
                goals=resultado.visitante.goals,
            ),
            result=resultado.result,  # type: ignore[arg-type]
            duels=[DuelRead.a_partir_do_duelo(duelo) for duelo in resultado.duelos],
        )


class MatchListQuery(BaseModel):
    """`GET /matches`: filtro opcional `club_id` (RN21)."""

    model_config = ConfigDict(extra="ignore")

    club_id: InteiroDeQuery | None = Field(default=None, le=ID_MAXIMO)

    def para_filtros(self) -> FiltrosDePartida:
        return FiltrosDePartida(clube_id=self.club_id)


class StandingRead(BaseModel):
    position: int
    club_id: int
    club_name: str
    played: int
    wins: int
    draws: int
    losses: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int

    @classmethod
    def a_partir_da_linha(cls, linha: LinhaDeClassificacao) -> "StandingRead":
        return cls(
            position=linha.position,
            club_id=linha.club_id,
            club_name=linha.club_name,
            played=linha.played,
            wins=linha.wins,
            draws=linha.draws,
            losses=linha.losses,
            goals_for=linha.goals_for,
            goals_against=linha.goals_against,
            goal_difference=linha.goal_difference,
            points=linha.points,
        )
