"""Avaya telephony provider configuration.

This module provides configuration management for the Avaya telephony
provider. Avaya is a major enterprise telephony provider in the UK,
commonly used by councils and large organizations.

Products include:
- Avaya Aura Communication Manager
- Avaya IP Office
- Avaya Application Enablement Services (AES)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class AvayaConfig:
    """Configuration for Avaya provider.

    Avaya is a major enterprise telephony provider in the UK, commonly used
    by councils and large organizations. Products include:
    - Avaya Aura Communication Manager
    - Avaya IP Office
    - Avaya Application Enablement Services (AES)
    """

    server_host: str | None = None
    """Avaya AES or Communication Manager host."""

    server_port: int = 8443
    """Port for Avaya Web Services (default: 8443)."""

    username: str | None = None
    """Avaya username for authentication."""

    password: str | None = None
    """Avaya password for authentication."""

    extension: str | None = None
    """Default extension for outbound calls."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    webhook_secret: str | None = None
    """Secret for webhook signature validation."""

    use_ssl: bool = True
    """Whether to use HTTPS (default: True)."""

    default_from_number: str | None = None
    """Default caller ID for outbound calls."""

    aes_enabled: bool = False
    """Use AES (Application Enablement Services) for advanced features."""

    ip_office_mode: bool = False
    """Use IP Office specific API endpoints."""

    @classmethod
    def from_env(cls) -> AvayaConfig:
        """Load configuration from environment variables.

        Returns:
            AvayaConfig instance populated from environment variables.
        """
        port_str = os.getenv("AVAYA_SERVER_PORT", "8443")
        try:
            port = int(port_str)
        except ValueError:
            port = 8443

        return cls(
            server_host=os.getenv("AVAYA_SERVER_HOST"),
            server_port=port,
            username=os.getenv("AVAYA_USERNAME"),
            password=os.getenv("AVAYA_PASSWORD"),
            extension=os.getenv("AVAYA_EXTENSION"),
            webhook_base_url=os.getenv("AVAYA_WEBHOOK_BASE_URL"),
            webhook_secret=os.getenv("AVAYA_WEBHOOK_SECRET"),
            use_ssl=os.getenv("AVAYA_USE_SSL", "true").lower() == "true",
            default_from_number=os.getenv("AVAYA_DEFAULT_FROM_NUMBER"),
            aes_enabled=os.getenv("AVAYA_AES_ENABLED", "false").lower() == "true",
            ip_office_mode=os.getenv("AVAYA_IP_OFFICE_MODE", "false").lower()
            == "true",
        )

    def is_configured(self) -> bool:
        """Check if Avaya is properly configured.

        Returns:
            True if server_host, username, and password are set.
        """
        return (
            self.server_host is not None
            and self.username is not None
            and self.password is not None
        )
