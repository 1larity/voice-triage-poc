#!/usr/bin/env python3
"""Run telephony webhook smoke checks from provider fixture corpus."""

from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import hmac
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

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

FIXTURE_DIR = (
    Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "telephony_webhooks"
)


class _SmokeAvayaProvider(AvayaProvider):
    """Concrete Avaya variant for local validation checks."""

    async def play_audio(self, call_id: str, audio_url: str, loop: bool = False) -> bool:
        """Stub playback for abstract interface compliance."""
        del call_id, audio_url, loop
        return False


def _build_provider(provider_name: str, config_payload: dict[str, Any]) -> TelephonyProvider:
    """Instantiate provider from fixture configuration."""
    provider_map: dict[str, type[TelephonyProvider]] = {
        "avaya": _SmokeAvayaProvider,
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
    """Compute signature value from fixture signature descriptor."""
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


def _build_headers(case_payload: dict[str, Any], body: bytes, path: str) -> dict[str, str]:
    """Build case headers and attach computed signatures."""
    headers = {str(k): str(v) for k, v in case_payload.get("headers", {}).items()}
    signature_spec = case_payload.get("signature")
    if signature_spec:
        header_name = str(signature_spec["header"])
        headers[header_name] = _compute_signature(signature_spec, body, path)
    return headers


def _load_cases(
    requested_providers: set[str] | None = None,
    only_valid: bool = False,
) -> list[dict[str, Any]]:
    """Load provider fixture cases from disk."""
    cases: list[dict[str, Any]] = []
    for fixture_path in sorted(FIXTURE_DIR.glob("*.json")):
        fixture_doc = json.loads(fixture_path.read_text(encoding="utf-8"))
        provider = str(fixture_doc["provider"])
        if requested_providers and provider not in requested_providers:
            continue
        config_payload = dict(fixture_doc.get("config", {}))
        for case_payload in fixture_doc.get("cases", []):
            if only_valid and not bool(case_payload.get("expected_valid")):
                continue
            cases.append(
                {
                    "fixture_name": fixture_path.name,
                    "provider": provider,
                    "config": config_payload,
                    "case": case_payload,
                }
            )
    return cases


def _expected_remote_statuses(case_payload: dict[str, Any]) -> set[int]:
    """Map expected fixture outcome to accepted webhook HTTP statuses."""
    if not bool(case_payload.get("expected_valid")):
        return {403}

    headers = {str(k).lower(): str(v) for k, v in case_payload.get("headers", {}).items()}
    if "validationtoken" in headers:
        return {200}

    # Valid signatures may still fail payload-shape validation in the handler.
    return {200, 422}


async def _run_local_validation(cases: list[dict[str, Any]]) -> int:
    """Run provider-local webhook validation against fixture contract."""
    failures = 0
    for entry in cases:
        case_payload = entry["case"]
        provider_name = str(entry["provider"])
        provider = _build_provider(provider_name, entry["config"])
        path = str(case_payload["path"])
        body = str(case_payload["body"]).encode("utf-8")
        headers = _build_headers(case_payload, body, path)
        expected = bool(case_payload["expected_valid"])
        actual = await provider.validate_webhook(headers, body, path)
        ok = actual is expected
        status = "PASS" if ok else "FAIL"
        print(
            f"[{status}] local {provider_name}:{case_payload['name']} "
            f"(expected={expected}, actual={actual})"
        )
        if not ok:
            failures += 1
    return failures


def _run_remote_validation(cases: list[dict[str, Any]], base_url: str, timeout: float) -> int:
    """Run HTTP webhook checks against a live local/remote application URL."""
    failures = 0
    clean_base_url = base_url.rstrip("/")

    for entry in cases:
        case_payload = entry["case"]
        provider_name = str(entry["provider"])
        path = str(case_payload["path"])
        body = str(case_payload["body"]).encode("utf-8")
        headers = _build_headers(case_payload, body, path)
        url = f"{clean_base_url}{path}"
        request = urllib.request.Request(url=url, data=body, headers=headers, method="POST")

        response_code = 0
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                response_code = int(response.getcode())
        except urllib.error.HTTPError as exc:
            response_code = int(exc.code)
        except urllib.error.URLError as exc:
            print(f"[FAIL] remote {provider_name}:{case_payload['name']} ({exc})")
            failures += 1
            continue

        expected_codes = _expected_remote_statuses(case_payload)
        ok = response_code in expected_codes
        status = "PASS" if ok else "FAIL"
        print(
            f"[{status}] remote {provider_name}:{case_payload['name']} "
            f"(status={response_code}, expected={sorted(expected_codes)})"
        )
        if not ok:
            failures += 1

    return failures


def main() -> int:
    """Entrypoint for telephony provider smoke runner."""
    parser = argparse.ArgumentParser(
        description=(
            "Run telephony webhook smoke checks from fixture corpus. "
            "Use local mode for provider-only contract checks or remote mode "
            "to exercise live webhook endpoints."
        )
    )
    parser.add_argument(
        "--mode",
        choices=("local", "remote"),
        default="local",
        help="Smoke execution mode.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:8000",
        help="Base URL for remote mode.",
    )
    parser.add_argument(
        "--provider",
        action="append",
        default=[],
        help="Provider name filter (repeatable).",
    )
    parser.add_argument(
        "--only-valid",
        action="store_true",
        help="Execute only fixtures where expected_valid=true.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=float,
        default=10.0,
        help="Per-request timeout for remote mode.",
    )
    args = parser.parse_args()

    requested_providers = {item.strip().lower() for item in args.provider if item.strip()}
    cases = _load_cases(
        requested_providers=requested_providers or None,
        only_valid=bool(args.only_valid),
    )

    if not cases:
        print("No fixture cases selected.")
        return 1

    if args.mode == "local":
        failures = asyncio.run(_run_local_validation(cases))
    else:
        failures = _run_remote_validation(cases, args.base_url, args.timeout_seconds)

    passed = len(cases) - failures
    print(f"Summary: {passed}/{len(cases)} passed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
