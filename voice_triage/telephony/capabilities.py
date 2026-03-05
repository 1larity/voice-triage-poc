"""Provider capability profiles for telephony integrations."""

from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ProviderCapabilities:
    """Describes practical runtime capabilities for a provider."""

    provider: str
    inbound_webhook: bool
    webhook_auth: bool
    multi_turn_loop: bool
    outbound_call: bool
    realtime_media: bool
    ready_for_live_voice_oob: bool
    requires_external_bridge: bool
    notes: list[str]


_PROVIDER_CAPABILITY_MAP: dict[str, ProviderCapabilities] = {
    "twilio": ProviderCapabilities(
        provider="twilio",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["TwiML flow implemented", "Realtime media stream path is placeholder"],
    ),
    "vonage": ProviderCapabilities(
        provider="vonage",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["NCCO flow implemented", "Realtime media stream path is placeholder"],
    ),
    "nexmo": ProviderCapabilities(
        provider="nexmo",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Alias of Vonage provider"],
    ),
    "sip": ProviderCapabilities(
        provider="sip",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=True,
        notes=["Requires SIP-to-HTTP bridge/gateway"],
    ),
    "gamma": ProviderCapabilities(
        provider="gamma",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=True,
        notes=["SIP bridge required", "Gamma signature validation implemented"],
    ),
    "bt": ProviderCapabilities(
        provider="bt",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=True,
        notes=["SIP bridge required", "Bearer token validation implemented"],
    ),
    "ringcentral": ProviderCapabilities(
        provider="ringcentral",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Verification-token validation supported"],
    ),
    "zoom": ProviderCapabilities(
        provider="zoom",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Webhook signature validation implemented"],
    ),
    "zoom_phone": ProviderCapabilities(
        provider="zoom_phone",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Alias of Zoom provider"],
    ),
    "teams": ProviderCapabilities(
        provider="teams",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=False,
        requires_external_bridge=True,
        notes=["Graph webhook flow works", "Full media hosting loop still required"],
    ),
    "microsoft_teams": ProviderCapabilities(
        provider="microsoft_teams",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=False,
        requires_external_bridge=True,
        notes=["Alias of Teams provider"],
    ),
    "teams_direct_routing": ProviderCapabilities(
        provider="teams_direct_routing",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=False,
        requires_external_bridge=True,
        notes=["Alias of Teams provider"],
    ),
    "circleloop": ProviderCapabilities(
        provider="circleloop",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Webhook signature validation implemented"],
    ),
    "nfon": ProviderCapabilities(
        provider="nfon",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Webhook signature validation implemented"],
    ),
    "discord": ProviderCapabilities(
        provider="discord",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=False,
        requires_external_bridge=True,
        notes=["Webhook/session loop works", "True voice media bridge still required"],
    ),
    "avaya": ProviderCapabilities(
        provider="avaya",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Basic auth/HMAC validation supported"],
    ),
    "avaya_aes": ProviderCapabilities(
        provider="avaya_aes",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Alias of Avaya provider"],
    ),
    "avaya_ip_office": ProviderCapabilities(
        provider="avaya_ip_office",
        inbound_webhook=True,
        webhook_auth=True,
        multi_turn_loop=True,
        outbound_call=True,
        realtime_media=False,
        ready_for_live_voice_oob=True,
        requires_external_bridge=False,
        notes=["Alias of Avaya provider"],
    ),
}


def get_provider_capabilities(provider_name: str) -> ProviderCapabilities:
    """Return capabilities for a provider name."""
    provider_key = provider_name.lower()
    if provider_key in _PROVIDER_CAPABILITY_MAP:
        return _PROVIDER_CAPABILITY_MAP[provider_key]
    return ProviderCapabilities(
        provider=provider_key,
        inbound_webhook=False,
        webhook_auth=False,
        multi_turn_loop=False,
        outbound_call=False,
        realtime_media=False,
        ready_for_live_voice_oob=False,
        requires_external_bridge=True,
        notes=["No capability profile available yet"],
    )


def list_provider_capabilities(provider_names: list[str]) -> list[dict[str, object]]:
    """Return capability profiles as JSON-safe dictionaries."""
    profiles = [asdict(get_provider_capabilities(name)) for name in sorted(set(provider_names))]
    return profiles
