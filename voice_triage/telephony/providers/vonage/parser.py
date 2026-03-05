"""Vonage webhook parsing utilities.

This module provides functions for parsing Vonage webhook payloads
and converting them to standardized PhoneCall objects.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)

logger = logging.getLogger(__name__)

# Mapping from Vonage status to our CallStatus
VONAGE_STATUS_MAP: dict[str, CallStatus] = {
    "started": CallStatus.RINGING,
    "ringing": CallStatus.RINGING,
    "answered": CallStatus.IN_PROGRESS,
    "in-progress": CallStatus.IN_PROGRESS,
    "completed": CallStatus.COMPLETED,
    "failed": CallStatus.FAILED,
    "busy": CallStatus.BUSY,
    "no-answer": CallStatus.NO_ANSWER,
    "cancelled": CallStatus.CANCELED,
    "rejected": CallStatus.FAILED,
    "timeout": CallStatus.NO_ANSWER,
}


def parse_vonage_time(time_str: str | None) -> datetime | None:
    """Parse Vonage timestamp string.

    Args:
        time_str: ISO 8601 timestamp string.

    Returns:
        Parsed datetime or None.
    """
    if not time_str:
        return None
    try:
        # Vonage uses ISO 8601 format
        return datetime.fromisoformat(time_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def parse_inbound_call(
    body: bytes,
    form_data: dict[str, str],
) -> PhoneCall:
    """Parse an inbound call from Vonage webhook.

    Args:
        body: Raw request body.
        form_data: Parsed form/JSON data from Vonage.

    Returns:
        PhoneCall object.
    """
    # Vonage sends JSON for voice webhooks
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = form_data

    uuid = data.get("uuid", data.get("conversation_uuid", ""))
    from_number = data.get("from", "")
    to_number = data.get("to", "")
    call_status = data.get("status", "ringing")
    direction = data.get("direction", "inbound")

    # Parse direction
    if "inbound" in direction.lower():
        call_direction = CallDirection.INBOUND
    else:
        call_direction = CallDirection.OUTBOUND

    # Parse status
    status = VONAGE_STATUS_MAP.get(call_status.lower(), CallStatus.RINGING)

    return PhoneCall(
        call_id=uuid,
        from_number=from_number,
        to_number=to_number,
        direction=call_direction,
        status=status,
        provider="vonage",
        started_at=datetime.now(tz=UTC),
        metadata={
            "conversation_uuid": data.get("conversation_uuid"),
            "network": data.get("network"),
            "call_duration": data.get("duration"),
        },
    )


def validate_vonage_signature(
    signature: str,
    body: bytes,
    api_secret: str,
) -> bool:
    """Validate Vonage webhook signature.

    Vonage uses HMAC-SHA512 for signature validation.

    Args:
        signature: Signature from X-Vonage-Signature header.
        body: Raw request body.
        api_secret: Vonage API secret.

    Returns:
        True if signature is valid.
    """
    try:
        expected = hmac.new(
            api_secret.encode("utf-8"),
            body,
            hashlib.sha512,
        ).hexdigest()

        return hmac.compare_digest(expected, signature.lower())
    except Exception as exc:
        logger.warning(f"Failed to validate Vonage signature: {exc}")
        return False


def parse_call_status_response(
    call_detail: dict[str, Any],
    call_id: str,
) -> PhoneCall:
    """Parse call status response from Vonage API.

    Args:
        call_detail: Call details from Vonage API.
        call_id: Call UUID.

    Returns:
        PhoneCall object.
    """
    return PhoneCall(
        call_id=call_detail.get("uuid", call_id),
        from_number=call_detail.get("from", ""),
        to_number=call_detail.get("to", ""),
        direction=CallDirection.OUTBOUND
        if call_detail.get("direction") == "outbound"
        else CallDirection.INBOUND,
        status=VONAGE_STATUS_MAP.get(
            call_detail.get("status", ""), CallStatus.RINGING
        ),
        provider="vonage",
        started_at=parse_vonage_time(call_detail.get("start_time")),
        ended_at=parse_vonage_time(call_detail.get("end_time")),
        duration_seconds=int(call_detail.get("duration", 0) or 0),
        recording_url=call_detail.get("recording_url"),
    )
