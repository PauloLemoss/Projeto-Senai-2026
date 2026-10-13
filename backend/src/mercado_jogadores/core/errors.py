class ErroDeDominio(Exception):
    """Base para exceções que o service levanta e o exception handler traduz em HTTP."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class NaoEncontradoError(ErroDeDominio):
    """Recurso inexistente ou id fora do formato aceito (V8) -> 404."""


class ConflitoError(ErroDeDominio):
    """Regra de negócio violada (V9) -> 409."""


class RequisicaoInvalidaError(ErroDeDominio):
    """Dado, formato ou parâmetro inválido (V9) -> 400."""
