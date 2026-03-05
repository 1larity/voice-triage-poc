"""Discord telephony provider implementation.

This module re-exports the decomposed Discord provider components for
backward compatibility. The actual implementation is in the providers/discord/
subdirectory.

Discord is a popular communication platform that supports:
- Voice channels for real-time communication
- Bot interactions via webhooks
- Guild (server) based voice connections
- WebSocket-based real-time events

Documentation: https://discord.com/developers/docs
"""

from voice_triage.telephony.providers.discord import (
    DISCORD_STATUS_MAP,
    DiscordGateway,
    DiscordProvider,
    DiscordVoiceConnection,
    generate_interaction_response,
    parse_channel_id,
    parse_inbound_interaction,
    validate_ed25519_signature,
    validate_hmac_signature,
)

__all__ = [
    "DISCORD_STATUS_MAP",
    "DiscordGateway",
    "DiscordProvider",
    "DiscordVoiceConnection",
    "generate_interaction_response",
    "parse_channel_id",
    "parse_inbound_interaction",
    "validate_ed25519_signature",
    "validate_hmac_signature",
]
