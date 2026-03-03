"""rag.factory module."""

from __future__ import annotations

from voice_triage.rag.answer import LocalRagService, RagService
from voice_triage.rag.byo import ByoInferenceRagService
from voice_triage.rag.retrieve import SqliteRetriever
from voice_triage.util.config import Settings


def create_rag_service(settings: Settings) -> RagService:
    """Create a RagService according to configured inference backend settings."""
    local_service = LocalRagService(SqliteRetriever(settings.rag_index_path))

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
