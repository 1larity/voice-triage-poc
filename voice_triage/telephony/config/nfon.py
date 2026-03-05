"""NFON cloud PBX telephony provider configuration.

This module provides configuration management for the NFON cloud PBX
telephony provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from voice_triage.telephony.config.base import _env_bool


@dataclass
class NFONConfig:
    """Configuration for NFON cloud PBX provider."""

    client_id: str | None = None
    """NFON OAuth Client ID."""

    client_secret: str | None = None
    """NFON OAuth Client Secret."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    default_from_number: str | None = None
    """Default phone number for outbound calls."""

    account_id: str | None = None
    """NFON account identifier."""

    webhook_secret: str | None = None
    """Secret for webhook signature validation."""

    use_uk_endpoint: bool = True
    """Whether to use UK API endpoints."""

    @classmethod
    def from_env(cls) -> NFONConfig:
        """Load configuration from environment variables.

        Returns:
            NFONConfig instance populated from environment variables.
        """
        return cls(
            client_id=os.getenv("NFON_CLIENT_ID"),
            client_secret=os.getenv("NFON_CLIENT_SECRET"),
            webhook_base_url=os.getenv("NFON_WEBHOOK_BASE_URL"),
            default_from_number=os.getenv("NFON_DEFAULT_FROM_NUMBER"),
            account_id=os.getenv("NFON_ACCOUNT_ID"),
            webhook_secret=os.getenv("NFON_WEBHOOK_SECRET"),
            use_uk_endpoint=_env_bool("NFON_USE_UK_ENDPOINT", default=True),
        )

    def is_configured(self) -> bool:
        """Check if NFON is properly configured.

        Returns:
            True if both client_id and client_secret are set.
        """
        return all([self.client_id, self.client_secret])
