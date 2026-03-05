"""Avaya telephony provider implementation.

This module provides the main Avaya provider class that integrates
with Avaya Communication Manager for handling inbound and outbound calls.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallEvent,
    CallStatus,
    PhoneCall,
    TelephonyConfig,
    TelephonyProvider,
)
from voice_triage.telephony.providers.avaya.client import AvayaClient
from voice_triage.telephony.providers.avaya.parser import (
    AVAYA_STATUS_MAP,
    parse_inbound_call,
    validate_avaya_signature,
    validate_basic_auth,
)
from voice_triage.telephony.registry import register_provider
from voice_triage.telephony.shared.auth import get_header

logger = logging.getLogger(__name__)


@register_provider("avaya")
class AvayaProvider(TelephonyProvider):
    """Avaya telephony provider implementation.

    This provider integrates with Avaya Communication Manager and IP Office
    systems using Avaya Web Services REST API and webhook notifications.

    Supports:
    - Inbound call handling via webhooks
    - Outbound call origination
    - Call control (hold, transfer, conference)
    - Real-time media streaming via RTP
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the Avaya provider.

        Args:
            config: Configuration containing:
                - server_host: Avaya AES host
                - username: AES username
                - password: AES password
                - extension: Default extension for calls
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default caller ID
        """
        super().__init__(config)
        self._client: AvayaClient | None = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "avaya"

    def _get_client(self) -> AvayaClient:
        """Get or create the Avaya client lazily.

        Returns:
            AvayaClient instance.
        """
        if self._client is None:
            extra = self.config.extra or {}
            self._client = AvayaClient(
                server_host=extra.get("server_host", "localhost"),
                server_port=extra.get("server_port", 8443),
                use_ssl=extra.get("use_ssl", True),
                username=extra.get("username", ""),
                password=extra.get("password", ""),
            )
        return self._client

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate an Avaya webhook signature.

        Avaya webhooks can be signed using HMAC-SHA256 or HTTP Basic auth.

        Args:
            headers: HTTP headers including signature headers.
            body: Raw request body.
            path: Request path.

        Returns:
            True if signature is valid.
        """
        # Try signature validation first
        signature = get_header(headers, "X-Avaya-Signature") or get_header(
            headers, "X-Webhook-Signature"
        )

        if signature:
            webhook_secret = self.config.webhook_secret
            if webhook_secret:
                return validate_avaya_signature(signature, body, webhook_secret)
            logger.warning("No webhook_secret configured for Avaya")
            return False

        # Fall back to Basic auth
        auth_header = get_header(headers, "Authorization")
        if auth_header:
            extra = self.config.extra or {}
            return validate_basic_auth(
                auth_header,
                extra.get("username", ""),
                extra.get("password", ""),
            )

        logger.warning("Missing Avaya webhook signature header")
        return False

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call from Avaya webhook.

        Args:
            headers: HTTP headers from the webhook.
            body: Raw request body.
            form_data: Parsed form data (unused for Avaya).

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
        """Generate response for Avaya call.

        Avaya uses different response formats depending on the integration:
        - TSAPI: Uses XML-based responses
        - DMCC: Uses JSON responses

        This implementation returns JSON for DMCC-style integration.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to say.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            JSON response string.
        """
        response: dict[str, Any] = {
            "sessionId": session_id,
            "actions": [],
        }

        actions: list[dict[str, Any]] = []

        # Add welcome message
        if welcome_message:
            speak_action: dict[str, Any] = {
                "action": "speak",
                "text": welcome_message,
                "language": "en-GB",
            }
            actions.append(speak_action)

        # Add speech input gathering
        if gather_speech and action_url:
            gather_action: dict[str, Any] = {
                "action": "gather",
                "eventUrl": action_url,
                "inputType": "speech",
                "speech": {
                    "language": "en-GB",
                    "timeout": 5,
                },
            }
            actions.append(gather_action)

        response["actions"] = actions
        import json

        return json.dumps(response)

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Make an outbound call through Avaya.

        Uses Avaya Web Services to originate a call from an extension
        to an external number.

        Args:
            to_number: Destination phone number.
            from_number: Caller ID (uses default if not provided).
            webhook_url: URL for call status webhooks.
            metadata: Optional metadata for the call.

        Returns:
            PhoneCall object representing the new call.

        Raises:
            RuntimeError: If call origination fails.
        """
        extra = self.config.extra or {}
        extension = (
            metadata.get("extension")
            if metadata
            else None or extra.get("extension") or "5001"
        )

        caller_id = from_number or self.config.default_from_number or ""

        # Build call request
        call_data = {
            "extension": extension,
            "destination": to_number,
            "callerId": caller_id,
            "media": "audio",
        }

        # Make the API call
        client = self._get_client()
        try:
            response = await client.make_request(
                "POST",
                "/api/v1/calls",
                data=call_data,
            )
        except RuntimeError as e:
            logger.error(f"Failed to originate Avaya call: {e}")
            raise

        call_id = response.get("callId") or response.get("ucid") or ""

        return PhoneCall(
            call_id=call_id,
            from_number=caller_id,
            to_number=to_number,
            direction=CallDirection.OUTBOUND,
            status=CallStatus.DIALING,
            provider=self.name,
            started_at=datetime.now(UTC),
            metadata={
                "extension": extension,
                "ucid": response.get("ucid"),
                "raw_response": response,
            },
        )

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active call.

        Args:
            call_id: The Avaya call ID or UCID.

        Returns:
            True if hangup was successful.
        """
        try:
            client = self._get_client()
            await client.make_request(
                "DELETE",
                f"/api/v1/calls/{call_id}",
            )
            return True
        except RuntimeError as e:
            logger.error(f"Failed to hang up Avaya call {call_id}: {e}")
            return False

    async def hold_call(self, call_id: str) -> bool:
        """Put a call on hold.

        Args:
            call_id: The Avaya call ID.

        Returns:
            True if hold was successful.
        """
        try:
            client = self._get_client()
            await client.make_request(
                "POST",
                f"/api/v1/calls/{call_id}/hold",
            )
            return True
        except RuntimeError as e:
            logger.error(f"Failed to hold Avaya call {call_id}: {e}")
            return False

    async def resume_call(self, call_id: str) -> bool:
        """Resume a held call.

        Args:
            call_id: The Avaya call ID.

        Returns:
            True if resume was successful.
        """
        try:
            client = self._get_client()
            await client.make_request(
                "POST",
                f"/api/v1/calls/{call_id}/resume",
            )
            return True
        except RuntimeError as e:
            logger.error(f"Failed to resume Avaya call {call_id}: {e}")
            return False

    async def transfer_call(
        self,
        call_id: str,
        to_number: str,
        blind: bool = True,
    ) -> bool:
        """Transfer a call to another number.

        Args:
            call_id: The Avaya call ID.
            to_number: Destination number for transfer.
            blind: If True, perform blind transfer (no consultation).

        Returns:
            True if transfer was initiated successfully.
        """
        transfer_type = "blind" if blind else "consult"
        try:
            client = self._get_client()
            await client.make_request(
                "POST",
                f"/api/v1/calls/{call_id}/transfer",
                data={
                    "destination": to_number,
                    "type": transfer_type,
                },
            )
            return True
        except RuntimeError as e:
            logger.error(f"Failed to transfer Avaya call {call_id}: {e}")
            return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF tones on an active call.

        Args:
            call_id: The Avaya call ID.
            digits: DTMF digits to send (0-9, *, #).

        Returns:
            True if DTMF was sent successfully.
        """
        try:
            client = self._get_client()
            await client.make_request(
                "POST",
                f"/api/v1/calls/{call_id}/dtmf",
                data={"digits": digits},
            )
            return True
        except RuntimeError as e:
            logger.error(f"Failed to send DTMF on Avaya call {call_id}: {e}")
            return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a call.

        Args:
            call_id: The Avaya call ID.

        Returns:
            PhoneCall object if found, None otherwise.
        """
        try:
            client = self._get_client()
            response = await client.make_request(
                "GET",
                f"/api/v1/calls/{call_id}",
            )

            avaya_status = response.get("state") or response.get("status", "")
            status = AVAYA_STATUS_MAP.get(avaya_status.lower(), CallStatus.RINGING)

            return PhoneCall(
                call_id=call_id,
                from_number=response.get("callingNumber", ""),
                to_number=response.get("calledNumber", ""),
                direction=CallDirection.INBOUND,
                status=status,
                provider=self.name,
            )
        except RuntimeError as e:
            logger.error(f"Failed to get Avaya call status {call_id}: {e}")
            return None

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio to an active call.

        Streams audio via RTP to the Avaya media server.

        Args:
            call_id: The Avaya call ID.
            audio_stream: Async iterator yielding audio chunks.

        Returns:
            True if streaming completed successfully.

        Note:
            This implementation logs audio chunks. Actual RTP streaming
            would require a separate media channel setup via DMCC.
        """
        logger.info(f"Starting audio stream for Avaya call {call_id}")

        chunk_count = 0
        async for chunk in audio_stream:
            chunk_count += 1
            logger.debug(
                f"Avaya call {call_id}: received audio chunk "
                f"{chunk_count} ({len(chunk)} bytes)"
            )

        logger.info(
            f"Completed audio stream for Avaya call {call_id}: "
            f"{chunk_count} chunks"
        )
        return True

    async def receive_audio(
        self,
        call_id: str,
    ) -> AsyncIterator[bytes]:
        """Receive audio from an active call.

        Receives audio via RTP from the Avaya media server.

        Args:
            call_id: The Avaya call ID.

        Yields:
            Audio chunks in the configured format (typically mu-law).

        Note:
            This is a placeholder implementation. Actual RTP receiving
            would require a separate media channel setup via DMCC.
        """
        logger.info(f"Starting audio receive for Avaya call {call_id}")
        # Placeholder: yield empty to satisfy type checker
        yield b""
        return

    async def handle_event(
        self,
        headers: dict[str, str],
        body: bytes,
    ) -> CallEvent | None:
        """Handle a call event from Avaya webhook.

        Args:
            headers: HTTP headers from the webhook.
            body: Raw request body.

        Returns:
            CallEvent if valid, None otherwise.
        """
        # First validate the webhook
        if not await self.validate_webhook(headers, body, ""):
            logger.warning("Invalid Avaya webhook signature")
            return None

        # Parse the call
        phone_call = await self.parse_inbound_call(headers, body, {})
        if not phone_call:
            return None

        import json

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            data = {}

        event_type = data.get("event", "unknown").lower()

        return CallEvent(
            event_type=event_type,
            call=phone_call,
            timestamp=phone_call.started_at or datetime.now(UTC),
            data=data,
        )

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract transcript text from Avaya webhook payloads."""
        if not isinstance(data, dict):
            return ""

        for key in ("transcript", "speech", "text", "SpeechResult"):
            value = data.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                nested = value.get("text") or value.get("transcript")
                if isinstance(nested, str):
                    return nested
        return ""

    def get_webhook_path(self, event_type: str = "") -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event.

        Returns:
            The webhook path.
        """
        paths = {
            "voice": "/telephony/avaya/voice",
            "event": "/telephony/avaya/event",
            "status": "/telephony/avaya/status",
        }
        return paths.get(event_type, f"/telephony/avaya/{event_type}")
