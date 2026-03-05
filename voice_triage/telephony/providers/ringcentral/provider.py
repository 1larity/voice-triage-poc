"""RingCentral telephony provider implementation.

This module provides the main RingCentral provider class that integrates
with RingCentral's Cloud PBX API for handling inbound and outbound calls.
"""

from __future__ import annotations

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
from voice_triage.telephony.providers.ringcentral.client import (
    RINGCENTRAL_API_URL,
    RINGCENTRAL_UK_API_URL,
    RingCentralClient,
)
from voice_triage.telephony.providers.ringcentral.parser import (
    RINGCENTRAL_STATUS_MAP,
    parse_inbound_call,
)
from voice_triage.telephony.providers.ringcentral.response import (
    generate_call_control_response,
)
from voice_triage.telephony.registry import register_provider
from voice_triage.telephony.shared.auth import get_header

logger = logging.getLogger(__name__)


@register_provider("ringcentral")
class RingCentralProvider(TelephonyProvider):
    """RingCentral telephony provider implementation.

    RingCentral is a major UC telephony provider offering:
    - Voice calls (inbound/outbound)
    - SIP trunking
    - Programmable voice with RingCentral API
    - Call recording
    - Unified communications

    Documentation: https://developers.ringcentral.com/
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the RingCentral provider.

        Args:
            config: Configuration containing:
                - api_key: RingCentral OAuth Client ID
                - api_secret: RingCentral OAuth Client Secret
                - account_sid: RingCentral Account ID
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default RingCentral phone number
                - extra:
                    - webhook_secret: Secret for webhook validation
                    - use_uk_endpoint: Whether to use UK API endpoint
        """
        super().__init__(config)
        self._client: RingCentralClient | None = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "ringcentral"

    @property
    def tenant_id(self) -> str:
        """Get the RingCentral Tenant ID."""
        return self.config.account_sid or self.config.extra.get("tenant_id", "")

    @property
    def api_url(self) -> str:
        """Get the RingCentral API URL based on configuration."""
        use_uk_endpoint = self.config.extra.get("use_uk_endpoint", True)
        return RINGCENTRAL_UK_API_URL if use_uk_endpoint else RINGCENTRAL_API_URL

    def _get_client(self) -> RingCentralClient:
        """Get or create the RingCentral client lazily.

        Returns:
            RingCentralClient instance.

        Raises:
            ValueError: If required configuration is missing.
        """
        if self._client is None:
            if not self.config.api_key or not self.config.api_secret:
                raise ValueError("RingCentral api_key and api_secret are required")

            account_id = self.config.account_sid or self.config.extra.get("account_id", "")
            if not account_id:
                raise ValueError("RingCentral account_sid or account_id is required")

            self._client = RingCentralClient(
                client_id=self.config.api_key,
                client_secret=self.config.api_secret,
                account_id=account_id,
                api_url=self.api_url,
            )
        return self._client

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate a RingCentral webhook signature.

        RingCentral signs webhooks with a verification token.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            path: Request path.

        Returns:
            True if signature is valid.
        """
        # RingCentral uses verification tokens
        verification_token = get_header(headers, "Verification-Token")

        webhook_secret = self.config.extra.get("webhook_secret")
        if not webhook_secret:
            logger.warning("No webhook_secret configured for RingCentral")
            return True  # Allow if no secret configured

        if not verification_token:
            logger.warning("Missing RingCentral verification token")
            return False

        return hmac.compare_digest(verification_token, webhook_secret)

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call from RingCentral webhook.

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
        """Generate a RingCentral call control response.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to play.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            JSON response for RingCentral call control.
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
        """Initiate an outbound call via RingCentral.

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

            call_id = data.get("id") or data.get("call_id", "")

            return PhoneCall(
                call_id=call_id,
                from_number=from_num,
                to_number=to_number,
                direction=CallDirection.OUTBOUND,
                status=RINGCENTRAL_STATUS_MAP.get(
                    data.get("status", "ringing"),
                    CallStatus.RINGING,
                ),
                provider="ringcentral",
                started_at=datetime.now(tz=UTC),
                metadata={
                    "call_data": data,
                    "custom_metadata": metadata,
                },
            )
        except Exception as exc:
            logger.error(f"Failed to make outbound call via RingCentral: {exc}")
            raise RuntimeError(f"RingCentral outbound call failed: {exc}") from exc

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active RingCentral call.

        Args:
            call_id: The RingCentral call ID.

        Returns:
            True if the call was hung up successfully.
        """
        try:
            client = self._get_client()
            await client.hangup_call(call_id)
            return True
        except Exception as exc:
            logger.error(f"Failed to hang up RingCentral call: {exc}")
            return False

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a RingCentral call.

        Args:
            call_id: The RingCentral call ID.
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
            logger.error(f"Failed to play audio via RingCentral: {exc}")
            return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a RingCentral call.

        Args:
            call_id: The RingCentral call ID.
            digits: DTMF digits to send.

        Returns:
            True if digits were sent successfully.
        """
        try:
            client = self._get_client()
            await client.send_digits(call_id, digits)
            return True
        except Exception as exc:
            logger.error(f"Failed to send digits via RingCentral: {exc}")
            return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a RingCentral call.

        Args:
            call_id: The RingCentral call ID.

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
            status_str = data.get("result", data.get("status", "unknown"))
            status = RINGCENTRAL_STATUS_MAP.get(status_str.lower(), CallStatus.UNKNOWN)

            # Parse timestamps
            started_at = None
            if "startTime" in data:
                try:
                    started_at = datetime.fromisoformat(
                        data["startTime"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            ended_at = None
            if "endTime" in data:
                try:
                    ended_at = datetime.fromisoformat(
                        data["endTime"].replace("Z", "+00:00")
                    )
                except (ValueError, TypeError):
                    pass

            return PhoneCall(
                call_id=call_id,
                from_number=data.get("from", {}).get("phoneNumber", ""),
                to_number=data.get("to", [{}])[0].get("phoneNumber", "") if data.get("to") else "",
                direction=direction,
                status=status,
                provider="ringcentral",
                started_at=started_at,
                ended_at=ended_at,
                duration_seconds=data.get("duration"),
                metadata={
                    "original_data": data,
                },
            )
        except Exception as exc:
            logger.error(f"Failed to get RingCentral call status: {exc}")
            return None

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a RingCentral call.

        Note: RingCentral may not support real-time audio streaming.
        This implementation logs a warning and returns False.

        Args:
            call_id: The RingCentral call ID.
            audio_stream: Async iterator of audio chunks.

        Returns:
            True if streaming completed successfully.
        """
        logger.warning(
            "Real-time audio streaming may not be supported by RingCentral. "
            "Consider using pre-recorded audio with play_audio()."
        )
        return False

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract transcript text from RingCentral webhook payloads."""
        if not isinstance(data, dict):
            return ""

        body_data = data.get("body", data)
        if not isinstance(body_data, dict):
            return ""

        speech_to_text = body_data.get("speechToText")
        if isinstance(speech_to_text, dict):
            text = speech_to_text.get("transcript")
            if isinstance(text, str):
                return text

        for key in ("transcript", "speechResult", "text"):
            value = body_data.get(key)
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
            "voice": "/telephony/ringcentral/voice",
            "status": "/telephony/ringcentral/status",
            "recording": "/telephony/ringcentral/recording",
        }
        return paths.get(event_type, f"/telephony/ringcentral/{event_type}")
