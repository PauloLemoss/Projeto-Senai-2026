from mercado_jogadores.clubes.validacao import sigla_corresponde_ao_nome


class TestSiglaCorrespondeAoNome:
    def test_sigla_valida_e_aceita(self) -> None:
        assert sigla_corresponde_ao_nome("Águias FC", "AGU") is True

    def test_sigla_que_nao_comeca_pela_primeira_letra_e_recusada(self) -> None:
        assert sigla_corresponde_ao_nome("Águias FC", "GUI") is False

    def test_sigla_com_tres_letras_iguais_e_recusada(self) -> None:
        assert sigla_corresponde_ao_nome("Ana Ana Ana", "AAA") is False

    def test_sigla_fora_de_ordem_no_nome_e_recusada(self) -> None:
        assert sigla_corresponde_ao_nome("Águias FC", "AUG") is False
