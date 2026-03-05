"""Avaya HTTP client wrapper for API interactions.

This module provides a wrapper around Avaya Web Services REST API
for session management and API calls.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

logger = logging.getLogger(__name__)


class AvayaClient:
    """Wrapper for Avaya Web Services REST API.

    This class handles authentication and session management, and
    HTTP requests to Avaya Communication Manager.
    """

    def __init__(
        self,
        server_host: str = "localhost",
        server_port: int = 8443,
        use_ssl: bool = True,
        username: str = "",
        password: str = "",
    ) -> None:
        """Initialize the Avaya client.

        Args:
            server_host: Avaya AES host.
            server_port: Avaya AES port.
            use_ssl: Whether to use HTTPS.
            username: AES username.
            password: AES password.
        """
        self._server_host = server_host
        self._server_port = server_port
        self._use_ssl = use_ssl
        self._username = username
        self._password = password
        self._session_token: str | None = None
        self._session_expires: datetime | None = None

    def _get_base_url(self) -> str:
        """Get the base URL for Avaya Web Services.

        Returns:
            Base URL string.
        """
        scheme = "https" if self._use_ssl else "http"
        return f"{scheme}://{self._server_host}:{self._server_port}"

    async def get_session_token(self) -> str:
        """Get or refresh the Avaya session token.

        Returns:
            Valid session token string.

        Raises:
            RuntimeError: If authentication fails.
        """
        now = datetime.now(UTC)

        # Check if we have a valid token
        if self._session_token and self._session_expires:
            if now < self._session_expires:
                return self._session_token

        # Authenticate to get new token
        import aiohttp

        base_url = self._get_base_url()
        auth_url = f"{base_url}/api/v1/authentication/sessions"

        credentials = {
            "username": self._username,
            "password": self._password,
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    auth_url,
                    json=credentials,
                    headers={"Content-Type": "application/json"},
                    ssl=False,  # May need to disable for self-signed certs
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        self._session_token = data.get("token") or data.get(
                            "sessionId"
                        )
                        # Token typically expires in 1 hour
                        self._session_expires = data.get("expires")
                        if isinstance(self._session_expires, str):
                            self._session_expires = datetime.fromisoformat(
                                self._session_expires.replace("Z", "+00:00")
                            )
                        else:
                            from datetime import timedelta

                            self._session_expires = now + timedelta(hours=1)
                        return self._session_token
                    else:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"Avaya authentication failed: {response.status} - "
                            f"{error_text}"
                        )
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Failed to connect to Avaya server: {e}") from e

    async def make_request(
        self,
        method: str,
        endpoint: str,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Make an authenticated request to Avaya Web Services.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE).
            endpoint: API endpoint path.
            data: Optional request body data.

        Returns:
            Response JSON data.

        Raises:
            RuntimeError: If request fails.
        """
        import aiohttp

        token = await self.get_session_token()
        base_url = self._get_base_url()
        url = urljoin(base_url, endpoint)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    url,
                    json=data,
                    headers=headers,
                    ssl=False,
                ) as response:
                    if response.status in (200, 201, 204):
                        if response.content_length and response.content_length > 0:
                            return await response.json()
                        return {}
                    else:
                        error_text = await response.text()
                        raise RuntimeError(
                            f"Avaya API request failed: {response.status} - "
                            f"{error_text}"
                        )
        except aiohttp.ClientError as e:
            raise RuntimeError(f"Avaya API request error: {e}") from e
