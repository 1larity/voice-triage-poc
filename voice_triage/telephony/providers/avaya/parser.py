"""Avaya webhook parsing utilities.

This module provides functions for parsing Avaya webhook payloads
and converting them to standardized PhoneCall objects.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
from datetime import UTC, datetime

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)

logger = logging.getLogger(__name__)

# Mapping from Avaya status to our CallStatus
AVAYA_STATUS_MAP: dict[str, CallStatus] = {
    # TSAPI/DMCC states
    "idle": CallStatus.IDLE,
    "seized": CallStatus.RINGING,
    "alerting": CallStatus.RINGING,
    "dialing": CallStatus.DIALING,
    "connecting": CallStatus.DIALING,
    "connected": CallStatus.IN_PROGRESS,
    "held": CallStatus.HELD,
    "conferenced": CallStatus.IN_PROGRESS,
    "transferred": CallStatus.IN_PROGRESS,
    "dropped": CallStatus.COMPLETED,
    "failed": CallStatus.FAILED,
    "busy": CallStatus.BUSY,
    "no_answer": CallStatus.NO_ANSWER,
    "network_congestion": CallStatus.FAILED,
    "network_out_of_order": CallStatus.FAILED,
    # Avaya Experience Portal states
    "queued": CallStatus.QUEUED,
    "routing": CallStatus.RINGING,
    "talking": CallStatus.IN_PROGRESS,
    "wrapup": CallStatus.COMPLETED,
    "abandoned": CallStatus.NO_ANSWER,
    # Generic states
    "active": CallStatus.IN_PROGRESS,
    "terminated": CallStatus.COMPLETED,
    "cancelled": CallStatus.CANCELED,
}


def parse_inbound_call(
    body: bytes,
    form_data: dict[str, str],
) -> PhoneCall:
    """Parse an inbound call from Avaya webhook data.

    Avaya webhook payload format (typical):
    {
        "event": "call_initiated",
        "callId": "12345678",
        "callingNumber": "07123456789",
        "calledNumber": "02071234567",
        "extension": "5001",
        "timestamp": "2024-01-15T10:30:00Z"
    }

    Args:
        body: Raw request body.
        form_data: Parsed form data (unused for Avaya, uses JSON).

    Returns:
        PhoneCall object if valid.

    Raises:
        ValueError: If call data is invalid.
    """
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        logger.error("Failed to parse Avaya webhook body as JSON")
        raise ValueError(f"Invalid JSON in webhook body: {e}") from e

    # Extract call details
    call_id = data.get("callId") or data.get("call_id") or data.get("ucid")
    if not call_id:
        logger.warning("Avaya webhook missing call ID")
        raise ValueError("Missing call ID in webhook data")

    # Get phone numbers
    from_number = (
        data.get("callingNumber")
        or data.get("calling_number")
        or data.get("ani")
        or data.get("from")
        or "unknown"
    )
    to_number = (
        data.get("calledNumber")
        or data.get("called_number")
        or data.get("dnis")
        or data.get("to")
        or "unknown"
    )

    # Determine direction
    event_type = data.get("event", "").lower()
    direction = CallDirection.INBOUND
    if "outbound" in event_type or "originated" in event_type:
        direction = CallDirection.OUTBOUND

    # Map status
    avaya_status = (
        data.get("state")
        or data.get("status")
        or data.get("callState")
        or "alerting"
    )
    status = AVAYA_STATUS_MAP.get(avaya_status.lower(), CallStatus.RINGING)

    # Parse timestamp
    timestamp_str = data.get("timestamp") or data.get("time")
    if timestamp_str:
        try:
            timestamp = datetime.fromisoformat(
                timestamp_str.replace("Z", "+00:00")
            )
        except ValueError:
            timestamp = datetime.now(UTC)
    else:
        timestamp = datetime.now(UTC)

    return PhoneCall(
        call_id=str(call_id),
        from_number=from_number,
        to_number=to_number,
        direction=direction,
        status=status,
        provider="avaya",
        started_at=timestamp,
        metadata={
            "extension": data.get("extension"),
            "queue": data.get("queue") or data.get("split"),
            "agent": data.get("agent") or data.get("agentId"),
            "ucid": data.get("ucid"),  # Universal Call ID
            "event_type": event_type,
            "raw_data": data,
        },
    )


def validate_avaya_signature(
    signature: str,
    body: bytes,
    webhook_secret: str,
) -> bool:
    """Validate Avaya webhook signature.

    Avaya webhooks can be signed using HMAC-SHA256.

    Args:
        signature: Signature from X-Avaya-Signature header.
        body: Raw request body.
        webhook_secret: Shared secret for signature.

    Returns:
        True if signature is valid.
    """
    if not signature or not webhook_secret:
        return False

    try:
        expected = hmac.new(
            webhook_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)
    except Exception as exc:
        logger.warning(f"Failed to validate Avaya signature: {exc}")
        return False


def validate_basic_auth(
    auth_header: str,
    expected_username: str,
    expected_password: str,
) -> bool:
    """Validate HTTP Basic authentication.

    Args:
        auth_header: Authorization header value.
        expected_username: Expected username.
        expected_password: Expected password.

    Returns:
            True if credentials are valid.
    """
    if not auth_header or not auth_header.startswith("Basic "):
        return False

    try:
        encoded_credentials = auth_header[6:]
        decoded = base64.b64decode(encoded_credentials).decode("utf-8")
        username, password = decoded.split(":", 1)

        return username == expected_username and password == expected_password
    except (ValueError, UnicodeDecodeError):
        return False
