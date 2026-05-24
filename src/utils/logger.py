"""
Logging centralizado para CloudMetrics pipeline.
Todos los módulos deben importar get_logger desde aquí.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from dotenv import load_dotenv
from loguru import logger

if TYPE_CHECKING:
    from loguru import Logger

load_dotenv()

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOGS_DIR = _PROJECT_ROOT / "logs"
_LOGS_DIR.mkdir(exist_ok=True)

_LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO").upper()

_CONSOLE_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{extra[module]}</cyan> | "
    "{message}"
)
_FILE_FORMAT = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {extra[module]} | {message}"

# Configuración base: eliminar el handler por defecto de loguru
logger.remove()

# Handler de consola con colores
logger.add(
    sys.stdout,
    format=_CONSOLE_FORMAT,
    level=_LOG_LEVEL,
    colorize=True,
    filter=lambda record: "module" in record["extra"],
)

# Handler de archivo rotado diariamente
logger.add(
    _LOGS_DIR / "pipeline_{time:YYYY-MM-DD}.log",
    format=_FILE_FORMAT,
    level=_LOG_LEVEL,
    rotation="00:00",       # nuevo archivo cada día a medianoche
    retention="30 days",
    encoding="utf-8",
    filter=lambda record: "module" in record["extra"],
)


def get_logger(module_name: str) -> Logger:
    """Retorna un logger configurado con el nombre del módulo como contexto.

    Args:
        module_name: Nombre del módulo o script que llama al logger.
            Recomendado: usar __name__ o un string descriptivo corto
            (ej. "crm_ingestion", "quality_checks").

    Returns:
        Logger de loguru con el campo `module` fijado en el contexto,
        listo para usar con .info(), .warning(), .error(), etc.

    Example:
        >>> log = get_logger(__name__)
        >>> log.info("Iniciando ingesta CRM")
        2026-05-23 12:00:00 | INFO     | src.ingestion.crm_ingestion | Iniciando ingesta CRM
    """
    return logger.bind(module=module_name)
