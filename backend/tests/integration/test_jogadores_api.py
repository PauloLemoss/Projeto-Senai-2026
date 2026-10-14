"""Testes de ponta a ponta via TestClient, cobrindo cada #### Scenario das specs
`api-conventions` e `jogadores` desta change."""

from fastapi.testclient import TestClient

from mercado_jogadores.clubes.models import Clube
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


def _cadastrar(client: TestClient, **sobrescritas: object) -> dict:
    corpo = {**_JOGADOR_VALIDO, **sobrescritas}
    resposta = client.post("/api/v1/players", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _atribuir_a_um_clube(db_session, jogador_id: int) -> None:
    clube = Clube(nome="Clube Teste", nome_normalizado="clube teste", sigla="CLT")
    db_session.add(clube)
    db_session.commit()
    db_session.query(Jogador).filter(Jogador.id == jogador_id).update({"clube_id": clube.id})
    db_session.commit()


# ---------------------------------------------------------------------------
# api-conventions
# ---------------------------------------------------------------------------


class TestCorpoDeveSerObjetoJson:
    def test_corpo_e_um_array(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/players", json=[])
        assert resposta.status_code == 400
        assert resposta.json()["message"]

    def test_corpo_e_um_valor_simples(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/players", content='"x"', headers={"Content-Type": "application/json"})
        assert resposta.status_code == 400

    def test_json_malformado(self, client: TestClient) -> None:
        resposta = client.post(
            "/api/v1/players", content="{isso nao e json", headers={"Content-Type": "application/json"}
        )
        assert resposta.status_code == 400


class TestValoresDeListaExatos:
    def test_enum_em_minusculas_e_recusado(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/players", json={**_JOGADOR_VALIDO, "position": "mei"})
        assert resposta.status_code == 400


class TestCampoObrigatorio:
    def test_campo_ausente(self, client: TestClient) -> None:
        corpo = {k: v for k, v in _JOGADOR_VALIDO.items() if k != "age"}
        resposta = client.post("/api/v1/players", json=corpo)
        assert resposta.status_code == 400

    def test_campo_nulo(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/players", json={**_JOGADOR_VALIDO, "age": None})
        assert resposta.status_code == 400


class TestCamposControladosPeloSistemaIgnorados:
    def test_campo_calculado_enviado_e_ignorado(self, client: TestClient) -> None:
        jogador = _cadastrar(client, base_value=999999, condition="DOENTE", club_id=42)
        assert jogador["base_value"] != 999999
        assert jogador["condition"] == "APTO"
        assert jogador["club_id"] is None

    def test_nome_de_campo_fora_do_snake_case_e_tratado_como_inexistente(
        self, client: TestClient
    ) -> None:
        corpo = {k: v for k, v in _JOGADOR_VALIDO.items() if k != "age"}
        corpo["playerAge"] = 25  # nome fora do snake_case: ignorado, "age" continua ausente
        resposta = client.post("/api/v1/players", json=corpo)
        assert resposta.status_code == 400


class TestRecursoOuIdInexistente:
    def test_caminho_inexistente(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/rota-que-nao-existe")
        assert resposta.status_code == 404
        assert resposta.json()["message"]

    def test_id_na_url_em_formato_invalido(self, client: TestClient) -> None:
        for id_invalido in ("abc", "0", "-1", "1.5", "01"):
            resposta = client.get(f"/api/v1/players/{id_invalido}")
            assert resposta.status_code == 404, id_invalido

    def test_id_na_url_acima_do_limite(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/players/2147483648")
        assert resposta.status_code == 404


class TestCodigosDeErroPadronizados:
    def test_recusa_de_regra_de_negocio_responde_409_com_message(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        resposta = client.delete(f"/api/v1/players/{jogador['id']}")
        assert resposta.status_code == 204

        # excluir de novo (já excluído) -> 404, não 409: confere que os dois caminhos de erro
        # retornam o formato padronizado
        resposta_2 = client.delete(f"/api/v1/players/{jogador['id']}")
        assert resposta_2.status_code == 404
        assert resposta_2.json()["message"]

    def test_nenhuma_informacao_de_implementacao_vaza_na_recusa(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/players", json=[])
        corpo = resposta.json()
        assert "traceback" not in str(corpo).lower()
        assert set(corpo.keys()) == {"message"} or "message" in corpo


class TestCriacaoResponde201ComLocation:
    def test_criacao_bem_sucedida(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/players", json=_JOGADOR_VALIDO)
        assert resposta.status_code == 201
        assert resposta.headers["location"] == f"/api/v1/players/{resposta.json()['id']}"
        assert "application/json" in resposta.headers["content-type"]


# ---------------------------------------------------------------------------
# jogadores
# ---------------------------------------------------------------------------


class TestCadastroCalculaEGravaOValorBase:
    def test_cadastro_sem_jovem_promessa(self, client: TestClient) -> None:
        jogador = _cadastrar(client)  # overall 75, potential 86, idade 25 -> 40.00
        assert jogador["base_value"] == 40.00


class TestJogadorNasceLivreEApto:
    def test_cadastro_basico(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        assert jogador["condition"] == "APTO"
        assert jogador["club_id"] is None


class TestConsultaCalculaOverallEValorDeMercado:
    def test_jogador_apto_sem_ajuste_de_idade(self, client: TestClient) -> None:
        # Linha do GOL na tabela de exemplo do RN06: overall 68. APTO + idade 25 (22-31) -> sem
        # desconto nem ajuste, então o valor de mercado deve ser igual ao valor base.
        jogador = _cadastrar(
            client,
            name="Goleiro Teste",
            position="GOL",
            pace=55,
            shooting=30,
            passing=65,
            dribbling=40,
            defending=72,
            physical=68,
            potential=72,
            age=25,
            agility=50,
        )
        resposta = client.get(f"/api/v1/players/{jogador['id']}")
        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["overall"] == 68
        assert corpo["market_value"] == jogador["base_value"]

    def test_desconto_reduzido_pela_metade_por_alta_agilidade(self, client: TestClient) -> None:
        jogador = _cadastrar(client, agility=80)
        client.patch(f"/api/v1/players/{jogador['id']}/condition", json={"condition": "MAL_CONDICIONADO"})

        resposta = client.get(f"/api/v1/players/{jogador['id']}")
        # valor_base 40.00, MAL_CONDICIONADO + agilidade 80 (desconto/2=7.5%), idade 25 (0%)
        assert resposta.json()["market_value"] == 37.00


class TestEdicaoAlteraSoNomePosicaoAgilidadeEIdade:
    def test_edicao_valida_nao_muda_indicadores_nem_valor_base(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        resposta = client.put(
            f"/api/v1/players/{jogador['id']}",
            json={"name": "Meia Lua", "position": "MEI", "agility": 90, "age": 25},
        )
        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["agility"] == 90
        assert corpo["base_value"] == jogador["base_value"]
        assert corpo["potential"] == jogador["potential"]

    def test_mudanca_de_posicao_de_jogador_com_clube_e_recusada(self, client: TestClient, db_session) -> None:
        jogador = _cadastrar(client)
        _atribuir_a_um_clube(db_session, jogador["id"])

        resposta = client.put(
            f"/api/v1/players/{jogador['id']}",
            json={"name": "Meia Lua", "position": "ATA", "agility": 85, "age": 25},
        )
        assert resposta.status_code == 409
        assert resposta.json()["message"]

    def test_reducao_de_idade_e_recusada(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        resposta = client.put(
            f"/api/v1/players/{jogador['id']}",
            json={"name": "Meia Lua", "position": "MEI", "agility": 85, "age": 24},
        )
        assert resposta.status_code == 409


class TestAlteracaoDeCondicaoMaquinaDeEstados:
    def test_transicao_direta_de_doente_para_apto_e_recusada(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        client.patch(f"/api/v1/players/{jogador['id']}/condition", json={"condition": "DOENTE"})

        resposta = client.patch(
            f"/api/v1/players/{jogador['id']}/condition", json={"condition": "APTO"}
        )
        assert resposta.status_code == 409

    def test_enviar_a_condicao_atual_e_aceito_sem_mudanca(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        resposta = client.patch(
            f"/api/v1/players/{jogador['id']}/condition", json={"condition": "APTO"}
        )
        assert resposta.status_code == 200
        assert resposta.json()["condition"] == "APTO"

    def test_condicao_fora_da_lista_e_recusada(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        resposta = client.patch(
            f"/api/v1/players/{jogador['id']}/condition", json={"condition": "LESIONADO"}
        )
        assert resposta.status_code == 400


class TestExclusaoLogicaDeJogadorLivre:
    def test_exclusao_de_jogador_livre(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        resposta = client.delete(f"/api/v1/players/{jogador['id']}")
        assert resposta.status_code == 204
        assert resposta.content == b""

    def test_exclusao_de_jogador_com_clube_e_recusada(self, client: TestClient, db_session) -> None:
        jogador = _cadastrar(client)
        _atribuir_a_um_clube(db_session, jogador["id"])

        resposta = client.delete(f"/api/v1/players/{jogador['id']}")
        assert resposta.status_code == 409

    def test_jogador_excluido_conta_como_inexistente(self, client: TestClient) -> None:
        jogador = _cadastrar(client)
        client.delete(f"/api/v1/players/{jogador['id']}")

        assert client.get(f"/api/v1/players/{jogador['id']}").status_code == 404
        assert (
            client.put(
                f"/api/v1/players/{jogador['id']}",
                json={"name": "X Y", "position": "MEI", "agility": 50, "age": 25},
            ).status_code
            == 404
        )
        assert (
            client.patch(
                f"/api/v1/players/{jogador['id']}/condition", json={"condition": "DOENTE"}
            ).status_code
            == 404
        )
        assert client.delete(f"/api/v1/players/{jogador['id']}").status_code == 404
