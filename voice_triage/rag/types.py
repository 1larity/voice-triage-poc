"""rag.types module."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class DocumentChunk:
    """Documentchunk."""

    chunk_id: str
    source: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RetrievedChunk:
    """Retrievedchunk."""

    chunk: DocumentChunk
    score: float
