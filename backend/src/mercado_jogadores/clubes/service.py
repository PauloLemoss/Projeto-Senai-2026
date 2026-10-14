"""Regras de negócio do domínio clube (RN10, RN11). Único lugar onde essas regras vivem —
o router nunca as recalcula, só delega aqui.

A validação de formato de `nome`/`sigla` e a correspondência sigla↔nome (função pura, sem
banco) ficam no schema `ClubeCreate` (camada HTTP) — ver design.md. Aqui só as regras que
dependem de persistência: unicidade, limite de clubes e os valores calculados a cada consulta.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.clubes.repository import ClubeRepository
from mercado_jogadores.core.datas import FUSO_BRASILIA
from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError
from mercado_jogadores.core.validation import normalizar_para_busca
from mercado_jogadores.jogadores.calculos import ORDEM_DAS_POSICOES
from mercado_jogadores.jogadores.repository import FiltrosSql, JogadorRepository
from mercado_jogadores.jogadores.service import JogadorComCalculados, calcular_indicadores
from mercado_jogadores.mercado.calculos import calcular_dias_restantes_e_percentual_de_multa
from mercado_jogadores.mercado.repository import ContratoRepository

LIMITE_DE_CLUBES = 20


@dataclass
class DadosCadastroClube:
    nome: str
    sigla: str


@dataclass
class ContratoDoElenco:
    purchase_value: Decimal
    loyalty_until: datetime
    remaining_days: int
    penalty_rate: int


@dataclass
class JogadorDoElenco:
    calculados: JogadorComCalculados
    contract: ContratoDoElenco | None


@dataclass
class ClubeComElenco:
    clube: Clube
    elenco: list[JogadorDoElenco]
    squad_value: Decimal
    net_worth: Decimal


@dataclass
class ClubeComPatrimonio:
    clube: Clube
    squad_value: Decimal
    net_worth: Decimal


class ClubeService:
    def __init__(
        self,
        clube_repository: ClubeRepository,
        jogador_repository: JogadorRepository,
        contrato_repository: ContratoRepository,
    ) -> None:
        self._clubes = clube_repository
        self._jogadores = jogador_repository
        self._contratos = contrato_repository

    def cadastrar(self, dados: DadosCadastroClube) -> ClubeComElenco:
        nome_normalizado = dados.nome.lower()

        if self._clubes.obter_por_nome_normalizado(nome_normalizado) is not None:
            raise ConflitoError("Já existe um clube com esse nome.")
        if self._clubes.obter_por_sigla(dados.sigla) is not None:
            raise ConflitoError("Já existe um clube com essa sigla.")
        if self._clubes.contar() >= LIMITE_DE_CLUBES:
            raise ConflitoError(f"A liga já atingiu o limite de {LIMITE_DE_CLUBES} clubes.")

        clube = Clube(
            nome=dados.nome,
            nome_normalizado=nome_normalizado,
            sigla=dados.sigla,
            caixa=Decimal("300.00"),
        )
        clube = self._clubes.salvar(clube)
        return self._com_elenco(clube, datetime.now(FUSO_BRASILIA))

    def consultar(self, clube_id: int, momento: datetime) -> ClubeComElenco:
        clube = self._obter_ou_falhar(clube_id)
        return self._com_elenco(clube, momento)

    def listar(self, sort: str = "name") -> list[ClubeComPatrimonio]:
        clubes = [self._com_patrimonio(c) for c in self._clubes.listar()]

        clubes = sorted(clubes, key=lambda c: c.clube.id)
        clubes = sorted(clubes, key=lambda c: normalizar_para_busca(c.clube.nome))
        if sort in ("net_worth_asc", "net_worth_desc"):
            clubes = sorted(clubes, key=lambda c: c.net_worth, reverse=sort == "net_worth_desc")

        return clubes

    def _obter_ou_falhar(self, clube_id: int) -> Clube:
        clube = self._clubes.obter(clube_id)
        if clube is None:
            raise NaoEncontradoError("Clube não encontrado.")
        return clube

    def _elenco_com_valores(self, clube_id: int) -> list[JogadorComCalculados]:
        jogadores = self._jogadores.listar(FiltrosSql(club_id=clube_id))
        return [calcular_indicadores(j) for j in jogadores]

    def _ordenar_elenco(
        self, elenco: list[JogadorComCalculados]
    ) -> list[JogadorComCalculados]:
        elenco = sorted(elenco, key=lambda item: item.jogador.id)
        elenco = sorted(elenco, key=lambda item: normalizar_para_busca(item.jogador.nome))
        elenco = sorted(elenco, key=lambda item: ORDEM_DAS_POSICOES.index(item.jogador.posicao))
        return elenco

    def _com_elenco(self, clube: Clube, momento: datetime) -> ClubeComElenco:
        calculados = self._ordenar_elenco(self._elenco_com_valores(clube.id))
        squad_value = sum((item.market_value for item in calculados), Decimal("0.00"))
        elenco = [
            JogadorDoElenco(
                calculados=item, contract=self._contrato_do_elenco(item.jogador.id, momento)
            )
            for item in calculados
        ]
        return ClubeComElenco(
            clube=clube, elenco=elenco, squad_value=squad_value, net_worth=clube.caixa + squad_value
        )

    def _contrato_do_elenco(self, jogador_id: int, momento: datetime) -> ContratoDoElenco | None:
        contrato = self._contratos.obter_ativo_por_jogador(jogador_id)
        if contrato is None:
            return None
        dias_restantes, percentual = calcular_dias_restantes_e_percentual_de_multa(
            contrato.fidelidade_ate, momento
        )
        return ContratoDoElenco(
            purchase_value=contrato.valor_compra,
            loyalty_until=contrato.fidelidade_ate,
            remaining_days=dias_restantes,
            penalty_rate=percentual,
        )

    def _com_patrimonio(self, clube: Clube) -> ClubeComPatrimonio:
        elenco = self._elenco_com_valores(clube.id)
        squad_value = sum((item.market_value for item in elenco), Decimal("0.00"))
        return ClubeComPatrimonio(
            clube=clube, squad_value=squad_value, net_worth=clube.caixa + squad_value
        )
