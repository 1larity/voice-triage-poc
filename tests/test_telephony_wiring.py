"""Integration-focused telephony wiring tests."""

from __future__ import annotations

import json
from types import SimpleNamespace
from typing import cast

import pytest

import voice_triage.http.rest as rest_module
import voice_triage.web.server as web_server_module
from voice_triage.telephony.base import TelephonyConfig
from voice_triage.telephony.config.settings import TelephonySettings, load_telephony_settings
from voice_triage.telephony.providers.teams.parser import generate_teams_response
from voice_triage.telephony.providers.teams.provider import TeamsDirectRoutingProvider
from voice_triage.telephony.registry import list_providers
from voice_triage.telephony.webhooks import build_telephony_handler


def _make_fake_runtime() -> rest_module.ApiRuntime:
    """Create a lightweight runtime object for app-construction tests."""

    class _FakeEngine:
        def __init__(self) -> None:
            self.sessions: dict[str, object] = {}

        def create_session(self) -> tuple[str, str]:
            return ("session-1", "hello")

        def process_turn(self, session_id: str, transcript: str) -> SimpleNamespace:
            del session_id, transcript
            return SimpleNamespace(response_text="ok")

    return rest_module.ApiRuntime(
        settings=cast(rest_module.Settings, object()),
        asr_client=cast(rest_module.WhisperCppClient, object()),
        tts_client=cast(rest_module.PiperClient, object()),
        available_voices={},
        default_voice_id=None,
        engine=_FakeEngine(),
    )


def test_to_provider_configs_maps_extended_provider_configs() -> None:
    """Provider config conversion should include all configured providers."""
    settings = TelephonySettings()
    settings.twilio.account_sid = "ac"
    settings.twilio.auth_token = "token"
    settings.vonage.api_key = "vk"
    settings.vonage.api_secret = "vs"
    settings.sip.sip_server = "sip.example"
    settings.sip.sip_username = "u"
    settings.sip.sip_password = "p"
    settings.gamma.sip_server = "gamma.example"
    settings.gamma.sip_username = "u"
    settings.gamma.sip_password = "p"
    settings.bt.sip_server = "bt.example"
    settings.bt.sip_username = "u"
    settings.bt.sip_password = "p"
    settings.ringcentral.client_id = "rcid"
    settings.ringcentral.client_secret = "rcsecret"
    settings.ringcentral.jwt_token = "jwt"
    settings.zoom.account_id = "zoom-account"
    settings.zoom.client_id = "zoom-id"
    settings.zoom.client_secret = "zoom-secret"
    settings.teams.tenant_id = "tenant"
    settings.teams.client_id = "teams-id"
    settings.teams.client_secret = "teams-secret"
    settings.circleloop.api_key = "cl-key"
    settings.circleloop.api_secret = "cl-secret"
    settings.nfon.client_id = "nfon-id"
    settings.nfon.client_secret = "nfon-secret"
    settings.discord.bot_token = "discord-token"
    settings.avaya.server_host = "avaya-host"
    settings.avaya.username = "avaya-user"
    settings.avaya.password = "avaya-pass"

    configs = settings.to_provider_configs()

    expected = {
        "twilio",
        "vonage",
        "nexmo",
        "sip",
        "gamma",
        "bt",
        "ringcentral",
        "zoom",
        "teams",
        "circleloop",
        "nfon",
        "discord",
        "avaya",
        "avaya_aes",
        "avaya_ip_office",
    }
    assert expected.issubset(set(configs.keys()))
    assert all("provider_name" not in payload for payload in configs.values())
    assert configs["zoom"]["api_key"] == "zoom-id"
    assert configs["avaya"]["extra"]["server_host"] == "avaya-host"


def test_load_telephony_settings_merges_zoom_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment-based Zoom config should be merged into loaded settings."""
    monkeypatch.setenv("ZOOM_ACCOUNT_ID", "zoom-account")
    monkeypatch.setenv("ZOOM_CLIENT_ID", "zoom-id")
    monkeypatch.setenv("ZOOM_CLIENT_SECRET", "zoom-secret")

    settings = load_telephony_settings()

    assert settings.zoom.account_id == "zoom-account"
    assert settings.zoom.is_configured()


def test_build_telephony_handler_registers_twilio() -> None:
    """Handler builder should tolerate provider_name in payload and still register."""
    handler = build_telephony_handler(
        provider_configs={
            "twilio": {
                "provider_name": "twilio",
                "account_sid": "ac123",
                "auth_token": "token123",
                "webhook_base_url": "https://example.com",
            }
        }
    )
    assert "twilio" in handler.registry.list_registered()


def test_list_providers_includes_extended_provider_set() -> None:
    """Provider registry should include non-legacy providers after auto-import."""
    providers = set(list_providers())
    assert {"ringcentral", "zoom", "teams", "circleloop", "nfon", "sip", "discord"}.issubset(
        providers
    )


@pytest.mark.asyncio
async def test_teams_webhook_validation_supports_graph_value_payload() -> None:
    """Teams provider should validate clientState from Graph notification array."""
    provider = TeamsDirectRoutingProvider(
        TelephonyConfig(provider_name="teams", extra={"webhook_secret": "state-123"})
    )
    body = json.dumps({"value": [{"clientState": "state-123"}]}).encode("utf-8")
    assert await provider.validate_webhook({}, body, "/telephony/teams/voice")


def test_generate_teams_response_has_mutable_actions_list() -> None:
    """Teams response generation should return usable JSON actions list."""
    response = generate_teams_response(
        session_id="session-1",
        welcome_message="Hello",
        gather_speech=True,
        action_url="/telephony/teams/voice/session-1",
    )
    payload = json.loads(response)
    assert isinstance(payload["actions"], list)
    assert len(payload["actions"]) == 2


def test_create_rest_app_mounts_telephony_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    """REST app should include telephony router endpoints."""
    fake_runtime = _make_fake_runtime()
    monkeypatch.setattr(rest_module, "initialize_runtime", lambda settings=None: fake_runtime)

    app = rest_module.create_rest_app()
    paths = {route.path for route in app.routes}
    assert "/telephony/providers" in paths
    assert "/telephony/capabilities" in paths
    assert "/telephony/{provider_name}/voice" in paths
    assert "/telephony/{provider_name}/status" in paths
    assert "/telephony/twilio/status" in paths
    assert "/telephony/teams/callback" in paths
    assert "/telephony/teams/notification" in paths


def test_create_web_app_mounts_telephony_routes(monkeypatch: pytest.MonkeyPatch) -> None:
    """Web app should include telephony router endpoints."""
    fake_runtime = _make_fake_runtime()
    monkeypatch.setattr(web_server_module, "initialize_runtime", lambda: fake_runtime)

    app = web_server_module.create_app()
    paths = {route.path for route in app.routes}
    assert "/telephony/providers" in paths
    assert "/telephony/capabilities" in paths
    assert "/telephony/{provider_name}/voice" in paths
    assert "/telephony/{provider_name}/status" in paths
    assert "/telephony/twilio/status" in paths
    assert "/telephony/teams/callback" in paths
    assert "/telephony/teams/notification" in paths
