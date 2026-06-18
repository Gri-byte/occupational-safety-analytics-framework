"""
Logging configuration for the HSE Analytics Framework.

Usage anywhere in the package::

    from utils.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Pipeline started")
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

_FORMATTER = logging.Formatter(
    fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)


def get_logger(name: str, log_file: Path | None = None) -> logging.Logger:
    """Return a logger with console + optional file handlers."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    console = logging.StreamHandler(sys.stdout)
    console.setLevel(logging.INFO)
    console.setFormatter(_FORMATTER)
    logger.addHandler(console)

    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(_FORMATTER)
        logger.addHandler(fh)

    return logger