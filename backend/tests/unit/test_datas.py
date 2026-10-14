from datetime import UTC, datetime

import pytest

from mercado_jogadores.core.datas import (
    FUSO_BRASILIA,
    formatar_datetime_rn01,
    parsear_datetime_rn01,
)


class TestParsearDatetimeRn01:
    def test_formato_de_entrada_valido_e_aceito(self) -> None:
        resultado = parsear_datetime_rn01("2027-03-02T10:15-03:00")

        assert resultado == datetime(2027, 3, 2, 10, 15, tzinfo=FUSO_BRASILIA)

    @pytest.mark.parametrize(
        "texto",
        [
            "2027-03-02T10:15",
            "2027-03-02T10:15+00:00",
            "2027-03-02T10:15Z",
            "02/03/2027 10:15",
            "2027-03-02T10:15:00-03:00",
        ],
    )
    def test_entrada_sem_o_offset_correto_e_recusada(self, texto: str) -> None:
        with pytest.raises(ValueError):
            parsear_datetime_rn01(texto)

    def test_data_inexistente_e_recusada(self) -> None:
        with pytest.raises(ValueError):
            parsear_datetime_rn01("2027-02-30T10:15-03:00")

    def test_hora_inexistente_e_recusada(self) -> None:
        with pytest.raises(ValueError):
            parsear_datetime_rn01("2027-03-02T24:00-03:00")


class TestFormatarDatetimeRn01:
    def test_resposta_traz_o_formato_com_segundos(self) -> None:
        momento = datetime(2027, 3, 2, 10, 15, 0, tzinfo=FUSO_BRASILIA)

        assert formatar_datetime_rn01(momento) == "2027-03-02T10:15:00-03:00"

    def test_converte_de_outro_fuso_para_brasilia(self) -> None:
        momento_utc = datetime(2027, 3, 2, 13, 15, 0, tzinfo=UTC)

        assert formatar_datetime_rn01(momento_utc) == "2027-03-02T10:15:00-03:00"
