"""NFON telephony provider implementation.

This module provides the main NFON provider class implementing TelephonyProvider.
"""

from __future__ import annotations

import logging

from voice_triage.telephony.base import (
    TelephonyConfig,
    TelephonyProvider,
)
from voice_triage.telephony.providers.nfon.client import (
    NFON_API_URL,
    NFON_UK_API_URL,
    NFONClient,
)
from voice_triage.telephony.registry import register_provider

logger = logging.getLogger(__name__)


@register_provider("nfon")
class NFONProvider(TelephonyProvider):
    """NFON telephony provider implementation.

    This provider integrates with NFON's Cloud PBX API for
    handling inbound and outbound calls in the UK.

    NFON uses OAuth 2.0 for authentication with API key/secret
    for server-to-server integrations.
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the NFON provider.

        Args:
            config: Configuration containing:
                - api_key: NFON API Key
                - api_secret: NFON API Secret
                - account_sid: NFON Tenant ID
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default NFON phone number
                - extra:
                    - tenant_id: NFON Tenant ID (alternative to account_sid)
                    - extension_id: Extension ID for outbound calls
                    - webhook_secret: Secret for webhook validation
                    - use_uk_endpoint: Use UK-specific API endpoint
        """
        super().__init__( config)
        self._client = NFONClient(config)
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "nfon"

    @property
    def tenant_id(self) -> str:
        """Get the NFON Tenant ID."""
        return self.config.account_sid or self.config.extra.get("tenant_id", "")

    @property
    def api_url(self) -> str:
        """Get the NFON API URL based on configuration."""
        use_uk_endpoint = self.config.extra.get("use_uk_endpoint", True)
        return NFON_UK_API_URL if use_uk_endpoint else NFON_API_URL

    async def _get_access_token(self) -> str:
        """Get a valid NFON access token.

        Returns:
            Valid OAuth access token.

        Raises:
            RuntimeError: If authentication fails.
        """
        return await self._client.get_access_token()

