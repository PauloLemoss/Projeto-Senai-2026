from fastapi.testclient import TestClient

from mercado_jogadores.core.config import get_settings


def test_cors_libera_a_origem_configurada(client: TestClient) -> None:
    origem = get_settings().cors_origin

    resposta = client.get("/api/v1/players/1", headers={"Origin": origem})

    assert resposta.headers["access-control-allow-origin"] == origem


def test_cors_nao_libera_outra_origem(client: TestClient) -> None:
    resposta = client.get(
        "/api/v1/players/1", headers={"Origin": "http://origem-nao-autorizada.com"}
    )

    assert "access-control-allow-origin" not in resposta.headers
