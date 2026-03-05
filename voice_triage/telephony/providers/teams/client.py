"""Microsoft Teams Graph API client.

This module provides a client wrapper for Microsoft Graph API
with authentication handling for Teams Direct Routing.
"""

from __future__ import annotations

import logging
import time

logger = logging.getLogger(__name__)

# Microsoft Graph API base URL
GRAPH_API_URL = "https://graph.microsoft.com/v1.0"


class TeamsGraphClient:
    """Microsoft Graph API client for Teams Direct Routing.

    This client handles authentication and API calls to Microsoft Graph
    for Teams telephony operations.
    """

    def __init__(
        self,
        tenant_id: str,
        client_id: str,
        client_secret: str,
    ) -> None:
        """Initialize the Teams Graph client.

        Args:
            tenant_id: Azure Tenant ID.
            client_id: Azure AD Application ID.
            client_secret: Azure AD Client Secret.
        """
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def get_access_token(self) -> str:
        """Get a valid Microsoft Graph access token.

        Returns:
            Valid OAuth access token.

        Raises:
            RuntimeError: If authentication fails.
        """
        # Check if we have a valid token
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token

        try:
            import httpx

            # Azure AD token endpoint
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "scope": "https://graph.microsoft.com/.default",
                        "grant_type": "client_credentials",
                    },
                    headers={
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                response.raise_for_status()
                data = response.json()
                self._access_token = data["access_token"]
                self._token_expires_at = time.time() + data.get("expires_in", 3600)
                return self._access_token

        except Exception as exc:
            logger.error(f"Failed to get Microsoft Graph access token: {exc}")
            raise RuntimeError(f"Microsoft Graph authentication failed: {exc}") from exc
