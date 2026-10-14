from decimal import Decimal

import pytest

from mercado_jogadores.liga.calculos import (
    TitularEmCampo,
    aplicar_efeito_de_condicao,
    arredondar_inteiro,
    calcular_placar_e_resultado,
    formacao_fecha_com_as_posicoes,
    montar_duelos,
    resultado_por_placar,
)


class TestFormacaoFechaComAsPosicoes:
    @pytest.mark.parametrize(
        "formation, posicoes",
        [
            ("3-1", ["GOL", "ZAG", "LAT", "LAT", "ATA"]),
            ("2-2", ["GOL", "ZAG", "LAT", "ATA", "ATA"]),
            ("2-1-1", ["GOL", "ZAG", "LAT", "MEI", "ATA"]),
            ("1-2-1", ["GOL", "ZAG", "MEI", "MEI", "ATA"]),
        ],
    )
    def test_exemplos_de_escalacao_da_rn19_fecham_a_formacao(
        self, formation: str, posicoes: list[str]
    ) -> None:
        assert formacao_fecha_com_as_posicoes(formation, posicoes) is True

    def test_goleiro_a_mais_e_recusado(self) -> None:
        # 2-1-1 com 2 goleiros em vez de 1
        assert formacao_fecha_com_as_posicoes("2-1-1", ["GOL", "GOL", "LAT", "MEI", "ATA"]) is False

    def test_sem_goleiro_e_recusado(self) -> None:
        assert formacao_fecha_com_as_posicoes("2-1-1", ["ZAG", "ZAG", "LAT", "MEI", "ATA"]) is False

    def test_setor_a_mais_e_recusado(self) -> None:
        # 2-1-1 pede 1 MEI; aqui vêm 2 MEI e falta 1 de defesa
        assert formacao_fecha_com_as_posicoes("2-1-1", ["GOL", "ZAG", "MEI", "MEI", "ATA"]) is False

    def test_setor_a_menos_e_recusado(self) -> None:
        # 3-1 pede 3 de defesa; aqui vem só 2
        assert formacao_fecha_com_as_posicoes("3-1", ["GOL", "ZAG", "LAT", "MEI", "ATA"]) is False


class TestArredondarInteiro:
    def test_exemplos_do_enunciado(self) -> None:
        assert arredondar_inteiro(Decimal("62.9")) == 63
        assert arredondar_inteiro(Decimal("42.5")) == 43


class TestAplicarEfeitoDeCondicao:
    def test_mal_condicionado_74_vira_63(self) -> None:
        assert aplicar_efeito_de_condicao(74, "MAL_CONDICIONADO") == 63

    def test_mal_condicionado_50_vira_43(self) -> None:
        assert aplicar_efeito_de_condicao(50, "MAL_CONDICIONADO") == 43

    def test_apto_nao_muda_o_atributo(self) -> None:
        assert aplicar_efeito_de_condicao(74, "APTO") == 74


def _titular(**sobrescritas: object) -> TitularEmCampo:
    base = {
        "jogador_id": 0,
        "nome": "",
        "posicao": "GOL",
        "condicao": "APTO",
        "finalizacao": 0,
        "passe": 0,
        "drible": 0,
        "defesa": 0,
    }
    base.update(sobrescritas)
    return TitularEmCampo(**base)


class TestMontarDuelosECalcularPlacar:
    """Reproduz de ponta a ponta o exemplo da RN20: Águias FC (mandante) × Delta FC (visitante),
    os dois no 2-1-1, com o LAT do Águias FC MAL_CONDICIONADO."""

    def _titulares_aguias(self) -> list[TitularEmCampo]:
        return [
            _titular(jogador_id=30, nome="Rui Prado", posicao="GOL", defesa=77),
            _titular(jogador_id=32, nome="Téo Brandão", posicao="ZAG", defesa=84),
            _titular(
                jogador_id=31,
                nome="Davi Lins",
                posicao="LAT",
                condicao="MAL_CONDICIONADO",
                drible=74,
                defesa=66,
            ),
            _titular(jogador_id=33, nome="Lauro Neves", posicao="MEI", passe=82),
            _titular(jogador_id=34, nome="Otto Rangel", posicao="ATA", finalizacao=75),
        ]

    def _titulares_delta(self) -> list[TitularEmCampo]:
        return [
            _titular(jogador_id=40, nome="Ivo Teles", posicao="GOL", defesa=72),
            _titular(jogador_id=41, nome="Hugo Vaz", posicao="ZAG", defesa=84),
            _titular(jogador_id=42, nome="Lino Matos", posicao="LAT", drible=79, defesa=63),
            _titular(jogador_id=43, nome="Nei Soares", posicao="MEI", passe=70),
            _titular(jogador_id=44, nome="Ugo Falcão", posicao="ATA", finalizacao=81),
        ]

    def test_os_6_duelos_batem_com_a_tabela_do_exemplo(self) -> None:
        duelos = montar_duelos(1, self._titulares_aguias(), 2, self._titulares_delta())

        assert len(duelos) == 6
        resultado = [
            (
                d.ordem,
                d.clube_atacante_id,
                d.atacante.nome,
                d.valor_ataque,
                d.defensor.nome,
                d.valor_defesa,
                d.gol,
            )
            for d in duelos
        ]
        assert resultado == [
            (1, 1, "Otto Rangel", 75, "Ivo Teles", 72, True),
            (2, 1, "Lauro Neves", 82, "Hugo Vaz", 84, False),
            (3, 1, "Davi Lins", 63, "Lino Matos", 63, False),
            (4, 2, "Ugo Falcão", 81, "Rui Prado", 77, True),
            (5, 2, "Nei Soares", 70, "Téo Brandão", 84, False),
            (6, 2, "Lino Matos", 79, "Davi Lins", 56, True),
        ]

    def test_placar_e_resultado_batem_com_o_exemplo(self) -> None:
        duelos = montar_duelos(1, self._titulares_aguias(), 2, self._titulares_delta())

        gols_mandante, gols_visitante, resultado = calcular_placar_e_resultado(duelos)

        assert (gols_mandante, gols_visitante, resultado) == (1, 2, "VISITANTE")


class TestResultadoPorPlacar:
    def test_mandante_com_mais_gols(self) -> None:
        assert resultado_por_placar(2, 1) == "MANDANTE"

    def test_visitante_com_mais_gols(self) -> None:
        assert resultado_por_placar(1, 2) == "VISITANTE"

    def test_empate(self) -> None:
        assert resultado_por_placar(1, 1) == "EMPATE"
