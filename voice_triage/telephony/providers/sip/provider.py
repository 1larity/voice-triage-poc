"""SIP trunking telephony provider implementation.

This module provides the main SIP provider classes that integrate
with SIP trunking gateways for handling inbound and outbound calls.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
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
from voice_triage.telephony.providers.sip.parser import (
    parse_inbound_call,
)
from voice_triage.telephony.providers.sip.response import (
    generate_call_control_response,
)
from voice_triage.telephony.registry import register_provider

logger = logging.getLogger(__name__)


@register_provider("sip")
class SIPProvider(TelephonyProvider):
    """SIP trunking telephony provider implementation.

    This provider supports generic SIP trunking for UK providers like
    Gamma Telecom, BT, Virgin Media Business, etc.

    The implementation uses a SIP gateway/bridge approach where the
    application connects to a SIP server/gateway that handles the
    actual SIP signaling.
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the SIP provider.

        Args:
            config: Configuration containing:
                - provider_name: "sip"
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default phone number
                - extra: SIP-specific settings:
                    - sip_server: SIP server hostname/IP
                    - sip_port: SIP server port (default 5060)
                    - sip_username: SIP authentication username
                    - sip_password: SIP authentication password
                    - sip_transport: "udp", "tcp", or "tls"
                    - sip_domain: SIP domain/realm
        """
        super().__init__(config)
        self._sip_client: Any = None
        self._active_calls: dict[str, PhoneCall] = {}

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "sip"

    @property
    def sip_server(self) -> str:
        """Get the SIP server address."""
        return self.config.extra.get("sip_server", "")

    @property
    def sip_port(self) -> int:
        """Get the SIP server port."""
        return self.config.extra.get("sip_port", 5060)

    @property
    def sip_transport(self) -> str:
        """Get the SIP transport protocol."""
        return self.config.extra.get("sip_transport", "udp")

    def _get_sip_client(self) -> Any:
        """Get or create the SIP client lazily."""
        if self._sip_client is None:
            # SIP integration typically requires a SIP stack
            # This is a placeholder for SIP client initialization
            # In production, you would use a library like pyvoip or similar
            logger.info(
                f"Initializing SIP client for {self.sip_server}:{self.sip_port}"
            )
            self._sip_client = True  # Placeholder
        return self._sip_client

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate a SIP webhook request.

        For SIP trunking, webhooks typically come from a SIP gateway
        that converts SIP events to HTTP webhooks.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            path: Request path.

        Returns:
            True if the webhook is valid.
        """
        # Check for shared secret if configured
        shared_secret = self.config.extra.get("webhook_secret")
        if shared_secret:
            provided_secret = headers.get("X-SIP-Secret", "")
            return provided_secret == shared_secret

        # Check for IP whitelist if configured
        allowed_ips = self.config.extra.get("allowed_webhook_ips", [])
        if allowed_ips:
            # In a real implementation, you'd check the source IP
            pass

        # Default: accept if no validation configured
        return True

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call from SIP gateway webhook.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            form_data: Parsed form/JSON data.

        Returns:
            PhoneCall object.
        """
        return parse_inbound_call(headers, body, form_data)

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate SIP gateway response.

        For SIP trunking, this generates a JSON response that the
        SIP gateway can interpret for call control.

        Args:
            session_id: Session ID.
            welcome_message: Optional welcome message.
            gather_speech: Whether to gather speech.
            action_url: URL for speech results.

        Returns:
            JSON response string.
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
        """Initiate an outbound SIP call.

        Args:
            to_number: Destination phone number in E.164 format.
            from_number: Source phone number.
            webhook_url: Webhook URL for call events.
            metadata: Additional metadata.

        Returns:
            PhoneCall object.
        """
        from_num = from_number or self.config.default_from_number
        if not from_num:
            raise ValueError("No from_number provided and no default configured")

        call_id = str(uuid.uuid4())

        # In production, this would send a SIP INVITE via the SIP stack
        logger.info(
            f"Initiating SIP call {call_id} from {from_num} to {to_number} "
            f"via {self.sip_server}:{self.sip_port}"
        )

        call = PhoneCall(
            call_id=call_id,
            from_number=from_num,
            to_number=to_number,
            direction=CallDirection.OUTBOUND,
            status=CallStatus.RINGING,
            provider="sip",
            started_at=datetime.now(tz=UTC),
            metadata={
                "sip_server": self.sip_server,
                "sip_port": self.sip_port,
                "sip_transport": self.sip_transport,
                **(metadata or {}),
            },
        )

        self._active_calls[call_id] = call
        return call

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up a SIP call.

        Args:
            call_id: SIP Call-ID.

        Returns:
            True if successful.
        """
        if call_id not in self._active_calls:
            logger.warning(f"Call {call_id} not found in active calls")
            return False

        # In production, this would send a SIP BYE
        logger.info(f"Sending SIP BYE for call {call_id}")

        call = self._active_calls[call_id]
        call.status = CallStatus.COMPLETED
        call.ended_at = datetime.now(tz=UTC)

        return True

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a SIP call.

        Args:
            call_id: SIP Call-ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop.

        Returns:
            True if successful.
        """
        if call_id not in self._active_calls:
            return False

        # In production, this would use RTP to stream audio
        # or use a media server like Asterisk/FreeSWITCH
        logger.info(f"Playing audio {audio_url} in call {call_id}")
        return True

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits via RTP.

        Args:
            call_id: SIP Call-ID.
            digits: DTMF digits.

        Returns:
            True if successful.
        """
        if call_id not in self._active_calls:
            return False

        # In production, this would send DTMF via RTP (RFC 2833)
        logger.info(f"Sending DTMF digits '{digits}' in call {call_id}")
        return True

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a SIP call.

        Args:
            call_id: SIP Call-ID.

        Returns:
            PhoneCall object or None.
        """
        return self._active_calls.get(call_id)

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a SIP call via RTP.

        Args:
            call_id: SIP Call-ID.
            audio_stream: Async iterator of audio chunks (PCM 16-bit, 8kHz).

        Returns:
            True if successful.
        """
        if call_id not in self._active_calls:
            return False

        # In production, this would stream audio via RTP
        logger.info(f"Streaming audio to call {call_id}")

        async for _chunk in audio_stream:
            # Send chunk via RTP
            pass

        return True

    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event.

        Returns:
            The webhook path.
        """
        paths = {
            "voice": "/telephony/sip/voice",
            "status": "/telephony/sip/status",
            "answer": "/telephony/sip/answer",
            "hangup": "/telephony/sip/hangup",
        }
        return paths.get(event_type, f"/telephony/sip/{event_type}")

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract transcript from SIP webhook data.

        Args:
            data: Parsed request data from the webhook.

        Returns:
            Extracted transcript string.
        """
        # Generic SIP providers use transcript or speech field
        return data.get("transcript", data.get("speech", ""))


@register_provider("gamma")
class GammaProvider(SIPProvider):
    """Gamma Telecom SIP trunking provider.

    Gamma Telecom is one of the UK's largest SIP trunking providers.
    This provider extends the base SIP provider with Gamma-specific
    configurations and features.

    Key features:
    - UK-wide coverage
    - High availability SIP trunking
    - Number portability
    - Emergency call support

    Documentation: https://www.gamma.co.uk/
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "gamma"

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate Gamma-specific webhook signature."""
        # Gamma uses a specific header for webhook validation
        gamma_signature = headers.get("X-Gamma-Signature", "")

        if not gamma_signature:
            # Fall back to base SIP validation
            return await super().validate_webhook(headers, body, path)

        # Validate Gamma signature
        secret = self.config.extra.get("webhook_secret", "")
        if not secret:
            return True

        expected = hmac.new(
            secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, gamma_signature)


@register_provider("bt")
class BTProvider(SIPProvider):
    """BT (British Telecom) SIP trunking provider.

    BT is the UK's incumbent telecommunications provider, offering
    SIP trunking services for businesses.

    Key features:
    - Extensive UK coverage
    - Integration with BT services
    - Enterprise-grade reliability

    Documentation: https://business.bt.com/
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "bt"

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate BT-specific webhook signature."""
        # BT uses OAuth-style tokens for webhook authentication
        auth_header = headers.get("Authorization", "")

        if not auth_header:
            return await super().validate_webhook(headers, body, path)

        # Validate Bearer token
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            expected_token = self.config.extra.get("webhook_token", "")
            return token == expected_token

        return False


@register_provider("virgin")
class VirginMediaProvider(SIPProvider):
    """Virgin Media Business SIP trunking provider.

    Virgin Media Business provides SIP trunking services in the UK.

    Documentation: https://www.virginmediabusiness.co.uk/
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "virgin"


@register_provider("talktalk")
class TalkTalkProvider(SIPProvider):
    """TalkTalk Business SIP trunking provider.

    TalkTalk Business provides SIP trunking services in the UK.

    Documentation: https://www.talktalkbusiness.co.uk/
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "talktalk"
