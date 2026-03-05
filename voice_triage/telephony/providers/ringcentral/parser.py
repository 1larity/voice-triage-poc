"""RingCentral webhook parsing utilities.

This module provides functions for parsing RingCentral webhook payloads.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)

# Mapping from RingCentral status to our CallStatus
RINGCENTRAL_STATUS_MAP: dict[str, CallStatus] = {
    "queued": CallStatus.RINGING,
    "ringing": CallStatus.RINGING,
    "in-progress": CallStatus.IN_PROGRESS,
    "in_progress": CallStatus.IN_PROGRESS,
    "connected": CallStatus.IN_PROGRESS,
    "busy": CallStatus.BUSY,
    "failed": CallStatus.FAILED,
    "noanswer": CallStatus.NO_ANSWER,
    "no-answer": CallStatus.NO_ANSWER,
    "canceled": CallStatus.CANCELED,
    "cancelled": CallStatus.CANCELED,
    "completed": CallStatus.COMPLETED,
    "disconnected": CallStatus.COMPLETED,
    "unknown": CallStatus.UNKNOWN,
}


def parse_call_status(status_str: str) -> CallStatus:
    """Parse RingCentral call status string to CallStatus enum.

    Args:
        status_str: Status string from RingCentral webhook.

    Returns:
        CallStatus enum value.
    """
    return RINGCENTRAL_STATUS_MAP.get(status_str.lower(), CallStatus.UNKNOWN)


def parse_direction(direction_str: str) -> CallDirection:
    """Parse RingCentral direction string to CallDirection enum.

    Args:
        direction_str: Direction string from RingCentral webhook.

    Returns:
        CallDirection enum value.
    """
    direction_lower = direction_str.lower()
    if direction_lower in ("outbound", "outgoing"):
        return CallDirection.OUTBOUND
    return CallDirection.INBOUND


def parse_inbound_call(
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
    # Try JSON first, then fall back to form data
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = form_data

    # Extract call details from RingCentral webhook format
    # RingCentral webhooks have a body property with call details
    body_data = data.get("body", data)

    call_id = (
        body_data.get("id")
        or body_data.get("sessionId")
        or body_data.get("call_id", str(uuid.uuid4()))
    )
    
    # Extract phone numbers
    from_number = ""
    to_number = ""
    
    # RingCentral format: from/to can be objects with phoneNumber
    from_data = body_data.get("from", {})
    if isinstance(from_data, dict):
        from_number = from_data.get("phoneNumber", from_data.get("number", ""))
    elif isinstance(from_data, str):
        from_number = from_data

    to_data = body_data.get("to", [])
    if isinstance(to_data, list) and to_data:
        first_to = to_data[0]
        if isinstance(first_to, dict):
            to_number = first_to.get("phoneNumber", first_to.get("number", ""))
        elif isinstance(first_to, str):
            to_number = first_to
    elif isinstance(to_data, dict):
        to_number = to_data.get("phoneNumber", to_data.get("number", ""))
    elif isinstance(to_data, str):
        to_number = to_data

    # Parse status
    status_str = body_data.get("status", body_data.get("callStatus", "ringing"))
    status = parse_call_status(status_str)

    # Parse direction
    direction_str = body_data.get("direction", body_data.get("type", "inbound"))
    direction = parse_direction(direction_str)

    # Parse timestamps
    started_at = None
    timestamp_fields = ["startTime", "start_time", "created", "timestamp", "datetime"]
    for field in timestamp_fields:
        if field in body_data:
            try:
                started_at = datetime.fromisoformat(
                    body_data[field].replace("Z", "+00:00")
                )
                break
            except (ValueError, TypeError, AttributeError):
                pass

    return PhoneCall(
        call_id=call_id,
        from_number=from_number,
        to_number=to_number,
        direction=direction,
        status=status,
        provider="ringcentral",
        started_at=started_at,
        metadata={
            "event_type": data.get("event"),
            "original_data": data,
        },
    )


def parse_call_status_update(
    body: bytes,
) -> dict:
    """Parse a call status update webhook from RingCentral.

    Args:
        body: Raw request body.

    Returns:
        Dictionary with call status update data.
    """
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}

    body_data = data.get("body", data)

    return {
        "call_id": body_data.get("id") or body_data.get("sessionId"),
        "status": parse_call_status(body_data.get("status", "unknown")),
        "duration": body_data.get("duration"),
        "ended_at": body_data.get("endTime") or body_data.get("ended_at"),
        "recording_url": body_data.get("recording") or body_data.get("recording_url"),
        "original_data": data,
    }
