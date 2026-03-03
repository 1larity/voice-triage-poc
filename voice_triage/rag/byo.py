"""rag.byo module."""

from __future__ import annotations

import json
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from voice_triage.rag.answer import RagService


class ByoInferenceRagService:
    """RAG service adapter that delegates answer generation to a BYO REST inference endpoint."""

    def __init__(
        self,
        endpoint_url: str,
        *,
        timeout_seconds: float = 12.0,
        api_style: str = "generic",
        model: str | None = None,
        api_key: str | None = None,
        system_prompt: str | None = None,
        fallback_service: RagService | None = None,
    ) -> None:
        """Initialize a BYO adapter for generic or OpenAI-compatible endpoints."""
        self.endpoint_url = endpoint_url
        self.timeout_seconds = timeout_seconds
        self.api_style = api_style.strip().lower()
        self.model = (model or "").strip() or None
        self.api_key = (api_key or "").strip() or None
        self.system_prompt = (system_prompt or "").strip() or None
        self.fallback_service = fallback_service

    def answer(self, question: str) -> tuple[str, dict[str, Any]]:
        """Generate an answer through the configured BYO endpoint."""
        try:
            request = self._build_request(question)
        except ValueError as exc:
            return self._fallback(question, f"invalid_config:{exc}")

        try:
            with urlopen(request, timeout=self.timeout_seconds) as response:
                raw = response.read().decode("utf-8")
        except URLError as exc:
            return self._fallback(question, f"endpoint_unavailable:{exc}")

        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return self._fallback(question, "invalid_json_response")

        return self._parse_response(question, parsed)

    def _build_request(self, question: str) -> Request:
        """Build an HTTP request for the configured BYO API style."""
        payload: dict[str, Any]
        if self.api_style in {"generic", "rest"}:
            payload = {"query": question}
        elif self.api_style in {"openai", "openai_compat", "ollama_openai"}:
            model = self.model or "llama3.1:8b"
            messages: list[dict[str, str]] = []
            if self.system_prompt:
                messages.append({"role": "system", "content": self.system_prompt})
            messages.append({"role": "user", "content": question})
            payload = {
                "model": model,
                "messages": messages,
                "stream": False,
            }
        else:
            raise ValueError(f"Unsupported BYO API style: {self.api_style!r}")

        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        return Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST",
        )

    def _parse_response(self, question: str, parsed: Any) -> tuple[str, dict[str, Any]]:
        """Parse endpoint responses for generic and OpenAI-compatible payloads."""
        if not isinstance(parsed, dict):
            return self._fallback(question, "response_not_object")

        if self.api_style in {"generic", "rest"}:
            answer_value = parsed.get("answer")
            if not isinstance(answer_value, str) or not answer_value.strip():
                return self._fallback(question, "missing_answer")

            metadata = parsed.get("metadata")
            metadata_dict = metadata if isinstance(metadata, dict) else {}
            response_meta: dict[str, Any] = {
                "used_byo_inference": True,
                "backend": "byo",
                "api_style": self.api_style,
                **metadata_dict,
            }
            return answer_value.strip(), response_meta

        choices = parsed.get("choices")
        if not isinstance(choices, list) or not choices:
            return self._fallback(question, "missing_choices")
        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            return self._fallback(question, "invalid_choice_item")

        message = first_choice.get("message")
        if isinstance(message, dict):
            content = message.get("content")
        else:
            content = first_choice.get("text")

        if not isinstance(content, str) or not content.strip():
            return self._fallback(question, "missing_content")

        response_meta = {
            "used_byo_inference": True,
            "backend": "byo",
            "api_style": self.api_style,
            "provider_model": parsed.get("model"),
        }
        return content.strip(), response_meta

    def _fallback(self, question: str, reason: str) -> tuple[str, dict[str, Any]]:
        """Use local fallback service when BYO fails or is misconfigured."""
        if self.fallback_service is None:
            return (
                "The configured BYO inference service is unavailable right now.",
                {
                    "used_byo_inference": False,
                    "backend": "byo",
                    "api_style": self.api_style,
                    "fallback_reason": reason,
                },
            )
        answer, metadata = self.fallback_service.answer(question)
        return answer, {
            **metadata,
            "used_byo_inference": False,
            "backend": "byo_with_local_fallback",
            "api_style": self.api_style,
            "fallback_reason": reason,
        }
