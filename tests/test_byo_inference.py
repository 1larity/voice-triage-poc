from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request

import pytest

from voice_triage.rag.answer import RagService
from voice_triage.rag.byo import ByoInferenceRagService


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return False

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


class _FallbackRagService:
    def answer(self, question: str) -> tuple[str, dict[str, Any]]:
        return (f"fallback:{question}", {"used_kb": False, "backend": "local"})


def test_byo_inference_service_uses_remote_answer(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_urlopen(request: object, timeout: float) -> _FakeResponse:
        assert timeout == 5.0
        return _FakeResponse({"answer": "remote answer", "metadata": {"provider": "mock"}})

    monkeypatch.setattr("voice_triage.rag.byo.urlopen", fake_urlopen)
    service = ByoInferenceRagService("http://localhost:9000/infer", timeout_seconds=5.0)

    answer, metadata = service.answer("hello")

    assert answer == "remote answer"
    assert metadata["used_byo_inference"] is True
    assert metadata["provider"] == "mock"


def test_byo_inference_service_supports_openai_compatible_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen_request: dict[str, Any] = {}

    def fake_urlopen(request: Request, timeout: float) -> _FakeResponse:
        seen_request["timeout"] = timeout
        seen_request["body"] = json.loads(request.data.decode("utf-8"))
        seen_request["authorization"] = request.get_header("Authorization")
        return _FakeResponse(
            {
                "model": "llama3.1:8b",
                "choices": [{"message": {"content": "Ollama OpenAI answer"}}],
            }
        )

    monkeypatch.setattr("voice_triage.rag.byo.urlopen", fake_urlopen)
    service = ByoInferenceRagService(
        "http://localhost:11434/v1/chat/completions",
        timeout_seconds=4.0,
        api_style="openai",
        model="llama3.1:8b",
        api_key="test-key",
        system_prompt="Be concise.",
    )

    answer, metadata = service.answer("How do I order a garden waste bin?")

    assert seen_request["timeout"] == 4.0
    assert seen_request["authorization"] == "Bearer test-key"
    assert seen_request["body"]["model"] == "llama3.1:8b"
    assert seen_request["body"]["stream"] is False
    assert len(seen_request["body"]["messages"]) == 2
    assert seen_request["body"]["messages"][0]["role"] == "system"
    assert seen_request["body"]["messages"][1]["role"] == "user"

    assert answer == "Ollama OpenAI answer"
    assert metadata["used_byo_inference"] is True
    assert metadata["api_style"] == "openai"
    assert metadata["provider_model"] == "llama3.1:8b"


def test_byo_inference_service_falls_back_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: object, timeout: float) -> _FakeResponse:
        raise URLError("connection refused")

    monkeypatch.setattr("voice_triage.rag.byo.urlopen", fake_urlopen)
    fallback: RagService = _FallbackRagService()
    service = ByoInferenceRagService(
        "http://localhost:9000/infer",
        timeout_seconds=5.0,
        fallback_service=fallback,
    )

    answer, metadata = service.answer("hello")

    assert answer == "fallback:hello"
    assert metadata["used_byo_inference"] is False
    assert metadata["backend"] == "byo_with_local_fallback"


def test_byo_inference_service_falls_back_on_openai_missing_content(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_urlopen(request: Request, timeout: float) -> _FakeResponse:
        return _FakeResponse({"model": "llama3.1:8b", "choices": [{"message": {}}]})

    monkeypatch.setattr("voice_triage.rag.byo.urlopen", fake_urlopen)
    fallback: RagService = _FallbackRagService()
    service = ByoInferenceRagService(
        "http://localhost:11434/v1/chat/completions",
        timeout_seconds=5.0,
        api_style="openai",
        fallback_service=fallback,
    )

    answer, metadata = service.answer("hello")

    assert answer == "fallback:hello"
    assert metadata["used_byo_inference"] is False
    assert metadata["fallback_reason"] == "missing_content"
