"""CircleLoop UK telephony provider configuration.

This module provides configuration management for the CircleLoop UK
telephony provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class CircleLoopConfig:
    """Configuration for CircleLoop UK provider."""

    api_key: str | None = None
    """CircleLoop API Key."""

    api_secret: str | None = None
    """CircleLoop API Secret."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    default_from_number: str | None = None
    """Default phone number for outbound calls."""

    webhook_secret: str | None = None
    """Secret for webhook signature validation."""

    @classmethod
    def from_env(cls) -> CircleLoopConfig:
        """Load configuration from environment variables.

        Returns:
            CircleLoopConfig instance populated from environment variables.
        """
        return cls(
            api_key=os.getenv("CIRCLELOOP_API_KEY"),
            api_secret=os.getenv("CIRCLELOOP_API_SECRET"),
            webhook_base_url=os.getenv("CIRCLELOOP_WEBHOOK_BASE_URL"),
            default_from_number=os.getenv("CIRCLELOOP_DEFAULT_FROM_NUMBER"),
            webhook_secret=os.getenv("CIRCLELOOP_WEBHOOK_SECRET"),
        )

    def is_configured(self) -> bool:
        """Check if CircleLoop is properly configured.

        Returns:
            True if both api_key and api_secret are set.
        """
        return all([self.api_key, self.api_secret])
