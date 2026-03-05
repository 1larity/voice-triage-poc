"""Vonage client wrapper for API interactions.

This module provides a wrapper around the Vonage SDK for
Voice API operations.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class VonageClient:
    """Wrapper for Vonage Voice API client.

    This class provides a lazy-loaded wrapper around the Vonage SDK,
    handling client initialization and providing access to voice operations.
    """

    def __init__(self, api_key: str, api_secret: str) -> None:
        """Initialize the Vonage client wrapper.

        Args:
            api_key: Vonage API key.
            api_secret: Vonage API secret.
        """
        self._api_key = api_key
        self._api_secret = api_secret
        self._client: Any = None
        self._voice_client: Any = None

    def _ensure_client(self) -> None:
        """Ensure the Vonage client is initialized.

        Raises:
            RuntimeError: If the vonage package is not installed.
        """
        if self._client is None:
            try:
                import vonage

                self._client = vonage.Client(
                    key=self._api_key,
                    secret=self._api_secret,
                )
                self._voice_client = vonage.Voice(self._client)
            except ImportError as exc:
                raise RuntimeError(
                    "vonage package is required for Vonage integration. "
                    "Install it with: pip install vonage"
                ) from exc

    @property
    def voice(self) -> Any:
        """Get the Vonage Voice client.

        Returns:
            Vonage Voice client instance.
        """
        self._ensure_client()
        return self._voice_client

    def create_call(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create a new outbound call.

        Args:
            params: Call parameters including to, from, and NCCO.

        Returns:
            Response containing call UUID and details.
        """
        return self.voice.create_call(params)

    def hangup(self, call_id: str) -> bool:
        """Hang up an active call.

        Args:
            call_id: Vonage call UUID.

        Returns:
            True if successful.
        """
        self.voice.hangup(call_id)
        return True

    def send_dtmf(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a call.

        Args:
            call_id: Vonage call UUID.
            digits: DTMF digits to send.

        Returns:
            True if successful.
        """
        self.voice.send_dtmf(call_id, digits)
        return True

    def get_call(self, call_id: str) -> dict[str, Any]:
        """Get details of a specific call.

        Args:
            call_id: Vonage call UUID.

        Returns:
            Call details dictionary.
        """
        return self.voice.get_call(call_id)

    def update_call(
        self,
        call_id: str,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Update an active call.

        Args:
            call_id: Vonage call UUID.
            params: Update parameters (e.g., transfer action).

        Returns:
            Response from the update operation.
        """
        return self.voice.update_call(call_id, params)
