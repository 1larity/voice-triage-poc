"""Contract fixture tests for telephony webhook validation."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
from pathlib import Path
from typing import Any

import pytest

from voice_triage.telephony.base import TelephonyConfig, TelephonyProvider
from voice_triage.telephony.providers.avaya.provider import AvayaProvider
from voice_triage.telephony.providers.circleloop.provider import CircleLoopProvider
from voice_triage.telephony.providers.discord.provider import DiscordProvider
from voice_triage.telephony.providers.nfon.provider import NFONProvider
from voice_triage.telephony.providers.ringcentral.provider import RingCentralProvider
from voice_triage.telephony.providers.sip.provider import BTProvider, GammaProvider, SIPProvider
from voice_triage.telephony.providers.teams.provider import TeamsDirectRoutingProvider
from voice_triage.telephony.providers.twilio.provider import TwilioProvider
from voice_triage.telephony.providers.vonage.provider import VonageProvider
from voice_triage.telephony.providers.zoom.provider import ZoomPhoneProvider

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "telephony_webhooks"


class _ContractAvayaProvider(AvayaProvider):
    """Concrete Avaya test provider for webhook-contract validation."""

    async def play_audio(self, call_id: str, audio_url: str, loop: bool = False) -> bool:
        """Stub media playback for abstract interface compliance in tests."""
        del call_id, audio_url, loop
        return False


def _build_provider(provider_name: str, config_payload: dict[str, Any]) -> TelephonyProvider:
    """Instantiate provider under test from fixture configuration."""
    provider_map: dict[str, type[TelephonyProvider]] = {
        "avaya": _ContractAvayaProvider,
        "bt": BTProvider,
        "circleloop": CircleLoopProvider,
        "discord": DiscordProvider,
        "gamma": GammaProvider,
        "nfon": NFONProvider,
        "ringcentral": RingCentralProvider,
        "sip": SIPProvider,
        "teams": TeamsDirectRoutingProvider,
        "twilio": TwilioProvider,
        "vonage": VonageProvider,
        "zoom": ZoomPhoneProvider,
    }
    provider_cls = provider_map[provider_name]
    payload = dict(config_payload)
    payload.pop("provider_name", None)
    return provider_cls(TelephonyConfig(provider_name=provider_name, **payload))


def _compute_signature(signature_spec: dict[str, Any], body: bytes, path: str) -> str:
    """Compute signature header values from fixture signature descriptors."""
    signature_type = str(signature_spec["type"])
    secret = str(signature_spec["secret"])

    if signature_type == "twilio_sha1_base64":
        base_url = str(signature_spec["base_url"]).rstrip("/")
        payload = f"{base_url}{path}{body.decode('utf-8')}"
        digest = hmac.new(
            secret.encode("utf-8"),
            payload.encode("utf-8"),
            hashlib.sha1,
        ).digest()
        return base64.b64encode(digest).decode("utf-8")

    if signature_type == "hmac_sha256_hex":
        return hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()

    if signature_type == "hmac_sha256_hex_prefixed":
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return f"sha256={digest}"

    if signature_type == "hmac_sha512_hex":
        return hmac.new(secret.encode("utf-8"), body, hashlib.sha512).hexdigest()

    if signature_type == "zoom_v0_sha256":
        digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
        return f"v0={digest}"

    raise ValueError(f"Unknown signature type: {signature_type}")


def _build_headers(
    case_payload: dict[str, Any],
    body: bytes,
    path: str,
) -> dict[str, str]:
    """Build final headers for a fixture case, including computed signatures."""
    headers = {str(key): str(value) for key, value in case_payload.get("headers", {}).items()}
    signature_spec = case_payload.get("signature")
    if signature_spec:
        header_name = str(signature_spec["header"])
        headers[header_name] = _compute_signature(signature_spec, body, path)
    return headers


def _load_fixture_parameters() -> list[Any]:
    """Load fixture cases from disk as pytest parameter entries."""
    parameters: list[Any] = []
    for fixture_path in sorted(FIXTURE_DIR.glob("*.json")):
        fixture_doc = json.loads(fixture_path.read_text(encoding="utf-8"))
        provider_name = str(fixture_doc["provider"])
        config_payload = dict(fixture_doc.get("config", {}))
        for case_payload in fixture_doc.get("cases", []):
            case_name = str(case_payload["name"])
            parameters.append(
                pytest.param(
                    provider_name,
                    config_payload,
                    case_payload,
                    fixture_path.name,
                    id=f"{fixture_path.stem}:{case_name}",
                )
            )
    return parameters


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("provider_name", "config_payload", "case_payload", "fixture_name"),
    _load_fixture_parameters(),
)
async def test_webhook_contract_fixture_validation(
    provider_name: str,
    config_payload: dict[str, Any],
    case_payload: dict[str, Any],
    fixture_name: str,
) -> None:
    """Provider webhook validation should match fixture contract expectation."""
    body = str(case_payload["body"]).encode("utf-8")
    path = str(case_payload["path"])
    headers = _build_headers(case_payload, body, path)
    expected = bool(case_payload["expected_valid"])
    provider = _build_provider(provider_name, config_payload)

    actual = await provider.validate_webhook(headers, body, path)

    assert actual is expected, (
        f"Fixture contract mismatch for {fixture_name}:{case_payload['name']} "
        f"(provider={provider_name}, expected={expected}, actual={actual})"
    )


def test_webhook_contract_fixture_coverage_includes_all_primary_providers() -> None:
    """Fixture corpus should cover all primary telephony providers."""
    providers_with_fixtures: set[str] = set()
    for fixture_path in sorted(FIXTURE_DIR.glob("*.json")):
        fixture_doc = json.loads(fixture_path.read_text(encoding="utf-8"))
        providers_with_fixtures.add(str(fixture_doc["provider"]))

    expected_providers = {
        "avaya",
        "bt",
        "circleloop",
        "discord",
        "gamma",
        "nfon",
        "ringcentral",
        "sip",
        "teams",
        "twilio",
        "vonage",
        "zoom",
    }
    assert providers_with_fixtures == expected_providers
