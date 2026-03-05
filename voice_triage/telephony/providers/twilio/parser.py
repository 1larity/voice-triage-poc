"""Twilio webhook parsing utilities.

This module provides parsing utilities for Twilio webhooks.
"""

from __future__ import annotations

from datetime import UTC, datetime

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)

# Mapping from Twilio status to our CallStatus
TWILIO_STATUS_MAP: dict[str, CallStatus] = {
    "queued": CallStatus.RINGING,
    "ringing": CallStatus.RINGING,
    "in-progress": CallStatus.IN_PROGRESS,
    "completed": CallStatus.COMPLETED,
    "failed": CallStatus.FAILED,
    "busy": CallStatus.BUSY,
    "no-answer": CallStatus.NO_ANSWER,
    "canceled": CallStatus.CANCELED,
}


def parse_direction(direction_str: str) -> CallDirection:
    """Parse Twilio direction string.

    Args:
        direction_str: Direction string from Twilio.

    Returns:
        CallDirection enum value.
    """
    direction_lower = direction_str.lower()
    if "inbound" in direction_lower:
        return CallDirection.INBOUND
    return CallDirection.OUTBOUND


def parse_call_status(status_str: str) -> CallStatus:
    """Parse Twilio call status string.

    Args:
        status_str: Status string from Twilio.

    Returns:
        CallStatus enum value.
    """
    return TWILIO_STATUS_MAP.get(status_str.lower(), CallStatus.RINGING)


def parse_inbound_call(form_data: dict[str, str]) -> PhoneCall:
    """Parse an inbound call from Twilio webhook data.

    Args:
        form_data: Parsed form data from Twilio.

    Returns:
        PhoneCall object representing the inbound call.
    """
    call_sid = form_data.get("CallSid", "")
    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    call_status = form_data.get("CallStatus", "ringing")
    direction_str = form_data.get("Direction", "inbound")

    # Parse direction
    call_direction = parse_direction(direction_str)

    # Parse status
    status = parse_call_status(call_status)

    return PhoneCall(
        call_id=call_sid,
        from_number=from_number,
        to_number=to_number,
        direction=call_direction,
        status=status,
        provider="twilio",
        started_at=datetime.now(tz=UTC),
        metadata={
            "account_sid": form_data.get("AccountSid"),
            "api_version": form_data.get("ApiVersion"),
            "forwarded_from": form_data.get("ForwardedFrom"),
            "caller_name": form_data.get("CallerName"),
        },
    )


def parse_call_status_response(form_data: dict[str, str]) -> PhoneCall | None:
    """Parse call status from Twilio status callback webhook.

    Args:
        form_data: Parsed form data from Twilio status callback.

    Returns:
        PhoneCall object or None if parsing fails.
    """
    call_sid = form_data.get("CallSid")
    if not call_sid:
        return None

    from_number = form_data.get("From", "")
    to_number = form_data.get("To", "")
    call_status = form_data.get("CallStatus", "ringing")
    call_duration = form_data.get("CallDuration", "0")

    # Parse timestamps
    started_at = None
    ended_at = None
    timestamp_str = form_data.get("Timestamp")
    if timestamp_str:
        try:
            started_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            pass

    # Parse duration
    duration_seconds = 0
    try:
        duration_seconds = int(call_duration)
    except (ValueError, TypeError):
        pass

    status = parse_call_status(call_status)

    return PhoneCall(
        call_id=call_sid,
        from_number=from_number,
        to_number=to_number,
        direction=CallDirection.OUTBOUND,
        status=status,
        provider="twilio",
        started_at=started_at,
        ended_at=ended_at,
        duration_seconds=duration_seconds,
        metadata={"original_data": form_data},
    )
