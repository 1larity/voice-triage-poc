"""Twilio telephony provider implementation.

This module provides the main Twilio provider class that integrates
with Twilio's Programmable Voice API for handling inbound and outbound calls.
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
from voice_triage.telephony.providers.twilio.client import TwilioClient
from voice_triage.telephony.providers.twilio.parser import (
    TWILIO_STATUS_MAP,
    parse_inbound_call,
)
from voice_triage.telephony.providers.twilio.response import (
    generate_full_response,
)
from voice_triage.telephony.registry import register_provider
from voice_triage.telephony.shared.auth import get_header

logger = logging.getLogger(__name__)


@register_provider("twilio")
class TwilioProvider(TelephonyProvider):
    """Twilio telephony provider implementation.

    This provider integrates with Twilio's Programmable Voice API for
    handling inbound and outbound calls in the UK.
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the Twilio provider.

        Args:
            config: Configuration containing:
                - account_sid: Twilio Account SID
                - auth_token: Twilio Auth Token
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default Twilio phone number
        """
        super().__init__(config)
        self._client: TwilioClient | None = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "twilio"

    def _get_client(self) -> TwilioClient:
        """Get or create the Twilio client lazily.

        Returns:
            TwilioClient instance.
        """
        if self._client is None:
            if not self.config.account_sid or not self.config.auth_token:
                raise ValueError("Twilio account_sid and auth_token are required")
            self._client = TwilioClient(
                self.config.account_sid,
                self.config.auth_token,
            )
        return self._client

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate a Twilio webhook signature.

        Twilio signs webhooks with X-Twilio-Signature header.

        Args:
            headers: HTTP headers including X-Twilio-Signature.
            body: Raw request body.
            path: Request path.

        Returns:
            True if signature is valid.
        """
        signature = get_header(headers, "X-Twilio-Signature")
        if not signature:
            logger.warning("Missing X-Twilio-Signature header")
            return False

        if not self.config.webhook_base_url:
            logger.warning("No webhook_base_url configured for validation")
            return False

        # Build the full URL
        url = f"{self.config.webhook_base_url.rstrip('/')}{path}"

        # Validate signature
        return self._validate_twilio_signature(
            url=url,
            params={},  # For POST with body, we validate URL only
            signature=signature,
            body=body,
        )

    def _validate_twilio_signature(
        self,
        url: str,
        params: dict[str, str],
        signature: str,
        body: bytes | None = None,
    ) -> bool:
        """Validate Twilio signature.

        Args:
            url: The full URL of the webhook.
            params: URL parameters (for GET) or None for POST body.
            signature: The X-Twilio-Signature header value.
            body: Raw POST body for body validation.

        Returns:
            True if valid.
        """
        auth_token = self.config.auth_token
        if not auth_token:
            return False

        # For POST requests with body, concatenate URL and body
        if body:
            data = url + body.decode("utf-8")
        else:
            # For GET or form data, sort and concatenate params
            sorted_params = sorted(params.items())
            data = url + "".join(f"{k}{v}" for k, v in sorted_params)

        # Compute HMAC-SHA1
        computed = hmac.new(
            auth_token.encode("utf-8"),
            data.encode("utf-8"),
            hashlib.sha1,
        ).digest()

        # Compare with signature (base64 encoded)
        import base64

        expected = base64.b64encode(computed).decode("utf-8")
        return hmac.compare_digest(expected, signature)

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call from Twilio webhook.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            form_data: Parsed form data from Twilio.

        Returns:
            PhoneCall object.
        """
        return parse_inbound_call(form_data)

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate TwiML response for call control.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to say.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            TwiML XML string.
        """
        return generate_full_response(
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
        """Initiate an outbound call via Twilio.

        Args:
            to_number: Destination phone number in E.164 format.
            from_number: Source phone number (uses default if not provided).
            webhook_url: URL for call status webhooks.
            metadata: Additional metadata.

        Returns:
            PhoneCall object.
        """
        client = self._get_client()

        from_num = from_number or self.config.default_from_number
        if not from_num:
            raise ValueError("No from_number provided and no default configured")

        # Build call parameters
        call_params: dict[str, Any] = {
            "to": to_number,
            "from_": from_num,
        }

        # Add webhook URL
        if webhook_url:
            call_params["url"] = webhook_url
            call_params["status_callback"] = f"{webhook_url}/status"
            call_params["status_callback_event"] = [
                "initiated",
                "ringing",
                "answered",
                "completed",
            ]

        # Make the call
        call = client.calls.create(**call_params)

        return PhoneCall(
            call_id=call.sid,
            from_number=from_num,
            to_number=to_number,
            direction=CallDirection.OUTBOUND,
            status=TWILIO_STATUS_MAP.get(call.status, CallStatus.RINGING),
            provider="twilio",
            started_at=datetime.now(tz=UTC),
            metadata=metadata or {},
        )

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active Twilio call.

        Args:
            call_id: Twilio Call SID.

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()
            call = client.hangup_call(call_id)
            return call.status == "completed"
        except Exception as exc:
            logger.error(f"Failed to hang up call {call_id}: {exc}")
            return False

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a Twilio call.

        Args:
            call_id: Twilio Call SID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()
            client.play_audio(call_id, audio_url, loop)
            return True
        except Exception as exc:
            logger.error(f"Failed to play audio in call {call_id}: {exc}")
            return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a Twilio call.

        Args:
            call_id: Twilio Call SID.
            digits: DTMF digits to send.

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()
            client.send_digits(call_id, digits)
            return True
        except Exception as exc:
            logger.error(f"Failed to send digits in call {call_id}: {exc}")
            return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a Twilio call.

        Args:
            call_id: Twilio Call SID.

        Returns:
            PhoneCall object or None.
        """
        try:
            client = self._get_client()
            call = client.get_call(call_id).fetch()

            return PhoneCall(
                call_id=call.sid,
                from_number=call.from_,
                to_number=call.to,
                direction=(
                    CallDirection.OUTBOUND
                    if call.direction == "outbound"
                    else CallDirection.INBOUND
                ),
                status=TWILIO_STATUS_MAP.get(call.status, CallStatus.RINGING),
                provider="twilio",
                started_at=call.start_time,
                ended_at=call.end_time,
                duration_seconds=call.duration,
                recording_url=call.recording_url,
            )
        except Exception as exc:
            logger.error(f"Failed to get call status for {call_id}: {exc}")
            return None

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a Twilio call.

        Note: This requires Twilio Media Streams which uses WebSocket.
        For real-time streaming, consider using TwiML's Stream verb.

        Args:
            call_id: Twilio Call SID.
            audio_stream: Async iterator of audio chunks.

        Returns:
            True if successful.
        """
        # Twilio media streaming requires WebSocket connection
        # This is a placeholder for the streaming implementation
        logger.warning(
            "Real-time audio streaming requires Twilio Media Streams. "
            "Consider using the Stream TwiML verb or MediaStream API."
        )
        return False

    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event.

        Returns:
            The webhook path.
        """
        paths = {
            "voice": "/telephony/twilio/voice",
            "status": "/telephony/twilio/status",
            "recording": "/telephony/twilio/recording",
            "transcription": "/telephony/twilio/transcription",
        }
        return paths.get(event_type, f"/telephony/twilio/{event_type}")

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract transcript from Twilio webhook data.

        Args:
            data: Parsed request data from the webhook.

        Returns:
            Extracted transcript string.
        """
        # Twilio sends speech result in SpeechResult parameter
        return data.get("SpeechResult", data.get("Body", ""))

    def get_response_content_type(self) -> str:
        """Get the content type for TwiML responses.

        Returns:
            'application/xml' for TwiML.
        """
        return "application/xml"
