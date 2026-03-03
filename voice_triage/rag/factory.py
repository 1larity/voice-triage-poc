"""rag.factory module."""

from __future__ import annotations

from voice_triage.rag.answer import LocalRagService, RagAnswerConfig, RagService
from voice_triage.rag.byo import ByoInferenceRagService
from voice_triage.rag.retrieve import SqliteRetriever
from voice_triage.util.config import Settings


def create_rag_service(settings: Settings) -> RagService:
    """Create a RagService according to configured inference backend settings."""
    answer_config = RagAnswerConfig(
        retrieval_top_k=settings.rag_retrieval_top_k,
        relevance_threshold=settings.rag_relevance_threshold,
        focus_weight=settings.rag_focus_weight,
        section_boost=settings.rag_section_boost,
        score_drop_threshold=settings.rag_score_drop_threshold,
        max_answer_chars=settings.rag_max_answer_chars,
        boosted_sections=frozenset(settings.rag_boosted_sections),
    )
    local_service = LocalRagService(
        retriever=SqliteRetriever(settings.rag_index_path),
        config=answer_config,
    )

    backend = settings.inference_backend.strip().lower()
    if backend != "byo":
        return local_service

    endpoint = (settings.byo_inference_url or "").strip()
    if not endpoint:
        return local_service

    return ByoInferenceRagService(
        endpoint_url=endpoint,
        timeout_seconds=settings.byo_inference_timeout_seconds,
        api_style=settings.byo_inference_api_style,
        model=settings.byo_inference_model,
        api_key=settings.byo_inference_api_key,
        system_prompt=settings.byo_inference_system_prompt,
        fallback_service=local_service,
    )
