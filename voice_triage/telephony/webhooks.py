"""Telephony webhook endpoints for FastAPI integration.

This module provides FastAPI router endpoints for handling webhooks
from various telephony providers (Twilio, Vonage, SIP).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Any, Final

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from fastapi.responses import PlainTextResponse

from voice_triage.telephony.base import PhoneCall
from voice_triage.telephony.capabilities import list_provider_capabilities
from voice_triage.telephony.registry import TelephonyRegistry
from voice_triage.telephony.shared.auth import get_header

logger = logging.getLogger(__name__)

# Default welcome message for inbound calls
DEFAULT_WELCOME_MESSAGE = (
    "Hello, and welcome to the council services helpline. How can I help you today?"
)

_PATH_TOKEN_RE = re.compile(r"([^[.\]]+)|\[(\d+)\]")
_TIMESTAMP_HEADERS: Final[tuple[str, ...]] = (
    "X-Signature-Timestamp",
    "X-Zm-Request-Timestamp",
    "X-Request-Timestamp",
    "X-Timestamp",
    "Timestamp",
)

_PROVIDER_PAYLOAD_SCHEMAS: Final[dict[str, dict[str, list[str]]]] = {
    "twilio": {
        "call_id": ["CallSid"],
        "from_number": ["From"],
        "to_number": ["To"],
    },
    "vonage": {
        "call_id": ["uuid", "conversation_uuid"],
        "from_number": ["from"],
        "to_number": ["to"],
    },
    "nexmo": {
        "call_id": ["uuid", "conversation_uuid"],
        "from_number": ["from"],
        "to_number": ["to"],
    },
    "sip": {
        "call_id": ["call_id", "Call-ID"],
        "from_number": ["from", "From"],
        "to_number": ["to", "To"],
    },
    "gamma": {
        "call_id": ["call_id", "Call-ID"],
        "from_number": ["from", "From"],
        "to_number": ["to", "To"],
    },
    "bt": {
        "call_id": ["call_id", "Call-ID"],
        "from_number": ["from", "From"],
        "to_number": ["to", "To"],
    },
    "ringcentral": {
        "call_id": ["body.id", "body.sessionId", "body.call_id", "id", "sessionId", "call_id"],
        "from_number": ["body.from.phoneNumber", "body.from.number", "from.phoneNumber", "from"],
        "to_number": [
            "body.to[0].phoneNumber",
            "body.to.phoneNumber",
            "body.to.number",
            "to[0].phoneNumber",
            "to.phoneNumber",
            "to",
        ],
    },
    "zoom": {
        "call_id": [
            "payload.object.call_id",
            "payload.object.sessionId",
            "payload.object.id",
            "call_id",
            "id",
        ],
        "from_number": [
            "payload.object.from.phone_number",
            "payload.object.from.number",
            "payload.object.caller_number",
            "from",
        ],
        "to_number": [
            "payload.object.to.phone_number",
            "payload.object.to.number",
            "payload.object.callee_number",
            "to",
        ],
    },
    "zoom_phone": {
        "call_id": [
            "payload.object.call_id",
            "payload.object.sessionId",
            "payload.object.id",
            "call_id",
            "id",
        ],
        "from_number": [
            "payload.object.from.phone_number",
            "payload.object.from.number",
            "payload.object.caller_number",
            "from",
        ],
        "to_number": [
            "payload.object.to.phone_number",
            "payload.object.to.number",
            "payload.object.callee_number",
            "to",
        ],
    },
    "teams": {
        "call_id": ["value[0].resourceData.id", "value[0].resourceData.callId", "id"],
        "from_number": ["value[0].resourceData.from.identity.phone.id", "from.phoneNumber"],
        "to_number": ["value[0].resourceData.to[0].identity.phone.id", "to[0].phoneNumber"],
    },
    "microsoft_teams": {
        "call_id": ["value[0].resourceData.id", "value[0].resourceData.callId", "id"],
        "from_number": ["value[0].resourceData.from.identity.phone.id", "from.phoneNumber"],
        "to_number": ["value[0].resourceData.to[0].identity.phone.id", "to[0].phoneNumber"],
    },
    "teams_direct_routing": {
        "call_id": ["value[0].resourceData.id", "value[0].resourceData.callId", "id"],
        "from_number": ["value[0].resourceData.from.identity.phone.id", "from.phoneNumber"],
        "to_number": ["value[0].resourceData.to[0].identity.phone.id", "to[0].phoneNumber"],
    },
    "circleloop": {
        "call_id": ["call_id", "CallID", "id"],
        "from_number": ["from", "caller_id", "From"],
        "to_number": ["to", "called_number", "To"],
    },
    "nfon": {
        "call_id": ["call.callId", "call.id", "callId"],
        "from_number": ["call.from", "call.callerId", "call.caller_number", "from"],
        "to_number": [
            "call.to",
            "call.calledNumber",
            "call.destination",
            "call.callee_number",
            "to",
        ],
    },
    "discord": {
        "interaction_type": ["type"],
        "channel_id": ["channel_id", "channel_id.id"],
    },
    "avaya": {
        "call_id": ["callId", "call_id", "ucid"],
        "from_number": ["callingNumber", "calling_number", "ani", "from"],
        "to_number": ["calledNumber", "called_number", "dnis", "to"],
    },
    "avaya_aes": {
        "call_id": ["callId", "call_id", "ucid"],
        "from_number": ["callingNumber", "calling_number", "ani", "from"],
        "to_number": ["calledNumber", "called_number", "dnis", "to"],
    },
    "avaya_ip_office": {
        "call_id": ["callId", "call_id", "ucid"],
        "from_number": ["callingNumber", "calling_number", "ani", "from"],
        "to_number": ["calledNumber", "called_number", "dnis", "to"],
    },
}

_PROVIDER_STATUS_PATHS: Final[dict[str, list[str]]] = {
    "twilio": ["CallStatus", "status"],
    "vonage": ["status", "call_status"],
    "nexmo": ["status", "call_status"],
    "sip": ["status", "sip_status", "CallStatus"],
    "gamma": ["status", "sip_status", "CallStatus"],
    "bt": ["status", "sip_status", "CallStatus"],
    "ringcentral": ["body.status", "body.callStatus", "status", "CallStatus"],
    "zoom": ["payload.object.status", "status", "call_status", "CallStatus"],
    "zoom_phone": ["payload.object.status", "status", "call_status", "CallStatus"],
    "teams": [
        "value[0].resourceData.state",
        "value[0].resourceData.status",
        "state",
        "status",
    ],
    "microsoft_teams": [
        "value[0].resourceData.state",
        "value[0].resourceData.status",
        "state",
        "status",
    ],
    "teams_direct_routing": [
        "value[0].resourceData.state",
        "value[0].resourceData.status",
        "state",
        "status",
    ],
    "circleloop": ["status", "call_status", "CallStatus"],
    "nfon": ["call.status", "call.state", "status", "CallStatus"],
    "discord": ["status", "state", "CallStatus"],
    "avaya": ["state", "status", "callState", "CallStatus"],
    "avaya_aes": ["state", "status", "callState", "CallStatus"],
    "avaya_ip_office": ["state", "status", "callState", "CallStatus"],
}

_TERMINAL_STATUS_VALUES: Final[set[str]] = {
    "completed",
    "failed",
    "no_answer",
    "canceled",
    "busy",
    "disconnected",
    "terminated",
    "ended",
    "rejected",
    "timeout",
    "missed",
    "abandoned",
    "wrapup",
    "dropped",
    "idle",
    "unavailable",
}

_STATUS_NORMALIZATION_ALIASES: Final[dict[str, str]] = {
    "cancelled": "canceled",
    "noanswer": "no_answer",
    "inprogress": "in_progress",
}

_DEFAULT_RATE_LIMIT_CACHE_MAX_KEYS: Final[int] = 10_000
_DEFAULT_REPLAY_CACHE_MAX_ENTRIES: Final[int] = 10_000
_DEFAULT_RATE_LIMIT_SWEEP_INTERVAL_SECONDS: Final[int] = 30


class TelephonyWebhookHandler:
    """Handler for telephony webhooks.

    This class processes incoming webhooks from telephony providers
    and integrates with the conversation engine.
    """

    def __init__(
        self,
        registry: TelephonyRegistry,
        conversation_handler: Any | None = None,
        webhook_rate_limit_per_minute: int = 120,
        webhook_replay_window_seconds: int = 300,
        webhook_rate_limit_cache_max_keys: int = _DEFAULT_RATE_LIMIT_CACHE_MAX_KEYS,
        webhook_replay_cache_max_entries: int = _DEFAULT_REPLAY_CACHE_MAX_ENTRIES,
        webhook_rate_limit_sweep_interval_seconds: int = _DEFAULT_RATE_LIMIT_SWEEP_INTERVAL_SECONDS,
        time_provider: Callable[[], float] | None = None,
    ) -> None:
        """Initialize the webhook handler.

        Args:
            registry: Telephony provider registry.
            conversation_handler: Handler for processing conversations.
            webhook_rate_limit_per_minute: Max requests per provider/source IP per minute.
            webhook_replay_window_seconds: Window for replay detection and timestamp checks.
            webhook_rate_limit_cache_max_keys: Max provider/source IP keys retained in memory.
            webhook_replay_cache_max_entries: Max replay keys retained in memory.
            webhook_rate_limit_sweep_interval_seconds: Seconds between global stale-key sweeps.
            time_provider: Optional timestamp provider for tests.
        """
        self.registry = registry
        self.conversation_handler = conversation_handler
        self._call_sessions: dict[str, str] = {}  # call_id -> session_id
        self._rate_limit_per_minute = max(1, webhook_rate_limit_per_minute)
        self._replay_window_seconds = max(1, webhook_replay_window_seconds)
        self._rate_limit_cache_max_keys = max(1, webhook_rate_limit_cache_max_keys)
        self._replay_cache_max_entries = max(1, webhook_replay_cache_max_entries)
        self._rate_limit_sweep_interval_seconds = max(
            1, webhook_rate_limit_sweep_interval_seconds
        )
        self._time_provider = time_provider or time.time
        self._rate_limit_hits: dict[str, deque[float]] = {}
        self._last_rate_limit_sweep_at = 0.0
        self._replay_cache: dict[str, float] = {}
        self._lock = threading.Lock()

    def _prune_rate_limit_cache_locked(self, now: float, cutoff: float) -> None:
        """Prune stale and excess rate-limit buckets.

        Requires caller to hold ``self._lock``.
        """
        should_sweep = (
            now - self._last_rate_limit_sweep_at >= self._rate_limit_sweep_interval_seconds
            or len(self._rate_limit_hits) > self._rate_limit_cache_max_keys
        )
        if not should_sweep:
            return

        for key, window in list(self._rate_limit_hits.items()):
            while window and window[0] < cutoff:
                window.popleft()
            if not window:
                del self._rate_limit_hits[key]

        overflow = len(self._rate_limit_hits) - self._rate_limit_cache_max_keys
        if overflow > 0:
            # Evict least-recently-seen keys first to cap cardinality attacks.
            ranked = sorted(
                self._rate_limit_hits.items(),
                key=lambda item: item[1][-1] if item[1] else float("-inf"),
            )
            for key, _ in ranked[:overflow]:
                self._rate_limit_hits.pop(key, None)

        self._last_rate_limit_sweep_at = now

    def _prune_replay_cache_locked(self, now: float) -> None:
        """Prune expired and excess replay keys.

        Requires caller to hold ``self._lock``.
        """
        expired = [
            cache_key
            for cache_key, expiry in self._replay_cache.items()
            if expiry <= now
        ]
        for cache_key in expired:
            del self._replay_cache[cache_key]

        overflow = len(self._replay_cache) - self._replay_cache_max_entries
        if overflow > 0:
            oldest = sorted(self._replay_cache.items(), key=lambda item: item[1])[:overflow]
            for cache_key, _ in oldest:
                del self._replay_cache[cache_key]

    def _build_request_headers(self, request: Request) -> dict[str, str]:
        """Build normalized headers for provider validation/parsing."""
        headers = dict(request.headers)

        # Pass through client IP so providers can enforce allowlists.
        source_ip = request.client.host if request.client else ""
        if source_ip:
            headers.setdefault("x-source-ip", source_ip)

        # Microsoft Graph validation token is often provided as query param.
        validation_token = request.query_params.get("validationToken")
        if validation_token:
            headers.setdefault("validationtoken", validation_token)

        return headers

    def _maybe_validation_response(
        self,
        provider_name: str,
        provider: Any,
        headers: dict[str, str],
    ) -> Response | None:
        """Return provider validation challenge response when required."""
        validation_payload = provider.get_validation_response(headers)
        if validation_payload is None:
            return None
        logger.info(f"Responding to {provider_name} webhook validation challenge")
        return PlainTextResponse(validation_payload)

    def _extract_source_ip(self, headers: dict[str, str]) -> str:
        """Extract source IP from forwarded or direct source headers."""
        forwarded_for = get_header(headers, "X-Forwarded-For")
        if forwarded_for:
            first = forwarded_for.split(",")[0].strip()
            if first:
                return first

        for name in ("X-Real-IP", "X-Source-IP"):
            value = get_header(headers, name).strip()
            if value:
                return value
        return "unknown"

    def _enforce_rate_limit(self, provider_name: str, headers: dict[str, str]) -> None:
        """Enforce per-provider, per-source-IP request rate limit."""
        source_ip = self._extract_source_ip(headers)
        key = f"{provider_name.lower()}:{source_ip}"
        now = self._time_provider()
        cutoff = now - 60

        with self._lock:
            self._prune_rate_limit_cache_locked(now, cutoff)
            window = self._rate_limit_hits.setdefault(key, deque())
            while window and window[0] < cutoff:
                window.popleft()

            if len(window) >= self._rate_limit_per_minute:
                raise HTTPException(
                    status_code=429,
                    detail=(
                        f"Rate limit exceeded for {provider_name} webhooks "
                        f"from {source_ip} ({self._rate_limit_per_minute}/min)"
                    ),
                )
            window.append(now)
            self._prune_rate_limit_cache_locked(now, cutoff)

    def _parse_timestamp(self, raw_value: str) -> float | None:
        """Parse request timestamp header into unix seconds."""
        value = raw_value.strip()
        if not value:
            return None

        try:
            numeric = float(value)
            if numeric > 1e12:
                numeric /= 1000.0
            return numeric
        except ValueError:
            pass

        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt.timestamp()
        except ValueError:
            pass

        try:
            parsed = parsedate_to_datetime(value)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed.timestamp()
        except (TypeError, ValueError):
            return None

    def _validate_request_freshness(
        self,
        provider_name: str,
        headers: dict[str, str],
    ) -> None:
        """Reject stale webhook requests when a timestamp header is present."""
        now = self._time_provider()
        for header in _TIMESTAMP_HEADERS:
            raw = get_header(headers, header)
            if not raw:
                continue
            timestamp = self._parse_timestamp(raw)
            if timestamp is None:
                raise HTTPException(
                    status_code=403,
                    detail=f"Invalid {provider_name} timestamp header: {header}",
                )
            if abs(now - timestamp) > self._replay_window_seconds:
                raise HTTPException(
                    status_code=403,
                    detail=(
                        f"Stale {provider_name} webhook request "
                        f"(outside {self._replay_window_seconds}s window)"
                    ),
                )
            return

    def _extract_replay_timestamp(self, headers: dict[str, str]) -> float | None:
        """Extract parsed timestamp used by replay-key generation."""
        for header in _TIMESTAMP_HEADERS:
            raw = get_header(headers, header)
            if not raw:
                continue
            return self._parse_timestamp(raw)
        return None

    def _build_replay_key(
        self,
        provider_name: str,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> str | None:
        """Build a stable replay-protection key from request properties."""
        signature_headers = (
            "X-Twilio-Signature",
            "X-Vonage-Signature",
            "X-CircleLoop-Signature",
            "X-NFON-Signature",
            "Verification-Token",
            "X-Zm-Signature",
            "X-Signature-Ed25519",
            "X-Avaya-Signature",
            "X-Webhook-Signature",
            "X-Gamma-Signature",
            "X-Discord-Signature",
            "Authorization",
            "X-SIP-Secret",
        )
        auth_material = ""
        for name in signature_headers:
            value = get_header(headers, name)
            if value:
                auth_material = f"{name.lower()}={value}"
                break

        replay_timestamp = self._extract_replay_timestamp(headers)
        if replay_timestamp is None:
            # Avoid false positives for providers that do not include request timestamps.
            return None
        if not auth_material:
            auth_material = "timestamp-only"

        body_hash = hashlib.sha256(body).hexdigest()
        timestamp_bucket = int(replay_timestamp)
        return f"{provider_name.lower()}|{path}|{auth_material}|{timestamp_bucket}|{body_hash}"

    def _enforce_replay_protection(
        self,
        provider_name: str,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> None:
        """Reject duplicate webhook requests inside the replay window."""
        now = self._time_provider()
        key = self._build_replay_key(provider_name, headers, body, path)
        if key is None:
            return

        with self._lock:
            self._prune_replay_cache_locked(now)

            existing_expiry = self._replay_cache.get(key)
            if existing_expiry and existing_expiry > now:
                raise HTTPException(
                    status_code=409,
                    detail=f"Replay detected for {provider_name} webhook",
                )
            self._replay_cache[key] = now + self._replay_window_seconds
            self._prune_replay_cache_locked(now)

    def _resolve_path(self, data: Any, path: str) -> Any:
        """Resolve a nested value by dot/index path."""
        current = data
        for match in _PATH_TOKEN_RE.finditer(path):
            key_token = match.group(1)
            index_token = match.group(2)
            if key_token is not None:
                if not isinstance(current, dict) or key_token not in current:
                    return None
                current = current[key_token]
                continue
            if index_token is not None:
                if not isinstance(current, list):
                    return None
                index = int(index_token)
                if index >= len(current):
                    return None
                current = current[index]
        return current

    def _has_value(self, data: dict[str, Any], path: str) -> bool:
        """Check whether a nested path resolves to a non-empty value."""
        value = self._resolve_path(data, path)
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        if isinstance(value, (list, dict)):
            return bool(value)
        return True

    def _validate_inbound_payload_schema(
        self,
        provider_name: str,
        payload: dict[str, Any],
    ) -> None:
        """Validate provider-specific inbound payload shape before parsing."""
        schema = _PROVIDER_PAYLOAD_SCHEMAS.get(provider_name.lower())
        if not schema:
            return

        missing: list[str] = []
        for logical_field, candidate_paths in schema.items():
            if not any(self._has_value(payload, path) for path in candidate_paths):
                rendered_paths = " or ".join(candidate_paths)
                missing.append(f"{logical_field} ({rendered_paths})")

        if missing:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Invalid {provider_name} inbound payload: missing required "
                    + ", ".join(missing)
                ),
            )

    def _validate_parsed_call(self, provider_name: str, call: PhoneCall) -> None:
        """Validate parsed provider call payload and raise clear HTTP errors."""
        missing_fields: list[str] = []
        if not call.call_id:
            missing_fields.append("call_id")
        if not call.from_number:
            missing_fields.append("from_number")
        if not call.to_number:
            missing_fields.append("to_number")
        if missing_fields:
            detail = (
                f"Invalid {provider_name} inbound payload: missing "
                + ", ".join(missing_fields)
            )
            raise HTTPException(status_code=422, detail=detail)

    def _normalize_status_value(self, value: Any) -> str:
        """Normalize provider status values for reliable terminal-state matching."""
        if value is None:
            return ""
        normalized = re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")
        if not normalized:
            return ""
        return _STATUS_NORMALIZATION_ALIASES.get(normalized, normalized)

    def _extract_provider_status(
        self,
        provider_name: str,
        payload: dict[str, Any],
    ) -> str:
        """Extract normalized call status using provider-specific path fallbacks."""
        status_paths = _PROVIDER_STATUS_PATHS.get(provider_name.lower(), [])
        generic_paths = ("CallStatus", "status", "call_status", "state")
        for path in (*status_paths, *generic_paths):
            value = self._resolve_path(payload, path)
            normalized = self._normalize_status_value(value)
            if normalized:
                return normalized
        return "unknown"

    def _extract_provider_call_id(
        self,
        provider_name: str,
        payload: dict[str, Any],
    ) -> str | None:
        """Extract call identifier from provider-specific payload fields."""
        schema = _PROVIDER_PAYLOAD_SCHEMAS.get(provider_name.lower(), {})
        candidate_paths = schema.get("call_id", [])
        generic_paths = ("call_id", "CallSid", "uuid", "id")
        for path in (*candidate_paths, *generic_paths):
            value = self._resolve_path(payload, path)
            if value is None:
                continue
            rendered = str(value).strip()
            if rendered:
                return rendered
        return None

    def _is_terminal_status(self, normalized_status: str) -> bool:
        """Return whether a normalized provider status indicates call termination."""
        return normalized_status in _TERMINAL_STATUS_VALUES

    async def _parse_request_data(
        self,
        request: Request,
        body: bytes,
        headers: dict[str, str],
    ) -> dict[str, Any]:
        """Parse request payload across JSON, form, and query-string formats."""
        content_type = get_header(headers, "content-type").lower()

        if "application/json" in content_type:
            try:
                return json.loads(body.decode("utf-8"))
            except json.JSONDecodeError:
                return {}

        data: dict[str, Any] = dict(request.query_params)
        if (
            "application/x-www-form-urlencoded" in content_type
            or "multipart/form-data" in content_type
        ):
            try:
                form_data = await request.form()
                data.update({key: str(value) for key, value in form_data.items()})
            except Exception:
                logger.warning("Failed parsing form payload for telephony webhook")
        return data

    async def handle_inbound_call(
        self,
        provider_name: str,
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle an inbound call webhook.

        Args:
            provider_name: Name of the telephony provider.
            request: FastAPI request object.
            background_tasks: Background task queue.

        Returns:
            Response with call control markup (TwiML/NCCO/etc).
        """
        del background_tasks
        provider = self.registry.get(provider_name)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")

        # Get request body and headers
        body = await request.body()
        headers = self._build_request_headers(request)
        path = request.url.path

        validation_response = self._maybe_validation_response(
            provider_name, provider, headers
        )
        if validation_response is not None:
            return validation_response

        self._enforce_rate_limit(provider_name, headers)
        self._validate_request_freshness(provider_name, headers)

        # Validate webhook
        if not await provider.validate_webhook(headers, body, path):
            logger.warning(f"Invalid webhook signature from {provider_name}")
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
        self._enforce_replay_protection(provider_name, headers, body, path)

        # Parse form/query payload
        form_data = await self._parse_request_data(request, body, headers)
        self._validate_inbound_payload_schema(provider_name, form_data)

        # Parse the inbound call
        try:
            call = await provider.parse_inbound_call(headers, body, form_data)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid {provider_name} inbound payload: {exc}",
            ) from exc
        self._validate_parsed_call(provider_name, call)

        logger.info(
            f"Inbound call from {call.from_number} to {call.to_number} "
            f"(provider: {provider_name}, call_id: {call.call_id})"
        )

        # Create a new conversation session
        session_id = await self._create_session(call)
        self._call_sessions[call.call_id] = session_id

        # Generate response
        action_url = f"/telephony/{provider_name}/voice/{call.call_id}"
        response_markup = await provider.generate_twiml_response(
            session_id=session_id,
            welcome_message=DEFAULT_WELCOME_MESSAGE,
            gather_speech=True,
            action_url=action_url,
        )

        # Use provider's content type
        return Response(
            content=response_markup,
            media_type=provider.get_response_content_type(),
        )

    async def handle_speech_input(
        self,
        provider_name: str,
        call_id: str,
        request: Request,
    ) -> Response:
        """Handle speech input from a call.

        Args:
            provider_name: Name of the telephony provider.
            call_id: The call ID.
            request: FastAPI request object.

        Returns:
            Response with next action markup.
        """
        provider = self.registry.get(provider_name)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")

        # Get request body
        body = await request.body()
        headers = self._build_request_headers(request)

        validation_response = self._maybe_validation_response(
            provider_name, provider, headers
        )
        if validation_response is not None:
            return validation_response

        self._enforce_rate_limit(provider_name, headers)
        self._validate_request_freshness(provider_name, headers)

        # Validate webhook
        if not await provider.validate_webhook(headers, body, request.url.path):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
        self._enforce_replay_protection(provider_name, headers, body, request.url.path)

        # Parse speech input payload
        data = await self._parse_request_data(request, body, headers)

        # Extract transcript using provider's method
        transcript = provider.extract_transcript(data)

        if not transcript:
            # No speech detected, prompt again
            session_id = self._call_sessions.get(call_id, "")
            response_markup = await provider.generate_twiml_response(
                session_id=session_id,
                welcome_message="I didn't catch that. Could you please repeat?",
                gather_speech=True,
                action_url=f"/telephony/{provider_name}/voice/{call_id}",
            )
            return Response(
                content=response_markup,
                media_type=provider.get_response_content_type(),
            )

        logger.info(f"Speech input from call {call_id}: {transcript}")

        # Get session ID
        session_id = self._call_sessions.get(call_id) or call_id

        # Process the transcript through conversation engine
        response_text = await self._process_conversation(session_id, transcript)

        # Generate response with next action
        response_markup = await provider.generate_twiml_response(
            session_id=session_id,
            welcome_message=response_text,
            gather_speech=True,
            action_url=f"/telephony/{provider_name}/voice/{call_id}",
        )

        return Response(
            content=response_markup,
            media_type=provider.get_response_content_type(),
        )

    async def handle_call_status(
        self,
        provider_name: str,
        call_id: str,
        request: Request,
    ) -> Response:
        """Handle call status updates with route-provided call ID.

        Args:
            provider_name: Name of the telephony provider.
            call_id: The call ID.
            request: FastAPI request object.

        Returns:
            Acknowledgment response.
        """
        return await self._handle_call_status_request(
            provider_name=provider_name,
            request=request,
            route_call_id=call_id,
        )

    async def handle_call_status_auto(
        self,
        provider_name: str,
        request: Request,
    ) -> Response:
        """Handle call status updates without route-provided call ID.

        The call identifier is resolved from provider payload fields.
        """
        return await self._handle_call_status_request(
            provider_name=provider_name,
            request=request,
            route_call_id=None,
        )

    async def _handle_call_status_request(
        self,
        provider_name: str,
        request: Request,
        route_call_id: str | None,
    ) -> Response:
        """Shared status-handler implementation for routed and unrouted callbacks."""
        provider = self.registry.get(provider_name)
        if not provider:
            raise HTTPException(status_code=400, detail=f"Unknown provider: {provider_name}")

        body = await request.body()
        headers = self._build_request_headers(request)

        validation_response = self._maybe_validation_response(
            provider_name, provider, headers
        )
        if validation_response is not None:
            return validation_response

        self._enforce_rate_limit(provider_name, headers)
        self._validate_request_freshness(provider_name, headers)

        if not await provider.validate_webhook(headers, body, request.url.path):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
        self._enforce_replay_protection(provider_name, headers, body, request.url.path)

        # Parse status payload
        data = await self._parse_request_data(request, body, headers)

        status = self._extract_provider_status(provider_name, data)
        payload_call_id = self._extract_provider_call_id(provider_name, data)
        if route_call_id and payload_call_id and payload_call_id != route_call_id:
            logger.info(
                f"Call {route_call_id} status update: {status} "
                f"(payload_call_id: {payload_call_id})"
            )
        elif route_call_id:
            logger.info(f"Call {route_call_id} status update: {status}")
        elif payload_call_id:
            logger.info(f"Call {payload_call_id} status update: {status}")
        else:
            logger.info(f"Provider {provider_name} status update: {status} (missing call_id)")

        # Clean up sessions on terminal status, using both route and payload call IDs.
        if self._is_terminal_status(status):
            cleanup_ids: set[str] = set()
            if route_call_id:
                cleanup_ids.add(route_call_id)
            if payload_call_id:
                cleanup_ids.add(payload_call_id)
            for cleanup_id in cleanup_ids:
                self._call_sessions.pop(cleanup_id, None)

        return PlainTextResponse("OK")

    async def _create_session(self, call: PhoneCall) -> str:
        """Create a new conversation session for a call.

        Args:
            call: The inbound phone call.

        Returns:
            Session ID.
        """
        if self.conversation_handler:
            # Use the conversation handler to create a session
            session_id = await self.conversation_handler.create_session(
                metadata={
                    "call_id": call.call_id,
                    "from_number": call.from_number,
                    "to_number": call.to_number,
                    "provider": call.provider,
                }
            )
            return session_id
        else:
            # Generate a simple session ID
            import uuid
            return str(uuid.uuid4())

    async def _process_conversation(self, session_id: str, transcript: str) -> str:
        """Process a conversation turn.

        Args:
            session_id: Session ID.
            transcript: User's speech transcript.

        Returns:
            Assistant response text.
        """
        if self.conversation_handler:
            return await self.conversation_handler.process_turn(
                session_id=session_id,
                transcript=transcript,
            )
        else:
            # Default response if no handler configured
            return "Thank you for your message. How else can I help you today?"


def create_telephony_router(
    handler: TelephonyWebhookHandler,
    prefix: str = "/telephony",
) -> APIRouter:
    """Create a FastAPI router for telephony webhooks.

    Args:
        handler: The webhook handler instance.
        prefix: URL prefix for all routes.

    Returns:
        FastAPI router.
    """
    router = APIRouter(prefix=prefix, tags=["telephony"])

    # Twilio endpoints
    @router.post("/twilio/voice")
    async def twilio_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle Twilio voice webhook."""
        return await handler.handle_inbound_call("twilio", request, background_tasks)

    @router.post("/twilio/voice/{call_id}")
    async def twilio_voice_input(call_id: str, request: Request) -> Response:
        """Handle Twilio speech input."""
        return await handler.handle_speech_input("twilio", call_id, request)

    @router.post("/twilio/status/{call_id}")
    async def twilio_status(call_id: str, request: Request) -> Response:
        """Handle Twilio status callback."""
        return await handler.handle_call_status("twilio", call_id, request)

    @router.post("/twilio/status")
    async def twilio_status_no_call_id(request: Request) -> Response:
        """Handle Twilio status callback without route call ID."""
        return await handler.handle_call_status_auto("twilio", request)

    # Vonage/Nexmo endpoints
    @router.post("/vonage/voice")
    async def vonage_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle Vonage voice webhook."""
        return await handler.handle_inbound_call("vonage", request, background_tasks)

    @router.post("/vonage/voice/{call_id}")
    async def vonage_voice_input(call_id: str, request: Request) -> Response:
        """Handle Vonage speech input."""
        return await handler.handle_speech_input("vonage", call_id, request)

    @router.post("/vonage/event/{call_id}")
    async def vonage_event(call_id: str, request: Request) -> Response:
        """Handle Vonage event callback."""
        return await handler.handle_call_status("vonage", call_id, request)

    @router.post("/nexmo/voice")
    async def nexmo_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle Nexmo voice webhook (alias for Vonage)."""
        return await handler.handle_inbound_call("nexmo", request, background_tasks)

    # SIP/Gamma endpoints
    @router.post("/sip/voice")
    async def sip_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle SIP gateway voice webhook."""
        return await handler.handle_inbound_call("sip", request, background_tasks)

    @router.post("/sip/voice/{call_id}")
    async def sip_voice_input(call_id: str, request: Request) -> Response:
        """Handle SIP gateway speech input."""
        return await handler.handle_speech_input("sip", call_id, request)

    @router.post("/sip/status/{call_id}")
    async def sip_status(call_id: str, request: Request) -> Response:
        """Handle SIP gateway status callback."""
        return await handler.handle_call_status("sip", call_id, request)

    @router.post("/gamma/voice")
    async def gamma_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle Gamma Telecom voice webhook."""
        return await handler.handle_inbound_call("gamma", request, background_tasks)

    @router.post("/bt/voice")
    async def bt_voice(
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle BT voice webhook."""
        return await handler.handle_inbound_call("bt", request, background_tasks)

    @router.post("/teams/callback")
    async def teams_callback(request: Request) -> Response:
        """Handle Teams callback webhooks without route call ID."""
        return await handler.handle_call_status_auto("teams", request)

    @router.post("/teams/notification")
    async def teams_notification(request: Request) -> Response:
        """Handle Teams notification webhooks without route call ID."""
        return await handler.handle_call_status_auto("teams", request)

    # Generic provider routes for providers that follow /{provider}/voice style
    @router.post("/{provider_name}/voice")
    async def provider_voice(
        provider_name: str,
        request: Request,
        background_tasks: BackgroundTasks,
    ) -> Response:
        """Handle inbound voice webhooks for any registered provider."""
        return await handler.handle_inbound_call(provider_name, request, background_tasks)

    @router.post("/{provider_name}/voice/{call_id}")
    async def provider_voice_input(
        provider_name: str,
        call_id: str,
        request: Request,
    ) -> Response:
        """Handle speech input webhooks for any registered provider."""
        return await handler.handle_speech_input(provider_name, call_id, request)

    @router.post("/{provider_name}/status/{call_id}")
    async def provider_status(
        provider_name: str,
        call_id: str,
        request: Request,
    ) -> Response:
        """Handle status webhooks for any registered provider."""
        return await handler.handle_call_status(provider_name, call_id, request)

    @router.post("/{provider_name}/status")
    async def provider_status_no_call_id(
        provider_name: str,
        request: Request,
    ) -> Response:
        """Handle status webhooks without route call IDs for any provider."""
        return await handler.handle_call_status_auto(provider_name, request)

    @router.post("/{provider_name}/event/{call_id}")
    async def provider_event(
        provider_name: str,
        call_id: str,
        request: Request,
    ) -> Response:
        """Handle event-style status webhooks for any registered provider."""
        return await handler.handle_call_status(provider_name, call_id, request)

    @router.post("/{provider_name}/event")
    async def provider_event_no_call_id(
        provider_name: str,
        request: Request,
    ) -> Response:
        """Handle event-style status webhooks without route call IDs."""
        return await handler.handle_call_status_auto(provider_name, request)

    # Health check
    @router.get("/health")
    async def telephony_health() -> dict[str, Any]:
        """Health check for telephony endpoints."""
        return {
            "status": "ok",
            "providers": handler.registry.list_registered(),
        }

    # List available providers
    @router.get("/providers")
    async def list_providers() -> dict[str, list[str]]:
        """List available telephony providers."""
        from voice_triage.telephony.registry import list_providers as get_all_providers
        return {"providers": get_all_providers()}

    @router.get("/capabilities")
    async def provider_capabilities() -> dict[str, list[dict[str, object]]]:
        """List practical capabilities and OOB readiness per provider."""
        from voice_triage.telephony.registry import list_providers as get_all_providers

        providers = get_all_providers()
        return {"providers": list_provider_capabilities(providers)}

    return router


def build_telephony_handler(
    conversation_handler: Any | None = None,
    provider_configs: dict[str, dict[str, Any]] | None = None,
    webhook_rate_limit_per_minute: int = 120,
    webhook_replay_window_seconds: int = 300,
) -> TelephonyWebhookHandler:
    """Create and configure a telephony webhook handler.

    Args:
        conversation_handler: Handler for processing conversations.
        provider_configs: Optional provider configurations.
        webhook_rate_limit_per_minute: Max requests per provider/source IP per minute.
        webhook_replay_window_seconds: Replay-protection window in seconds.

    Returns:
        Configured TelephonyWebhookHandler instance.
    """
    from voice_triage.telephony.base import TelephonyConfig
    from voice_triage.telephony.registry import (
        ensure_builtin_providers_registered,
        get_provider,
    )

    ensure_builtin_providers_registered()
    registry = TelephonyRegistry()

    # Register configured providers
    if provider_configs:
        for provider_name, config_dict in provider_configs.items():
            try:
                payload = dict(config_dict)
                payload.pop("provider_name", None)
                config = TelephonyConfig(provider_name=provider_name, **payload)
                provider = get_provider(config)
                registry.register(provider)
                logger.info(f"Registered telephony provider: {provider_name}")
            except Exception as exc:
                logger.warning(f"Failed to register provider {provider_name}: {exc}")

    return TelephonyWebhookHandler(
        registry=registry,
        conversation_handler=conversation_handler,
        webhook_rate_limit_per_minute=webhook_rate_limit_per_minute,
        webhook_replay_window_seconds=webhook_replay_window_seconds,
    )


async def create_telephony_handler(
    conversation_handler: Any | None = None,
    provider_configs: dict[str, dict[str, Any]] | None = None,
    webhook_rate_limit_per_minute: int = 120,
    webhook_replay_window_seconds: int = 300,
) -> TelephonyWebhookHandler:
    """Create and configure a telephony webhook handler."""
    return build_telephony_handler(
        conversation_handler=conversation_handler,
        provider_configs=provider_configs,
        webhook_rate_limit_per_minute=webhook_rate_limit_per_minute,
        webhook_replay_window_seconds=webhook_replay_window_seconds,
    )
