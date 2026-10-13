import pytest

from mercado_jogadores.core.errors import NaoEncontradoError
from mercado_jogadores.core.validation import normalizar_texto, validar_id_da_url


class TestNormalizarTexto:
    def test_espacos_redundantes_sao_normalizados(self) -> None:
        assert normalizar_texto("  Meia   Zeta ") == "Meia Zeta"

    def test_caractere_de_controle_e_recusado(self) -> None:
        with pytest.raises(ValueError):
            normalizar_texto("Meia\tZeta")

    def test_quebra_de_linha_e_recusada(self) -> None:
        with pytest.raises(ValueError):
            normalizar_texto("Meia\nZeta")


class TestValidarIdDaUrl:
    @pytest.mark.parametrize("valor", ["abc", "0", "-1", "1.5", "01", "2147483648"])
    def test_formatos_invalidos_contam_como_inexistente(self, valor: str) -> None:
        with pytest.raises(NaoEncontradoError):
            validar_id_da_url(valor)

    def test_id_valido_e_convertido_para_inteiro(self) -> None:
        assert validar_id_da_url("42") == 42

    def test_limite_maximo_e_aceito(self) -> None:
        assert validar_id_da_url("2147483647") == 2_147_483_647
