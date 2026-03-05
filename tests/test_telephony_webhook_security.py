"""Security-focused tests for telephony webhook handling."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import AsyncIterator

import pytest
from fastapi import BackgroundTasks, HTTPException
from starlette.requests import Request

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
    TelephonyConfig,
    TelephonyProvider,
)
from voice_triage.telephony.capabilities import (
    get_provider_capabilities,
    list_provider_capabilities,
)
from voice_triage.telephony.providers.circleloop.provider import CircleLoopProvider
from voice_triage.telephony.providers.discord.provider import DiscordProvider
from voice_triage.telephony.providers.ringcentral.provider import RingCentralProvider
from voice_triage.telephony.providers.sip.provider import SIPProvider
from voice_triage.telephony.providers.teams.provider import TeamsDirectRoutingProvider
from voice_triage.telephony.providers.twilio.provider import TwilioProvider
from voice_triage.telephony.providers.vonage.provider import VonageProvider
from voice_triage.telephony.providers.zoom.provider import ZoomPhoneProvider
from voice_triage.telephony.registry import TelephonyRegistry
from voice_triage.telephony.webhooks import TelephonyWebhookHandler


def _make_request(
    *,
    path: str,
    body: bytes,
    headers: list[tuple[bytes, bytes]] | None = None,
    query_string: bytes = b"",
    client_ip: str = "127.0.0.1",
) -> Request:
    """Create an ASGI request object for webhook handler tests."""
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.request", "body": b"", "more_body": False}
        sent = True
        return {"type": "http.request", "body": body, "more_body": False}

    return Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": path,
            "query_string": query_string,
            "headers": headers or [(b"content-type", b"application/json")],
            "client": (client_ip, 10000),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
    )


@pytest.mark.asyncio
async def test_twilio_validation_accepts_lowercase_signature_header() -> None:
    """Twilio validation should be header-case insensitive."""
    token = "twilio-secret"
    body = b"CallSid=CA123&From=%2B447700900001"
    path = "/telephony/twilio/voice"
    base_url = "https://example.com"
    full_url = f"{base_url}{path}"

    raw = full_url + body.decode("utf-8")
    digest = hmac.new(token.encode("utf-8"), raw.encode("utf-8"), hashlib.sha1).digest()
    signature = base64.b64encode(digest).decode("utf-8")

    provider = TwilioProvider(
        TelephonyConfig(
            provider_name="twilio",
            auth_token=token,
            webhook_base_url=base_url,
        )
    )

    assert await provider.validate_webhook({"x-twilio-signature": signature}, body, path)


@pytest.mark.asyncio
async def test_sip_webhook_ip_allowlist_is_enforced() -> None:
    """SIP provider should enforce configured source IP allowlist."""
    provider = SIPProvider(
        TelephonyConfig(
            provider_name="sip",
            extra={"allowed_webhook_ips": ["198.51.100.10", "203.0.113.0/24"]},
        )
    )

    assert await provider.validate_webhook(
        {"x-source-ip": "198.51.100.10"},
        b"{}",
        "/telephony/sip/voice",
    )
    assert await provider.validate_webhook(
        {"x-source-ip": "203.0.113.77"},
        b"{}",
        "/telephony/sip/voice",
    )
    assert not await provider.validate_webhook(
        {"x-source-ip": "192.0.2.50"},
        b"{}",
        "/telephony/sip/voice",
    )


@pytest.mark.asyncio
async def test_vonage_authorization_header_requires_configured_secret() -> None:
    """Vonage bearer authorization should fail unless webhook_secret is configured."""
    provider = VonageProvider(
        TelephonyConfig(
            provider_name="vonage",
            api_secret="api-secret",
        )
    )

    result = await provider.validate_webhook(
        headers={"Authorization": "Bearer any-token"},
        body=b"{}",
        path="/telephony/vonage/voice",
    )
    assert result is False


@pytest.mark.asyncio
async def test_vonage_authorization_header_with_configured_secret() -> None:
    """Vonage bearer authorization should validate when configured."""
    provider = VonageProvider(
        TelephonyConfig(
            provider_name="vonage",
            webhook_secret="expected-token",
            api_secret="api-secret",
        )
    )

    result = await provider.validate_webhook(
        headers={"authorization": "Bearer expected-token"},
        body=b"{}",
        path="/telephony/vonage/voice",
    )
    assert result is True


@pytest.mark.asyncio
async def test_discord_hmac_validation_requires_signature_header() -> None:
    """Discord HMAC fallback must include signature header and valid digest."""
    provider = DiscordProvider(
        TelephonyConfig(
            provider_name="discord",
            webhook_secret="discord-secret",
        )
    )

    body = b'{"type":2}'
    missing_sig = await provider.validate_webhook(
        headers={},
        body=body,
        path="/telephony/discord/voice",
    )
    assert missing_sig is False

    signature = hmac.new(b"discord-secret", body, hashlib.sha256).hexdigest()
    valid = await provider.validate_webhook(
        headers={"x-discord-signature": signature},
        body=body,
        path="/telephony/discord/voice",
    )
    assert valid is True


@pytest.mark.asyncio
async def test_ringcentral_validation_requires_configured_secret() -> None:
    """RingCentral validation should fail closed when no webhook secret is set."""
    provider = RingCentralProvider(TelephonyConfig(provider_name="ringcentral"))

    result = await provider.validate_webhook(
        headers={"Verification-Token": "token"},
        body=b"{}",
        path="/telephony/ringcentral/voice",
    )
    assert result is False


@pytest.mark.asyncio
async def test_teams_validation_token_is_echoed_from_query_param() -> None:
    """Webhook handler should echo Teams validation token challenge."""
    registry = TelephonyRegistry()
    registry.register(
        TeamsDirectRoutingProvider(
            TelephonyConfig(
                provider_name="teams",
                extra={"webhook_secret": "state-123"},
            )
        )
    )
    handler = TelephonyWebhookHandler(registry=registry)

    async def receive() -> dict[str, object]:
        return {"type": "http.request", "body": b"{}", "more_body": False}

    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/telephony/teams/voice",
            "query_string": b"validationToken=abc123",
            "headers": [(b"content-type", b"application/json")],
            "client": ("127.0.0.1", 10000),
            "server": ("testserver", 80),
            "root_path": "",
        },
        receive,
    )

    response = await handler.handle_inbound_call("teams", request, BackgroundTasks())
    assert response.status_code == 200
    assert response.body.decode("utf-8") == "abc123"


def test_transcript_extraction_ringcentral_zoom_teams_circleloop() -> None:
    """Providers should extract transcript from common nested payload formats."""
    ringcentral = RingCentralProvider(TelephonyConfig(provider_name="ringcentral"))
    assert (
        ringcentral.extract_transcript(
            {"body": {"speechToText": {"transcript": "hello from ringcentral"}}}
        )
        == "hello from ringcentral"
    )

    zoom = ZoomPhoneProvider(TelephonyConfig(provider_name="zoom"))
    assert (
        zoom.extract_transcript(
            {"payload": {"object": {"speechResult": {"text": "hello from zoom"}}}}
        )
        == "hello from zoom"
    )

    teams = TeamsDirectRoutingProvider(TelephonyConfig(provider_name="teams"))
    assert (
        teams.extract_transcript(
            {"value": [{"resourceData": {"transcript": "hello from teams"}}]}
        )
        == "hello from teams"
    )

    circleloop = CircleLoopProvider(TelephonyConfig(provider_name="circleloop"))
    assert circleloop.extract_transcript({"speechResult": {"text": "hello from circleloop"}}) == (
        "hello from circleloop"
    )


def test_capability_profiles_cover_known_providers() -> None:
    """Capability helper should return readiness metadata for core providers."""
    twilio = get_provider_capabilities("twilio")
    discord = get_provider_capabilities("discord")
    teams = get_provider_capabilities("teams")
    profiles = list_provider_capabilities(["discord", "twilio"])

    assert twilio.ready_for_live_voice_oob is True
    assert discord.ready_for_live_voice_oob is False
    assert teams.ready_for_live_voice_oob is False
    assert [profile["provider"] for profile in profiles] == ["discord", "twilio"]


class _BrokenInboundProvider(TelephonyProvider):
    """Provider that returns incomplete call payload for validation testing."""

    @property
    def name(self) -> str:
        return "broken"

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        del headers, body, path
        return True

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        del headers, body, form_data
        return PhoneCall(
            call_id="",
            from_number="+447700900001",
            to_number="",
            direction=CallDirection.INBOUND,
            status=CallStatus.RINGING,
            provider="broken",
        )

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        del session_id, welcome_message, gather_speech, action_url
        return "{}"

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> PhoneCall:
        del to_number, from_number, webhook_url, metadata
        raise NotImplementedError

    async def hangup_call(self, call_id: str) -> bool:
        del call_id
        return False

    async def play_audio(self, call_id: str, audio_url: str, loop: bool = False) -> bool:
        del call_id, audio_url, loop
        return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        del call_id, digits
        return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        del call_id
        return None

    async def stream_audio(self, call_id: str, audio_stream: AsyncIterator[bytes]) -> bool:
        del call_id, audio_stream
        return False

    def get_webhook_path(self, event_type: str) -> str:
        return f"/telephony/broken/{event_type}"


class _HappyInboundProvider(TelephonyProvider):
    """Provider that always validates and returns parseable calls."""

    @property
    def name(self) -> str:
        return self.config.provider_name

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        del headers, body, path
        return True

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        del headers
        data = form_data
        if not data:
            data = json.loads(body.decode("utf-8"))
        call_id = str(data.get("call_id", "ok-call"))
        from_number = str(data.get("from", "+447700900001"))
        to_number = str(data.get("to", "+447700900002"))
        return PhoneCall(
            call_id=call_id,
            from_number=from_number,
            to_number=to_number,
            direction=CallDirection.INBOUND,
            status=CallStatus.RINGING,
            provider=self.config.provider_name,
        )

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        del session_id, welcome_message, gather_speech, action_url
        return "{}"

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> PhoneCall:
        del to_number, from_number, webhook_url, metadata
        raise NotImplementedError

    async def hangup_call(self, call_id: str) -> bool:
        del call_id
        return False

    async def play_audio(self, call_id: str, audio_url: str, loop: bool = False) -> bool:
        del call_id, audio_url, loop
        return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        del call_id, digits
        return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        del call_id
        return None

    async def stream_audio(self, call_id: str, audio_stream: AsyncIterator[bytes]) -> bool:
        del call_id, audio_stream
        return False

    def get_webhook_path(self, event_type: str) -> str:
        return f"/telephony/{self.name}/{event_type}"


@pytest.mark.asyncio
async def test_inbound_payload_validation_returns_422_for_missing_required_fields() -> None:
    """Webhook handler should reject parsed calls missing required fields."""
    registry = TelephonyRegistry()
    registry.register(_BrokenInboundProvider(TelephonyConfig(provider_name="broken")))
    handler = TelephonyWebhookHandler(registry=registry)
    request = _make_request(path="/telephony/broken/voice", body=b"{}")

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle_inbound_call("broken", request, BackgroundTasks())

    assert exc_info.value.status_code == 422
    assert "missing call_id, to_number" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_rate_limit_blocks_excess_requests_per_provider_and_source_ip() -> None:
    """Webhook handler should enforce per-provider/source-IP rate limits."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="custom")))
    handler = TelephonyWebhookHandler(
        registry=registry,
        webhook_rate_limit_per_minute=1,
        webhook_replay_window_seconds=120,
        time_provider=lambda: 1_000.0,
    )

    request_one = _make_request(
        path="/telephony/custom/voice",
        body=b'{"call_id":"a","from":"+1","to":"+2"}',
    )
    request_two = _make_request(
        path="/telephony/custom/voice",
        body=b'{"call_id":"b","from":"+1","to":"+2"}',
    )

    response = await handler.handle_inbound_call("custom", request_one, BackgroundTasks())
    assert response.status_code == 200

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle_inbound_call("custom", request_two, BackgroundTasks())
    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_replay_protection_rejects_duplicate_requests() -> None:
    """Webhook handler should reject duplicate signed/payload-identical requests."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="custom")))
    handler = TelephonyWebhookHandler(
        registry=registry,
        webhook_rate_limit_per_minute=10,
        webhook_replay_window_seconds=120,
        time_provider=lambda: 2_000.0,
    )
    body = b'{"call_id":"same","from":"+1","to":"+2"}'

    headers = [
        (b"content-type", b"application/json"),
        (b"x-signature-timestamp", b"2000"),
    ]
    first = _make_request(path="/telephony/custom/voice", body=body, headers=headers)
    second = _make_request(path="/telephony/custom/voice", body=body, headers=headers)

    response = await handler.handle_inbound_call("custom", first, BackgroundTasks())
    assert response.status_code == 200

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle_inbound_call("custom", second, BackgroundTasks())
    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_timestamp_freshness_rejects_stale_requests() -> None:
    """Webhook handler should reject stale timestamped requests."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="custom")))
    handler = TelephonyWebhookHandler(
        registry=registry,
        webhook_rate_limit_per_minute=10,
        webhook_replay_window_seconds=60,
        time_provider=lambda: 1_000.0,
    )
    request = _make_request(
        path="/telephony/custom/voice",
        body=b'{"call_id":"fresh","from":"+1","to":"+2"}',
        headers=[
            (b"content-type", b"application/json"),
            (b"x-signature-timestamp", b"900"),
        ],
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle_inbound_call("custom", request, BackgroundTasks())
    assert exc_info.value.status_code == 403
    assert "Stale custom webhook request" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_provider_specific_schema_validation_runs_before_parse() -> None:
    """Twilio inbound payload should fail fast when required raw fields are missing."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="twilio")))
    handler = TelephonyWebhookHandler(
        registry=registry,
        webhook_rate_limit_per_minute=10,
        webhook_replay_window_seconds=60,
    )
    request = _make_request(
        path="/telephony/twilio/voice",
        body=b'{"From":"+447700900001","To":"+447700900002"}',
    )

    with pytest.raises(HTTPException) as exc_info:
        await handler.handle_inbound_call("twilio", request, BackgroundTasks())
    assert exc_info.value.status_code == 422
    assert "call_id (CallSid)" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_status_cleanup_uses_provider_specific_nested_fields() -> None:
    """Status callbacks should clean sessions using nested provider payload fields."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="teams")))
    handler = TelephonyWebhookHandler(registry=registry)
    handler._call_sessions["route-call"] = "route-session"
    handler._call_sessions["teams-call-1"] = "teams-session"

    request = _make_request(
        path="/telephony/teams/status/route-call",
        body=(
            b'{"value":[{"resourceData":{"state":"disconnected","id":"teams-call-1"}}]}'
        ),
    )
    response = await handler.handle_call_status("teams", "route-call", request)

    assert response.status_code == 200
    assert "route-call" not in handler._call_sessions
    assert "teams-call-1" not in handler._call_sessions


@pytest.mark.asyncio
async def test_status_cleanup_works_without_route_call_id() -> None:
    """Status callbacks without call-id route params should still clean terminal sessions."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="teams")))
    handler = TelephonyWebhookHandler(registry=registry)
    handler._call_sessions["teams-call-2"] = "teams-session"

    request = _make_request(
        path="/telephony/teams/callback",
        body=(
            b'{"value":[{"resourceData":{"state":"disconnected","id":"teams-call-2"}}]}'
        ),
    )
    response = await handler.handle_call_status_auto("teams", request)

    assert response.status_code == 200
    assert "teams-call-2" not in handler._call_sessions


@pytest.mark.asyncio
async def test_status_cleanup_ignores_non_terminal_states() -> None:
    """In-progress state updates should not remove active call sessions."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="twilio")))
    handler = TelephonyWebhookHandler(registry=registry)
    handler._call_sessions["tw-call"] = "tw-session"

    request = _make_request(
        path="/telephony/twilio/status/tw-call",
        body=b'{"CallStatus":"in-progress"}',
    )
    response = await handler.handle_call_status("twilio", "tw-call", request)

    assert response.status_code == 200
    assert handler._call_sessions["tw-call"] == "tw-session"


@pytest.mark.asyncio
async def test_status_cleanup_normalizes_cancelled_variant() -> None:
    """British-spelled cancelled status should still trigger cleanup."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="vonage")))
    handler = TelephonyWebhookHandler(registry=registry)
    handler._call_sessions["vonage-call"] = "vonage-session"

    request = _make_request(
        path="/telephony/vonage/status/vonage-call",
        body=b'{"status":"cancelled"}',
    )
    response = await handler.handle_call_status("vonage", "vonage-call", request)

    assert response.status_code == 200
    assert "vonage-call" not in handler._call_sessions


@pytest.mark.asyncio
async def test_status_cleanup_normalizes_noanswer_variant() -> None:
    """noanswer status variant should trigger terminal cleanup."""
    registry = TelephonyRegistry()
    registry.register(_HappyInboundProvider(TelephonyConfig(provider_name="circleloop")))
    handler = TelephonyWebhookHandler(registry=registry)
    handler._call_sessions["circle-call"] = "circle-session"

    request = _make_request(
        path="/telephony/circleloop/status/circle-call",
        body=b'{"status":"noanswer"}',
    )
    response = await handler.handle_call_status("circleloop", "circle-call", request)

    assert response.status_code == 200
    assert "circle-call" not in handler._call_sessions


def test_rate_limit_cache_prunes_stale_source_keys() -> None:
    """Rate-limit key map should prune stale provider/source buckets."""
    registry = TelephonyRegistry()
    now_ref = [1_000.0]
    handler = TelephonyWebhookHandler(
        registry=registry,
        webhook_rate_limit_per_minute=10,
        webhook_rate_limit_cache_max_keys=2,
        webhook_rate_limit_sweep_interval_seconds=1,
        time_provider=lambda: now_ref[0],
    )

    handler._enforce_rate_limit("custom", {"x-source-ip": "198.51.100.1"})
    handler._enforce_rate_limit("custom", {"x-source-ip": "198.51.100.2"})
    assert len(handler._rate_limit_hits) == 2

    now_ref[0] = 2_000.0
    handler._enforce_rate_limit("custom", {"x-source-ip": "198.51.100.3"})

    assert len(handler._rate_limit_hits) == 1
    assert "custom:198.51.100.3" in handler._rate_limit_hits


def test_replay_cache_enforces_max_entries() -> None:
    """Replay cache should evict oldest keys when max entries is exceeded."""
    registry = TelephonyRegistry()
    handler = TelephonyWebhookHandler(
        registry=registry,
        webhook_replay_window_seconds=120,
        webhook_replay_cache_max_entries=2,
        time_provider=lambda: 1_000.0,
    )
    headers = {
        "x-signature-timestamp": "1000",
        "x-twilio-signature": "sig-123",
    }
    path = "/telephony/custom/voice"
    first_body = b'{"call_id":"one"}'
    second_body = b'{"call_id":"two"}'
    third_body = b'{"call_id":"three"}'

    first_key = handler._build_replay_key("custom", headers, first_body, path)
    assert first_key is not None
    handler._enforce_replay_protection("custom", headers, first_body, path)
    handler._enforce_replay_protection("custom", headers, second_body, path)
    handler._enforce_replay_protection("custom", headers, third_body, path)

    assert len(handler._replay_cache) == 2
    assert first_key not in handler._replay_cache
