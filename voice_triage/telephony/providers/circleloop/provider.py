"""CircleLoop telephony provider implementation.

This module provides the main CircleLoop provider class that integrates
with CircleLoop's cloud phone system API for handling inbound and outbound calls.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
    TelephonyConfig,
    TelephonyProvider,
)
from voice_triage.telephony.providers.circleloop.client import CircleLoopClient
from voice_triage.telephony.providers.circleloop.parser import (
    CIRCLELOOP_STATUS_MAP,
    parse_inbound_call,
)
from voice_triage.telephony.providers.circleloop.response import (
    generate_call_control_response,
)
from voice_triage.telephony.registry import register_provider
from voice_triage.telephony.shared.auth import get_header

logger = logging.getLogger(__name__)


@register_provider("circleloop")
class CircleLoopProvider(TelephonyProvider):
    """CircleLoop telephony provider implementation.

    CircleLoop is a UK-based cloud phone system provider offering:
    - Voice calls (inbound/outbound)
    - Call recording
    - Call analytics
    - Multi-device support

    Documentation: https://developer.circleloop.com/
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the CircleLoop provider.

        Args:
            config: Configuration containing:
                - api_key: CircleLoop API key
                - api_secret: CircleLoop API secret
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default CircleLoop phone number
                - extra:
                    - webhook_secret: Secret for webhook validation
                    - use_uk_endpoint: Whether to use UK API endpoint
        """
        super().__init__(config)
        self._client: CircleLoopClient | None = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "circleloop"

    def _get_client(self) -> CircleLoopClient:
        """Get or create the CircleLoop client lazily.

        Returns:
            CircleLoopClient instance.

        Raises:
            ValueError: If required configuration is missing.
        """
        if self._client is None:
            if not self.config.api_key or not self.config.api_secret:
                raise ValueError("CircleLoop api_key and api_secret are required")

            use_uk_endpoint = self.config.extra.get("use_uk_endpoint", True)
            self._client = CircleLoopClient(
                api_key=self.config.api_key,
                api_secret=self.config.api_secret,
                api_url=None if use_uk_endpoint else "https://api.circleloop.com/v1",
            )
        return self._client

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate a CircleLoop webhook signature.

        CircleLoop signs webhooks with X-CircleLoop-Signature header.

        Args:
            headers: HTTP headers including X-CircleLoop-Signature.
            body: Raw request body.
            path: Request path.

        Returns:
            True if signature is valid.
        """
        signature = get_header(headers, "X-CircleLoop-Signature")

        if not signature:
            logger.warning("Missing CircleLoop webhook signature")
            return False

        webhook_secret = self.config.extra.get("webhook_secret")
        if not webhook_secret:
            logger.warning("No webhook_secret configured for CircleLoop")
            return False

        try:
            # CircleLoop uses HMAC-SHA256
            expected = hmac.new(
                webhook_secret.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(expected, signature)
        except Exception as exc:
            logger.warning(f"Failed to validate CircleLoop webhook: {exc}")
            return False

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call from CircleLoop webhook.

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
        """Generate a CircleLoop call control response.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to play.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            JSON response for CircleLoop call control.
        """
        return generate_call_control_response(
            session_id=session_id,
            welcome_message=welcome_message,
            gather_speech=gather_speech,
            action_url=action_url,
        )

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Initiate an outbound call via CircleLoop.

        Args:
            to_number: Destination phone number in E.164 format.
            from_number: Source phone number (uses default if not provided).
            webhook_url: URL for call status webhooks.
            metadata: Additional metadata to attach to the call.

        Returns:
            A PhoneCall object representing the initiated call.
        """
        client = self._get_client()

        from_num = from_number or self.config.default_from_number
        if not from_num:
            raise ValueError("No from_number provided and no default configured")

        try:
            data = await client.create_call(
                to_number=to_number,
                from_number=from_num,
                webhook_url=webhook_url,
            )

            call_id = data.get("call_id") or data.get("id", "")

            return PhoneCall(
                call_id=call_id,
                from_number=from_num,
                to_number=to_number,
                direction=CallDirection.OUTBOUND,
                status=CIRCLELOOP_STATUS_MAP.get(
                    data.get("status", "ringing"),
                    CallStatus.RINGING,
                ),
                provider="circleloop",
                started_at=datetime.now(tz=UTC),
                metadata={
                    "call_data": data,
                    "custom_metadata": metadata,
                },
            )
        except Exception as exc:
            logger.error(f"Failed to make outbound call via CircleLoop: {exc}")
            raise RuntimeError(f"CircleLoop outbound call failed: {exc}") from exc

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active CircleLoop call.

        Args:
            call_id: The CircleLoop call ID.

        Returns:
            True if the call was hung up successfully.
        """
        try:
            client = self._get_client()
            await client.hangup_call(call_id)
            return True
        except Exception as exc:
            logger.error(f"Failed to hang up CircleLoop call: {exc}")
            return False

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a CircleLoop call.

        Args:
            call_id: The CircleLoop call ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            True if audio started playing successfully.
        """
        try:
            client = self._get_client()
            await client.play_audio(call_id, audio_url, loop)
            return True
        except Exception as exc:
            logger.error(f"Failed to play audio via CircleLoop: {exc}")
            return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a CircleLoop call.

        Args:
            call_id: The CircleLoop call ID.
            digits: DTMF digits to send.

        Returns:
            True if digits were sent successfully.
        """
        try:
            client = self._get_client()
            await client.send_digits(call_id, digits)
            return True
        except Exception as exc:
            logger.error(f"Failed to send digits via CircleLoop: {exc}")
            return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a CircleLoop call.

        Args:
            call_id: The CircleLoop call ID.

        Returns:
            PhoneCall object if found, None otherwise.
        """
        try:
            client = self._get_client()
            data = await client.get_call(call_id)

            # Parse direction
            direction_str = data.get("direction", "inbound")
            direction = CallDirection.INBOUND
            if direction_str.lower() in ("outbound", "outgoing"):
                direction = CallDirection.OUTBOUND

            # Parse status
            status_str = data.get("status", "unknown")
            status = CIRCLELOOP_STATUS_MAP.get(status_str.lower(), CallStatus.UNKNOWN)

            # Parse timestamps
            started_at = None
            if "start_time" in data:
                try:
                    started_at = datetime.fromisoformat(
                        data["start_time"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            ended_at = None
            if "end_time" in data:
                try:
                    ended_at = datetime.fromisoformat(
                        data["end_time"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            return PhoneCall(
                call_id=call_id,
                from_number=data.get("from", ""),
                to_number=data.get("to", ""),
                direction=direction,
                status=status,
                provider="circleloop",
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=data.get("duration"),
                metadata={
                    "original_data": data,
                },
            )
        except Exception as exc:
            logger.error(f"Failed to get CircleLoop call status: {exc}")
            return None

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a CircleLoop call.

        Note: CircleLoop may not support real-time audio streaming.
        This implementation logs a warning and returns False.

        Args:
            call_id: The CircleLoop call ID.
            audio_stream: Async iterator of audio chunks.

        Returns:
            True if streaming completed successfully.
        """
        logger.warning(
            "Real-time audio streaming may not be supported by CircleLoop. "
            "Consider using pre-recorded audio with play_audio()."
        )
        return False

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract transcript text from CircleLoop webhook payloads."""
        if not isinstance(data, dict):
            return ""

        for key in ("transcript", "speech", "text", "speechResult"):
            value = data.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                nested = value.get("text") or value.get("transcript")
                if isinstance(nested, str):
                    return nested
        return ""

    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event.

        Returns:
            The webhook path.
        """
        paths = {
            "voice": "/telephony/circleloop/voice",
            "status": "/telephony/circleloop/status",
            "recording": "/telephony/circleloop/recording",
        }
        return paths.get(event_type, f"/telephony/circleloop/{event_type}")
