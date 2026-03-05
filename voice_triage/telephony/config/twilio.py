"""Twilio telephony provider configuration.

This module provides configuration management for the Twilio telephony provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class TwilioConfig:
    """Configuration for Twilio provider."""

    account_sid: str | None = None
    """Twilio Account SID."""

    auth_token: str | None = None
    """Twilio Auth Token."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    default_from_number: str | None = None
    """Default phone number for outbound calls."""

    @classmethod
    def from_env(cls) -> TwilioConfig:
        """Load configuration from environment variables.

        Returns:
            TwilioConfig instance populated from environment variables.
        """
        return cls(
            account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
            auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
            webhook_base_url=os.getenv("TWILIO_WEBHOOK_BASE_URL"),
            default_from_number=os.getenv("TWILIO_DEFAULT_FROM_NUMBER"),
        )

    def is_configured(self) -> bool:
        """Check if Twilio is properly configured.

        Returns:
            True if both account_sid and auth_token are set.
        """
        return all([self.account_sid, self.auth_token])
