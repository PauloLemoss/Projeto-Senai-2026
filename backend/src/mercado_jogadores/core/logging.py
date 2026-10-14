"""Registro de logs por requisição (barema B5, "Registro de logs"): uma linha legível, com
data/hora, método, caminho e status, por requisição HTTP — via `structlog`, nunca `print`."""

import logging

import structlog


def configurar_logging() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="%Y-%m-%d %H:%M:%S"),
            structlog.processors.KeyValueRenderer(key_order=["event", "method", "path", "status"]),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
    )


def obter_logger() -> structlog.stdlib.BoundLogger:
    return structlog.get_logger("mercado_jogadores.requisicoes")
