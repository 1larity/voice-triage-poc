"""RingCentral telephony provider configuration.

This module provides configuration management for the RingCentral UK
telephony provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from voice_triage.telephony.config.base import _env_bool


@dataclass
class RingCentralConfig:
    """Configuration for RingCentral UK provider."""

    client_id: str | None = None
    """RingCentral OAuth Client ID."""

    client_secret: str | None = None
    """RingCentral OAuth Client Secret."""

    jwt_token: str | None = None
    """JWT token for authentication (alternative to password flow)."""

    username: str | None = None
    """Phone number or extension for password flow authentication."""

    extension: str | None = None
    """Optional extension number."""

    password: str | None = None
    """Password for password flow authentication."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    default_from_number: str | None = None
    """Default phone number for outbound calls."""

    account_id: str | None = None
    """RingCentral account identifier."""

    webhook_secret: str | None = None
    """Secret for webhook signature validation."""

    use_uk_endpoint: bool = True
    """Whether to use UK/EU API endpoints."""

    @classmethod
    def from_env(cls) -> RingCentralConfig:
        """Load configuration from environment variables.

        Returns:
            RingCentralConfig instance populated from environment variables.
        """
        return cls(
            client_id=os.getenv("RINGCENTRAL_CLIENT_ID"),
            client_secret=os.getenv("RINGCENTRAL_CLIENT_SECRET"),
            jwt_token=os.getenv("RINGCENTRAL_JWT_TOKEN"),
            username=os.getenv("RINGCENTRAL_USERNAME"),
            extension=os.getenv("RINGCENTRAL_EXTENSION"),
            password=os.getenv("RINGCENTRAL_PASSWORD"),
            account_id=os.getenv("RINGCENTRAL_ACCOUNT_ID"),
            webhook_base_url=os.getenv("RINGCENTRAL_WEBHOOK_BASE_URL"),
            default_from_number=os.getenv("RINGCENTRAL_DEFAULT_FROM_NUMBER"),
            webhook_secret=os.getenv("RINGCENTRAL_WEBHOOK_SECRET"),
            use_uk_endpoint=_env_bool("RINGCENTRAL_USE_UK_ENDPOINT", default=True),
        )

    def is_configured(self) -> bool:
        """Check if RingCentral is properly configured.

        Returns:
            True if OAuth credentials are present along with either JWT or password.
        """
        has_oauth = all([self.client_id, self.client_secret])
        has_jwt = bool(has_oauth and self.jwt_token)
        has_password = bool(has_oauth and all([self.username, self.password]))
        return has_jwt or has_password
