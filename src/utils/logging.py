"""Structured logging configuration for the research agent.

Replaces ad-hoc `print()` calls throughout the codebase with
proper module-level loggers supporting DEBUG/INFO/WARNING/ERROR levels.

Usage:
    from src.utils.logging import get_logger
    logger = get_logger(__name__)
    logger.info("Processing %d items", count)
    logger.warning("Rate limit approached: %s", msg)
    logger.error("Failed to fetch paper: %s", exc_info=True)

In production (Docker), logs go to stderr. In development, they print
to stdout with colored formatting.
"""

import logging
import sys
from typing import Optional

# Module-level flag to ensure config is applied once
_configured = False


def configure_logging(
    level: int = logging.INFO,
    fmt: Optional[str] = None,
    force: bool = False,
) -> None:
    """Configure the root logger once.

    Args:
        level: Logging level (default: INFO).
        fmt: Optional custom format string.
        force: Reconfigure even if already configured.
    """
    global _configured
    if _configured and not force:
        return
    _configured = True

    if fmt is None:
        fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))

    root = logging.getLogger()
    root.setLevel(level)
    # Avoid duplicate handlers on re-config
    if not force:
        if any(isinstance(h, logging.StreamHandler) for h in root.handlers):
            return
    root.handlers.clear()
    root.addHandler(handler)


def get_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """Get a logger for the given module name.

    Ensures the root logger is configured on first call.

    Args:
        name: Usually ``__name__`` from the calling module.
        level: Optional per-logger level override.

    Returns:
        A configured Logger instance.
    """
    configure_logging()
    logger = logging.getLogger(name)
    if level is not None:
        logger.setLevel(level)
    return logger


# Convenience: pre-configure on import so ``from src.utils.logging import logger`` works
# for modules that want a single shared logger (less granular than get_logger).
logger = get_logger("cs599")