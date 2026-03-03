"""rag.answer module."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Protocol

from voice_triage.rag.retrieve import SqliteRetriever
from voice_triage.rag.stopwords import STOPWORDS


class RagService(Protocol):
    """Ragservice."""

    def answer(self, question: str) -> tuple[str, dict[str, Any]]:
        """Return answer text plus route metadata."""


class LocalRagService:
    """Localragservice."""

    def __init__(self, retriever: SqliteRetriever, config: RagAnswerConfig | None = None) -> None:
        """init  ."""
        self.retriever = retriever
        self.config = config or RagAnswerConfig()

    def answer(self, question: str) -> tuple[str, dict[str, Any]]:
        """Answer."""
        results = self.retriever.retrieve(question, top_k=self.config.retrieval_top_k)
        if not results:
            return (
                UNKNOWN_KNOWLEDGE_BASE_RESPONSE,
                {"hits": [], "used_kb": False},
            )

        best = results[0]
        if best.score < self.config.relevance_threshold:
            return (
                UNKNOWN_KNOWLEDGE_BASE_RESPONSE,
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

        answer = _render_targeted_answer(question=question, results=results, config=self.config)
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


@dataclass(frozen=True)
class RagAnswerConfig:
    """Tunable settings for local knowledge base answer rendering."""

    retrieval_top_k: int = 6
    relevance_threshold: float = 0.2
    focus_weight: float = 0.55
    section_boost: float = 0.06
    score_drop_threshold: float = 0.18
    max_answer_chars: int = 280
    boosted_sections: frozenset[str] = field(
        default_factory=lambda: frozenset({"key_points", "summary"})
    )


UNKNOWN_KNOWLEDGE_BASE_RESPONSE = (
    "Sorry, I do not have an answer for that yet. "
    "Please try asking in a different way, or ask about council services such as bins, parking, "
    "housing, planning, registrars, and governance."
)


def _render_targeted_answer(question: str, results: list[Any], config: RagAnswerConfig) -> str:
    """Render a concise answer focused on query-matching sub-topics."""
    question_tokens = _tokenize(question)
    candidates: list[tuple[float, str]] = []

    for result in results:
        section = str(result.chunk.metadata.get("section", "")).lower()
        if section == "demo_questions":
            continue
        text = _normalize_answer_text(result.chunk.text)
        if not text:
            continue
        focused_text = _focus_text_to_query(text=text, question_tokens=question_tokens)
        focus = _focus_score(question_tokens, focused_text)
        section_boost = config.section_boost if section in config.boosted_sections else 0.0
        combined = result.score + (focus * config.focus_weight) + section_boost
        candidates.append((combined, focused_text))

    if not candidates:
        return UNKNOWN_KNOWLEDGE_BASE_RESPONSE

    candidates.sort(key=lambda item: item[0], reverse=True)
    selected: list[str] = []
    top_score = candidates[0][0]
    for score, text in candidates:
        if text in selected:
            continue
        if selected and score < (top_score - config.score_drop_threshold):
            continue
        selected.append(text)
        if len(selected) >= 2:
            break

    if selected:
        normalized = " ".join(_ensure_sentence(item) for item in selected)
        return _truncate(normalized, max_chars=config.max_answer_chars)

    return UNKNOWN_KNOWLEDGE_BASE_RESPONSE


def _normalize_answer_text(text: str) -> str:
    """Normalize chunk text into concise, user-facing sentence fragments."""
    cleaned = _fix_common_mojibake(" ".join(text.split()).strip())
    cleaned = re.sub(r"\b(title|tags|summary|key_points|demo_questions)\s*:\s*", "", cleaned)
    cleaned = cleaned.strip(" -;,:")
    return cleaned


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


def _tokenize(text: str) -> set[str]:
    """Tokenize text into normalized terms used for query focus scoring."""
    raw_tokens = re.findall(r"[a-z0-9]+", text.lower())
    return {token for token in raw_tokens if token not in STOPWORDS}


def _focus_score(question_tokens: set[str], answer_text: str) -> float:
    """Compute lexical focus score between query tokens and candidate answer text."""
    if not question_tokens:
        return 0.0
    answer_tokens = _tokenize(answer_text)
    if not answer_tokens:
        return 0.0
    overlap = len(question_tokens & answer_tokens)
    if overlap == 0:
        return 0.0
    return overlap / max(1, len(question_tokens))


def _focus_text_to_query(text: str, question_tokens: set[str]) -> str:
    """Reduce mixed bullet text to the most query-relevant fragment when possible."""
    if not question_tokens:
        return text

    lowered = text.lower()
    if " have " in lowered:
        prefix, suffix = text.split(" have ", 1)
        items = [item.strip(" .") for item in re.split(r",|\band\b", suffix) if item.strip(" .")]
        matching_items = [
            item for item in items if _focus_score(question_tokens, item) > 0
        ]
        if matching_items:
            joined = " and ".join(matching_items)
            return f"{prefix.strip()} have {joined}"

    clauses = [
        clause.strip(" .")
        for clause in re.split(r"[.;]|,", text)
        if clause.strip(" .")
    ]
    if not clauses:
        return text
    clauses.sort(key=lambda clause: _focus_score(question_tokens, clause), reverse=True)
    best = clauses[0]
    if _focus_score(question_tokens, best) > 0:
        return best
    return text


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
