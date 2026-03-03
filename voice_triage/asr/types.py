"""asr.types module."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AsrMetadata:
    """Asrmetadata."""

    model: str | None = None
    language: str | None = None


@dataclass(frozen=True)
class AsrResult:
    """Asrresult."""

    text: str
    metadata: AsrMetadata
