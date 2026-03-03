"""nlu.schemas module."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Intent(StrEnum):
    """Intent."""

    RAG_QA = "RAG_QA"
    MOVE_HOME = "MOVE_HOME"
    ELECTORAL_REGISTER = "ELECTORAL_REGISTER"
    COUNCIL_TAX = "COUNCIL_TAX"
    UNKNOWN = "UNKNOWN"


class ExtractionResult(BaseModel):
    """Extractionresult."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent
    raw_text: str
    postcode: str | None = None
    address_line: str | None = None
    move_date: str | None = None


class CallSessionRecord(BaseModel):
    """Callsessionrecord."""

    model_config = ConfigDict(extra="forbid")

    started_at: datetime
    transcript: str
    extracted: ExtractionResult
    route: str
    outcome: dict[str, Any] = Field(default_factory=dict)
