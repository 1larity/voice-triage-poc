"""SIP webhook parsing utilities.

This module provides functions for parsing SIP trunking webhook payloads.
"""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)

# Mapping from SIP status codes to our CallStatus
SIP_STATUS_MAP: dict[int, CallStatus] = {
    100: CallStatus.RINGING,  # Trying
    180: CallStatus.RINGING,  # Ringing
    181: CallStatus.RINGING,  # Call Is Being Forwarded
    182: CallStatus.RINGING,  # Queued
    183: CallStatus.RINGING,  # Session Progress
    200: CallStatus.IN_PROGRESS,  # OK
    486: CallStatus.BUSY,  # Busy Here
    487: CallStatus.CANCELED,  # Request Terminated
    480: CallStatus.NO_ANSWER,  # Temporarily Unavailable
    484: CallStatus.FAILED,  # Address Incomplete
    500: CallStatus.FAILED,  # Server Internal Error
    503: CallStatus.FAILED,  # Service Unavailable
}


def parse_call_status(status_code: int | str) -> CallStatus:
    """Parse SIP status code to CallStatus enum.

    Args:
        status_code: SIP status code (100-503).

    Returns:
        CallStatus enum value.
    """
    if isinstance(status_code, int):
        return SIP_STATUS_MAP.get(status_code, CallStatus.RINGING)
    if isinstance(status_code, str):
        try:
            code = int(status_code)
            return SIP_STATUS_MAP.get(code, CallStatus.RINGING)
        except ValueError:
            return CallStatus.UNKNOWN
    return CallStatus.UNKNOWN


def extract_phone_from_sip_uri(uri: str) -> str:
    """Extract phone number from SIP URI.

    Args:
        uri: SIP URI like "sip:+441234567890@example.com"

    Returns:
        Phone number in E.164 format.
    """
    if not uri:
        return ""

    # Handle "Display Name" <sip:...> format
    if "<" in uri and ">" in uri:
        uri = uri.split("<")[1].split(">")[0]

    # Extract from sip: or sips: URI
    if "sip:" in uri.lower():
        uri = uri.lower().split("sip:")[1]
    elif "sips:" in uri.lower():
        uri = uri.lower().split("sips:")[1]

    # Remove domain part
    if "@" in uri:
        uri = uri.split("@")[0]

    # Remove any URL parameters
    if ";" in uri:
        uri = uri.split(";")[0]

    # Remove any query parameters
    if "?" in uri:
        uri = uri.split("?")[0]

    return uri.strip()


def parse_inbound_call(
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
    # Try JSON first, then form data
    try:
        data = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        data = form_data

    call_id = data.get("call_id", data.get("Call-ID", str(uuid.uuid4())))
    from_number = data.get("from", data.get("From", ""))
    to_number = data.get("to", data.get("To", ""))
    sip_status = data.get("status", data.get("sip_status", 180))

    # Parse phone numbers from SIP URIs
    from_number = extract_phone_from_sip_uri(from_number)
    to_number = extract_phone_from_sip_uri(to_number)

    # Parse status
    if isinstance(sip_status, int):
        status = SIP_STATUS_MAP.get(sip_status, CallStatus.RINGING)
    else:
        status = CallStatus.RINGING

    call = PhoneCall(
        call_id=call_id,
        from_number=from_number,
        to_number=to_number,
        direction=CallDirection.INBOUND,
        status=status,
        provider="sip",
        started_at=datetime.now(tz=UTC),
        metadata={
            "sip_call_id": call_id,
            "remote_ip": data.get("remote_ip"),
            "codec": data.get("codec", "PCMU"),
        },
    )

    return call


def parse_call_status_update(
    body: bytes,
) -> dict:
    """Parse a call status update webhook from SIP gateway.

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
        "call_id": data.get("call_id") or data.get("Call-ID"),
        "status": parse_call_status(data.get("status", data.get("sip_status", 180))),
        "duration": data.get("duration"),
        "ended_at": data.get("end_time") or data.get("ended_at"),
        "recording_url": data.get("recording_url"),
        "original_data": data,
    }
