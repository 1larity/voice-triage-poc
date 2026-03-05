"""Base utilities for telephony configuration.

This module provides helper functions and base utilities used across
all telephony provider configurations.
"""

from __future__ import annotations

import os


def _env_bool(name: str, default: bool) -> bool:
    """Parse boolean environment variable.

    Args:
        name: Environment variable name.
        default: Default value if not set.

    Returns:
        Parsed boolean value.
    """
    raw = os.getenv(name)
    if raw is None:
        return default
    normalized = raw.strip().lower()
    return normalized in {"1", "true", "yes", "on"}
