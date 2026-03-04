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
    process_answer_max_chars: int = 520
    process_answer_max_points: int = 4


UNKNOWN_KNOWLEDGE_BASE_RESPONSE = (
    "Sorry, I do not have an answer for that yet. "
    "Please try asking in a different way, or ask about council services such as bins, parking, "
    "housing, planning, registrars, and governance."
)


@dataclass(frozen=True)
class _AnswerCandidate:
    """Internal candidate container used for targeted answer ranking."""

    score: float
    text: str
    source: str
    section: str
    bullet_index: int


@dataclass(frozen=True)
class _QueryProfile:
    """Heuristic query analysis to control concise vs multi-step rendering."""

    asks_for_process: bool
    asks_for_requirements: bool
    asks_for_timeline: bool
    asks_for_cost: bool

    @property
    def wants_expanded_answer(self) -> bool:
        """Whether the response should surface multiple actionable points."""
        return self.asks_for_process or self.asks_for_requirements


def _render_targeted_answer(question: str, results: list[Any], config: RagAnswerConfig) -> str:
    """Render a concise answer focused on query-matching sub-topics."""
    question_tokens = _tokenize(question)
    profile = _analyze_query(question)
    candidates: list[_AnswerCandidate] = []

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
        candidates.append(
            _AnswerCandidate(
                score=combined,
                text=focused_text,
                source=result.chunk.source,
                section=section,
                bullet_index=_bullet_index(result.chunk.metadata),
            )
        )

    if not candidates:
        return UNKNOWN_KNOWLEDGE_BASE_RESPONSE

    ranked_candidates = _select_source_focused_candidates(candidates)

    if profile.wants_expanded_answer:
        selected_points = _select_expanded_points(
            ranked_candidates,
            max_points=config.process_answer_max_points,
        )
        if not selected_points:
            return UNKNOWN_KNOWLEDGE_BASE_RESPONSE
        expanded = _format_expanded_answer(selected_points)
        return _truncate(expanded, max_chars=config.process_answer_max_chars)

    selected: list[str] = []
    top_score = ranked_candidates[0].score
    for candidate in ranked_candidates:
        if candidate.text in selected:
            continue
        if selected and candidate.score < (top_score - config.score_drop_threshold):
            continue
        selected.append(candidate.text)
        if len(selected) >= 2:
            break

    if selected:
        normalized = " ".join(_ensure_sentence(item) for item in selected)
        return _truncate(normalized, max_chars=config.max_answer_chars)

    return UNKNOWN_KNOWLEDGE_BASE_RESPONSE


def _analyze_query(question: str) -> _QueryProfile:
    """Infer broad user intent classes for response shaping."""
    lowered = question.lower()
    asks_for_process = any(
        phrase in lowered
        for phrase in (
            "how do i",
            "how can i",
            "how to",
            "steps",
            "process",
            "procedure",
            "apply",
            "application",
            "what next",
        )
    )
    asks_for_requirements = any(
        phrase in lowered
        for phrase in (
            "what do i need",
            "requirements",
            "documents",
            "evidence",
            "eligibility",
            "criteria",
        )
    )
    asks_for_timeline = any(
        phrase in lowered for phrase in ("how long", "timescale", "when will", "how quickly")
    )
    asks_for_cost = any(phrase in lowered for phrase in ("how much", "cost", "fee", "price"))
    return _QueryProfile(
        asks_for_process=asks_for_process,
        asks_for_requirements=asks_for_requirements,
        asks_for_timeline=asks_for_timeline,
        asks_for_cost=asks_for_cost,
    )


def _select_source_focused_candidates(candidates: list[_AnswerCandidate]) -> list[_AnswerCandidate]:
    """Prefer the strongest source to avoid mixing unrelated topics in one answer."""
    sorted_candidates = sorted(candidates, key=lambda item: item.score, reverse=True)
    top = sorted_candidates[0]
    per_source_best: dict[str, float] = {}
    for candidate in sorted_candidates:
        existing = per_source_best.get(candidate.source)
        if existing is None or candidate.score > existing:
            per_source_best[candidate.source] = candidate.score

    primary_source = max(per_source_best.items(), key=lambda item: item[1])[0]
    source_filtered = [
        candidate for candidate in sorted_candidates if candidate.source == primary_source
    ]
    if not source_filtered:
        return sorted_candidates

    # If the primary source is very close to the global top, keep focus on that source only.
    if source_filtered[0].score >= top.score - 0.12:
        return source_filtered
    return sorted_candidates


def _select_expanded_points(candidates: list[_AnswerCandidate], max_points: int) -> list[str]:
    """Select ordered points for process-style answers."""
    ordered = sorted(candidates, key=lambda item: (item.bullet_index, -item.score))
    selected: list[str] = []
    seen: set[str] = set()
    for candidate in ordered:
        if candidate.text in seen:
            continue
        if not candidate.text:
            continue
        seen.add(candidate.text)
        selected.append(_ensure_sentence(candidate.text))
        if len(selected) >= max_points:
            break
    return selected


def _format_expanded_answer(points: list[str]) -> str:
    """Format multi-point guidance using short numbered steps."""
    if len(points) == 1:
        return points[0]
    rendered = " ".join(f"{index + 1}) {point}" for index, point in enumerate(points))
    return f"Here are the main steps: {rendered}"


def _bullet_index(metadata: dict[str, Any]) -> int:
    """Safely read bullet_index metadata for deterministic point ordering."""
    raw = metadata.get("bullet_index")
    if isinstance(raw, int):
        return raw
    return 999


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
    normalized: set[str] = set()
    for token in raw_tokens:
        if token.endswith("ies") and len(token) > 4:
            token = f"{token[:-3]}y"
        elif token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("ed") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 3:
            token = token[:-1]
        if token and token not in STOPWORDS:
            normalized.add(token)
    return normalized


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
    verb_match = re.search(r"\b(have|has|had)\b", lowered)
    if verb_match is not None:
        verb_start = verb_match.start()
        verb_end = verb_match.end()
        prefix = text[:verb_start]
        suffix = text[verb_end:]
        items = [item.strip(" .") for item in re.split(r",|\band\b", suffix) if item.strip(" .")]
        matching_items = [
            item for item in items if _focus_score(question_tokens, item) > 0
        ]
        if matching_items:
            joined = " and ".join(matching_items)
            verb = text[verb_start:verb_end]
            return f"{prefix.strip()} {verb} {joined}".strip()

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
