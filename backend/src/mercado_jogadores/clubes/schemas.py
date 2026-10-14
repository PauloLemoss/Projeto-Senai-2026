import re
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from mercado_jogadores.clubes.service import (
    ClubeComElenco,
    ClubeComPatrimonio,
    DadosCadastroClube,
    JogadorDoElenco,
)
from mercado_jogadores.clubes.validacao import sigla_corresponde_ao_nome
from mercado_jogadores.core.datas import formatar_datetime_rn01
from mercado_jogadores.core.validation import normalizar_texto
from mercado_jogadores.jogadores.schemas import JogadorRead

_SIGLA_BASICA = re.compile(r"^[A-Z]{3}$")


def _validar_nome_de_clube(nome: str) -> str:
    texto = normalizar_texto(nome)
    if not all(c.isalpha() or c in " -." for c in texto):
        raise ValueError("O nome só pode conter letras, espaço, hífen e ponto.")
    if not 2 <= len(texto.split(" ")) <= 5:
        raise ValueError("O nome deve ter de 2 a 5 palavras.")
    return texto


def _validar_formato_basico_da_sigla(sigla: str) -> str:
    if not isinstance(sigla, str) or not _SIGLA_BASICA.match(sigla):
        raise ValueError("A sigla deve ter exatamente 3 letras maiúsculas, sem acento.")
    return sigla


class ClubeCreate(BaseModel):
    """RN10 — "Limites de cada campo" (`name`/`acronym` do Clube)."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=3, max_length=60)
    acronym: str = Field(min_length=3, max_length=3)

    @field_validator("name", mode="before")
    @classmethod
    def _normalizar_nome(cls, v: object) -> object:
        return _validar_nome_de_clube(v) if isinstance(v, str) else v

    @field_validator("acronym", mode="before")
    @classmethod
    def _validar_sigla(cls, v: object) -> object:
        return _validar_formato_basico_da_sigla(v) if isinstance(v, str) else v

    @model_validator(mode="after")
    def _validar_sigla_corresponde_ao_nome(self) -> "ClubeCreate":
        if not sigla_corresponde_ao_nome(self.name, self.acronym):
            raise ValueError(
                "A sigla deve ser formada por três letras do nome, nessa ordem, começando pela "
                "primeira letra do nome, sem repetir a mesma letra três vezes."
            )
        return self

    def para_dados_de_cadastro(self) -> DadosCadastroClube:
        return DadosCadastroClube(nome=self.name, sigla=self.acronym)


class ClubeRead(BaseModel):
    """Campos mínimos de cada clube — resposta de `POST /clubs` e itens de `GET /clubs`."""

    id: int
    name: str
    acronym: str
    cash: Decimal
    squad_value: Decimal
    net_worth: Decimal

    @field_serializer("cash", "squad_value", "net_worth")
    def _serializar_moeda_como_numero(self, valor: Decimal) -> float:
        return float(valor)

    @classmethod
    def a_partir_do_resultado(
        cls, resultado: "ClubeComPatrimonio | ClubeComElenco"
    ) -> "ClubeRead":
        return cls(
            id=resultado.clube.id,
            name=resultado.clube.nome,
            acronym=resultado.clube.sigla,
            cash=resultado.clube.caixa,
            squad_value=resultado.squad_value,
            net_worth=resultado.net_worth,
        )


class ContratoDoElencoRead(BaseModel):
    """`contract` de cada jogador do elenco (RN11) — formato diferente do `contract` de
    `BuyRead` (sem `status`; com `remaining_days`/`penalty_rate`, calculados a cada consulta)."""

    purchase_value: Decimal
    loyalty_until: str
    remaining_days: int
    penalty_rate: int

    @field_serializer("purchase_value")
    def _serializar_moeda_como_numero(self, valor: Decimal) -> float:
        return float(valor)


class JogadorDoElencoRead(JogadorRead):
    """Jogador do elenco de `GET /clubs/{id}`: adiciona `contract`."""

    contract: ContratoDoElencoRead | None

    @classmethod
    def a_partir_do_resultado(cls, item: JogadorDoElenco) -> "JogadorDoElencoRead":
        resultado = item.calculados
        jogador = resultado.jogador
        contract = None
        if item.contract is not None:
            contract = ContratoDoElencoRead(
                purchase_value=item.contract.purchase_value,
                loyalty_until=formatar_datetime_rn01(item.contract.loyalty_until),
                remaining_days=item.contract.remaining_days,
                penalty_rate=item.contract.penalty_rate,
            )
        return cls(
            id=jogador.id,
            name=jogador.nome,
            position=jogador.posicao,  # type: ignore[arg-type]
            agility=jogador.agilidade,
            age=jogador.idade,
            condition=jogador.condicao,  # type: ignore[arg-type]
            base_value=jogador.valor_base,
            market_value=resultado.market_value,
            pace=jogador.velocidade,
            shooting=jogador.finalizacao,
            passing=jogador.passe,
            dribbling=jogador.drible,
            defending=jogador.defesa,
            physical=jogador.fisico,
            potential=jogador.potencial,
            overall=resultado.overall,
            club_id=jogador.clube_id,
            contract=contract,
        )


class ClubeComElencoRead(ClubeRead):
    """`GET /clubs/{id}`: adiciona o elenco, com o `contract` de cada jogador (RN11)."""

    players: list[JogadorDoElencoRead]

    @classmethod
    def a_partir_do_resultado(cls, resultado: ClubeComElenco) -> "ClubeComElencoRead":
        return cls(
            id=resultado.clube.id,
            name=resultado.clube.nome,
            acronym=resultado.clube.sigla,
            cash=resultado.clube.caixa,
            squad_value=resultado.squad_value,
            net_worth=resultado.net_worth,
            players=[
                JogadorDoElencoRead.a_partir_do_resultado(item) for item in resultado.elenco
            ],
        )
