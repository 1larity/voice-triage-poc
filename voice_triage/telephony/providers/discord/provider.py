"""Discord voice provider implementation.

Discord is a popular communication platform for communities, including
councils and public sector organizations. This provider enables voice
triage integration for councils with Discord presence.

Features:
- Voice channel connections via Discord Bot API
- Real-time audio streaming via Voice WebSocket
- Text channel integration for multi-modal interactions
- Guild (server) based community management

Discord is increasingly used by UK councils for community engagement,
particularly for younger demographics and tech-forward communities.

Documentation:
- Bot API: https://discord.com/developers/docs/intro
- Voice: https://discord.com/developers/docs/topics/voice-connections
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
    TelephonyConfig,
    TelephonyProvider,
)
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
from voice_triage.telephony.registry import register_provider
from voice_triage.telephony.shared.auth import get_header

logger = logging.getLogger(__name__)


@register_provider("discord")
class DiscordProvider(TelephonyProvider):
    """Discord voice provider implementation.

    This provider integrates with Discord's Bot API and Voice WebSocket
    for handling voice interactions in Discord guilds (servers).

    Unlike traditional telephony providers, Discord uses:
    - Bot tokens for authentication (not SIP credentials)
    - WebSocket for real-time bidirectional audio
    - Opus codec for audio encoding
    - Guild/channel IDs instead of phone numbers
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the Discord provider.

        Args:
            config: Configuration containing:
                - api_key: Discord Bot Token
                - webhook_secret: Optional secret for webhook validation
                - extra: Dict with optional keys:
                    - guild_id: Discord Guild (Server) ID
                    - voice_channel_id: Default voice channel ID
                    - text_channel_id: Default text channel ID for interactions
                    - application_id: Discord Application ID
        """
        super().__init__(config)
        self._http_client: Any = None
        self._gateway: DiscordGateway | None = None
        self._voice_connections: dict[str, DiscordVoiceConnection] = {}

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "discord"

    @property
    def bot_token(self) -> str | None:
        """Get the Discord bot token from config."""
        return self.config.api_key

    @property
    def guild_id(self) -> str | None:
        """Get the configured guild ID."""
        return self.config.extra.get("guild_id")

    @property
    def default_voice_channel_id(self) -> str | None:
        """Get the default voice channel ID."""
        return self.config.extra.get("voice_channel_id")

    def _get_http_client(self) -> Any:
        """Get or create HTTP client for Discord API.

        Lazily imports discord.py for HTTP operations.
        """
        if self._http_client is None:
            try:
                from discord.http import HTTPClient

                # Create HTTP client with bot token
                self._http_client = HTTPClient(self.bot_token)
            except ImportError as exc:
                raise RuntimeError(
                    "discord.py package is required for Discord integration. "
                    "Install it with: pip install discord.py"
                ) from exc
        return self._http_client

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate a Discord webhook/interaction signature.

        Discord signs interactions with ED25519 signature.
        For webhooks, uses HMAC-SHA256 with webhook secret.

        Args:
            headers: HTTP headers including X-Signature-Ed25519.
            body: Raw request body.
            path: Request path (unused for Discord).

        Returns:
            True if signature is valid.
        """
        signature = get_header(headers, "X-Signature-Ed25519")
        timestamp = get_header(headers, "X-Signature-Timestamp")

        if signature and timestamp:
            # Discord Interaction signature (ED25519)
            return await self._validate_interaction_signature(
                signature=signature,
                timestamp=timestamp,
                body=body,
            )

        # Fallback to HMAC webhook validation
        webhook_secret = self.config.webhook_secret
        if not webhook_secret:
            logger.warning("No webhook_secret configured for Discord validation")
            return False

        webhook_signature = get_header(headers, "X-Discord-Signature")
        if not webhook_signature:
            logger.warning("Missing Discord webhook signature header")
            return False

        return validate_hmac_signature(webhook_signature, body, webhook_secret)

    async def _validate_interaction_signature(
        self,
        signature: str,
        timestamp: str,
        body: bytes,
    ) -> bool:
        """Validate Discord interaction signature using ED25519.

        Args:
            signature: The X-Signature-Ed25519 header value.
            timestamp: The X-Signature-Timestamp header value.
            body: Raw request body.

        Returns:
            True if valid.
        """
        application_id = self.config.extra.get("application_id")
        if not application_id:
            logger.warning("No application_id configured for Discord signature validation")
            return False

        # Get public key from Discord or use configured one
        public_key = self.config.extra.get("public_key")
        if not public_key:
            # Fetch public key from Discord API
            public_key = await self._fetch_application_public_key(application_id)

        if not public_key:
            return False

        return await validate_ed25519_signature(signature, timestamp, body, public_key)

    async def _fetch_application_public_key(self, application_id: str) -> str | None:
        """Fetch the public key for the Discord application.

        Args:
            application_id: Discord Application ID.

        Returns:
            Public key hex string or None.
        """
        logger.warning(
            "Discord public key auto-fetch is not implemented; configure "
            "DISCORD_PUBLIC_KEY (provider extra.public_key)"
        )
        try:
            self._get_http_client()
            # This would call Discord API to get application info
            # For now, return None - should be configured directly
            return None
        except Exception as exc:
            logger.error(f"Failed to fetch Discord application public key: {exc}")
            return None

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound Discord interaction as a "call".

        Discord doesn't have traditional calls, but voice channel joins
        and interactions can be treated as call-like events.

        Args:
            headers: HTTP headers.
            body: Raw request body (JSON for Discord).
            form_data: Parsed data (may be empty for Discord).

        Returns:
            PhoneCall object representing the Discord interaction.
        """
        return parse_inbound_interaction(
            body=body,
            guild_id=self.guild_id,
            default_channel_id=self.default_voice_channel_id,
        )

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate a Discord interaction response.

        Unlike TwiML, Discord uses JSON interaction responses.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message.
            gather_speech: Whether to wait for speech input.
            action_url: URL for follow-up (unused for Discord).

        Returns:
            JSON string for Discord interaction response.
        """
        return generate_interaction_response(
            content=welcome_message or "Hello! How can I help you today?",
        )

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Initiate a Discord voice channel connection.

        For Discord, "outbound call" means joining a voice channel.

        Args:
            to_number: Voice channel ID to join (format: discord:channel/{id}).
            from_number: Bot identifier (unused).
            webhook_url: Webhook for events.
            metadata: Additional metadata.

        Returns:
            PhoneCall object representing the voice connection.
        """
        # Parse channel ID from to_number
        channel_id = parse_channel_id(to_number)
        if not channel_id:
            channel_id = self.default_voice_channel_id

        if not channel_id:
            raise ValueError("No voice channel ID provided and no default configured")

        # Create voice connection
        guild_id = metadata.get("guild_id", self.guild_id) if metadata else self.guild_id

        call_id = f"discord_voice_{channel_id}_{int(time.time())}"

        # Create PhoneCall object
        call = PhoneCall(
            call_id=call_id,
            from_number="discord:bot",
            to_number=f"discord:channel/{channel_id}",
            direction=CallDirection.OUTBOUND,
            status=CallStatus.RINGING,
            provider="discord",
            started_at=datetime.now(tz=UTC),
            metadata={
                "channel_id": channel_id,
                "guild_id": guild_id,
                **(metadata or {}),
            },
        )

        # Store voice connection
        self._voice_connections[call_id] = DiscordVoiceConnection(
            guild_id=guild_id or "",
            channel_id=channel_id,
            call_id=call_id,
        )

        return call

    async def hangup_call(self, call_id: str) -> bool:
        """Disconnect from a Discord voice channel.

        Args:
            call_id: The voice connection call ID.

        Returns:
            True if disconnected successfully.
        """
        try:
            connection = self._voice_connections.get(call_id)
            if connection:
                await connection.disconnect()
                del self._voice_connections[call_id]
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to disconnect Discord voice {call_id}: {exc}")
            return False

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio in a Discord voice channel.

        Args:
            call_id: The voice connection call ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            True if audio started playing.
        """
        try:
            connection = self._voice_connections.get(call_id)
            if connection:
                await connection.play(audio_url, loop=loop)
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to play audio in Discord voice {call_id}: {exc}")
            return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits (not applicable for Discord).

        Discord doesn't support DTMF. This method logs a warning.

        Args:
            call_id: The voice connection call ID.
            digits: DTMF digits to send.

        Returns:
            False (not supported).
        """
        logger.warning("DTMF is not supported for Discord voice connections")
        return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a Discord voice connection.

        Args:
            call_id: The voice connection call ID.

        Returns:
            PhoneCall object or None.
        """
        connection = self._voice_connections.get(call_id)
        if not connection:
            return None

        status = DISCORD_STATUS_MAP.get(connection.state, CallStatus.RINGING)

        return PhoneCall(
            call_id=call_id,
            from_number="discord:bot",
            to_number=f"discord:channel/{connection.channel_id}",
            direction=CallDirection.OUTBOUND,
            status=status,
            provider="discord",
            started_at=connection.connected_at,
            metadata={
                "guild_id": connection.guild_id,
                "channel_id": connection.channel_id,
                "state": connection.state,
            },
        )

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a Discord voice channel.

        Args:
            call_id: The voice connection call ID.
            audio_stream: Async iterator of audio chunks (Opus encoded).

        Returns:
            True if streaming started successfully.
        """
        try:
            connection = self._voice_connections.get(call_id)
            if connection:
                await connection.stream(audio_stream)
                return True
            return False
        except Exception as exc:
            logger.error(f"Failed to stream audio in Discord voice {call_id}: {exc}")
            return False

    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event.

        Returns:
            The webhook path.
        """
        paths = {
            "interaction": "/telephony/discord/interaction",
            "voice": "/telephony/discord/voice",
            "event": "/telephony/discord/event",
        }
        return paths.get(event_type, f"/telephony/discord/{event_type}")

    async def send_message(
        self,
        channel_id: str,
        content: str,
        embed: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        """Send a text message to a Discord channel.

        This is a Discord-specific method for text interactions.

        Args:
            channel_id: Discord channel ID.
            content: Message content.
            embed: Optional embed object.

        Returns:
            Message data or None on failure.
        """
        try:
            _client = self._get_http_client()
            # Use discord.py HTTP client to send message
            # This is a simplified implementation
            payload: dict[str, Any] = {"content": content}
            if embed:
                payload["embeds"] = [embed]

            # Note: Actual implementation would use discord.py's HTTP client
            logger.info(f"Would send Discord message to channel {channel_id}: {content[:50]}...")
            return {"id": "mock_message_id", "content": content}
        except Exception as exc:
            logger.error(f"Failed to send Discord message: {exc}")
            return None

    async def get_guild_voice_channels(self, guild_id: str) -> list[dict[str, Any]]:
        """Get list of voice channels in a guild.

        Args:
            guild_id: Discord Guild ID.

        Returns:
            List of voice channel data.
        """
        try:
            _client = self._get_http_client()
            # Fetch guild channels via API
            # Simplified implementation
            return []
        except Exception as exc:
            logger.error(f"Failed to get guild voice channels: {exc}")
            return []
