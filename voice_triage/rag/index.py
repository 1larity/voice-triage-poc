"""rag.index module."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
from pathlib import Path


def init_index(index_db_path: Path) -> None:
    """Initialize sqlite tables used for local RAG chunks."""
    index_db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(index_db_path) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                text TEXT NOT NULL,
                embedding TEXT NOT NULL
            )
            """
        )


def chunk_text(text: str, max_chars: int = 500, overlap: int = 80) -> list[str]:
    """Chunk text."""
    normalized = " ".join(text.split())
    if not normalized:
        return []

    words = normalized.split(" ")
    if not words:
        return []

    chunks: list[str] = []
    index = 0
    while index < len(words):
        current_words: list[str] = []
        char_count = 0
        cursor = index

        while cursor < len(words):
            token = words[cursor]
            projected = char_count + len(token) + (1 if current_words else 0)
            if projected > max_chars and current_words:
                break
            current_words.append(token)
            char_count = projected
            cursor += 1

        if not current_words:
            current_words.append(words[cursor])
            cursor += 1

        chunks.append(" ".join(current_words))
        if cursor >= len(words):
            break

        overlap_chars = 0
        overlap_words = 0
        for token in reversed(current_words):
            overlap_chars += len(token) + 1
            overlap_words += 1
            if overlap_chars >= overlap:
                break

        index = max(index + 1, cursor - overlap_words)
    return chunks


def embed_text(text: str, dims: int = 16) -> list[float]:
    """Deterministic stub embedding based on SHA-256."""
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = [((digest[i] / 255.0) * 2.0) - 1.0 for i in range(dims)]
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


def build_index(kb_dir: Path, index_db_path: Path) -> int:
    """Build or refresh chunk index from ./kb local files."""
    init_index(index_db_path)

    chunk_count = 0
    kb_dir.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(index_db_path) as connection:
        connection.execute("DELETE FROM chunks")

        for source_path in sorted(kb_dir.rglob("*")):
            if not source_path.is_file() or source_path.suffix.lower() not in {".txt", ".md"}:
                continue

            source_text = source_path.read_text(encoding="utf-8", errors="ignore")
            pieces = chunk_text(source_text)
            for idx, piece in enumerate(pieces):
                chunk_id = f"{source_path.relative_to(kb_dir).as_posix()}::{idx}"
                embedding = embed_text(piece)
                connection.execute(
                    "INSERT INTO chunks (id, source, text, embedding) VALUES (?, ?, ?, ?)",
                    (
                        chunk_id,
                        source_path.relative_to(kb_dir).as_posix(),
                        piece,
                        json.dumps(embedding),
                    ),
                )
                chunk_count += 1

    return chunk_count
