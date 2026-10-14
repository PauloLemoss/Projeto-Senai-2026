import pytest
from pydantic import ValidationError

from mercado_jogadores.liga.schemas import LineupUpdate, MatchCreate


class TestLineupUpdate:
    def test_requisicao_valida_e_aceita(self) -> None:
        dados = LineupUpdate(formation="2-1-1", player_ids=[1, 2, 3, 4, 5])
        assert dados.player_ids == [1, 2, 3, 4, 5]

    def test_formation_fora_da_lista_e_recusada(self) -> None:
        with pytest.raises(ValidationError):
            LineupUpdate(formation="4-4-2", player_ids=[1, 2, 3, 4, 5])

    def test_player_ids_com_tamanho_diferente_de_5_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            LineupUpdate(formation="2-1-1", player_ids=[1, 2, 3, 4])
        with pytest.raises(ValidationError):
            LineupUpdate(formation="2-1-1", player_ids=[1, 2, 3, 4, 5, 6])

    def test_player_ids_com_ids_repetidos_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            LineupUpdate(formation="2-1-1", player_ids=[1, 2, 3, 4, 4])

    def test_player_ids_que_nao_e_lista_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            LineupUpdate(formation="2-1-1", player_ids="1,2,3,4,5")

    def test_player_id_nao_positivo_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            LineupUpdate(formation="2-1-1", player_ids=[0, 2, 3, 4, 5])
        with pytest.raises(ValidationError):
            LineupUpdate(formation="2-1-1", player_ids=[-1, 2, 3, 4, 5])

    def test_player_id_que_nao_e_inteiro_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            LineupUpdate(formation="2-1-1", player_ids=[1, 2, 3, 4, "5"])
        with pytest.raises(ValidationError):
            LineupUpdate(formation="2-1-1", player_ids=[1, 2, 3, 4, 5.5])


class TestMatchCreate:
    def test_requisicao_valida_e_aceita(self) -> None:
        dados = MatchCreate(home_club_id=1, away_club_id=2)
        assert (dados.home_club_id, dados.away_club_id) == (1, 2)

    def test_home_club_id_zero_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            MatchCreate(home_club_id=0, away_club_id=2)

    def test_home_club_id_negativo_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            MatchCreate(home_club_id=-1, away_club_id=2)

    def test_away_club_id_zero_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            MatchCreate(home_club_id=1, away_club_id=0)

    def test_away_club_id_negativo_e_recusado(self) -> None:
        with pytest.raises(ValidationError):
            MatchCreate(home_club_id=1, away_club_id=-2)
