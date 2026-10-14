"""Testes de ponta a ponta via TestClient, cobrindo cada #### Scenario da spec `liga`."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient

from mercado_jogadores.core.datas import FUSO_BRASILIA

_JOGADOR_FRACO = {
    "name": "Jogador Fraco",
    "position": "MEI",
    "agility": 50,
    "age": 25,
    "pace": 20,
    "shooting": 20,
    "passing": 20,
    "dribbling": 20,
    "defending": 20,
    "physical": 20,
    "potential": 20,
}

_TITULARES_2_1_1 = [
    ("Rui Prado", "GOL"),
    ("Téo Brandão", "ZAG"),
    ("Davi Lins", "LAT"),
    ("Lauro Neves", "MEI"),
    ("Otto Rangel", "ATA"),
]


def _cadastrar_jogador(client: TestClient, **sobrescritas: object) -> dict:
    corpo = {**_JOGADOR_FRACO, **sobrescritas}
    resposta = client.post("/api/v1/players", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _cadastrar_clube(client: TestClient, **sobrescritas: object) -> dict:
    corpo = {"name": "Águias FC", "acronym": "AGU", **sobrescritas}
    resposta = client.post("/api/v1/clubs", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _loyalty_until_daqui_a(dias: int) -> str:
    momento = datetime.now(FUSO_BRASILIA) + timedelta(days=dias)
    return momento.strftime("%Y-%m-%dT%H:%M") + "-03:00"


def _comprar(client: TestClient, jogador_id: int, club_id: int) -> None:
    corpo = {"club_id": club_id, "loyalty_until": _loyalty_until_daqui_a(365)}
    resposta = client.post(f"/api/v1/players/{jogador_id}/buy", json=corpo)
    assert resposta.status_code == 200, resposta.text


def _jogador_do_exemplo(nome: str, posicao: str, **atributos: int) -> dict:
    base = {
        "pace": 50,
        "shooting": 50,
        "passing": 50,
        "dribbling": 50,
        "defending": 50,
        "physical": 50,
    }
    base.update(atributos)
    return {
        "name": nome,
        "position": posicao,
        "agility": 70,
        "age": 25,
        "potential": max(base.values()),
        **base,
    }


_ROSTER_AGUIAS = [
    _jogador_do_exemplo("Rui Prado", "GOL", defending=77),
    _jogador_do_exemplo("Téo Brandão", "ZAG", defending=84),
    _jogador_do_exemplo("Davi Lins", "LAT", dribbling=74, defending=66),
    _jogador_do_exemplo("Lauro Neves", "MEI", passing=82),
    _jogador_do_exemplo("Otto Rangel", "ATA", shooting=75),
]
_ROSTER_DELTA = [
    _jogador_do_exemplo("Ivo Teles", "GOL", defending=72),
    _jogador_do_exemplo("Hugo Vaz", "ZAG", defending=84),
    _jogador_do_exemplo("Lino Matos", "LAT", dribbling=79, defending=63),
    _jogador_do_exemplo("Nei Soares", "MEI", passing=70),
    _jogador_do_exemplo("Ugo Falcão", "ATA", shooting=81),
]


def _escalar_roster(
    client: TestClient, nome_do_clube: str, acronimo: str, roster: list[dict]
) -> tuple[dict, list[dict]]:
    """Cadastra um clube e o `roster` dado (RN20), compra todos para o clube e escala no
    `2-1-1`. Devolve o clube e os jogadores cadastrados, na ordem do `roster`."""
    clube = _cadastrar_clube(client, name=nome_do_clube, acronym=acronimo)
    jogadores = []
    for corpo in roster:
        resposta = client.post("/api/v1/players", json=corpo)
        assert resposta.status_code == 201, resposta.text
        jogador = resposta.json()
        _comprar(client, jogador["id"], clube["id"])
        jogadores.append(jogador)

    resposta = client.put(
        f"/api/v1/clubs/{clube['id']}/lineup",
        json={"formation": "2-1-1", "player_ids": [j["id"] for j in jogadores]},
    )
    assert resposta.status_code == 200, resposta.text
    return clube, jogadores


def _escalar_clube_2_1_1(
    client: TestClient, nome_do_clube: str, acronimo: str
) -> tuple[dict, list[dict]]:
    """Cadastra um clube e 5 titulares (GOL, ZAG, LAT, MEI, ATA), compra todos para o clube e
    escala no `2-1-1`. Devolve o clube e os jogadores cadastrados, na ordem dos titulares."""
    clube = _cadastrar_clube(client, name=nome_do_clube, acronym=acronimo)
    jogadores = []
    for nome, posicao in _TITULARES_2_1_1:
        jogador = _cadastrar_jogador(client, name=nome, position=posicao)
        _comprar(client, jogador["id"], clube["id"])
        jogadores.append(jogador)

    resposta = client.put(
        f"/api/v1/clubs/{clube['id']}/lineup",
        json={"formation": "2-1-1", "player_ids": [j["id"] for j in jogadores]},
    )
    assert resposta.status_code == 200, resposta.text
    return clube, jogadores


class TestEscalacao:
    def test_escalacao_feliz_bate_com_o_exemplo_2_4_1_do_enunciado(
        self, client: TestClient
    ) -> None:
        clube = _cadastrar_clube(client)
        jogadores = []
        for nome, posicao in _TITULARES_2_1_1:
            jogador = _cadastrar_jogador(client, name=nome, position=posicao)
            _comprar(client, jogador["id"], clube["id"])
            jogadores.append(jogador)

        resposta = client.put(
            f"/api/v1/clubs/{clube['id']}/lineup",
            json={"formation": "2-1-1", "player_ids": [j["id"] for j in jogadores]},
        )

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["club_id"] == clube["id"]
        assert corpo["formation"] == "2-1-1"
        assert corpo["complete"] is True
        assert [p["id"] for p in corpo["players"]] == [j["id"] for j in jogadores]
        assert [p["position"] for p in corpo["players"]] == ["GOL", "ZAG", "LAT", "MEI", "ATA"]
        for jogador in corpo["players"]:
            assert jogador["condition"] == "APTO"

    def test_jogador_fora_do_elenco_do_clube_e_recusado(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)
        jogadores = []
        for nome, posicao in _TITULARES_2_1_1[:4]:
            jogador = _cadastrar_jogador(client, name=nome, position=posicao)
            _comprar(client, jogador["id"], clube["id"])
            jogadores.append(jogador)
        jogador_livre = _cadastrar_jogador(client, name="Jogador Livre", position="ATA")

        resposta = client.put(
            f"/api/v1/clubs/{clube['id']}/lineup",
            json={
                "formation": "2-1-1",
                "player_ids": [j["id"] for j in jogadores] + [jogador_livre["id"]],
            },
        )

        assert resposta.status_code == 409, resposta.text
        assert "message" in resposta.json()

    def test_jogador_doente_e_recusado(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)
        jogadores = []
        for nome, posicao in _TITULARES_2_1_1:
            jogador = _cadastrar_jogador(client, name=nome, position=posicao)
            _comprar(client, jogador["id"], clube["id"])
            jogadores.append(jogador)
        resposta_condicao = client.patch(
            f"/api/v1/players/{jogadores[-1]['id']}/condition", json={"condition": "DOENTE"}
        )
        assert resposta_condicao.status_code == 200, resposta_condicao.text

        resposta = client.put(
            f"/api/v1/clubs/{clube['id']}/lineup",
            json={"formation": "2-1-1", "player_ids": [j["id"] for j in jogadores]},
        )

        assert resposta.status_code == 409, resposta.text

    def test_posicoes_que_nao_fecham_a_formacao_sao_recusadas(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)
        jogadores = []
        for nome, posicao in [
            ("Jogador Um", "GOL"),
            ("Jogador Dois", "GOL"),
            ("Jogador Tres", "ZAG"),
            ("Jogador Quatro", "LAT"),
            ("Jogador Cinco", "ATA"),
        ]:
            jogador = _cadastrar_jogador(client, name=nome, position=posicao)
            _comprar(client, jogador["id"], clube["id"])
            jogadores.append(jogador)

        resposta = client.put(
            f"/api/v1/clubs/{clube['id']}/lineup",
            json={"formation": "2-1-1", "player_ids": [j["id"] for j in jogadores]},
        )

        assert resposta.status_code == 409, resposta.text

    def test_formation_fora_da_lista_e_recusada(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        resposta = client.put(
            f"/api/v1/clubs/{clube['id']}/lineup",
            json={"formation": "4-4-2", "player_ids": [1, 2, 3, 4, 5]},
        )

        assert resposta.status_code == 400, resposta.text

    def test_player_ids_fora_do_formato_e_recusado(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        resposta = client.put(
            f"/api/v1/clubs/{clube['id']}/lineup",
            json={"formation": "2-1-1", "player_ids": [1, 2, 3, 4]},
        )

        assert resposta.status_code == 400, resposta.text

    def test_clube_inexistente_e_recusado(self, client: TestClient) -> None:
        resposta = client.put(
            "/api/v1/clubs/999999/lineup",
            json={"formation": "2-1-1", "player_ids": [1, 2, 3, 4, 5]},
        )

        assert resposta.status_code == 404, resposta.text

    def test_jogador_inexistente_e_recusado(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)
        jogadores = []
        for nome, posicao in _TITULARES_2_1_1[:4]:
            jogador = _cadastrar_jogador(client, name=nome, position=posicao)
            _comprar(client, jogador["id"], clube["id"])
            jogadores.append(jogador)

        resposta = client.put(
            f"/api/v1/clubs/{clube['id']}/lineup",
            json={"formation": "2-1-1", "player_ids": [j["id"] for j in jogadores] + [999999]},
        )

        assert resposta.status_code == 404, resposta.text


class TestConsultarEscalacao:
    def test_clube_sem_escalacao(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/lineup")

        assert resposta.status_code == 200, resposta.text
        assert resposta.json() == {
            "club_id": clube["id"],
            "formation": None,
            "complete": False,
            "players": [],
        }

    def test_clube_com_escalacao_completa(self, client: TestClient) -> None:
        clube, _jogadores = _escalar_clube_2_1_1(client, "Delta FC", "DEL")

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/lineup")

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["complete"] is True
        assert len(corpo["players"]) == 5

    def test_clube_inexistente(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/clubs/999999/lineup")

        assert resposta.status_code == 404, resposta.text


class TestPartida:
    def test_partida_feliz_bate_com_o_formato_do_exemplo_2_4_2_do_enunciado(
        self, client: TestClient
    ) -> None:
        mandante, _ = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        visitante, _ = _escalar_clube_2_1_1(client, "Delta FC", "DEL")

        resposta = client.post(
            "/api/v1/matches",
            json={"home_club_id": mandante["id"], "away_club_id": visitante["id"]},
        )

        assert resposta.status_code == 201, resposta.text
        assert resposta.headers["location"] == f"/api/v1/matches/{resposta.json()['id']}"
        corpo = resposta.json()
        assert corpo["home"]["club_id"] == mandante["id"]
        assert corpo["away"]["club_id"] == visitante["id"]
        assert corpo["home"]["formation"] == "2-1-1"
        assert corpo["away"]["formation"] == "2-1-1"
        assert corpo["result"] in ("MANDANTE", "VISITANTE", "EMPATE")
        assert len(corpo["duels"]) == 6
        for ordem, duelo in enumerate(corpo["duels"], start=1):
            assert duelo["order"] == ordem
            assert set(duelo["attacker"]) == {
                "player_id",
                "player_name",
                "position",
                "condition",
                "attribute",
                "value",
            }
            assert set(duelo["defender"]) == {
                "player_id",
                "player_name",
                "position",
                "condition",
                "attribute",
                "value",
            }
            assert isinstance(duelo["goal"], bool)

    def test_mandante_igual_ao_visitante_e_recusado(self, client: TestClient) -> None:
        clube, _ = _escalar_clube_2_1_1(client, "Águias FC", "AGU")

        resposta = client.post(
            "/api/v1/matches", json={"home_club_id": clube["id"], "away_club_id": clube["id"]}
        )

        assert resposta.status_code == 400, resposta.text

    def test_clube_inexistente_e_recusado(self, client: TestClient) -> None:
        clube, _ = _escalar_clube_2_1_1(client, "Águias FC", "AGU")

        resposta = client.post(
            "/api/v1/matches", json={"home_club_id": clube["id"], "away_club_id": 999999}
        )

        assert resposta.status_code == 404, resposta.text

    def test_home_club_id_como_string_e_recusado(self, client: TestClient) -> None:
        mandante, _ = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        visitante, _ = _escalar_clube_2_1_1(client, "Delta FC", "DEL")

        resposta = client.post(
            "/api/v1/matches",
            json={"home_club_id": str(mandante["id"]), "away_club_id": visitante["id"]},
        )

        assert resposta.status_code == 400, resposta.text

    def test_escalacao_incompleta_recusa_a_partida(self, client: TestClient) -> None:
        mandante, jogadores = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        visitante = _cadastrar_clube(client, name="Delta FC", acronym="DEL")
        resposta_venda = client.post(f"/api/v1/players/{jogadores[0]['id']}/sell")
        assert resposta_venda.status_code == 200, resposta_venda.text

        resposta = client.post(
            "/api/v1/matches",
            json={"home_club_id": mandante["id"], "away_club_id": visitante["id"]},
        )

        assert resposta.status_code == 409, resposta.text


class TestHistoricoDetalheEClassificacao:
    def test_historico_e_detalhe_da_partida(self, client: TestClient) -> None:
        mandante, _ = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        visitante, _ = _escalar_clube_2_1_1(client, "Delta FC", "DEL")
        criada = client.post(
            "/api/v1/matches",
            json={"home_club_id": mandante["id"], "away_club_id": visitante["id"]},
        ).json()

        historico = client.get("/api/v1/matches")
        assert historico.status_code == 200, historico.text
        assert "duels" not in historico.json()[0]

        filtrado = client.get(f"/api/v1/matches?club_id={mandante['id']}")
        assert filtrado.status_code == 200, filtrado.text
        assert all(
            mandante["id"] in (p["home"]["club_id"], p["away"]["club_id"]) for p in filtrado.json()
        )

        clube_inexistente = client.get("/api/v1/matches?club_id=999999")
        assert clube_inexistente.status_code == 404, clube_inexistente.text

        detalhe = client.get(f"/api/v1/matches/{criada['id']}")
        assert detalhe.status_code == 200, detalhe.text
        assert len(detalhe.json()["duels"]) == 6

        partida_inexistente = client.get("/api/v1/matches/999999")
        assert partida_inexistente.status_code == 404, partida_inexistente.text

    def test_classificacao_traz_todos_os_clubes_inclusive_zerados(self, client: TestClient) -> None:
        mandante, _ = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        visitante, _ = _escalar_clube_2_1_1(client, "Delta FC", "DEL")
        sem_jogar = _cadastrar_clube(client, name="Gama SC", acronym="GSC")
        client.post(
            "/api/v1/matches",
            json={"home_club_id": mandante["id"], "away_club_id": visitante["id"]},
        )

        resposta = client.get("/api/v1/standings")

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert len(corpo) == 3
        linha_sem_jogar = next(l for l in corpo if l["club_id"] == sem_jogar["id"])
        assert (
            linha_sem_jogar["played"],
            linha_sem_jogar["wins"],
            linha_sem_jogar["draws"],
            linha_sem_jogar["losses"],
            linha_sem_jogar["goals_for"],
            linha_sem_jogar["goals_against"],
            linha_sem_jogar["goal_difference"],
            linha_sem_jogar["points"],
        ) == (0, 0, 0, 0, 0, 0, 0, 0)
        posicoes = [l["position"] for l in corpo]
        assert posicoes == list(range(1, len(corpo) + 1))


class TestEscalacaoSubstituiAAnterior:
    def test_nova_escalacao_substitui_a_anterior_por_inteiro(self, client: TestClient) -> None:
        clube, jogadores = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        novo_goleiro = _cadastrar_jogador(client, name="Novo Goleiro", position="GOL")
        _comprar(client, novo_goleiro["id"], clube["id"])
        novos_ids = [novo_goleiro["id"]] + [j["id"] for j in jogadores[1:]]

        resposta = client.put(
            f"/api/v1/clubs/{clube['id']}/lineup",
            json={"formation": "2-1-1", "player_ids": novos_ids},
        )

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert {p["id"] for p in corpo["players"]} == set(novos_ids)
        assert jogadores[0]["id"] not in {p["id"] for p in corpo["players"]}


class TestTitularSaiDaEscalacao:
    def test_venda_do_titular_deixa_a_escalacao_incompleta(self, client: TestClient) -> None:
        clube, jogadores = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        vendido = jogadores[-1]  # Otto Rangel (ATA)

        resposta_venda = client.post(f"/api/v1/players/{vendido['id']}/sell")
        assert resposta_venda.status_code == 200, resposta_venda.text

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/lineup")
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["complete"] is False
        assert corpo["formation"] == "2-1-1"
        assert vendido["id"] not in {p["id"] for p in corpo["players"]}
        assert len(corpo["players"]) == 4

    def test_titular_que_fica_doente_sai_da_escalacao(self, client: TestClient) -> None:
        clube, jogadores = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        fica_doente = jogadores[-1]

        resposta_condicao = client.patch(
            f"/api/v1/players/{fica_doente['id']}/condition", json={"condition": "DOENTE"}
        )
        assert resposta_condicao.status_code == 200, resposta_condicao.text

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/lineup")
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["complete"] is False
        assert corpo["formation"] == "2-1-1"
        assert fica_doente["id"] not in {p["id"] for p in corpo["players"]}

    def test_jogador_nao_volta_sozinho_ao_deixar_de_estar_doente(self, client: TestClient) -> None:
        clube, jogadores = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        fica_doente = jogadores[-1]
        client.patch(f"/api/v1/players/{fica_doente['id']}/condition", json={"condition": "DOENTE"})

        resposta_volta = client.patch(
            f"/api/v1/players/{fica_doente['id']}/condition", json={"condition": "MAL_CONDICIONADO"}
        )
        assert resposta_volta.status_code == 200, resposta_volta.text

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/lineup")
        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert fica_doente["id"] not in {p["id"] for p in corpo["players"]}
        assert corpo["complete"] is False


class TestPartidaDePontaAPontaComOExemploDaRN20:
    def test_placar_result_e_os_6_duelos_batem_com_o_exemplo(self, client: TestClient) -> None:
        aguias, titulares_aguias = _escalar_roster(client, "Águias FC", "AGU", _ROSTER_AGUIAS)
        delta, _ = _escalar_roster(client, "Delta FC", "DEL", _ROSTER_DELTA)
        davi_lins = next(j for j in titulares_aguias if j["name"] == "Davi Lins")
        resposta_condicao = client.patch(
            f"/api/v1/players/{davi_lins['id']}/condition", json={"condition": "MAL_CONDICIONADO"}
        )
        assert resposta_condicao.status_code == 200, resposta_condicao.text
        caixa_aguias_antes = client.get(f"/api/v1/clubs/{aguias['id']}").json()["cash"]
        caixa_delta_antes = client.get(f"/api/v1/clubs/{delta['id']}").json()["cash"]

        resposta = client.post(
            "/api/v1/matches",
            json={"home_club_id": aguias["id"], "away_club_id": delta["id"]},
        )

        assert resposta.status_code == 201, resposta.text
        corpo = resposta.json()
        assert corpo["home"]["goals"] == 1
        assert corpo["away"]["goals"] == 2
        assert corpo["result"] == "VISITANTE"
        tabela = [
            (
                d["order"],
                d["attacking_club_id"],
                d["attacker"]["player_name"],
                d["attacker"]["value"],
                d["defender"]["player_name"],
                d["defender"]["value"],
                d["goal"],
            )
            for d in corpo["duels"]
        ]
        assert tabela == [
            (1, aguias["id"], "Otto Rangel", 75, "Ivo Teles", 72, True),
            (2, aguias["id"], "Lauro Neves", 82, "Hugo Vaz", 84, False),
            (3, aguias["id"], "Davi Lins", 63, "Lino Matos", 63, False),
            (4, delta["id"], "Ugo Falcão", 81, "Rui Prado", 77, True),
            (5, delta["id"], "Nei Soares", 70, "Téo Brandão", 84, False),
            (6, delta["id"], "Lino Matos", 79, "Davi Lins", 56, True),
        ]

        # RN20: a partida não muda caixa, escalação nem jogadores.
        assert client.get(f"/api/v1/clubs/{aguias['id']}").json()["cash"] == caixa_aguias_antes
        assert client.get(f"/api/v1/clubs/{delta['id']}").json()["cash"] == caixa_delta_antes
        lineup_aguias = client.get(f"/api/v1/clubs/{aguias['id']}/lineup").json()
        assert lineup_aguias["complete"] is True
        assert len(lineup_aguias["players"]) == 5
        davi_lins_depois = client.get(f"/api/v1/players/{davi_lins['id']}").json()
        assert davi_lins_depois["dribbling"] == 74
        assert davi_lins_depois["defending"] == 66
        assert davi_lins_depois["condition"] == "MAL_CONDICIONADO"


class TestClassificacaoComOExemploDoEnunciado:
    def test_classificacao_com_6_clubes_e_4_partidas(self, client: TestClient) -> None:
        aguias, _ = _escalar_clube_2_1_1(client, "Águias FC", "AGU")
        delta, _ = _escalar_clube_2_1_1(client, "Delta FC", "DEL")
        gama, _ = _escalar_clube_2_1_1(client, "Gama SC", "GAM")
        epsilon, _ = _escalar_clube_2_1_1(client, "Épsilon EC", "EPS")
        mangue = _cadastrar_clube(client, name="Mangue FC", acronym="MAN")
        tubaroes = _cadastrar_clube(client, name="Tubarões EC", acronym="TUB")

        def _jogar(mandante_id: int, visitante_id: int) -> dict:
            resposta = client.post(
                "/api/v1/matches",
                json={"home_club_id": mandante_id, "away_club_id": visitante_id},
            )
            assert resposta.status_code == 201, resposta.text
            return resposta.json()

        # As partidas são jogadas de verdade (placar calculado pelos 6 duelos), então não dá pra
        # forçar o placar exato do exemplo do enunciado aqui — o que se verifica é a mecânica da
        # classificação (ordenação, pontos, saldo, zerados), não os números exatos do enunciado
        # (já cobertos pelo teste unitário de `LigaService.classificacao`, que não depende de
        # `jogar_partida` e por isso controla o placar livremente).
        _jogar(aguias["id"], delta["id"])
        _jogar(gama["id"], epsilon["id"])
        _jogar(epsilon["id"], aguias["id"])
        _jogar(delta["id"], gama["id"])

        resposta = client.get("/api/v1/standings")

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert len(corpo) == 6
        assert {l["club_id"] for l in corpo} == {
            aguias["id"],
            delta["id"],
            gama["id"],
            epsilon["id"],
            mangue["id"],
            tubaroes["id"],
        }
        linha_mangue = next(l for l in corpo if l["club_id"] == mangue["id"])
        linha_tubaroes = next(l for l in corpo if l["club_id"] == tubaroes["id"])
        assert linha_mangue["played"] == 0
        assert linha_tubaroes["played"] == 0
        posicao_mangue = next(l["position"] for l in corpo if l["club_id"] == mangue["id"])
        posicao_tubaroes = next(l["position"] for l in corpo if l["club_id"] == tubaroes["id"])
        assert posicao_mangue < posicao_tubaroes  # desempate pelo nome (RN21.4)
        assert [l["position"] for l in corpo] == list(range(1, 7))
