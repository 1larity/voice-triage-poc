"""Discord telephony provider configuration.

This module provides configuration management for the Discord telephony
provider. Discord is used by councils with community Discord presence
for voice and text interactions.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class DiscordConfig:
    """Configuration for Discord provider.

    Discord is used by councils with community Discord presence
    for voice and text interactions.
    """

    bot_token: str | None = None
    """Discord Bot Token for authentication."""

    application_id: str | None = None
    """Discord Application ID for interaction verification."""

    public_key: str | None = None
    """Public key for Ed25519 signature verification."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    webhook_secret: str | None = None
    """Secret for webhook signature validation."""

    guild_id: str | None = None
    """Default Discord Guild (Server) ID."""

    voice_channel_id: str | None = None
    """Default voice channel ID."""

    text_channel_id: str | None = None
    """Default text channel ID for interactions."""

    @classmethod
    def from_env(cls) -> DiscordConfig:
        """Load configuration from environment variables.

        Returns:
            DiscordConfig instance populated from environment variables.
        """
        return cls(
            bot_token=os.getenv("DISCORD_BOT_TOKEN"),
            application_id=os.getenv("DISCORD_APPLICATION_ID"),
            public_key=os.getenv("DISCORD_PUBLIC_KEY"),
            webhook_base_url=os.getenv("DISCORD_WEBHOOK_BASE_URL"),
            webhook_secret=os.getenv("DISCORD_WEBHOOK_SECRET"),
            guild_id=os.getenv("DISCORD_GUILD_ID"),
            voice_channel_id=os.getenv("DISCORD_VOICE_CHANNEL_ID"),
            text_channel_id=os.getenv("DISCORD_TEXT_CHANNEL_ID"),
        )

    def is_configured(self) -> bool:
        """Check if Discord is properly configured.

        Returns:
            True if bot_token is set.
        """
        return self.bot_token is not None
