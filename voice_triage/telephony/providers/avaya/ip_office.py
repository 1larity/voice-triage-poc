"""Avaya IP Office provider implementation.

This module provides the Avaya IP Office specific provider, which is
Avaya's small-to-medium business solution popular with smaller councils.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)
from voice_triage.telephony.providers.avaya.client import AvayaClient
from voice_triage.telephony.providers.avaya.provider import AvayaProvider
from voice_triage.telephony.registry import register_provider

logger = logging.getLogger(__name__)


@register_provider("avaya_ip_office")
class AvayaIPOfficeProvider(AvayaProvider):
    """Avaya IP Office specific provider.

    IP Office is Avaya's small-to-medium business solution, popular with
    smaller councils. Has a slightly different API structure.
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "avaya_ip_office"

    def _get_client(self) -> AvayaClient:
        """Get or create the Avaya IP Office client.

        Returns:
            AvayaClient instance configured for IP Office.
        """
        if self._client is None:
            extra = self.config.extra or {}
            self._client = AvayaClient(
                server_host=extra.get("server_host", "localhost"),
                server_port=extra.get("server_port", 9443),
                use_ssl=extra.get("use_ssl", True),
                username=extra.get("username", ""),
                password=extra.get("password", ""),
            )
        return self._client

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Make an outbound call through IP Office.

        IP Office uses a slightly different API structure.

        Args:
            to_number: Destination phone number.
            from_number: Caller ID (uses default if not provided).
            webhook_url: URL for call status webhooks.
            metadata: Optional metadata for the call.

        Returns:
            PhoneCall object representing the new call.
        """
        extra = self.config.extra or {}
        extension = (
            metadata.get("extension")
            if metadata
            else None or extra.get("extension") or "100"
        )

        caller_id = from_number or self.config.default_from_number or ""

        # IP Office specific call request
        call_data = {
            "extension": extension,
            "target": to_number,
            "callerId": caller_id,
        }

        client = self._get_client()
        try:
            response = await client.make_request(
                "POST",
                "/ipo/api/v1/calls",
                data=call_data,
            )
        except RuntimeError as e:
            logger.error(f"Failed to originate IP Office call: {e}")
            raise

        call_id = response.get("callId") or ""

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
                "raw_response": response,
            },
        )
