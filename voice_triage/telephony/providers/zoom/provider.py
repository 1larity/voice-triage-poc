"""Zoom Phone telephony provider implementation.

This module provides the main Zoom Phone provider classes that integrate
with Zoom's Phone API for handling inbound and outbound calls.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
    TelephonyConfig,
    TelephonyProvider,
)
from voice_triage.telephony.providers.zoom.client import ZoomClient
from voice_triage.telephony.providers.zoom.parser import (
    parse_call_data,
    parse_inbound_call,
    validate_webhook_signature,
)
from voice_triage.telephony.providers.zoom.response import (
    generate_call_control_response,
)
from voice_triage.telephony.registry import register_provider

logger = logging.getLogger(__name__)


@register_provider("zoom")
@register_provider("zoom_phone")
class ZoomPhoneProvider(TelephonyProvider):
    """Zoom Phone telephony provider implementation.

    This provider integrates with Zoom's Phone API for
    handling inbound and outbound calls in the UK.

    Zoom Phone uses OAuth 2.0 for authentication with Server-to-Server
    OAuth being the recommended approach for backend integrations.
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the Zoom Phone provider.

        Args:
            config: Configuration containing:
                - api_key: Zoom Server-to-Server OAuth Client ID
                - api_secret: Zoom Server-to-Server OAuth Client Secret
                - account_sid: Zoom Account ID
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default Zoom Phone number
                - extra:
                    - account_id: Zoom Account ID (alternative to account_sid)
                    - webhook_secret: Secret for webhook validation
                    - site_id: Zoom Phone site ID (for multi-site setups)
        """
        super().__init__(config)
        self._client: ZoomClient | None = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "zoom"

    @property
    def account_id(self) -> str:
        """Get the Zoom Account ID."""
        return self.config.account_sid or self.config.extra.get("account_id", "")

    @property
    def webhook_secret(self) -> str:
        """Get the webhook secret."""
        return self.config.extra.get("webhook_secret", "")

    def _get_client(self) -> ZoomClient:
        """Get or create the Zoom client lazily."""
        if self._client is None:
            self._client = ZoomClient(
                client_id=self.config.api_key or "",
                client_secret=self.config.api_secret or "",
                account_id=self.account_id,
            )
        return self._client

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate a Zoom webhook signature.

        Zoom webhooks are signed with the webhook secret using HMAC-SHA256.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            path: Request path.

        Returns:
            True if signature is valid.
        """
        # Zoom sends signature in x-zm-signature header
        signature = headers.get("x-zm-signature") or headers.get("X-Zm-Signature")

        if not signature:
            logger.warning("Missing Zoom webhook signature")
            return False

        if not self.webhook_secret:
            logger.warning("No webhook_secret configured for Zoom webhook validation")
            return False

        return validate_webhook_signature(body, signature, self.webhook_secret)

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call webhook from Zoom Phone.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            form_data: Parsed form data from the request.

        Returns:
            A PhoneCall object representing the inbound call.
        """
        return parse_inbound_call(headers, body, form_data)

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate a Zoom Phone call control response.

        Zoom Phone uses a JSON-based call control format.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to play.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            JSON response for Zoom Phone call control.
        """
        return generate_call_control_response(
            session_id=session_id,
            welcome_message=welcome_message,
            gather_speech=gather_speech,
            action_url=action_url,
            speech_timeout=self.config.extra.get("speech_timeout", 5),
        )

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Initiate an outbound call via Zoom Phone.

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

        client = self._get_client()
        data = await client.make_call(
            to_number=to_number,
            from_number=from_number,
            webhook_url=webhook_url,
        )

        call_id = data.get("call_id") or data.get("id", "")

        return PhoneCall(
            call_id=call_id,
            from_number=from_number,
            to_number=to_number,
            direction=CallDirection.OUTBOUND,
            status=CallStatus.RINGING,
            provider="zoom",
            metadata={
                "call_data": data,
                "custom_metadata": metadata,
            },
        )

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active Zoom Phone call.

        Args:
            call_id: The Zoom Phone call ID.

        Returns:
            True if the call was hung up successfully.
        """
        client = self._get_client()
        return await client.hangup_call(call_id)

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
        client = self._get_client()
        return await client.play_audio(call_id, audio_url, loop)

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a Zoom Phone call.

        Args:
            call_id: The Zoom Phone call ID.
            digits: DTMF digits to send.

        Returns:
            True if digits were sent successfully.
        """
        client = self._get_client()
        return await client.send_digits(call_id, digits)

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a Zoom Phone call.

        Args:
            call_id: The Zoom Phone call ID.

        Returns:
            PhoneCall object if found, None otherwise.
        """
        client = self._get_client()
        data = await client.get_call(call_id)

        if data is None:
            return None

        return parse_call_data(data)

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a Zoom Phone call in real-time.

        Zoom Phone supports real-time audio streaming via WebSocket.

        Args:
            call_id: The Zoom Phone call ID.
            audio_stream: Async iterator of audio chunks (PCM 16-bit, 8kHz).

        Returns:
            True if streaming completed successfully.
        """
        # Zoom Phone supports WebSocket streaming for real-time audio
        # This is a simplified implementation
        logger.warning(
            "Zoom Phone real-time audio streaming requires WebSocket setup. "
            "Consider using pre-recorded audio with play_audio() instead."
        )
        return False

    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event (e.g., 'voice', 'status').

        Returns:
            The path portion of the webhook URL.
        """
        paths = {
            "voice": "/telephony/zoom/voice",
            "status": "/telephony/zoom/status",
            "event": "/telephony/zoom/event",
            "call": "/telephony/zoom/call",
        }
        return paths.get(event_type, f"/telephony/zoom/{event_type}")


@register_provider("zoom_uk")
class ZoomPhoneUKProvider(ZoomPhoneProvider):
    """Zoom Phone UK-specific provider with UK defaults.

    This is a convenience class that sets UK-specific defaults.
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "zoom_uk"

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize with UK defaults.

        Args:
            config: Configuration (region will be set to GB).
        """
        config.region = "GB"
        super().__init__(config)
