"""rag.answer module."""

from __future__ import annotations

import re
from typing import Any, Protocol

from voice_triage.rag.retrieve import SqliteRetriever


class RagService(Protocol):
    """Ragservice."""

    def answer(self, question: str) -> tuple[str, dict[str, Any]]:
        """Return answer text plus route metadata."""


class LocalRagService:
    """Localragservice."""

    def __init__(self, retriever: SqliteRetriever) -> None:
        """init  ."""
        self.retriever = retriever

    def answer(self, question: str) -> tuple[str, dict[str, Any]]:
        """Answer."""
        results = self.retriever.retrieve(question)
        if not results:
            return (
                "I don't have that information in the KB yet.",
                {"hits": [], "used_kb": False},
            )

        best = results[0]
        if best.score < 0.2:
            return (
                "I don't have that information in the KB yet.",
                {
                    "hits": [
                        {
                            "chunk_id": best.chunk.chunk_id,
                            "source": best.chunk.source,
                            "score": best.score,
                        }
                    ],
                    "used_kb": False,
                    "reason": "low_relevance",
                },
            )

        answer = _render_answer_from_chunk(best.chunk.text)
        metadata = {
            "used_kb": True,
            "hits": [
                {
                    "chunk_id": result.chunk.chunk_id,
                    "source": result.chunk.source,
                    "score": result.score,
                }
                for result in results
            ],
        }
        return answer, metadata


def _render_answer_from_chunk(text: str) -> str:
    """render answer from chunk."""
    cleaned = _fix_common_mojibake(" ".join(text.split()).strip())
    summary_items = _extract_section_bullets(cleaned, "summary")
    key_items = _extract_section_bullets(cleaned, "key_points")

    selected: list[str] = []
    for item in summary_items:
        if item not in selected:
            selected.append(item)
        if len(selected) >= 2:
            break
    for item in key_items:
        if item not in selected:
            selected.append(item)
        if len(selected) >= 2:
            break

    if selected:
        normalized = " ".join(_ensure_sentence(item) for item in selected)
        return _truncate(normalized, max_chars=280)

    fallback = re.sub(r"\btitle:\s*.+?(?=\b\w+:\s|$)", "", cleaned, flags=re.IGNORECASE)
    fallback = re.sub(r"\btags:\s*\[[^\]]*\]", "", fallback, flags=re.IGNORECASE)
    fallback = re.sub(r"\bdemo_questions:\s*.+$", "", fallback, flags=re.IGNORECASE)
    fallback = fallback.strip(" -;,:")
    if not fallback:
        return "I don't have that information in the KB yet."
    return _truncate(_ensure_sentence(fallback), max_chars=280)


def _extract_section_bullets(text: str, section: str) -> list[str]:
    """extract section bullets."""
    pattern = rf"\b{section}:\s*(.+?)(?=\b\w+:\s|$)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if match is None:
        return []
    block = match.group(1).strip()
    if not block:
        return []
    parts = [part.strip() for part in re.split(r"\s+-\s+", block) if part.strip()]
    if parts and not block.startswith("-"):
        parts = parts[1:]
    cleaned = [re.sub(r"\s+", " ", part).strip(" -;,:") for part in parts]
    return [item for item in cleaned if item]


def _ensure_sentence(text: str) -> str:
    """ensure sentence."""
    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return ""
    if normalized[-1] in ".!?":
        return normalized
    return f"{normalized}."


def _truncate(text: str, max_chars: int) -> str:
    """truncate."""
    if len(text) <= max_chars:
        return text
    truncated = text[: max_chars - 1].rstrip()
    return f"{truncated}..."


def _fix_common_mojibake(text: str) -> str:
    """fix common mojibake."""
    replacements = {
        "\u00e2\u20ac\u2122": "'",
        "\u00e2\u20ac\u02dc": "'",
        "\u00e2\u20ac\u0153": '"',
        "\u00e2\u20ac\u009d": '"',
        "\u00e2\u20ac\u201d": "-",
        "\u00e2\u20ac\u201c": "-",
        "\u00c2\u00a3": "£",
        "\u00c2": "",
    }
    fixed = text
    for source, target in replacements.items():
        fixed = fixed.replace(source, target)
    return fixed
