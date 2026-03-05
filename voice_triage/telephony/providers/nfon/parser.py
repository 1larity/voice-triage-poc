"""NFON webhook parsing utilities.

This module provides parsing functions for NFON webhook payloads.
"""

from __future__ import annotations

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

# Mapping from NFON status to our CallStatus
NFON_STATUS_MAP: dict[str, CallStatus] = {
    "initiating": CallStatus.RINGING,
    "ringing": CallStatus.RINGING,
    "dialing": CallStatus.RINGING,
    "proceeding": CallStatus.RINGING,
    "connected": CallStatus.IN_PROGRESS,
    "inprogress": CallStatus.IN_PROGRESS,
    "in_progress": CallStatus.IN_PROGRESS,
    "active": CallStatus.IN_PROGRESS,
    "onhold": CallStatus.IN_PROGRESS,
    "transferring": CallStatus.IN_PROGRESS,
    "completed": CallStatus.COMPLETED,
    "disconnected": CallStatus.COMPLETED,
    "terminated": CallStatus.COMPLETED,
    "ended": CallStatus.COMPLETED,
    "missed": CallStatus.NO_ANSWER,
    "noanswer": CallStatus.NO_ANSWER,
    "no_answer": CallStatus.NO_ANSWER,
    "busy": CallStatus.BUSY,
    "congestion": CallStatus.BUSY,
    "failed": CallStatus.FAILED,
    "cancelled": CallStatus.CANCELED,
    "canceled": CallStatus.CANCELED,
    "rejected": CallStatus.FAILED,
    "unavailable": CallStatus.FAILED,
}


def parse_inbound_call(
    headers: dict[str, str],
    body: bytes,
    form_data: dict[str, str],
) -> PhoneCall:
    """Parse an inbound call webhook from NFON.

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
        # Fall back to form data
        data = form_data

    # Extract call details from NFON webhook format
    call_data = data.get("call", data)
    call_id = (
        call_data.get("callId") or
        call_data.get("id") or
        form_data.get("callId", "")
    )
    from_number = (
        call_data.get("from") or
        call_data.get("callerId") or
        call_data.get("caller_number") or
        form_data.get("from", "")
    )
    to_number = (
        call_data.get("to") or
        call_data.get("calledNumber") or
        call_data.get("destination") or
        call_data.get("callee_number") or
        form_data.get("to", "")
    )

    # Handle nested phone number format
    if isinstance(from_number, dict):
        from_number = from_number.get("number", "")
    if isinstance(to_number, dict):
        to_number = to_number.get("number", "")

    # Parse status
    status_str = call_data.get("status") or call_data.get("state", "ringing")
    status = NFON_STATUS_MAP.get(status_str.lower(), CallStatus.RINGING)

    # Parse direction
    direction_str = call_data.get("direction") or call_data.get("type", "inbound")
    direction = CallDirection.INBOUND
    if direction_str.lower() in ("outbound", "outgoing"):
        direction = CallDirection.OUTBOUND

    # Parse timestamps
    started_at = None
    timestamp_fields = ["startTime", "start_time", "created", "timestamp"]
    for field in timestamp_fields:
        if field in call_data:
            try:
                started_at = datetime.fromisoformat(
                    call_data[field].replace("Z", "+00:00")
                )
                break
            except (ValueError, TypeError):
                pass

    return PhoneCall(
        call_id=call_id,
        from_number=from_number,
        to_number=to_number,
        direction=direction,
        status=status,
        provider="nfon",
        started_at=started_at,
        metadata={
            "tenant_id": call_data.get("tenantId"),
            "extension_id": call_data.get("extensionId"),
            "call_type": call_data.get("callType"),
            "recording_url": call_data.get("recordingUrl"),
            "original_data": call_data,
        },
    )


def parse_call_status_data(
    data: dict[str, Any],
) -> PhoneCall:
    """Parse call status response from NFON API.

    Args:
        data: Response data from NFON API.

    Returns:
        A PhoneCall object with updated status.
    """
    call_id = data.get("callId") or data.get("id")
    if not call_id:
        raise ValueError("No call ID in NFON response")

    # Parse call details
    from_number = ""
    to_number = ""

    for party in data.get("parties", []):
        from_data = party.get("from", {})
        if isinstance(from_data, dict):
            from_number = from_data.get("phoneNumber", "")
        to_data = party.get("to", {})
        if isinstance(to_data, dict):
            to_number = to_data.get("phoneNumber", "")
        elif isinstance(to_data, list) and to_data:
            to_number = to_data[0].get("phoneNumber", "")

    status_str = data.get("status", "unknown")
    status = NFON_STATUS_MAP.get(status_str.lower(), CallStatus.RINGING)

    # Parse direction
    direction_str = data.get("direction") or data.get("type", "inbound")
    direction = CallDirection.INBOUND
    if direction_str.lower() in ("outbound", "outgoing"):
        direction = CallDirection.OUTBOUND

    # Parse timestamps
    started_at = None
    timestamp_fields = ["startTime", "start_time", "created", "timestamp"]
    for field in timestamp_fields:
        if field in data:
            try:
                started_at = datetime.fromisoformat(
                    data[field].replace("Z", "+00:00")
                )
                break
            except (ValueError, TypeError):
                pass

    return PhoneCall(
        call_id=call_id,
        from_number=from_number,
        to_number=to_number,
        direction=direction,
        status=status,
        provider="nfon",
        started_at=started_at,
        metadata={
            "tenant_id": data.get("tenantId"),
            "extension_id": data.get("extensionId"),
            "call_type": data.get("callType"),
            "recording_url": data.get("recordingUrl"),
            "original_data": data,
        },
    )


def validate_nfon_signature(
    body: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Validate NFON webhook signature.

    Args:
        body: Raw request body.
        signature: X-NFON-Signature header value.
        secret: Webhook secret.

    Returns:
        True if signature is valid.
    """
    import hashlib
    import hmac

    expected = hmac.new(
        secret.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, signature.lower())
