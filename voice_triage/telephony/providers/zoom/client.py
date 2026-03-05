"""Zoom Phone API client wrapper.

This module provides the ZoomClient class for interacting with Zoom Phone APIs.
"""

from __future__ import annotations

import base64
import logging
import time
from typing import Any

logger = logging.getLogger(__name__)

# Zoom API base URL
ZOOM_API_URL = "https://api.zoom.us/v2"
ZOOM_OAUTH_URL = "https://zoom.us/oauth/token"


class ZoomClient:
    """Zoom Phone API client with OAuth authentication.

    This client handles Server-to-Server OAuth authentication and
    provides methods for making authenticated API calls to Zoom Phone.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        account_id: str,
    ) -> None:
        """Initialize the Zoom client.

        Args:
            client_id: Zoom Server-to-Server OAuth Client ID.
            client_secret: Zoom Server-to-Server OAuth Client Secret.
            account_id: Zoom Account ID.
        """
        self._client_id = client_id
        self._client_secret = client_secret
        self._account_id = account_id
        self._access_token: str | None = None
        self._token_expires_at: float = 0

    def _get_basic_auth(self) -> str:
        """Get Basic Auth header value.

        Returns:
            Base64 encoded client_id:client_secret.
        """
        credentials = f"{self._client_id}:{self._client_secret}"
        return base64.b64encode(credentials.encode()).decode()

    async def _get_access_token(self) -> str:
        """Get a valid Zoom Server-to-Server OAuth access token.

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
                response = await client.post(
                    ZOOM_OAUTH_URL,
                    params={
                        "grant_type": "account_credentials",
                        "account_id": self._account_id,
                    },
                    headers={
                        "Authorization": f"Basic {self._get_basic_auth()}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                )
                response.raise_for_status()
                data = response.json()
                self._access_token = data["access_token"]
                self._token_expires_at = time.time() + data.get("expires_in", 3600)
                return self._access_token

        except Exception as exc:
            logger.error(f"Failed to get Zoom access token: {exc}")
            raise RuntimeError(f"Zoom authentication failed: {exc}") from exc

    async def make_call(
        self,
        to_number: str,
        from_number: str,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        """Initiate an outbound call via Zoom Phone API.

        Args:
            to_number: Destination phone number in E.164 format.
            from_number: Source phone number.
            webhook_url: Optional webhook URL for call status updates.

        Returns:
            API response data.

        Raises:
            RuntimeError: If the API call fails.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                request_body: dict[str, Any] = {
                    "to": to_number,
                    "from": from_number,
                }

                if webhook_url:
                    request_body["webhook"] = webhook_url

                response = await client.post(
                    f"{ZOOM_API_URL}/phone/call",
                    json=request_body,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response.json()

        except Exception as exc:
            logger.error(f"Failed to make outbound call via Zoom: {exc}")
            raise RuntimeError(f"Zoom outbound call failed: {exc}") from exc

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active Zoom Phone call.

        Args:
            call_id: The Zoom Phone call ID.

        Returns:
            True if the call was hung up successfully.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{ZOOM_API_URL}/phone/call/{call_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )
                return response.status_code in (200, 204, 404)
        except Exception as exc:
            logger.error(f"Failed to hang up Zoom call: {exc}")
            return False

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a Zoom Phone call.

        Args:
            call_id: The Zoom Phone call ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            True if audio started playing successfully.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{ZOOM_API_URL}/phone/call/{call_id}/play",
                    json={
                        "audio_url": audio_url,
                        "loop": loop,
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                return response.status_code == 200
        except Exception as exc:
            logger.error(f"Failed to play audio via Zoom: {exc}")
            return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a Zoom Phone call.

        Args:
            call_id: The Zoom Phone call ID.
            digits: DTMF digits to send.

        Returns:
            True if digits were sent successfully.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{ZOOM_API_URL}/phone/call/{call_id}/dtmf",
                    json={
                        "digits": digits,
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                return response.status_code == 200
        except Exception as exc:
            logger.error(f"Failed to send digits via Zoom: {exc}")
            return False

    async def get_call(self, call_id: str) -> dict[str, Any] | None:
        """Get call details from Zoom Phone API.

        Args:
            call_id: The Zoom Phone call ID.

        Returns:
            Call data dictionary or None if not found.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{ZOOM_API_URL}/phone/call/{call_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error(f"Failed to get Zoom call status: {exc}")
            return None
