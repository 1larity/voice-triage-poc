"""Discord provider module exports.

This module provides the Discord telephony provider and related utilities.
"""

from voice_triage.telephony.providers.discord.connection import (
    DiscordGateway,
    DiscordVoiceConnection,
)
from voice_triage.telephony.providers.discord.parser import (
    DISCORD_STATUS_MAP,
    generate_interaction_response,
    parse_channel_id,
    parse_inbound_interaction,
    validate_ed25519_signature,
    validate_hmac_signature,
)
from voice_triage.telephony.providers.discord.provider import DiscordProvider

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
