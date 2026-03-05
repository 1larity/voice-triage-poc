"""Zoom Phone webhook parsing utilities.

This module provides functions for parsing Zoom Phone webhook payloads.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)

logger = logging.getLogger(__name__)


# Mapping from Zoom Phone status to our CallStatus
ZOOM_STATUS_MAP: dict[str, CallStatus] = {
    "init": CallStatus.RINGING,
    "ringing": CallStatus.RINGING,
    "inProgress": CallStatus.IN_PROGRESS,
    "in_progress": CallStatus.IN_PROGRESS,
    "connected": CallStatus.IN_PROGRESS,
    "hold": CallStatus.IN_PROGRESS,
    "transferring": CallStatus.IN_PROGRESS,
    "disconnected": CallStatus.COMPLETED,
    "completed": CallStatus.COMPLETED,
    "missed": CallStatus.NO_ANSWER,
    "busy": CallStatus.BUSY,
    "noAnswer": CallStatus.NO_ANSWER,
    "no_answer": CallStatus.NO_ANSWER,
    "failed": CallStatus.FAILED,
    "canceled": CallStatus.CANCELED,
    "cancelled": CallStatus.CANCELED,
    "rejected": CallStatus.FAILED,
}


def validate_webhook_signature(
    body: bytes,
    signature: str,
    webhook_secret: str,
) -> bool:
    """Validate Zoom webhook signature.

    Zoom webhooks are signed with the webhook secret using HMAC-SHA256.

    Args:
        body: Raw request body bytes.
        signature: Signature from x-zm-signature header.
        webhook_secret: Webhook secret for validation.

    Returns:
        True if signature is valid.
    """
    if not signature or not webhook_secret:
        return False

    try:
        expected = "v0=" + hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)
    except Exception as exc:
        logger.warning(f"Failed to validate Zoom webhook: {exc}")
        return False


def parse_call_status(status_str: str) -> CallStatus:
    """Parse Zoom status string to CallStatus enum.

    Args:
        status_str: Zoom status string.

    Returns:
        CallStatus enum value.
    """
    return ZOOM_STATUS_MAP.get(status_str, CallStatus.RINGING)


def parse_phone_number(value: str | dict | None) -> str:
    """Extract phone number from Zoom format.

    Zoom may return phone numbers as strings or nested objects.

    Args:
        value: Phone number value from Zoom API.

    Returns:
        Phone number string.
    """
    if value is None:
        return ""
    if isinstance(value, dict):
        return value.get("phone_number", value.get("number", ""))
    return str(value)


def parse_timestamp(data: dict, *fields: str) -> datetime | None:
    """Parse timestamp from Zoom data.

    Args:
        data: Dictionary containing timestamp fields.
        *fields: Field names to try (in order).

    Returns:
        Parsed datetime or None.
    """
    for field in fields:
        if field in data:
            try:
                return datetime.fromisoformat(
                    data[field].replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass
    return None


def parse_inbound_call(
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
    # Parse JSON body
    try:
        data = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError:
        data = form_data

    # Extract call details from Zoom webhook format
    # Zoom Phone webhooks have event and payload structure
    event = data.get("event", "")
    payload = data.get("payload", data)

    # Get call details from payload
    call_data = payload.get("object", payload)

    call_id = call_data.get("call_id") or call_data.get("sessionId") or call_data.get("id", "")
    from_number = parse_phone_number(call_data.get("from") or call_data.get("caller_number"))
    to_number = parse_phone_number(call_data.get("to") or call_data.get("callee_number"))

    # Parse status
    status_str = call_data.get("status", "ringing")
    status = parse_call_status(status_str)

    # Parse direction
    direction_str = call_data.get("direction", "inbound")
    direction = (
        CallDirection.INBOUND
        if direction_str.lower() == "inbound"
        else CallDirection.OUTBOUND
    )

    # Parse timestamps
    started_at = parse_timestamp(call_data, "start_time", "startTime", "datetime", "timestamp")

    return PhoneCall(
        call_id=call_id,
        from_number=from_number,
        to_number=to_number,
        direction=direction,
        status=status,
        provider="zoom",
        started_at=started_at,
        metadata={
            "event_type": event,
            "call_type": call_data.get("call_type"),
            "site_id": call_data.get("site_id"),
            "original_data": call_data,
        },
    )


def parse_call_data(data: dict[str, Any]) -> PhoneCall:
    """Parse call data from Zoom API response.

    Args:
        data: Call data dictionary from Zoom API.

    Returns:
        PhoneCall object.
    """
    call_id = data.get("id", data.get("call_id", ""))
    from_number = parse_phone_number(data.get("from", {}))
    to_number = parse_phone_number(data.get("to", {}))

    status_str = data.get("status", "unknown")
    status = parse_call_status(status_str)

    direction_str = data.get("direction", "inbound")
    direction = (
        CallDirection.INBOUND
        if direction_str.lower() == "inbound"
        else CallDirection.OUTBOUND
    )

    started_at = parse_timestamp(data, "start_time", "startTime")

    return PhoneCall(
        call_id=call_id,
        from_number=from_number,
        to_number=to_number,
        direction=direction,
        status=status,
        provider="zoom",
        started_at=started_at,
        duration_seconds=data.get("duration"),
        metadata={"original_data": data},
    )
