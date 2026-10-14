"""Regras de negócio do domínio mercado (RN12 a RN18). Único lugar onde essas regras vivem —
o router nunca as recalcula, só delega aqui.

A validação de formato/intervalo de `club_id`/`loyalty_until` (RN01, "Limites de cada campo")
fica no schema `BuyRequest` (camada HTTP) — ver design.md. Aqui só as regras que dependem de
persistência e do estado do jogador/clube.
"""

import csv
import io
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from mercado_jogadores.clubes.models import Clube
from mercado_jogadores.clubes.repository import ClubeRepository
from mercado_jogadores.core.datas import formatar_datetime_rn01
from mercado_jogadores.core.errors import ConflitoError, NaoEncontradoError
from mercado_jogadores.core.unidade_de_trabalho import UnidadeDeTrabalho
from mercado_jogadores.jogadores.repository import FiltrosSql, JogadorRepository
from mercado_jogadores.jogadores.service import calcular_indicadores
from mercado_jogadores.liga.repository import EscalacaoRepository
from mercado_jogadores.mercado.calculos import (
    calcular_comissao_de_venda,
    calcular_credito_na_venda,
    calcular_dias_restantes_e_percentual_de_multa,
    calcular_multa,
    calcular_taxa_de_compra,
    limite_de_compra,
)
from mercado_jogadores.mercado.models import Contrato, Transacao
from mercado_jogadores.mercado.repository import (
    ContratoRepository,
    FiltrosDeTransacao,
    TransacaoRepository,
)

LIMITE_DE_ELENCO = 12
CABECALHO_CSV = (
    "data_hora",
    "tipo",
    "jogador",
    "valor",
    "taxa_ou_comissao",
    "multa",
    "lucro",
    "variacao_caixa",
)


def _formatar_valor_csv(valor: Decimal) -> str:
    """RN18: 2 casas, vírgula decimal (não ponto — diferente da convenção de JSON da API)."""
    return f"{valor:.2f}".replace(".", ",")


@dataclass
class DadosDeCompra:
    club_id: int
    loyalty_until: datetime


@dataclass
class ResultadoDaCompra:
    transacao: Transacao
    contrato: Contrato
    clube: Clube


@dataclass
class ResultadoDaVenda:
    transacao: Transacao
    contrato: Contrato
    clube: Clube
    dias_restantes: int
    percentual_de_multa: int


@dataclass
class ResumoDeTransacoes:
    total_spent: Decimal
    total_received: Decimal
    total_fees: Decimal
    total_penalties: Decimal
    total_profit: Decimal


@dataclass
class HistoricoDeTransacoes:
    transacoes: list[Transacao]
    resumo: ResumoDeTransacoes


class MercadoService:
    def __init__(
        self,
        jogador_repository: JogadorRepository,
        clube_repository: ClubeRepository,
        contrato_repository: ContratoRepository,
        transacao_repository: TransacaoRepository,
        escalacao_repository: EscalacaoRepository,
        unidade_de_trabalho: UnidadeDeTrabalho,
    ) -> None:
        self._jogadores = jogador_repository
        self._clubes = clube_repository
        self._contratos = contrato_repository
        self._transacoes = transacao_repository
        self._escalacoes = escalacao_repository
        self._uot = unidade_de_trabalho

    def comprar(
        self, jogador_id: int, dados: DadosDeCompra, momento: datetime
    ) -> ResultadoDaCompra:
        jogador = self._jogadores.obter(jogador_id)
        if jogador is None:
            raise NaoEncontradoError("Jogador não encontrado.")
        if jogador.clube_id is not None:
            raise ConflitoError("Jogador não está livre.")

        clube = self._clubes.obter(dados.club_id)
        if clube is None:
            raise NaoEncontradoError("Clube não encontrado.")

        if self._transacoes.existe_venda(dados.club_id, jogador_id):
            raise ConflitoError("Esse clube já vendeu esse jogador antes; não pode recomprá-lo.")

        elenco = self._jogadores.listar(FiltrosSql(club_id=dados.club_id))
        if len(elenco) >= LIMITE_DE_ELENCO:
            raise ConflitoError(f"O elenco já tem o limite de {LIMITE_DE_ELENCO} jogadores.")

        valor_de_mercado = calcular_indicadores(jogador).market_value
        taxa = calcular_taxa_de_compra(valor_de_mercado)
        custo_total = valor_de_mercado + taxa
        if custo_total > limite_de_compra(clube.caixa):
            raise ConflitoError(
                f"O custo total ({custo_total}) passa do limite de 50% do caixa ({clube.caixa})."
            )

        jogador.clube_id = dados.club_id
        clube.caixa -= custo_total

        contrato = Contrato(
            jogador_id=jogador_id,
            clube_id=dados.club_id,
            valor_compra=valor_de_mercado,
            fidelidade_ate=dados.loyalty_until,
            situacao="ATIVO",
            iniciado_em=momento,
        )
        self._contratos.adicionar(contrato)

        transacao = Transacao(
            clube_id=dados.club_id,
            jogador_id=jogador_id,
            nome_jogador=jogador.nome,
            tipo="COMPRA",
            valor=valor_de_mercado,
            taxa=taxa,
            multa=Decimal("0.00"),
            lucro=None,
            variacao_caixa=-custo_total,
            criado_em=momento,
        )
        self._transacoes.adicionar(transacao)

        self._confirmar_ou_desfazer()
        return ResultadoDaCompra(transacao=transacao, contrato=contrato, clube=clube)

    def vender(self, jogador_id: int, momento: datetime) -> ResultadoDaVenda:
        jogador = self._jogadores.obter(jogador_id)
        if jogador is None:
            raise NaoEncontradoError("Jogador não encontrado.")
        if jogador.clube_id is None:
            raise ConflitoError("Jogador está livre.")

        clube_id = jogador.clube_id
        clube = self._clubes.obter(clube_id)
        contrato = self._contratos.obter_ativo_por_jogador(jogador_id)

        valor_de_mercado = calcular_indicadores(jogador).market_value
        dias_restantes, percentual = calcular_dias_restantes_e_percentual_de_multa(
            contrato.fidelidade_ate, momento
        )
        multa = calcular_multa(valor_de_mercado, percentual)
        lucro = valor_de_mercado - contrato.valor_compra
        comissao = calcular_comissao_de_venda(lucro)
        credito = calcular_credito_na_venda(valor_de_mercado, multa, comissao)

        jogador.clube_id = None
        clube.caixa += credito
        contrato.situacao = "RESCINDIDO" if multa > Decimal("0.00") else "ENCERRADO"
        contrato.encerrado_em = momento
        self._escalacoes.remover_titular(jogador_id)  # RN19.5

        transacao = Transacao(
            clube_id=clube_id,
            jogador_id=jogador_id,
            nome_jogador=jogador.nome,
            tipo="VENDA",
            valor=valor_de_mercado,
            taxa=comissao,
            multa=multa,
            lucro=lucro,
            variacao_caixa=credito,
            criado_em=momento,
        )
        self._transacoes.adicionar(transacao)

        self._confirmar_ou_desfazer()
        return ResultadoDaVenda(
            transacao=transacao,
            contrato=contrato,
            clube=clube,
            dias_restantes=dias_restantes,
            percentual_de_multa=percentual,
        )

    def historico(self, clube_id: int, filtros: FiltrosDeTransacao) -> HistoricoDeTransacoes:
        if self._clubes.obter(clube_id) is None:
            raise NaoEncontradoError("Clube não encontrado.")
        if filtros.jogador_id is not None and self._jogadores.obter(filtros.jogador_id) is None:
            raise NaoEncontradoError("Jogador não encontrado.")

        transacoes = self._transacoes.listar_por_clube(clube_id, filtros)
        return HistoricoDeTransacoes(transacoes=transacoes, resumo=self._resumo(transacoes))

    def exportar_csv(self, clube_id: int, filtros: FiltrosDeTransacao) -> str:
        """RN18: mesmos filtros e mesma ordem do histórico, em CSV (`;`, LF, UTF-8 sem BOM)."""
        historico = self.historico(clube_id, filtros)

        buffer = io.StringIO()
        writer = csv.writer(buffer, delimiter=";", quotechar='"', lineterminator="\n")
        writer.writerow(CABECALHO_CSV)
        for transacao in historico.transacoes:
            writer.writerow(
                [
                    formatar_datetime_rn01(transacao.criado_em),
                    transacao.tipo,
                    transacao.nome_jogador,
                    _formatar_valor_csv(transacao.valor),
                    _formatar_valor_csv(transacao.taxa),
                    _formatar_valor_csv(transacao.multa),
                    _formatar_valor_csv(transacao.lucro) if transacao.lucro is not None else "",
                    _formatar_valor_csv(transacao.variacao_caixa),
                ]
            )
        return buffer.getvalue()

    def _resumo(self, transacoes: list[Transacao]) -> ResumoDeTransacoes:
        compras = [t for t in transacoes if t.tipo == "COMPRA"]
        vendas = [t for t in transacoes if t.tipo == "VENDA"]
        return ResumoDeTransacoes(
            total_spent=sum((t.valor + t.taxa for t in compras), Decimal("0.00")),
            total_received=sum((t.variacao_caixa for t in vendas), Decimal("0.00")),
            total_fees=sum((t.taxa for t in transacoes), Decimal("0.00")),
            total_penalties=sum((t.multa for t in vendas), Decimal("0.00")),
            total_profit=sum((t.lucro for t in vendas if t.lucro is not None), Decimal("0.00")),
        )

    def _confirmar_ou_desfazer(self) -> None:
        try:
            self._uot.confirmar()
        except Exception:
            self._uot.desfazer()
            raise
