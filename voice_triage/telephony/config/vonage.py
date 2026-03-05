"""Vonage/Nexmo telephony provider configuration.

This module provides configuration management for the Vonage (formerly Nexmo)
telephony provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class VonageConfig:
    """Configuration for Vonage/Nexmo provider."""

    api_key: str | None = None
    """Vonage API Key."""

    api_secret: str | None = None
    """Vonage API Secret."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    default_from_number: str | None = None
    """Default phone number for outbound calls."""

    application_id: str | None = None
    """Vonage Application ID."""

    private_key_path: str | None = None
    """Path to private key for JWT authentication."""

    webhook_secret: str | None = None
    """Shared secret for validating inbound webhook bearer tokens."""

    @classmethod
    def from_env(cls) -> VonageConfig:
        """Load configuration from environment variables.

        Returns:
            VonageConfig instance populated from environment variables.
        """
        return cls(
            api_key=os.getenv("VONAGE_API_KEY"),
            api_secret=os.getenv("VONAGE_API_SECRET"),
            webhook_base_url=os.getenv("VONAGE_WEBHOOK_BASE_URL"),
            default_from_number=os.getenv("VONAGE_DEFAULT_FROM_NUMBER"),
            application_id=os.getenv("VONAGE_APPLICATION_ID"),
            private_key_path=os.getenv("VONAGE_PRIVATE_KEY_PATH"),
            webhook_secret=os.getenv("VONAGE_WEBHOOK_SECRET"),
        )

    def is_configured(self) -> bool:
        """Check if Vonage is properly configured.

        Returns:
            True if both api_key and api_secret are set.
        """
        return all([self.api_key, self.api_secret])
