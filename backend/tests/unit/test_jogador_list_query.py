from decimal import Decimal

import pytest
from pydantic import ValidationError

from mercado_jogadores.jogadores.schemas import JogadorListQuery


def test_todos_os_padroes() -> None:
    query = JogadorListQuery()
    assert query.sort == "name"
    assert query.page == 1
    assert query.limit == 10


def test_enum_em_minusculas_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(position="mei")


def test_inteiro_de_query_com_zero_a_esquerda_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(club_id="01")


def test_inteiro_de_query_valido() -> None:
    query = JogadorListQuery(club_id="5")
    assert query.club_id == 5


def test_search_vazio_e_recusado_por_tamanho_minimo() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(search="")


def test_search_com_um_caractere_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(search="a")


def test_decimal_de_query_valido() -> None:
    query = JogadorListQuery(min_value="10.5")
    assert query.min_value == Decimal("10.5")


def test_decimal_de_query_acima_do_limite_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(max_value="551")


def test_decimal_de_query_com_sinal_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(min_value="-5")


def test_min_age_acima_de_max_age_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(min_age="30", max_age="20")


def test_min_value_acima_de_max_value_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(min_value="100", max_value="50")


def test_free_true_com_club_id_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(free="true", club_id="1")


def test_free_false_com_club_id_e_aceito() -> None:
    query = JogadorListQuery(free="false", club_id="1")
    assert query.free is False
    assert query.club_id == 1


def test_free_com_valor_invalido_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(free="True")  # V5: caixa exata, "True" != "true"


def test_sort_com_dois_criterios_validos() -> None:
    query = JogadorListQuery(sort="value_asc,age_desc")
    assert query.sort == "value_asc,age_desc"
    assert query.para_filtros_de_listagem().sort == ["value_asc", "age_desc"]


def test_sort_repetindo_o_campo_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(sort="value_asc,value_desc")


def test_sort_com_tres_criterios_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(sort="name,age_asc,position")


def test_limit_acima_do_maximo_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(limit="51")


def test_page_zero_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(page="0")


def test_sort_com_token_fora_da_lista_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(sort="foo")


def test_sort_vazio_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(sort="")


def test_sort_explicitamente_nulo_usa_o_padrao() -> None:
    query = JogadorListQuery(sort=None)
    assert query.sort == "name"


def test_free_passado_como_booleano_direto() -> None:
    assert JogadorListQuery(free=True).free is True
    assert JogadorListQuery(free=False).free is False


def test_free_explicitamente_nulo_nao_filtra() -> None:
    assert JogadorListQuery(free=None).free is None


def test_inteiro_de_query_vazio_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(club_id="")


def test_inteiro_de_query_com_tipo_invalido_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(club_id=1.5)


def test_decimal_de_query_vazio_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(min_value="")


def test_decimal_de_query_com_tipo_invalido_e_recusado() -> None:
    with pytest.raises(ValidationError):
        JogadorListQuery(min_value=True)


def test_decimal_de_query_ja_decimal_e_aceito_sem_reprocessar() -> None:
    query = JogadorListQuery(min_value=Decimal("10.00"))
    assert query.min_value == Decimal("10.00")
