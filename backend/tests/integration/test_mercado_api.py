"""Testes de ponta a ponta via TestClient, cobrindo cada #### Scenario da spec `mercado`."""

from datetime import datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.jogadores.models import Jogador
from mercado_jogadores.mercado.models import Contrato

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

# Atributos baixos (overall ~20) para gerar valor de mercado no piso (1,00), sem taxa e sem
# risco de estourar o limite de 50% do caixa — usado nos cenários que só precisam de "um
# jogador qualquer", não de um valor específico.
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


def _cadastrar_jogador(client: TestClient, **sobrescritas: object) -> dict:
    corpo = {**_JOGADOR_VALIDO, **sobrescritas}
    resposta = client.post("/api/v1/players", json=corpo)
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


def _cadastrar_jogador_fraco(client: TestClient, **sobrescritas: object) -> dict:
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


def _comprar(client: TestClient, jogador_id: int, club_id: int, **sobrescritas: object):
    corpo = {"club_id": club_id, "loyalty_until": _loyalty_until_daqui_a(365), **sobrescritas}
    return client.post(f"/api/v1/players/{jogador_id}/buy", json=corpo)


def _definir_valor_base(db_session, jogador_id: int, valor: Decimal) -> None:
    db_session.query(Jogador).filter(Jogador.id == jogador_id).update({"valor_base": valor})
    db_session.commit()


def _definir_fidelidade_ate(db_session, jogador_id: int, fidelidade_ate: datetime) -> None:
    db_session.query(Contrato).filter(
        Contrato.jogador_id == jogador_id, Contrato.situacao == "ATIVO"
    ).update({"fidelidade_ate": fidelidade_ate})
    db_session.commit()


class TestCompra:
    def test_compra_feliz_bate_com_o_exemplo_2_3_1_do_enunciado(
        self, client: TestClient
    ) -> None:
        jogador = _cadastrar_jogador(client)
        condicao = client.patch(
            f"/api/v1/players/{jogador['id']}/condition", json={"condition": "MAL_CONDICIONADO"}
        )
        assert condicao.status_code == 200, condicao.text
        clube = _cadastrar_clube(client)

        resposta = client.post(
            f"/api/v1/players/{jogador['id']}/buy",
            json={"club_id": clube["id"], "loyalty_until": _loyalty_until_daqui_a(365)},
        )

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["type"] == "COMPRA"
        assert corpo["player_name"] == "Meia Lua"
        assert corpo["value"] == 37.00
        assert corpo["fee"] == 1.85
        assert corpo["penalty"] == 0.00
        assert corpo["profit"] is None
        assert corpo["cash_change"] == -38.85
        assert corpo["contract"]["purchase_value"] == 37.00
        assert corpo["contract"]["status"] == "ATIVO"
        assert corpo["club_cash"] == 261.15

    def test_compra_aceita_abaixo_do_limite_sem_taxa(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)

        resposta = _comprar(client, jogador["id"], clube["id"])

        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["fee"] == 0.00
        assert resposta.json()["value"] == 1.00

    def test_custo_total_igual_ao_limite_e_aceito(
        self, client: TestClient, db_session
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        _definir_valor_base(db_session, jogador["id"], Decimal("142.86"))
        clube = _cadastrar_clube(client)  # nasce com cash 300,00; limite 150,00

        resposta = _comprar(client, jogador["id"], clube["id"])

        assert resposta.status_code == 200, resposta.text
        assert resposta.json()["fee"] == 7.14
        assert resposta.json()["club_cash"] == 150.00

    def test_custo_total_acima_do_limite_e_recusado_e_nada_e_gravado(
        self, client: TestClient, db_session
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        _definir_valor_base(db_session, jogador["id"], Decimal("143.00"))
        clube = _cadastrar_clube(client)  # limite 150,00; custo seria 150,15

        resposta = _comprar(client, jogador["id"], clube["id"])

        assert resposta.status_code == 409
        assert resposta.json()["message"]
        assert client.get(f"/api/v1/players/{jogador['id']}").json()["club_id"] is None

    def test_jogador_que_nao_esta_livre_e_recusado(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        assert _comprar(client, jogador["id"], clube["id"]).status_code == 200

        resposta = _comprar(client, jogador["id"], clube["id"])

        assert resposta.status_code == 409
        assert resposta.json()["message"]

    def test_elenco_com_12_jogadores_recusa_a_13a_compra(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)
        nomes = [
            "Um Titular", "Dois Titular", "Tres Titular", "Quatro Titular", "Cinco Titular",
            "Seis Titular", "Sete Titular", "Oito Titular", "Nove Titular", "Dez Titular",
            "Onze Titular", "Doze Titular",
        ]
        for nome in nomes:
            titular = _cadastrar_jogador_fraco(client, name=nome)
            assert _comprar(client, titular["id"], clube["id"]).status_code == 200

        decimo_terceiro = _cadastrar_jogador_fraco(client, name="Decimo Terceiro")
        resposta = _comprar(client, decimo_terceiro["id"], clube["id"])

        assert resposta.status_code == 409
        assert resposta.json()["message"]

    def test_clube_que_ja_vendeu_o_jogador_nao_pode_recompra_lo_mas_outro_pode(
        self, client: TestClient
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube_a = _cadastrar_clube(client, name="Águias FC", acronym="AGU")
        clube_b = _cadastrar_clube(client, name="Leões FC", acronym="LEO")
        assert _comprar(client, jogador["id"], clube_a["id"]).status_code == 200
        assert client.post(f"/api/v1/players/{jogador['id']}/sell").status_code == 200

        recompra = _comprar(client, jogador["id"], clube_a["id"])
        assert recompra.status_code == 409
        assert recompra.json()["message"]

        outro_clube = _comprar(client, jogador["id"], clube_b["id"])
        assert outro_clube.status_code == 200

    def test_jogador_inexistente_e_recusado(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        resposta = _comprar(client, 999_999, clube["id"])

        assert resposta.status_code == 404
        assert resposta.json()["message"]

    def test_clube_inexistente_e_recusado(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)

        resposta = _comprar(client, jogador["id"], 999_999)

        assert resposta.status_code == 404
        assert resposta.json()["message"]

    def test_campo_obrigatorio_ausente_e_recusado(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)

        resposta = client.post(
            f"/api/v1/players/{jogador['id']}/buy", json={"club_id": clube["id"]}
        )

        assert resposta.status_code == 400

    def test_club_id_invalido_e_recusado(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)

        resposta = _comprar(client, jogador["id"], 0)

        assert resposta.status_code == 400

    def test_loyalty_until_fora_do_formato_e_recusado(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)

        resposta = _comprar(client, jogador["id"], clube["id"], loyalty_until="2027-03-02")

        assert resposta.status_code == 400

    def test_loyalty_until_nao_futuro_e_recusado(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)

        resposta = _comprar(
            client, jogador["id"], clube["id"], loyalty_until=_loyalty_until_daqui_a(-1)
        )

        assert resposta.status_code == 400

    def test_loyalty_until_acima_de_1095_dias_e_recusado(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)

        resposta = _comprar(
            client, jogador["id"], clube["id"], loyalty_until=_loyalty_until_daqui_a(1096)
        )

        assert resposta.status_code == 400


class TestVenda:
    def test_venda_de_ponta_a_ponta_bate_com_o_exemplo_2_3_2_do_enunciado(
        self, client: TestClient
    ) -> None:
        jogador = _cadastrar_jogador(client)
        client.patch(
            f"/api/v1/players/{jogador['id']}/condition", json={"condition": "MAL_CONDICIONADO"}
        )
        clube = _cadastrar_clube(client)
        # ~120 dias restantes na venda (cai na faixa 31-180 -> 10%, igual ao exemplo 2.3.2).
        compra = _comprar(
            client, jogador["id"], clube["id"], loyalty_until=_loyalty_until_daqui_a(120)
        )
        assert compra.status_code == 200

        volta = client.patch(
            f"/api/v1/players/{jogador['id']}/condition", json={"condition": "APTO"}
        )
        assert volta.status_code == 200

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["type"] == "VENDA"
        assert corpo["value"] == 40.00
        assert corpo["fee"] == 0.30
        assert corpo["penalty"] == 4.00
        assert corpo["profit"] == 3.00
        assert corpo["cash_change"] == 35.70
        assert corpo["purchase_value"] == 37.00
        assert corpo["contract_status"] == "RESCINDIDO"

    def test_fidelidade_ja_cumprida_nao_gera_multa(
        self, client: TestClient, db_session
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])
        _definir_fidelidade_ate(
            db_session, jogador["id"], datetime.now(FUSO_BRASILIA) - timedelta(days=1)
        )

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert corpo["remaining_days"] == 0
        assert corpo["penalty"] == 0.00
        assert corpo["contract_status"] == "ENCERRADO"

    def test_faixa_de_1_a_30_dias_gera_5_por_cento_de_multa(
        self, client: TestClient, db_session
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])
        _definir_fidelidade_ate(
            db_session, jogador["id"], datetime.now(FUSO_BRASILIA) + timedelta(days=30)
        )

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.json()["penalty_rate"] == 5
        assert resposta.json()["contract_status"] == "RESCINDIDO"

    def test_faixa_de_31_a_180_dias_gera_10_por_cento_de_multa(
        self, client: TestClient, db_session
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])
        _definir_fidelidade_ate(
            db_session,
            jogador["id"],
            datetime.now(FUSO_BRASILIA) + timedelta(days=30, minutes=1),
        )

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.json()["penalty_rate"] == 10

    def test_faixa_de_181_dias_ou_mais_gera_20_por_cento_de_multa(
        self, client: TestClient, db_session
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])
        _definir_fidelidade_ate(
            db_session,
            jogador["id"],
            datetime.now(FUSO_BRASILIA) + timedelta(days=180, minutes=1),
        )

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.json()["penalty_rate"] == 20

    def test_multa_e_limitada_a_dez(self, client: TestClient, db_session) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])
        _definir_valor_base(db_session, jogador["id"], Decimal("75.00"))
        _definir_fidelidade_ate(
            db_session, jogador["id"], datetime.now(FUSO_BRASILIA) + timedelta(days=200)
        )

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.json()["penalty_rate"] == 20  # 20% de 75,00 seria 15,00
        assert resposta.json()["penalty"] == 10.00

    def test_lucro_cruzando_as_duas_faixas_de_comissao(
        self, client: TestClient, db_session
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])  # valor de compra: 1,00 (piso)
        _definir_fidelidade_ate(
            db_session, jogador["id"], datetime.now(FUSO_BRASILIA) - timedelta(days=1)
        )
        _definir_valor_base(db_session, jogador["id"], Decimal("16.00"))  # lucro 15,00

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.json()["profit"] == 15.00
        assert resposta.json()["fee"] == 2.00

    def test_prejuizo_nao_gera_comissao(self, client: TestClient, db_session) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _definir_valor_base(db_session, jogador["id"], Decimal("30.00"))
        _comprar(client, jogador["id"], clube["id"])  # valor de compra: 30,00
        _definir_fidelidade_ate(
            db_session, jogador["id"], datetime.now(FUSO_BRASILIA) - timedelta(days=1)
        )
        _definir_valor_base(db_session, jogador["id"], Decimal("20.00"))  # prejuízo

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.json()["profit"] == -10.00
        assert resposta.json()["fee"] == 0.00

    def test_jogador_livre_nao_pode_ser_vendido(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)

        resposta = client.post(f"/api/v1/players/{jogador['id']}/sell")

        assert resposta.status_code == 409
        assert resposta.json()["message"]

    def test_jogador_inexistente_e_recusado(self, client: TestClient) -> None:
        resposta = client.post("/api/v1/players/999999/sell")

        assert resposta.status_code == 404
        assert resposta.json()["message"]


class TestHistoricoDeTransacoes:
    def test_sem_filtro_traz_compra_e_venda_com_os_totais_somados(
        self, client: TestClient
    ) -> None:
        jogador = _cadastrar_jogador(client)
        client.patch(
            f"/api/v1/players/{jogador['id']}/condition", json={"condition": "MAL_CONDICIONADO"}
        )
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"], loyalty_until=_loyalty_until_daqui_a(120))
        client.patch(f"/api/v1/players/{jogador['id']}/condition", json={"condition": "APTO"})
        client.post(f"/api/v1/players/{jogador['id']}/sell")

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/transactions")

        assert resposta.status_code == 200, resposta.text
        corpo = resposta.json()
        assert [t["type"] for t in corpo["data"]] == ["VENDA", "COMPRA"]
        assert corpo["summary"] == {
            "total_spent": 38.85,
            "total_received": 35.70,
            "total_fees": 2.15,
            "total_penalties": 4.00,
            "total_profit": 3.00,
        }

    def test_filtro_por_type_restringe_data_e_summary(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])
        client.post(f"/api/v1/players/{jogador['id']}/sell")

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/transactions?type=VENDA")

        corpo = resposta.json()
        assert [t["type"] for t in corpo["data"]] == ["VENDA"]
        assert corpo["summary"]["total_spent"] == 0.00

    def test_jogador_sem_transacoes_no_clube(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)

        resposta = client.get(
            f"/api/v1/clubs/{clube['id']}/transactions?player_id={jogador['id']}"
        )

        assert resposta.status_code == 200
        corpo = resposta.json()
        assert corpo["data"] == []
        assert all(v == 0.00 for v in corpo["summary"].values())

    def test_filtro_invalido_e_recusado(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/transactions?type=venda")

        assert resposta.status_code == 400

    def test_jogador_do_filtro_inexistente_e_recusado(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/transactions?player_id=999999")

        assert resposta.status_code == 404

    def test_clube_inexistente(self, client: TestClient) -> None:
        resposta = client.get("/api/v1/clubs/999999/transactions")

        assert resposta.status_code == 404

    def test_conciliacao_do_caixa_pelo_historico(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])
        client.post(f"/api/v1/players/{jogador['id']}/sell")

        historico = client.get(f"/api/v1/clubs/{clube['id']}/transactions").json()
        soma_variacao = sum(Decimal(str(t["cash_change"])) for t in historico["data"])
        caixa_atual = Decimal(str(client.get(f"/api/v1/clubs/{clube['id']}").json()["cash"]))

        assert Decimal("300.00") + soma_variacao == caixa_atual

    def test_transacoes_de_jogador_excluido_permanecem_no_historico(
        self, client: TestClient
    ) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])
        client.post(f"/api/v1/players/{jogador['id']}/sell")

        exclusao = client.delete(f"/api/v1/players/{jogador['id']}")
        assert exclusao.status_code == 204

        historico = client.get(f"/api/v1/clubs/{clube['id']}/transactions").json()
        assert len(historico["data"]) == 2


class TestExportacaoCsv:
    def test_exportacao_com_transacoes(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client)
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/transactions/export")

        assert resposta.status_code == 200
        assert resposta.headers["content-type"].startswith("text/csv")
        linhas = resposta.text.split("\n")
        assert linhas[0] == (
            "data_hora;tipo;jogador;valor;taxa_ou_comissao;multa;lucro;variacao_caixa"
        )
        assert linhas[1].split(";")[1] == "COMPRA"
        assert "\r\n" not in resposta.text

    def test_exportacao_sem_transacoes_traz_so_o_cabecalho(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/transactions/export")

        assert resposta.text == (
            "data_hora;tipo;jogador;valor;taxa_ou_comissao;multa;lucro;variacao_caixa\n"
        )

    def test_nome_do_jogador_com_aspas_e_escapado(self, client: TestClient) -> None:
        jogador = _cadastrar_jogador_fraco(client, name='Ze "Foguete" Lima')
        clube = _cadastrar_clube(client)
        _comprar(client, jogador["id"], clube["id"])

        resposta = client.get(f"/api/v1/clubs/{clube['id']}/transactions/export")

        assert '"Ze ""Foguete"" Lima"' in resposta.text

    def test_filtro_invalido_ou_recurso_inexistente(self, client: TestClient) -> None:
        clube = _cadastrar_clube(client)

        assert (
            client.get(f"/api/v1/clubs/{clube['id']}/transactions/export?type=venda").status_code
            == 400
        )
        assert client.get("/api/v1/clubs/999999/transactions/export").status_code == 404
