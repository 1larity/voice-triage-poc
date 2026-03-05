"""NFON API client wrapper.

This module provides a HTTP client wrapper for NFON's REST API.
"""

from __future__ import annotations

import logging
import time
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
    TelephonyConfig,
)

logger = logging.getLogger(__name__)

# NFON API base URLs
NFON_API_URL = "https://api.nfon.com/v1"
NFON_UK_API_URL = "https://api.nfon.co.uk/v1"


class NFONClient:
    """NFON API client wrapper.

    This class handles OAuth 2.0 authentication and API calls for NFON's Cloud PBX API.
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the NFON client.

        Args:
            config: TelephonyConfig instance.
        """
        self.config = config
        self._access_token: str | None = None
        self._token_expires_at: float = 0

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
        # Check if we have a valid token
        if self._access_token and time.time() < self._token_expires_at:
            return self._access_token
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                # NFON uses OAuth 2.0 client credentials flow
                response = await client.post(
                    f"{self.api_url}/oauth/token",
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.config.api_key,
                        "client_secret": self.config.api_secret,
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
            logger.error(f"Failed to get NFON access token: {exc}")
            raise RuntimeError(f"NFON authentication failed: {exc}") from exc

    async def _get_auth_headers(self, token: str) -> dict[str, str]:
        """Get authentication headers for NFON API.

        Args:
            token: Access token.

        Returns:
            Headers dictionary.
        """
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-API-Key": self.config.api_key or "",
        }

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Initiate an outbound call via NFON.

        Args:
            to_number: Destination phone number in E.164 format.
            from_number: Source phone number (uses default if not provided).
            webhook_url: URL for call status webhooks.
            metadata: Additional metadata to attach to the call.

        Returns:
            A PhoneCall object representing the initiated call.
        """
        from_number = from_number or self.config.default_from_number
        if not from_number:
            raise ValueError("No from_number provided and no default configured")

        access_token = await self._get_access_token()
        request_body = {
            "destination": to_number,
            "source": from_number,
            "tenantId": self.tenant_id,
        }
        if webhook_url:
            request_body["webhookUrl"] = webhook_url
            request_body["callbackUri"] = (
                f"{self.config.webhook_base_url}/telephony/nfon/callback"
            )

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/calls",
                    json=request_body,
                    headers=await self._get_auth_headers(access_token),
                )
                response.raise_for_status()
                data = response.json()
                call_id = data.get("callId") or data.get("id", "")

                return PhoneCall(
                    call_id=call_id,
                    from_number=from_number,
                    to_number=to_number,
                    direction=CallDirection.OUTBOUND,
                    status=CallStatus.RINGING,
                    provider="nfon",
                    metadata={
                        "tenant_id": self.tenant_id,
                        "original_response": data,
                    },
                )
        except Exception as exc:
            logger.error(f"Failed to make NFON outbound call: {exc}")
            raise RuntimeError(f"NFON call failed: {exc}") from exc

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active NFON call.

        Args:
            call_id: The NFON call ID.

        Returns:
            True if hangup was successful.
        """
        access_token = await self._get_access_token()
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/calls/{call_id}/hangup",
                    json={"action": "hangup"},
                    headers=await self._get_auth_headers(access_token),
                )
                if response.status_code in (200, 204):
                    return True
                return False
        except Exception as exc:
            logger.error(f"Failed to hang up NFON call: {exc}")
            return False

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into an NFON call.

        Args:
            call_id: The NFON call ID.
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
                    f"{self.api_url}/calls/{call_id}/play",
                    json={"audioUrl": audio_url, "loop": loop},
                    headers=await self._get_auth_headers(access_token),
                )
                return response.status_code in (200, 204)
        except Exception as exc:
            logger.error(f"Failed to play audio via NFON: {exc}")
            return False

    async def send_digits(
        self,
        call_id: str,
        digits: str,
    ) -> bool:
        """Send DTMF digits into an NFON call.

        Args:
            call_id: The NFON call ID.
            digits: DTMF digits to send.

        Returns:
            True if digits were sent successfully.
        """
        access_token = await self._get_access_token()
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.api_url}/calls/{call_id}/dtmf",
                    json={"digits": digits},
                    headers=await self._get_auth_headers(access_token),
                )
                return response.status_code in (200, 204)
        except Exception as exc:
            logger.error(f"Failed to send digits via NFON: {exc}")
            return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a call.

        Args:
            call_id: The NFON call ID.

        Returns:
            PhoneCall object if found, None otherwise.
        """
        from voice_triage.telephony.providers.nfon.parser import (
            NFON_STATUS_MAP,
        )

        access_token = await self._get_access_token()
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.api_url}/calls/{call_id}",
                    headers=await self._get_auth_headers(access_token),
                )
                if response.status_code == 404:
                    return None
                response.raise_for_status()
                data = response.json()
                call_id = data.get("callId") or data.get("id")

                # Parse call details
                from_number = ""
                to_number = ""

                for party in data.get("parties", []):
                    from_data = party.get("from", {})
                    if isinstance(from_data, dict):
                        from_number = from_data.get("phoneNumber", "")
                    to_data = party.get("to", {})
                    if isinstance(to_data, dict):
                        to_number = to_data.get("phoneNumber", "")
                    elif isinstance(to_data, list) and to_data:
                        to_number = to_data[0].get("phoneNumber", "")

                status_str = data.get("status", "unknown")
                status = NFON_STATUS_MAP.get(
                    status_str.lower(), CallStatus.RINGING
                )

                # Parse direction
                direction_str = data.get("direction") or data.get("type", "inbound")
                direction = CallDirection.INBOUND
                if direction_str.lower() in ("outbound", "outgoing"):
                    direction = CallDirection.OUTBOUND

                # Parse timestamps
                started_at = None
                timestamp_fields = ["startTime", "start_time", "created", "timestamp"]
                for field in timestamp_fields:
                    if field in data:
                        try:
                            started_at = datetime.fromisoformat(
                                data[field].replace("Z", "+00:00")
                            )
                            break
                        except (ValueError, TypeError):
                            pass

                return PhoneCall(
                    call_id=call_id,
                    from_number=from_number,
                    to_number=to_number,
                    direction=direction,
                    status=status,
                    provider="nfon",
                    started_at=started_at,
                    metadata={
                        "tenant_id": data.get("tenantId"),
                        "extension_id": data.get("extensionId"),
                        "call_type": data.get("callType"),
                        "recording_url": data.get("recordingUrl"),
                        "original_data": data,
                    },
                )
        except Exception as exc:
            logger.error(f"Failed to get NFON call status: {exc}")
            return None

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into an NFON call in real-time.

        NFON supports WebSocket streaming for real-time audio.

        Args:
            call_id: The NFON call ID.
            audio_stream: Async iterator of audio chunks (PCM 16-bit, 8kHz).

        Returns:
            True if streaming completed successfully.
        """
        logger.warning(
            "NFON real-time audio streaming requires WebSocket setup. "
            "Consider using pre-recorded audio with play_audio() instead."
        )
        return False

    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event (e.g., 'voice', 'status', 'event', 'call').

        Returns:
            The path portion of the webhook URL.
        """
        paths = {
            "voice": "/telephony/nfon/voice",
            "status": "/telephony/nfon/status",
            "event": "/telephony/nfon/event",
            "call": "/telephony/nfon/call",
        }
        return paths.get(event_type, f"/telephony/nfon/{event_type}")
