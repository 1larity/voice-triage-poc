"""Zoom Phone telephony provider configuration.

This module provides configuration management for the Zoom Phone
telephony provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class ZoomConfig:
    """Configuration for Zoom Phone provider."""

    account_id: str | None = None
    """Zoom Account ID for Server-to-Server OAuth."""

    client_id: str | None = None
    """Zoom OAuth Client ID."""

    client_secret: str | None = None
    """Zoom OAuth Client Secret."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    default_from_number: str | None = None
    """Default phone number for outbound calls."""

    webhook_secret: str | None = None
    """Secret for webhook signature validation."""

    @classmethod
    def from_env(cls) -> ZoomConfig:
        """Load configuration from environment variables.

        Returns:
            ZoomConfig instance populated from environment variables.
        """
        return cls(
            account_id=os.getenv("ZOOM_ACCOUNT_ID"),
            client_id=os.getenv("ZOOM_CLIENT_ID"),
            client_secret=os.getenv("ZOOM_CLIENT_SECRET"),
            webhook_base_url=os.getenv("ZOOM_WEBHOOK_BASE_URL"),
            default_from_number=os.getenv("ZOOM_DEFAULT_FROM_NUMBER"),
            webhook_secret=os.getenv("ZOOM_WEBHOOK_SECRET"),
        )

    def is_configured(self) -> bool:
        """Check if Zoom Phone is properly configured.

        Returns:
            True if account_id, client_id, and client_secret are set.
        """
        return all([self.account_id, self.client_id, self.client_secret])
