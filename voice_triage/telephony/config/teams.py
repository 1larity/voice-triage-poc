"""Microsoft Teams Direct Routing telephony provider configuration.

This module provides configuration management for Microsoft Teams
Direct Routing telephony provider.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class TeamsConfig:
    """Configuration for Microsoft Teams Direct Routing provider."""

    tenant_id: str | None = None
    """Azure AD Tenant ID."""

    client_id: str | None = None
    """Azure AD Application Client ID."""

    client_secret: str | None = None
    """Azure AD Application Client Secret."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    default_from_number: str | None = None
    """Default phone number for outbound calls."""

    sip_domain: str | None = None
    """SIP domain for Direct Routing."""

    sbc_fqdn: str | None = None
    """Session Border Controller FQDN."""

    webhook_secret: str | None = None
    """Secret for webhook validation."""

    @classmethod
    def from_env(cls) -> TeamsConfig:
        """Load configuration from environment variables.

        Returns:
            TeamsConfig instance populated from environment variables.
        """
        return cls(
            tenant_id=os.getenv("TEAMS_TENANT_ID"),
            client_id=os.getenv("TEAMS_CLIENT_ID"),
            client_secret=os.getenv("TEAMS_CLIENT_SECRET"),
            webhook_base_url=os.getenv("TEAMS_WEBHOOK_BASE_URL"),
            default_from_number=os.getenv("TEAMS_DEFAULT_FROM_NUMBER"),
            sip_domain=os.getenv("TEAMS_SIP_DOMAIN"),
            sbc_fqdn=os.getenv("TEAMS_SBC_FQDN"),
            webhook_secret=os.getenv("TEAMS_WEBHOOK_SECRET"),
        )

    def is_configured(self) -> bool:
        """Check if Teams Direct Routing is properly configured.

        Returns:
            True if tenant_id, client_id, and client_secret are set.
        """
        return all([self.tenant_id, self.client_id, self.client_secret])
