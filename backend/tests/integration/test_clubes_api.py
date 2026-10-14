"""Testes de ponta a ponta via TestClient, cobrindo cada #### Scenario da spec `clubes`."""

from fastapi.testclient import TestClient

from mercado_jogadores.jogadores.models import Jogador

_JOGADOR_VALIDO = {
    "name": "Meia Lua",
    "position": "MEI",
    "agility": 85,
    "age": 25,
    "pace": 70,
    "shooting": 68,
    "passing": 82,
    "dribbling": 79,
    "defending": 55,
    "physical": 64,
    "potential": 86,
}


def _cadastrar_clube(client: TestClient, **sobrescritas: object) -> dict:
    corpo = {"name": "Águias FC", "acronym": "AGU", **sobrescritas}
    resposta = client.post("/api/v1/clubs", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _cadastrar_jogador(client: TestClient, **sobrescritas: object) -> dict:
    corpo = {**_JOGADOR_VALIDO, **sobrescritas}
    resposta = client.post("/api/v1/players", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _atribuir_a_um_clube(db_session, jogador_id: int, clube_id: int) -> None:
    db_session.query(Jogador).filter(Jogador.id == jogador_id).update({"clube_id": clube_id})
    db_session.commit()


def _primeiras_tres_letras(nome: str) -> str:
    letras = [c for c in nome.upper() if c.isalpha()]
    return "".join(letras[:3])


class TestCriacaoDeClube:
    def test_criacao_valida_responde_201_com_location_e_corpo_minimo(
        self, client: TestClient
    ) -> None:
        resposta = client.post("/api/v1/clubs", json={"name": "Águias FC", "acronym": "AGU"})

        assert resposta.status_code == 201
        assert resposta.headers["location"] == f"/api/v1/clubs/{resposta.json()['id']}"

        corpo = resposta.json()
        assert corpo["cash"] == 300.00
        assert corpo["squad_value"] == 0.00
        assert corpo["net_worth"] == 300.00

    def test_nome_duplicado_ignorando_caixa_e_recusado(self, client: TestClient) -> None:
        _cadastrar_clube(client, name="Águias FC", acronym="AGU")

        resposta = client.post(
            "/api/v1/clubs", json={"name": "  águias   fc ", "acronym": "AGU"}
        )

        assert resposta.status_code == 409
        assert resposta.json()["message"]

    def test_nome_com_acento_diferente_e_aceito(self, client: TestClient) -> None:
        _cadastrar_clube(client, name="Águias FC", acronym="AGU")

        resposta = client.post("/api/v1/clubs", json={"name": "Aguias FC", "acronym": "AGS"})

        assert resposta.status_code == 201

    def test_sigla_duplicada_e_recusada(self, client: TestClient) -> None:
        _cadastrar_clube(client, name="Águias FC", acronym="AGU")

        resposta = client.post(
            "/api/v1/clubs", json={"name": "Amigos United FC", "acronym": "AGU"}
        )

        assert resposta.status_code == 409
        assert resposta.json()["message"]

    def test_limite_de_20_clubes(self, client: TestClient) -> None:
        palavras = [
            "Alfa", "Beta", "Gama", "Delta", "Epsilon", "Zeta", "Eta", "Teta", "Iota", "Kapa",
            "Lambda", "Mu", "Nu", "Csi", "Omicron", "Pi", "Ro", "Sigma", "Tau", "Fi",
        ]
        for palavra in palavras:
            nome = f"{palavra} FC"
            _cadastrar_clube(client, name=nome, acronym=_primeiras_tres_letras(nome))

        resposta = client.post("/api/v1/clubs", json={"name": "Vita FC", "acronym": "VIT"})

        assert resposta.status_code == 409
        assert resposta.json()["message"]

    def test_nome_com_caractere_fora_do_permitido_e_recusado(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/clubs", json={"name": "Clube 10", "acronym": "CLU"})
        assert resposta.status_code == 400

    def test_nome_com_uma_palavra_so_e_recusado(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/clubs", json={"name": "Aguias", "acronym": "AGU"})
        assert resposta.status_code == 400

    def test_nome_com_mais_de_cinco_palavras_e_recusado(self, client: TestClient) -> None:
        resposta = client.post(
            "/api/v1/clubs", json={"name": "Um Dois Tres Quatro Cinco Seis", "acronym": "UDO"}
        )
        assert resposta.status_code == 400

    def test_sigla_fora_do_formato_basico_e_recusada(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/clubs", json={"name": "Águias FC", "acronym": "AG"})
        assert resposta.status_code == 400


class TestSiglaCorrespondeAoNome:
    def test_sigla_que_nao_comeca_pela_primeira_letra_e_recusada(
        self, client: TestClient
    ) -> None:
        resposta = client.post("/api/v1/clubs", json={"name": "Águias FC", "acronym": "GUI"})
        assert resposta.status_code == 400

    def test_sigla_com_as_tres_letras_iguais_e_recusada(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/clubs", json={"name": "Ana Ana Ana", "acronym": "AAA"})
        assert resposta.status_code == 400

    def test_sigla_fora_de_ordem_no_nome_e_recusada(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/clubs", json={"name": "Águias FC", "acronym": "AUG"})
        assert resposta.status_code == 400


class TestListagemDeClubes:
    def test_ordenacao_padrao_por_nome(self, client: TestClient) -> None:
        _cadastrar_clube(client, name="Zebras FC", acronym="ZEB")
        _cadastrar_clube(client, name="Águias FC", acronym="AGU")

        resposta = client.get("/api/v1/clubs")

        assert resposta.status_code == 200
        nomes = [c["name"] for c in resposta.json()]
        assert nomes == ["Águias FC", "Zebras FC"]

    def test_ordenacao_por_patrimonio_com_desempate(
        self, client: TestClient, db_session
    ) -> None:
        rico = _cadastrar_clube(client, name="Rico FC", acronym="RIC")
        _cadastrar_clube(client, name="Pobre FC", acronym="POB")

        jogador = _cadastrar_jogador(client)
        _atribuir_a_um_clube(db_session, jogador["id"], rico["id"])

        resposta = client.get("/api/v1/clubs?sort=net_worth_desc")

        assert resposta.status_code == 200
        nomes = [c["name"] for c in resposta.json()]
        assert nomes == ["Rico FC", "Pobre FC"]

    def test_valor_de_sort_invalido_e_recusado(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/clubs?sort=cash")
        assert resposta.status_code == 400


class TestConsultaDeClube:
    def test_clube_recem_criado_tem_elenco_vazio(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        resposta = client.get(f"/api/v1/clubs/{clube['id']}")

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["players"] == []
        assert corpo["squad_value"] == 0.00
        assert corpo["net_worth"] == corpo["cash"]

    def test_elenco_ordenado_por_posicao_depois_nome_depois_id(
        self, client: TestClient, db_session
    ) -> None:
        clube = _cadastrar_clube(client)

        meia = _cadastrar_jogador(client, name="Zeta Meia", position="MEI")
        atacante = _cadastrar_jogador(client, name="Ana Ataque", position="ATA")
        goleiro = _cadastrar_jogador(client, name="Beto Gol", position="GOL")

        for jogador in (meia, atacante, goleiro):
            _atribuir_a_um_clube(db_session, jogador["id"], clube["id"])

        resposta = client.get(f"/api/v1/clubs/{clube['id']}")

        nomes_em_ordem = [p["name"] for p in resposta.json()["players"]]
        assert nomes_em_ordem == ["Beto Gol", "Zeta Meia", "Ana Ataque"]

    def test_clube_inexistente_e_404(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/clubs/999999")

        assert resposta.status_code == 404
        assert resposta.json()["message"]
