"""CircleLoop webhook parsing utilities.

This module provides functions for parsing CircleLoop webhook payloads.
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

# Mapping from CircleLoop status to our CallStatus
CIRCLELOOP_STATUS_MAP: dict[str, CallStatus] = {
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
}


def parse_call_status(status_str: str) -> CallStatus:
    """Parse CircleLoop call status string to CallStatus enum.

    Args:
        status_str: Status string from CircleLoop webhook.

    Returns:
        CallStatus enum value.
    """
    return CIRCLELOOP_STATUS_MAP.get(status_str.lower(), CallStatus.UNKNOWN)


def parse_direction(direction_str: str) -> CallDirection:
    """Parse CircleLoop direction string to CallDirection enum.

    Args:
        direction_str: Direction string from CircleLoop webhook.

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
    """Parse an inbound call from CircleLoop webhook.

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

    # Extract call details from CircleLoop webhook format
    call_id = data.get("call_id") or data.get("CallID") or data.get("id", str(uuid.uuid4()))
    from_number = data.get("from") or data.get("caller_id") or data.get("From", "")
    to_number = data.get("to") or data.get("called_number") or data.get("To", "")

    # Handle nested phone number format
    if isinstance(from_number, dict):
        from_number = from_number.get("number", from_number.get("phone_number", ""))
    if isinstance(to_number, dict):
        to_number = to_number.get("number", to_number.get("phone_number", ""))

    # Parse status
    status_str = data.get("status", data.get("call_status", "ringing"))
    status = parse_call_status(status_str)

    # Parse direction
    direction_str = data.get("direction", data.get("type", "inbound"))
    direction = parse_direction(direction_str)

    # Parse timestamps
    started_at = None
    timestamp_fields = ["timestamp", "start_time", "startTime", "created", "datetime"]
    for field in timestamp_fields:
        if field in data:
            try:
                started_at = datetime.fromisoformat(
                    data[field].replace("Z", "+00:00")
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
        provider="circleloop",
        started_at=started_at,
        metadata={
            "original_data": data,
        },
    )


def parse_call_status_update(
    body: bytes,
) -> dict:
    """Parse a call status update webhook from CircleLoop.

    Args:
        body: Raw request body.

    Returns:
        Dictionary with call status update data.
    """
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}

    return {
        "call_id": data.get("call_id") or data.get("id"),
        "status": parse_call_status(data.get("status", "unknown")),
        "duration": data.get("duration"),
        "ended_at": data.get("end_time") or data.get("ended_at"),
        "recording_url": data.get("recording_url"),
        "original_data": data,
    }
