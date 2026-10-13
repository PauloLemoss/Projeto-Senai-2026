import re
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import (
    BaseModel,
    BeforeValidator,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)

from mercado_jogadores.core.validation import normalizar_texto
from mercado_jogadores.jogadores.service import (
    DadosCadastroJogador,
    DadosEdicaoJogador,
    FiltrosDeListagem,
    JogadorComCalculados,
    ListaDeJogadores,
)

Posicao = Literal["GOL", "ZAG", "LAT", "MEI", "ATA"]
Condicao = Literal["APTO", "MAL_CONDICIONADO", "DOENTE"]

_ATRIBUTOS = ("pace", "shooting", "passing", "dribbling", "defending", "physical")


def _validar_nome_de_jogador(nome: str) -> str:
    texto = normalizar_texto(nome)
    if any(c.isdigit() for c in texto):
        raise ValueError("O nome não pode conter dígitos.")
    if len(texto.split(" ")) < 2:
        raise ValueError("O nome precisa ter pelo menos duas palavras.")
    return texto


def _validar_inteiro_json(valor: object) -> object:
    """V2: número é número JSON — `15` é aceito, `"15"` (texto) é recusado; `50.5` é recusado
    e `50.0` vale 50. Sem isso, o Pydantic coagiria string numérica para int por padrão."""
    if isinstance(valor, bool):
        raise ValueError("Valor deve ser um número inteiro, não booleano.")
    if isinstance(valor, int):
        return valor
    if isinstance(valor, float):
        if valor.is_integer():
            return int(valor)
        raise ValueError("Valor inteiro não pode ter parte fracionária.")
    raise ValueError("Valor deve ser um número.")


InteiroEstrito = Annotated[int, BeforeValidator(_validar_inteiro_json)]


class JogadorCreate(BaseModel):
    """V1–V7 e os limites de campo de "Cadastro de Jogadores" do enunciado."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=3, max_length=100)
    position: Posicao
    agility: InteiroEstrito = Field(ge=1, le=100)
    age: InteiroEstrito = Field(ge=16, le=45)
    pace: InteiroEstrito = Field(ge=1, le=99)
    shooting: InteiroEstrito = Field(ge=1, le=99)
    passing: InteiroEstrito = Field(ge=1, le=99)
    dribbling: InteiroEstrito = Field(ge=1, le=99)
    defending: InteiroEstrito = Field(ge=1, le=99)
    physical: InteiroEstrito = Field(ge=1, le=99)
    potential: InteiroEstrito = Field(ge=1, le=99)

    @field_validator("name", mode="before")
    @classmethod
    def _normalizar_nome(cls, v: object) -> object:
        return _validar_nome_de_jogador(v) if isinstance(v, str) else v

    @model_validator(mode="after")
    def _validar_regras_cruzadas(self) -> "JogadorCreate":
        if self.age >= 35 and self.agility > 85:
            raise ValueError("Com 35 anos ou mais, a agilidade máxima é 85.")

        soma_atributos = sum(getattr(self, nome) for nome in _ATRIBUTOS)
        if soma_atributos > 480:
            raise ValueError("A soma dos seis atributos não pode passar de 480.")

        maior_atributo = max(getattr(self, nome) for nome in _ATRIBUTOS)
        if self.potential < maior_atributo:
            raise ValueError("O potencial não pode ser menor que o maior atributo.")
        if self.age >= 33 and self.potential != maior_atributo:
            raise ValueError(
                "No cadastro de jogador com 33 anos ou mais, o potencial deve ser igual ao "
                "maior atributo."
            )
        return self

    def para_dados_de_cadastro(self) -> DadosCadastroJogador:
        return DadosCadastroJogador(
            nome=self.name,
            posicao=self.position,
            agilidade=self.agility,
            idade=self.age,
            pace=self.pace,
            shooting=self.shooting,
            passing=self.passing,
            dribbling=self.dribbling,
            defending=self.defending,
            physical=self.physical,
            potential=self.potential,
        )


class JogadorUpdate(BaseModel):
    """RN08: o PUT exige os quatro campos, mesmo que só um mude."""

    model_config = ConfigDict(extra="ignore")

    name: str = Field(min_length=3, max_length=100)
    position: Posicao
    agility: InteiroEstrito = Field(ge=1, le=100)
    age: InteiroEstrito = Field(ge=16, le=45)

    @field_validator("name", mode="before")
    @classmethod
    def _normalizar_nome(cls, v: object) -> object:
        return _validar_nome_de_jogador(v) if isinstance(v, str) else v

    @model_validator(mode="after")
    def _validar_agilidade_pela_idade(self) -> "JogadorUpdate":
        if self.age >= 35 and self.agility > 85:
            raise ValueError("Com 35 anos ou mais, a agilidade máxima é 85.")
        return self

    def para_dados_de_edicao(self) -> DadosEdicaoJogador:
        return DadosEdicaoJogador(
            nome=self.name, posicao=self.position, agilidade=self.agility, idade=self.age
        )


class CondicaoUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    condition: Condicao


class JogadorRead(BaseModel):
    """Formato de resposta de todo endpoint que devolve um jogador (ver 2.1.2 do enunciado)."""

    id: int
    name: str
    position: Posicao
    agility: int
    age: int
    condition: Condicao
    base_value: Decimal
    market_value: Decimal
    pace: int
    shooting: int
    passing: int
    dribbling: int
    defending: int
    physical: int
    potential: int
    overall: int
    club_id: int | None

    @field_serializer("base_value", "market_value")
    def _serializar_moeda_como_numero(self, valor: Decimal) -> float:
        """Convenções da API: "Valores são números JSON" — Decimal vira string por padrão no
        Pydantic, o que violaria essa regra (a resposta traria "40.00" em vez de 40.00)."""
        return float(valor)

    @classmethod
    def a_partir_do_resultado(cls, resultado: JogadorComCalculados) -> "JogadorRead":
        jogador = resultado.jogador
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
        )


# ---------------------------------------------------------------------------
# Listagem (RN07) — query params chegam sempre como string; os formatos abaixo são os da
# query string (V2 de corpo JSON não se aplica aqui), por isso não reusam InteiroEstrito.
# ---------------------------------------------------------------------------

_INTEIRO_DE_QUERY = re.compile(r"^[1-9][0-9]*$")
_DECIMAL_DE_QUERY = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]{1,2})?$")
CampoDeOrdenacao = Literal["name", "value_asc", "value_desc", "age_asc", "age_desc", "position"]
_SORT_VALIDOS = frozenset(
    ("name", "value_asc", "value_desc", "age_asc", "age_desc", "position")
)


def _campo_de_sort(token: str) -> str:
    if token in ("value_asc", "value_desc"):
        return "value"
    if token in ("age_asc", "age_desc"):
        return "age"
    return token


def _validar_inteiro_de_query(valor: object) -> object:
    if valor is None or isinstance(valor, int):
        return valor
    if not isinstance(valor, str):
        raise ValueError("Valor deve ser um inteiro positivo.")
    if valor == "":
        raise ValueError("Valor não pode ser vazio.")
    if not _INTEIRO_DE_QUERY.match(valor):
        raise ValueError("Valor deve ser um inteiro positivo, sem zeros à esquerda.")
    return int(valor)


def _validar_decimal_de_query(valor: object) -> object:
    if valor is None or isinstance(valor, Decimal):
        return valor
    if not isinstance(valor, str):
        raise ValueError("Valor deve ser um decimal válido.")
    if valor == "":
        raise ValueError("Valor não pode ser vazio.")
    if not _DECIMAL_DE_QUERY.match(valor):
        raise ValueError("Valor deve ser um decimal válido (ex.: 10, 10.5, 10.55).")
    return Decimal(valor)


InteiroDeQuery = Annotated[int, BeforeValidator(_validar_inteiro_de_query)]
DecimalDeQuery = Annotated[Decimal, BeforeValidator(_validar_decimal_de_query)]


class JogadorListQuery(BaseModel):
    """Query params de `GET /players` (RN07, "1. Filtros e query params aceitos")."""

    model_config = ConfigDict(extra="ignore")

    search: str | None = Field(default=None, min_length=2, max_length=100)
    position: Posicao | None = None
    condition: Condicao | None = None
    free: bool | None = None
    club_id: InteiroDeQuery | None = Field(default=None, le=2_147_483_647)
    min_age: InteiroDeQuery | None = Field(default=None, ge=16, le=45)
    max_age: InteiroDeQuery | None = Field(default=None, ge=16, le=45)
    min_value: DecimalDeQuery | None = Field(default=None, ge=0, le=550)
    max_value: DecimalDeQuery | None = Field(default=None, ge=0, le=550)
    sort: str = Field(default="name")
    page: InteiroDeQuery = Field(default=1)
    limit: InteiroDeQuery = Field(default=10, ge=1, le=50)

    @field_validator("search", mode="before")
    @classmethod
    def _normalizar_search(cls, v: object) -> object:
        return normalizar_texto(v) if isinstance(v, str) else v

    @field_validator("free", mode="before")
    @classmethod
    def _validar_free(cls, v: object) -> object:
        if v is None or isinstance(v, bool):
            return v
        if v == "true":
            return True
        if v == "false":
            return False
        raise ValueError("free deve ser 'true' ou 'false'.")

    @field_validator("sort", mode="before")
    @classmethod
    def _validar_sort(cls, v: object) -> object:
        """Fica como string validada (não vira lista aqui): o suporte do FastAPI a "Pydantic
        model como query params" roda a validação em mais de uma passagem, e um validator que
        devolvesse um tipo diferente do campo (lista) quebraria na segunda passagem, recebendo
        de volta o que ele mesmo gerou da primeira vez."""
        if v is None:
            v = "name"
        if not isinstance(v, str) or v == "":
            raise ValueError("sort inválido.")
        tokens = v.split(",")
        if len(tokens) > 2:
            raise ValueError("sort aceita no máximo dois critérios.")
        for token in tokens:
            if token not in _SORT_VALIDOS:
                raise ValueError(f"sort inválido: {token}.")
        campos = [_campo_de_sort(token) for token in tokens]
        if len(campos) != len(set(campos)):
            raise ValueError("sort não pode repetir o mesmo campo.")
        return v

    @model_validator(mode="after")
    def _validar_combinacoes(self) -> "JogadorListQuery":
        if self.min_age is not None and self.max_age is not None and self.min_age > self.max_age:
            raise ValueError("min_age não pode ser maior que max_age.")
        if (
            self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value não pode ser maior que max_value.")
        if self.free is True and self.club_id is not None:
            raise ValueError("free=true não pode ser combinado com club_id.")
        return self

    def para_filtros_de_listagem(self) -> FiltrosDeListagem:
        return FiltrosDeListagem(
            search=self.search,
            position=self.position,
            condition=self.condition,
            free=self.free,
            club_id=self.club_id,
            min_age=self.min_age,
            max_age=self.max_age,
            min_value=self.min_value,
            max_value=self.max_value,
            sort=self.sort.split(","),
            page=self.page,
            limit=self.limit,
        )


class PaginationMeta(BaseModel):
    page: int
    limit: int
    total_items: int
    total_pages: int


class PlayerListResponse(BaseModel):
    data: list[JogadorRead]
    meta: PaginationMeta

    @classmethod
    def a_partir_do_resultado(cls, resultado: ListaDeJogadores) -> "PlayerListResponse":
        return cls(
            data=[JogadorRead.a_partir_do_resultado(item) for item in resultado.itens],
            meta=PaginationMeta(
                page=resultado.page,
                limit=resultado.limit,
                total_items=resultado.total_items,
                total_pages=resultado.total_pages,
            ),
        )
