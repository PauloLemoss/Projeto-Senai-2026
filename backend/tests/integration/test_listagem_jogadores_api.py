"""Testes de ponta a ponta de GET /players (RN07), contra o Postgres real."""

from fastapi.testclient import TestClient

_NOMES = ["Alfa", "Beta", "Gama", "Delta", "Epsilon", "Zeta", "Eta", "Theta"]

_JOGADOR_BASE = {
    "position": "MEI",
    "agility": 70,
    "age": 25,
    "pace": 60,
    "shooting": 60,
    "passing": 60,
    "dribbling": 60,
    "defending": 60,
    "physical": 60,
    "potential": 70,
}


def _cadastrar(client: TestClient, nome: str, **sobrescritas: object) -> dict:
    corpo = {**_JOGADOR_BASE, "name": nome, **sobrescritas}
    resposta = client.post("/api/v1/players", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


class TestListagemPaginadaBuscaEFiltros:
    def test_lista_vazia(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players")
        assert resposta.status_code == 200
        assert resposta.json() == {
            "data": [],
            "meta": {"page": 1, "limit": 10, "total_items": 0, "total_pages": 0},
        }

    def test_busca_ignora_acentos_e_caixa(self, client: TestClient) -> None:
        _cadastrar(client, "João Silva")
        _cadastrar(client, "Pedro Alves")

        resposta = client.get("/api/v1/players?search=joao")

        corpo = resposta.json()
        assert resposta.status_code == 200
        assert len(corpo["data"]) == 1
        assert corpo["data"][0]["name"] == "João Silva"

    def test_paginacao_intermediaria(self, client: TestClient) -> None:
        for i in range(23):
            _cadastrar(client, f"Jogador Numero {_NOMES[i % len(_NOMES)]}")

        resposta = client.get("/api/v1/players?limit=10&page=1")
        corpo = resposta.json()

        assert resposta.status_code == 200
        assert len(corpo["data"]) == 10
        assert corpo["meta"] == {"page": 1, "limit": 10, "total_items": 23, "total_pages": 3}

    def test_pagina_alem_da_ultima(self, client: TestClient) -> None:
        for i in range(5):
            _cadastrar(client, f"Jogador Numero {_NOMES[i % len(_NOMES)]}")

        resposta = client.get("/api/v1/players?limit=10&page=4")
        corpo = resposta.json()

        assert resposta.status_code == 200
        assert corpo["data"] == []
        assert corpo["meta"]["total_items"] == 5

    def test_filtro_por_posicao(self, client: TestClient) -> None:
        _cadastrar(client, "Jogador Mei", position="MEI")
        _cadastrar(client, "Jogador Ata", position="ATA")

        resposta = client.get("/api/v1/players?position=ATA")
        corpo = resposta.json()

        assert len(corpo["data"]) == 1
        assert corpo["data"][0]["position"] == "ATA"

    def test_filtro_por_valor_usa_market_value(self, client: TestClient) -> None:
        jogador = _cadastrar(client, "Jogador Jovem", age=20)  # idade <=21 -> +10% no valor
        valor_base = jogador["base_value"]

        resposta = client.get(f"/api/v1/players?min_value={valor_base + 0.01}")

        assert resposta.status_code == 200
        assert len(resposta.json()["data"]) == 1


class TestOrdenacao:
    def test_ordenacao_por_posicao_usa_ordem_fixa(self, client: TestClient) -> None:
        _cadastrar(client, "Jogador Zagueiro", position="ZAG")
        _cadastrar(client, "Jogador Atacante", position="ATA")
        _cadastrar(client, "Jogador Goleiro", position="GOL")

        resposta = client.get("/api/v1/players?sort=position")
        posicoes = [item["position"] for item in resposta.json()["data"]]

        assert posicoes == ["GOL", "ZAG", "ATA"]


class TestValidacaoDeParametros:
    def test_enum_em_minusculas_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?position=mei")
        assert resposta.status_code == 400
        assert resposta.json()["message"]

    def test_min_age_maior_que_max_age_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?min_age=30&max_age=20")
        assert resposta.status_code == 400

    def test_min_value_maior_que_max_value_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?min_value=100&max_value=50")
        assert resposta.status_code == 400

    def test_free_true_com_club_id_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?free=true&club_id=1")
        assert resposta.status_code == 400

    def test_sort_repetindo_campo_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?sort=value_asc,value_desc")
        assert resposta.status_code == 400

    def test_search_com_um_caractere_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?search=a")
        assert resposta.status_code == 400

    def test_limit_acima_do_maximo_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?limit=51")
        assert resposta.status_code == 400

    def test_id_com_zero_a_esquerda_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?club_id=01")
        assert resposta.status_code == 400

    def test_club_id_inexistente_e_recusado_com_404(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players?club_id=999999")
        assert resposta.status_code == 404
        assert resposta.json()["message"]
