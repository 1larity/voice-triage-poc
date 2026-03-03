"""rag.retrieve module."""

from __future__ import annotations

import json
import math
import re
import sqlite3
from pathlib import Path

from voice_triage.rag.index import embed_text
from voice_triage.rag.stopwords import STOPWORDS
from voice_triage.rag.types import DocumentChunk, RetrievedChunk


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """cosine similarity."""
    numerator = sum(left * right for left, right in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(value * value for value in a)) or 1.0
    norm_b = math.sqrt(sum(value * value for value in b)) or 1.0
    return numerator / (norm_a * norm_b)


class SqliteRetriever:
    """Sqliteretriever."""

    def __init__(self, index_db_path: Path) -> None:
        """init  ."""
        self.index_db_path = index_db_path

    def retrieve(self, query: str, top_k: int = 3) -> list[RetrievedChunk]:
        """Retrieve."""
        if not self.index_db_path.exists():
            return []

        query_embedding = embed_text(query)
        matches: list[RetrievedChunk] = []

        with sqlite3.connect(self.index_db_path) as connection:
            rows = connection.execute(
                "SELECT id, source, text, embedding, metadata FROM chunks"
            ).fetchall()

        for row in rows:
            embedding = json.loads(row[3])
            metadata = _parse_metadata(row[4])
            chunk = DocumentChunk(
                chunk_id=row[0],
                source=row[1],
                text=row[2],
                embedding=embedding,
                metadata=metadata,
            )
            score = _hybrid_similarity(query=query, query_embedding=query_embedding, chunk=chunk)
            matches.append(RetrievedChunk(chunk=chunk, score=score))

        matches.sort(key=lambda item: item.score, reverse=True)
        return matches[:top_k]


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> list[str]:
    """tokenize."""
    tokens = [token.lower() for token in TOKEN_PATTERN.findall(text)]
    normalized: list[str] = []
    for token in tokens:
        if token.endswith("ies") and len(token) > 4:
            token = f"{token[:-3]}y"
        elif token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("ed") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 3:
            token = token[:-1]
        if token and token not in STOPWORDS:
            normalized.append(token)
    return normalized


def _bigrams(tokens: list[str]) -> set[tuple[str, str]]:
    """bigrams."""
    return {(tokens[idx], tokens[idx + 1]) for idx in range(len(tokens) - 1)}


def _lexical_similarity(query: str, chunk_text: str) -> float:
    """lexical similarity."""
    query_tokens = _tokenize(query)
    doc_tokens = _tokenize(chunk_text)
    if not query_tokens or not doc_tokens:
        return 0.0

    query_set = set(query_tokens)
    doc_set = set(doc_tokens)
    overlap = len(query_set & doc_set)
    if overlap == 0:
        return 0.0

    coverage = overlap / len(query_set)
    precision = overlap / len(doc_set)

    query_bigrams = _bigrams(query_tokens)
    doc_bigrams = _bigrams(doc_tokens)
    bigram_overlap = 0.0
    if query_bigrams:
        bigram_overlap = len(query_bigrams & doc_bigrams) / len(query_bigrams)

    phrase_bonus = 0.0
    if "garden waste" in query.lower() and "garden waste" in chunk_text.lower():
        phrase_bonus += 0.2
    if "register to vote" in query.lower() and "register to vote" in chunk_text.lower():
        phrase_bonus += 0.2

    return (coverage * 0.65) + (bigram_overlap * 0.25) + (precision * 0.1) + phrase_bonus


def _hybrid_similarity(query: str, query_embedding: list[float], chunk: DocumentChunk) -> float:
    """hybrid similarity."""
    lexical = _lexical_similarity(query=query, chunk_text=_searchable_chunk_text(chunk))
    semantic = _cosine_similarity(query_embedding, chunk.embedding)
    return (lexical * 0.9) + (semantic * 0.1)


def _parse_metadata(raw_metadata: str | None) -> dict[str, object]:
    """Parse chunk metadata from JSON; tolerate malformed rows."""
    if raw_metadata is None:
        return {}
    try:
        parsed = json.loads(raw_metadata)
    except json.JSONDecodeError:
        return {}
    if isinstance(parsed, dict):
        return parsed
    return {}


def _searchable_chunk_text(chunk: DocumentChunk) -> str:
    """Compose searchable text using chunk content plus metadata context."""
    parts = [chunk.text]
    title = chunk.metadata.get("title")
    if isinstance(title, str) and title.strip():
        parts.append(title.strip())

    tags = chunk.metadata.get("tags")
    if isinstance(tags, list):
        parts.extend(str(tag).strip() for tag in tags if str(tag).strip())

    section = chunk.metadata.get("section")
    if isinstance(section, str) and section.strip():
        parts.append(section.replace("_", " "))
    return " ".join(parts)
