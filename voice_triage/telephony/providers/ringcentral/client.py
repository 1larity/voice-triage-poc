"""RingCentral API client wrapper.

This module provides a client for interacting with the RingCentral API.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# RingCentral API base URLs
RINGCENTRAL_API_URL = "https://platform.ringcentral.com"
RINGCENTRAL_UK_API_URL = "https://platform.ringcentral.co.uk"


class RingCentralClient:
    """RingCentral API client wrapper.

    This client handles authentication and HTTP communication with
    the RingCentral API.

    Attributes:
        client_id: RingCentral OAuth client ID.
        client_secret: RingCentral OAuth client secret.
        account_id: RingCentral account ID.
        api_url: RingCentral API base URL.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        account_id: str,
        api_url: str | None = None,
    ) -> None:
        """Initialize the RingCentral client.

        Args:
            client_id: RingCentral OAuth client ID.
            client_secret: RingCentral OAuth client secret.
            account_id: RingCentral account ID.
            api_url: Optional custom API URL (defaults to UK endpoint).
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.account_id = account_id
        self.api_url = api_url or RINGCENTRAL_UK_API_URL
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def get_access_token(self) -> str:
        """Get a valid RingCentral access token.

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

            async with httpx.AsyncClient() as client:
                # RingCentral uses OAuth 2.0 Server-to-Server
                credentials = f"{self.client_id}:{self.client_secret}"
                encoded = base64.b64encode(credentials.encode()).decode()

                response = await client.post(
                    f"{self.api_url}/restapi/oauth/token",
                    headers={
                        "Authorization": f"Basic {encoded}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={
                        "grant_type": "client_credentials",
                        "account_id": self.account_id,
                    },
                )
                response.raise_for_status()
                data = response.json()

                self._access_token = data["access_token"]
                self._token_expires_at = time.time() + data.get("expires_in", 3600)
                return self._access_token

        except Exception as exc:
            logger.error(f"Failed to get RingCentral access token: {exc}")
            raise RuntimeError(f"RingCentral authentication failed: {exc}") from exc

    async def make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to the RingCentral API.

        Args:
            method: HTTP method (GET, POST, etc.).
            endpoint: API endpoint (without base URL).
            **kwargs: Additional arguments to pass to httpx.

        Returns:
            JSON response data.

        Raises:
            RuntimeError: If the request fails.
        """
        token = await self.get_access_token()

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    f"{self.api_url}{endpoint}",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                    },
                    **kwargs,
                )
                response.raise_for_status()
                return response.json()

        except Exception as exc:
            logger.error(f"RingCentral API request failed: {exc}")
            raise RuntimeError(f"RingCentral API error: {exc}") from exc

    async def create_call(
        self,
        to_number: str,
        from_number: str,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        """Create an outbound call.

        Args:
            to_number: Destination phone number.
            from_number: Source phone number.
            webhook_url: Optional webhook URL for call events.

        Returns:
            Call data from the API.
        """
        data: dict[str, Any] = {
            "to": [{"phoneNumber": to_number}],
            "from": {"phoneNumber": from_number},
        }

        if webhook_url:
            data["webhook"] = webhook_url

        path = "/restapi/v1.0/account/~/extension/~/ring-out"
        return await self.make_request("POST", path, json=data)

    async def get_call(self, call_id: str) -> dict[str, Any]:
        """Get call details.

        Args:
            call_id: RingCentral call session ID.

        Returns:
            Call data from the API.
        """
        path = f"/restapi/v1.0/account/~/extension/~/call-log/{call_id}"
        return await self.make_request("GET", path)

    async def hangup_call(self, call_id: str) -> dict[str, Any]:
        """Hang up a call.

        Args:
            call_id: RingCentral call session ID.

        Returns:
            Response data from the API.
        """
        path = f"/restapi/v1.0/account/~/extension/~/ring-out/{call_id}"
        return await self.make_request("DELETE", path)

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> dict[str, Any]:
        """Play audio into a call.

        Args:
            call_id: RingCentral call session ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            Response data from the API.
        """
        return await self.make_request(
            "POST",
            f"/restapi/v1.0/account/~/telephony/sessions/{call_id}/parties/~/play",
            json={"resources": [{"uri": audio_url}], "loop": loop},
        )

    async def send_digits(self, call_id: str, digits: str) -> dict[str, Any]:
        """Send DTMF digits into a call.

        Args:
            call_id: RingCentral call session ID.
            digits: DTMF digits to send.

        Returns:
            Response data from the API.
        """
        return await self.make_request(
            "POST",
            f"/restapi/v1.0/account/~/telephony/sessions/{call_id}/parties/~/dtmf",
            json={"dtmf": digits},
        )
