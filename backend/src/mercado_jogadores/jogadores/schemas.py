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
    JogadorComCalculados,
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
