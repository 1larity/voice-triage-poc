"""Discord event parsing utilities.

This module provides parsing functions for Discord interactions
and voice events.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)

logger = logging.getLogger(__name__)

# Mapping from Discord voice states to our CallStatus
DISCORD_STATUS_MAP: dict[str, CallStatus] = {
    "CONNECTED": CallStatus.IN_PROGRESS,
    "CONNECTING": CallStatus.RINGING,
    "DISCONNECTED": CallStatus.COMPLETED,
    "RESUMING": CallStatus.IN_PROGRESS,
    "AWAITING_ENDPOINT": CallStatus.RINGING,
    "AUTHENTICATING": CallStatus.RINGING,
}


def parse_channel_id(identifier: str) -> str | None:
    """Parse channel ID from various formats.

    Args:
        identifier: Channel identifier in various formats.

    Returns:
        Channel ID or None.
    """
    if identifier.isdigit():
        return identifier

    if identifier.startswith("discord:channel/"):
        return identifier.split("/")[-1]

    if identifier.startswith("discord:guild/") and "/channel/" in identifier:
        parts = identifier.split("/channel/")
        return parts[-1] if parts else None

    return None


def parse_inbound_interaction(
    body: bytes,
    guild_id: str | None = None,
    default_channel_id: str | None = None,
) -> PhoneCall:
    """Parse an inbound Discord interaction as a "call".

    Discord doesn't have traditional calls, but voice channel joins
    and interactions can be treated as call-like events.

    Args:
        body: Raw request body (JSON for Discord).
        guild_id: Default guild ID if not in payload.
        default_channel_id: Default channel ID if not in payload.

    Returns:
        PhoneCall object representing the Discord interaction.
    """
    # Parse JSON body
    try:
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        data = {}

    interaction_type = data.get("type", 0)
    user_data = data.get("member", {}).get("user", {})
    parsed_guild_id = data.get("guild_id", guild_id)
    channel_data = data.get("channel_id", {})
    if isinstance(channel_data, dict):
        parsed_channel_id = channel_data.get("id", default_channel_id)
    else:
        parsed_channel_id = channel_data or default_channel_id

    # Generate a unique call ID
    call_id = f"discord_{parsed_guild_id}_{parsed_channel_id}_{int(time.time())}"

    # User info
    user_id = user_data.get("id", "unknown")
    username = user_data.get("username", "Unknown")
    discriminator = user_data.get("discriminator", "0000")

    # Create a "phone number" style identifier from Discord user
    from_identifier = f"discord:{username}#{discriminator} ({user_id})"
    to_identifier = f"discord:guild/{parsed_guild_id}/channel/{parsed_channel_id}"

    return PhoneCall(
        call_id=call_id,
        from_number=from_identifier,
        to_number=to_identifier,
        direction=CallDirection.INBOUND,
        status=CallStatus.IN_PROGRESS,
        provider="discord",
        started_at=None,
        metadata={
            "interaction_type": interaction_type,
            "user_id": user_id,
            "username": username,
            "discriminator": discriminator,
            "guild_id": parsed_guild_id,
            "channel_id": parsed_channel_id,
            "data": data,
        },
    )


def validate_hmac_signature(signature: str, body: bytes, secret: str) -> bool:
    """Validate HMAC signature for Discord webhooks.

    Args:
        signature: Signature from X-Discord-Signature header.
        body: Raw request body.
        secret: Webhook secret.

    Returns:
        True if valid.
    """
    if not signature or not secret:
        return False

    computed = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    normalized = signature
    if normalized.lower().startswith("sha256="):
        normalized = normalized.split("=", 1)[1]
    return hmac.compare_digest(computed, normalized.lower())


async def validate_ed25519_signature(
    signature: str,
    timestamp: str,
    body: bytes,
    public_key: str,
) -> bool:
    """Validate Discord interaction signature using ED25519.

    Args:
        signature: The X-Signature-Ed25519 header value.
        timestamp: The X-Signature-Timestamp header value.
        body: Raw request body.
        public_key: Discord application public key (hex).

    Returns:
        True if valid.
    """
    try:
        # Try to use nacl for Ed25519 verification
        import nacl.encoding
        import nacl.signing

        # Construct message to verify
        message = timestamp.encode() + body

        # Verify signature
        verify_key = nacl.signing.VerifyKey(public_key, encoder=nacl.encoding.HexEncoder)

        verify_key.verify(
            message,
            bytes.fromhex(signature),
        )
        return True

    except Exception as exc:
        logger.warning(f"Discord signature validation failed: {exc}")
        return False


def generate_interaction_response(
    content: str,
    tts: bool = False,
    embeds: list[dict[str, Any]] | None = None,
) -> str:
    """Generate a Discord interaction response.

    Args:
        content: Message content.
        tts: Whether to use text-to-speech.
        embeds: Optional list of embed objects.

    Returns:
        JSON string for Discord interaction response.
    """
    response: dict[str, Any] = {
        "type": 4,  # CHANNEL_MESSAGE_WITH_SOURCE
        "data": {
            "tts": tts,
            "content": content,
            "embeds": embeds or [],
            "allowed_mentions": {"parse": []},
        },
    }

    return json.dumps(response)
