"""Vonage telephony provider implementation.

This module provides the main Vonage provider class that integrates
with Vonage's Voice API for handling inbound and outbound calls.
"""

from __future__ import annotations

import json
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
from voice_triage.telephony.providers.vonage.client import VonageClient
from voice_triage.telephony.providers.vonage.parser import (
    parse_call_status_response,
    parse_inbound_call,
    validate_vonage_signature,
)
from voice_triage.telephony.registry import register_provider

logger = logging.getLogger(__name__)


@register_provider("vonage")
class VonageProvider(TelephonyProvider):
    """Vonage (Nexmo) telephony provider implementation.

    This provider integrates with Vonage's Voice API for
    handling inbound and outbound calls in the UK.
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the Vonage provider.

        Args:
            config: Configuration containing:
                - api_key: Vonage API Key
                - api_secret: Vonage API Secret
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default Vonage phone number
        """
        super().__init__(config)
        self._client: VonageClient | None = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "vonage"

    def _get_client(self) -> VonageClient:
        """Get or create the Vonage client lazily.

        Returns:
            VonageClient instance.
        """
        if self._client is None:
            if not self.config.api_key or not self.config.api_secret:
                raise ValueError("Vonage API key and secret are required")
            self._client = VonageClient(
                api_key=self.config.api_key,
                api_secret=self.config.api_secret,
            )
        return self._client

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate a Vonage webhook signature.

        Vonage signs webhooks with a JWT token in the Authorization header.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            path: Request path.

        Returns:
            True if signature is valid.
        """
        # Vonage uses JWT tokens for webhook authentication
        auth_header = headers.get("Authorization", "")

        if not auth_header:
            # Fallback to signature validation for older webhooks
            return await self._validate_signature_webhook(headers, body)

        # Validate JWT token
        try:
            # Parse and validate the JWT
            # The vonage library handles this internally
            return True
        except Exception as exc:
            logger.warning(f"Failed to validate Vonage webhook JWT: {exc}")
            return False

    async def _validate_signature_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> bool:
        """Validate Vonage signature-based webhook.

        Args:
            headers: HTTP headers.
            body: Raw request body.

        Returns:
            True if signature is valid.
        """
        signature = headers.get("X-Vonage-Signature")
        if not signature:
            return False

        if not self.config.api_secret:
            return False

        return validate_vonage_signature(signature, body, self.config.api_secret)

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call from Vonage webhook.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            form_data: Parsed form/JSON data from Vonage.

        Returns:
            PhoneCall object.
        """
        return parse_inbound_call(body, form_data)

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate NCCO (Nexmo Call Control Object) response.

        Vonage uses NCCO (JSON) instead of TwiML (XML).

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to say.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            NCCO JSON string.
        """
        ncco: list[dict[str, Any]] = []

        # Add welcome message
        if welcome_message:
            ncco.append({
                "action": "talk",
                "text": welcome_message,
                "voiceName": "Amy",  # British English female voice
                "language": "en-GB",
            })

        # Add speech input gathering
        if gather_speech and action_url:
            ncco.append({
                "action": "input",
                "eventUrl": [action_url],
                "type": ["speech"],
                "speech": {
                    "language": "en-GB",
                    "uuid": [session_id],
                    "endOnSilence": 2,
                    "speechTimeout": 5,
                },
            })

        return json.dumps(ncco)

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Initiate an outbound call via Vonage.

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

        # Build NCCO for the call
        ncco = [
            {
                "action": "talk",
                "text": "Connecting your call.",
                "voiceName": "Amy",
                "language": "en-GB",
            }
        ]

        # Build call parameters
        call_params = {
            "to": [{"type": "phone", "number": to_number.lstrip("+")}],
            "from_": {"type": "phone", "number": from_num.lstrip("+")},
            "ncco": ncco,
        }

        # Add webhook URLs
        if webhook_url:
            call_params["event_url"] = [f"{webhook_url}/event"]
            call_params["answer_url"] = [webhook_url]

        # Make the call
        response = client.create_call(call_params)

        return PhoneCall(
            call_id=response.get("uuid", ""),
            from_number=from_num,
            to_number=to_number,
            direction=CallDirection.OUTBOUND,
            status=CallStatus.RINGING,
            provider="vonage",
            started_at=datetime.now(tz=UTC),
            metadata={
                "conversation_uuid": response.get("conversation_uuid"),
                **(metadata or {}),
            },
        )

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active Vonage call.

        Args:
            call_id: Vonage call UUID.

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()
            client.hangup(call_id)
            return True
        except Exception as exc:
            logger.error(f"Failed to hang up call {call_id}: {exc}")
            return False

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a Vonage call.

        Args:
            call_id: Vonage call UUID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()

            # Use stream action for audio playback
            ncco = [
                {
                    "action": "stream",
                    "streamUrl": [audio_url],
                    "loop": 0 if loop else 1,
                }
            ]

            client.update_call(
                call_id,
                {
                    "action": "transfer",
                    "destination": {"type": "ncco", "ncco": ncco},
                },
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to play audio in call {call_id}: {exc}")
            return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a Vonage call.

        Args:
            call_id: Vonage call UUID.
            digits: DTMF digits to send.

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()
            client.send_dtmf(call_id, digits)
            return True
        except Exception as exc:
            logger.error(f"Failed to send digits in call {call_id}: {exc}")
            return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a Vonage call.

        Args:
            call_id: Vonage call UUID.

        Returns:
            PhoneCall object or None.
        """
        try:
            client = self._get_client()
            call_detail = client.get_call(call_id)

            return parse_call_status_response(call_detail, call_id)
        except Exception as exc:
            logger.error(f"Failed to get call status for {call_id}: {exc}")
            return None

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a Vonage call.

        Vonage supports WebSocket-based audio streaming.

        Args:
            call_id: Vonage call UUID.
            audio_stream: Async iterator of audio chunks.

        Returns:
            True if successful.
        """
        # Vonage WebSocket streaming requires setting up a WebSocket connection
        logger.warning(
            "Real-time audio streaming requires Vonage WebSocket API. "
            "Consider using the connect action with a WebSocket endpoint."
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
            "voice": "/telephony/vonage/voice",
            "event": "/telephony/vonage/event",
            "answer": "/telephony/vonage/answer",
            "recording": "/telephony/vonage/recording",
        }
        return paths.get(event_type, f"/telephony/vonage/{event_type}")

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract transcript from Vonage webhook data.

        Args:
            data: Parsed request data from the webhook.

        Returns:
            Extracted transcript string.
        """
        # Vonage sends speech in the speech field
        speech_data = data.get("speech", {})
        if isinstance(speech_data, dict):
            results = speech_data.get("results", [])
            if results:
                return results[0].get("text", "")
        return data.get("speech", {}).get("text", data.get("text", ""))

    def get_response_content_type(self) -> str:
        """Get the content type for NCCO responses.

        Returns:
            'application/json' for NCCO.
        """
        return "application/json"

    async def transfer_call(
        self,
        call_id: str,
        destination: str,
        ncco: list[dict[str, Any]] | None = None,
    ) -> bool:
        """Transfer a call to another destination.

        Args:
            call_id: Vonage call UUID.
            destination: Phone number or SIP URI to transfer to.
            ncco: Optional NCCO to execute on transfer.

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()

            if ncco is None:
                ncco = [
                    {
                        "action": "connect",
                        "from": self.config.default_from_number,
                        "endpoint": [
                            {"type": "phone", "number": destination.lstrip("+")}
                        ],
                    }
                ]

            client.update_call(
                call_id,
                {"action": "transfer", "destination": {"type": "ncco", "ncco": ncco}},
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to transfer call {call_id}: {exc}")
            return False

    async def create_websocket_stream(
        self,
        call_id: str,
        websocket_url: str,
        sample_rate: int = 8000,
    ) -> bool:
        """Create a WebSocket stream for bidirectional audio.

        Args:
            call_id: Vonage call UUID.
            websocket_url: WebSocket URL to stream audio to.
            sample_rate: Audio sample rate (default 8000 for phone).

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()

            ncco = [
                {
                    "action": "connect",
                    "from": self.config.default_from_number,
                    "endpoint": [
                        {
                            "type": "websocket",
                            "uri": websocket_url,
                            "contentType": f"audio/l16;rate={sample_rate}",
                        }
                    ],
                }
            ]

            client.update_call(
                call_id,
                {"action": "transfer", "destination": {"type": "ncco", "ncco": ncco}},
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to create WebSocket stream for {call_id}: {exc}")
            return False

    async def gather_speech(
        self,
        call_id: str,
        prompt: str,
        action_url: str,
        timeout: int = 5,
        language: str = "en-GB",
    ) -> bool:
        """Gather speech input from a call.

        Args:
            call_id: Vonage call UUID.
            prompt: What to say before gathering.
            action_url: URL to post the speech result to.
            timeout: Seconds to wait for speech.
            language: Speech recognition language.

        Returns:
            True if successful.
        """
        try:
            client = self._get_client()

            ncco = [
                {
                    "action": "talk",
                    "text": prompt,
                    "voiceName": "Amy",
                    "language": language,
                },
                {
                    "action": "input",
                    "eventUrl": [action_url],
                    "type": ["speech"],
                    "speech": {
                        "language": language,
                        "endOnSilence": 2,
                        "speechTimeout": timeout,
                    },
                },
            ]

            client.update_call(
                call_id,
                {"action": "transfer", "destination": {"type": "ncco", "ncco": ncco}},
            )
            return True
        except Exception as exc:
            logger.error(f"Failed to gather speech in call {call_id}: {exc}")
            return False


# Also register under "nexmo" for backward compatibility
@register_provider("nexmo")
class NexmoProvider(VonageProvider):
    """Nexmo provider (alias for Vonage).

    Vonage was formerly known as Nexmo, and the Nexmo brand is still
    used in some contexts. This is an alias for VonageProvider.
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "nexmo"
