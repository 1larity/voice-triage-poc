"""rag.index module."""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path
from typing import Any


def _create_chunks_table(connection: sqlite3.Connection, table_name: str) -> None:
    """Create a chunk table with the canonical schema."""
    connection.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id TEXT PRIMARY KEY,
            source TEXT NOT NULL,
            text TEXT NOT NULL,
            embedding TEXT NOT NULL,
            metadata TEXT NOT NULL DEFAULT '{{}}'
        )
        """
    )


def init_index(index_db_path: Path) -> None:
    """Initialize sqlite tables used for local RAG chunks."""
    index_db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(index_db_path) as connection:
        _create_chunks_table(connection, "chunks")
        columns = {
            str(row[1]).strip().lower()
            for row in connection.execute("PRAGMA table_info(chunks)").fetchall()
        }
        if "metadata" not in columns:
            connection.execute(
                "ALTER TABLE chunks ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'"
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


_SECTION_HEADER_PATTERN = re.compile(r"^([a-z][a-z0-9_ ]{1,40}):\s*$", flags=re.IGNORECASE)
_EXCLUDED_STRUCTURED_SECTIONS = {"demo_questions"}


def extract_structured_units(text: str) -> list[dict[str, Any]]:
    """Extract bullet-level units from structured knowledge base markdown."""
    title = ""
    tags: list[str] = []
    sections: dict[str, list[str]] = {}
    current_section: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        lowered = line.lower()

        if lowered.startswith("title:"):
            title = line.split(":", 1)[1].strip()
            current_section = None
            continue

        if lowered.startswith("tags:"):
            raw_tags = line.split(":", 1)[1].strip()
            raw_tags = raw_tags.strip("[]")
            tags = [token.strip().lower() for token in raw_tags.split(",") if token.strip()]
            current_section = None
            continue

        section_match = _SECTION_HEADER_PATTERN.match(line)
        if section_match:
            current_section = section_match.group(1).strip().lower().replace(" ", "_")
            sections.setdefault(current_section, [])
            continue

        if line.startswith("- ") and current_section:
            item = line[2:].strip()
            if item:
                sections[current_section].append(item)

    units: list[dict[str, Any]] = []
    for section, items in sections.items():
        if section in _EXCLUDED_STRUCTURED_SECTIONS:
            continue
        for idx, item in enumerate(items):
            search_parts = [item]
            if title:
                search_parts.append(title)
            if tags:
                search_parts.extend(tags)
            search_parts.append(section.replace("_", " "))

            units.append(
                {
                    "id_suffix": f"{section}::{idx}",
                    "text": item,
                    "search_text": " | ".join(search_parts),
                    "metadata": {
                        "title": title,
                        "tags": tags,
                        "section": section,
                        "bullet_index": idx,
                    },
                }
            )
    return units


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

    try:
        with sqlite3.connect(index_db_path, timeout=0.2) as connection:
            connection.execute("PRAGMA busy_timeout = 200")
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DROP TABLE IF EXISTS chunks_staging")
            _create_chunks_table(connection, "chunks_staging")

            for source_path in sorted(kb_dir.rglob("*")):
                if not source_path.is_file() or source_path.suffix.lower() not in {".txt", ".md"}:
                    continue

                source_text = source_path.read_text(encoding="utf-8", errors="ignore")
                source_rel_path = source_path.relative_to(kb_dir).as_posix()
                structured_units = extract_structured_units(source_text)

                if structured_units:
                    units = structured_units
                else:
                    units = [
                        {
                            "id_suffix": str(idx),
                            "text": piece,
                            "search_text": piece,
                            "metadata": {},
                        }
                        for idx, piece in enumerate(chunk_text(source_text))
                    ]

                for unit in units:
                    chunk_id = f"{source_rel_path}::{unit['id_suffix']}"
                    embedding = embed_text(str(unit["search_text"]))
                    connection.execute(
                        (
                            "INSERT INTO chunks_staging (id, source, text, embedding, metadata) "
                            "VALUES (?, ?, ?, ?, ?)"
                        ),
                        (
                            chunk_id,
                            source_rel_path,
                            str(unit["text"]),
                            json.dumps(embedding),
                            json.dumps(unit["metadata"]),
                        ),
                    )
                    chunk_count += 1

            connection.execute("DELETE FROM chunks")
            connection.execute(
                
                    "INSERT INTO chunks (id, source, text, embedding, metadata) "
                    "SELECT id, source, text, embedding, metadata FROM chunks_staging"
                
            )
            connection.execute("DROP TABLE chunks_staging")
    except sqlite3.OperationalError as exc:
        if "database is locked" in str(exc).lower():
            raise RuntimeError("Reindex already in progress. Please wait and retry.") from exc
        raise

    return chunk_count
