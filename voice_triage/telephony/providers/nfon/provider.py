"""NFON telephony provider implementation."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from voice_triage.telephony.base import (
    PhoneCall,
    TelephonyConfig,
    TelephonyProvider,
)
from voice_triage.telephony.providers.nfon.client import NFONClient
from voice_triage.telephony.providers.nfon.parser import (
    parse_inbound_call,
    validate_nfon_signature,
)
from voice_triage.telephony.registry import register_provider
from voice_triage.telephony.shared.auth import get_header

logger = logging.getLogger(__name__)


@register_provider("nfon")
class NFONProvider(TelephonyProvider):
    """NFON cloud PBX telephony provider."""

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize NFON provider."""
        super().__init__(config)
        self._client = NFONClient(config)

    @property
    def name(self) -> str:
        """Return provider name."""
        return "nfon"

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate NFON webhook signature."""
        del path
        signature = get_header(headers, "X-NFON-Signature")
        if not signature:
            logger.warning("Missing NFON webhook signature")
            return False

        webhook_secret = self.config.extra.get("webhook_secret") or self.config.webhook_secret
        if not webhook_secret:
            logger.warning("No webhook_secret configured for NFON webhook validation")
            return False

        return validate_nfon_signature(body, signature, webhook_secret)

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse inbound call payload."""
        return parse_inbound_call(headers, body, form_data)

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate NFON call-control response payload."""
        response: dict[str, Any] = {
            "sessionId": session_id,
            "actions": [],
        }
        if welcome_message:
            response["actions"].append({
                "action": "speak",
                "text": welcome_message,
                "language": "en-GB",
            })
        if gather_speech and action_url:
            response["actions"].append({
                "action": "gather",
                "input": "speech",
                "actionUrl": action_url,
                "language": "en-GB",
                "timeout": 5,
            })
        return json.dumps(response)

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Make outbound call."""
        return await self._client.make_outbound_call(
            to_number=to_number,
            from_number=from_number,
            webhook_url=webhook_url,
            metadata=metadata,
        )

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active call."""
        return await self._client.hangup_call(call_id)

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a call."""
        return await self._client.play_audio(call_id, audio_url, loop)

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits."""
        return await self._client.send_digits(call_id, digits)

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get call status."""
        return await self._client.get_call_status(call_id)

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio in real time."""
        return await self._client.stream_audio(call_id, audio_stream)

    def get_webhook_path(self, event_type: str) -> str:
        """Get webhook path for NFON event type."""
        return self._client.get_webhook_path(event_type)

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract speech transcript from webhook payload."""
        speech = data.get("speechResult") or data.get("speech")
        if isinstance(speech, dict):
            return speech.get("text", "")
        if isinstance(speech, str):
            return speech
        return data.get("transcript", "")

    def get_response_content_type(self) -> str:
        """Return response content type for NFON call-control payloads."""
        return "application/json"
