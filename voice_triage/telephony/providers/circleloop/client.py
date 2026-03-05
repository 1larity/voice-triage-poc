"""CircleLoop API client wrapper.

This module provides a client for interacting with the CircleLoop API.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# CircleLoop API base URLs
CIRCLELOOP_API_URL = "https://api.circleloop.com/v1"
CIRCLELOOP_UK_API_URL = "https://api.circleloop.co.uk/v1"


class CircleLoopClient:
    """CircleLoop API client wrapper.

    This client handles authentication and HTTP communication with
    the CircleLoop API.

    Attributes:
        api_key: CircleLoop API key.
        api_secret: CircleLoop API secret.
        api_url: CircleLoop API base URL.
    """

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        api_url: str | None = None,
    ) -> None:
        """Initialize the CircleLoop client.

        Args:
            api_key: CircleLoop API key.
            api_secret: CircleLoop API secret.
            api_url: Optional custom API URL (defaults to UK endpoint).
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_url = api_url or CIRCLELOOP_UK_API_URL
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    async def get_access_token(self) -> str:
        """Get a valid CircleLoop access token.

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
                # CircleLoop uses Basic Auth for token retrieval
                credentials = f"{self.api_key}:{self.api_secret}"
                encoded = base64.b64encode(credentials.encode()).decode()

                response = await client.post(
                    f"{self.api_url}/auth/token",
                    headers={
                        "Authorization": f"Basic {encoded}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    data={"grant_type": "client_credentials"},
                )
                response.raise_for_status()
                data = response.json()

                self._access_token = data["access_token"]
                self._token_expires_at = time.time() + data.get("expires_in", 3600)
                return self._access_token

        except Exception as exc:
            logger.error(f"Failed to get CircleLoop access token: {exc}")
            raise RuntimeError(f"CircleLoop authentication failed: {exc}") from exc

    async def make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        """Make an authenticated request to the CircleLoop API.

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
            logger.error(f"CircleLoop API request failed: {exc}")
            raise RuntimeError(f"CircleLoop API error: {exc}") from exc

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
            "to": to_number,
            "from": from_number,
        }

        if webhook_url:
            data["webhook_url"] = webhook_url

        return await self.make_request("POST", "/calls", json=data)

    async def get_call(self, call_id: str) -> dict[str, Any]:
        """Get call details.

        Args:
            call_id: CircleLoop call ID.

        Returns:
            Call data from the API.
        """
        return await self.make_request("GET", f"/calls/{call_id}")

    async def hangup_call(self, call_id: str) -> dict[str, Any]:
        """Hang up a call.

        Args:
            call_id: CircleLoop call ID.

        Returns:
            Response data from the API.
        """
        return await self.make_request("DELETE", f"/calls/{call_id}")

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> dict[str, Any]:
        """Play audio into a call.

        Args:
            call_id: CircleLoop call ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            Response data from the API.
        """
        return await self.make_request(
            "POST",
            f"/calls/{call_id}/play",
            json={"audio_url": audio_url, "loop": loop},
        )

    async def send_digits(self, call_id: str, digits: str) -> dict[str, Any]:
        """Send DTMF digits into a call.

        Args:
            call_id: CircleLoop call ID.
            digits: DTMF digits to send.

        Returns:
            Response data from the API.
        """
        return await self.make_request(
            "POST",
            f"/calls/{call_id}/dtmf",
            json={"digits": digits},
        )
