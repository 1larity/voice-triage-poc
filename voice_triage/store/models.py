"""store.models module."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from voice_triage.nlu.schemas import ExtractionResult


@dataclass(frozen=True)
class StoredSession:
    """Storedsession."""

    session_id: int
    started_at: datetime
    transcript: str
    extracted: ExtractionResult
    route: str
    outcome: dict[str, Any]
