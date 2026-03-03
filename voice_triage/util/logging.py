"""util.logging module."""

from __future__ import annotations

import logging


def setup_logging(level: str = "INFO") -> None:
    """Set a compact structured-ish log format for local debugging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s level=%(levelname)s name=%(name)s msg=%(message)s",
    )
