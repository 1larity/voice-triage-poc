"""Microsoft Teams Direct Routing parsing utilities.

This module provides parsing functions for Microsoft Teams
webhook notifications and call data.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
)

logger = logging.getLogger(__name__)

# Mapping from Teams status to our CallStatus
TEAMS_STATUS_MAP: dict[str, CallStatus] = {
    "connecting": CallStatus.RINGING,
    "ringing": CallStatus.RINGING,
    "earlymedia": CallStatus.RINGING,
    "connected": CallStatus.IN_PROGRESS,
    "inprogress": CallStatus.IN_PROGRESS,
    "in_progress": CallStatus.IN_PROGRESS,
    "onhold": CallStatus.IN_PROGRESS,
    "transferring": CallStatus.IN_PROGRESS,
    "disconnected": CallStatus.COMPLETED,
    "completed": CallStatus.COMPLETED,
    "terminated": CallStatus.COMPLETED,
    "missed": CallStatus.NO_ANSWER,
    "busy": CallStatus.BUSY,
    "noanswer": CallStatus.NO_ANSWER,
    "no_answer": CallStatus.NO_ANSWER,
    "failed": CallStatus.FAILED,
    "cancelled": CallStatus.CANCELED,
    "canceled": CallStatus.CANCELED,
    "rejected": CallStatus.FAILED,
}


def _get_phone_from_data(data: dict[str, Any] | None) -> str | None:
    """Extract phone number from data structure.

    Args:
        data: Data structure that may contain phone info.

    Returns:
        Phone number string or None.
    """
    if data is None:
        return None
    if "phoneNumber" in data:
        return data["phoneNumber"]
    if "identity" in data:
        phone_data = data["identity"].get("phone", {})
        return phone_data.get("id", "")
    return None


def parse_inbound_call(
    headers: dict[str, str],
    body: bytes,
    form_data: dict[str, str],
) -> PhoneCall:
    """Parse an inbound call webhook from Microsoft Teams.

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

    # Extract call details from Microsoft Graph notification format
    # Graph webhooks have value array with notifications
    notifications = data.get("value", [data]) if isinstance(data, dict) else [data]
    notification = notifications[0] if notifications else {}

    # Get the data
    resource_data = notification.get("resourceData", notification)

    call_id = (
        resource_data.get("id")
        or resource_data.get("callId")
        or resource_data.get("@odata.id", "").split("/")[-1]
        or str(uuid.uuid4())
    )

    # Extract the numbers
    from_number = _get_phone_from_data(resource_data.get("from", {}))
    to_number = _get_phone_from_data(resource_data.get("to", {}))

    # Handle different notification formats
    if "from" in resource_data:
        from_data = resource_data["from"]
        if isinstance(from_data, dict):
            extracted = _get_phone_from_data(from_data)
            if extracted:
                from_number = extracted

    if "to" in resource_data:
        to_data = resource_data["to"]
        if isinstance(to_data, list) and to_data:
            extracted = _get_phone_from_data(to_data[0])
            if extracted:
                to_number = extracted
        elif isinstance(to_data, dict):
            to_number = to_data.get("phoneNumber", "")

    # Parse status
    status_str = resource_data.get("state") or resource_data.get("status", "ringing")
    status = TEAMS_STATUS_MAP.get(status_str.lower(), CallStatus.RINGING)

    # Parse direction
    direction_str = resource_data.get("direction", "incoming")
    is_inbound = direction_str.lower() in ("incoming", "inbound")
    direction = CallDirection.INBOUND if is_inbound else CallDirection.OUTBOUND

    # Parse timestamps
    started_at = None
    if "creationDateTime" in resource_data:
        try:
            started_at = datetime.fromisoformat(
                resource_data["creationDateTime"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    return PhoneCall(
        call_id=call_id,
        from_number=from_number or "",
        to_number=to_number or "",
        direction=direction,
        status=status,
        provider="teams",
        started_at=started_at,
        metadata={
            "subscription_id": notification.get("subscriptionId"),
            "change_type": notification.get("changeType"),
            "resource": notification.get("resource"),
            "tenant_id": notification.get("tenantId"),
            "original_data": resource_data,
        },
    )


def parse_call_status_data(data: dict[str, Any]) -> PhoneCall | None:
    """Parse call status data from Microsoft Graph API response.

    Args:
        data: Parsed JSON data from Graph API.

    Returns:
        PhoneCall object if successful, None otherwise.
    """
    # Parse call details
    from_number = _get_phone_from_data(data.get("source", {}))

    targets = data.get("targets", [])
    to_number = ""
    if targets:
        phone_data = targets[0].get("identity", {}).get("phone", {})
        to_number = phone_data.get("id", "")

    status_str = data.get("state", "unknown")
    status = TEAMS_STATUS_MAP.get(status_str.lower(), CallStatus.RINGING)

    direction_str = data.get("direction", "incoming")
    is_incoming = direction_str.lower() == "incoming"
    direction = CallDirection.INBOUND if is_incoming else CallDirection.OUTBOUND

    # Parse timestamps
    started_at = None
    if "creationDateTime" in data:
        try:
            started_at = datetime.fromisoformat(
                data["creationDateTime"].replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            pass

    call_id = data.get("id", "")

    return PhoneCall(
        call_id=call_id,
        from_number=from_number or "",
        to_number=to_number,
        direction=direction,
        status=status,
        provider="teams",
        started_at=started_at,
        metadata={"original_data": data},
    )


def generate_teams_response(
    session_id: str,
    welcome_message: str | None = None,
    gather_speech: bool = True,
    action_url: str | None = None,
    speech_timeout: int = 5,
) -> str:
    """Generate a Microsoft Teams call control response.

    Microsoft Teams uses the Cloud Communications API which handles
    call control through API calls rather than markup responses.
    This method returns a JSON structure for reference.

    Args:
        session_id: Session ID for this conversation.
        welcome_message: Optional welcome message to play.
        gather_speech: Whether to gather speech input.
        action_url: URL to post gathered input to.
        speech_timeout: Timeout for speech gathering in seconds.

    Returns:
        JSON response describing the call flow.
    """
    # Microsoft Teams uses API-based call control
    # This JSON structure is for documentation/reference
    response: dict[str, Any] = {
        "session_id": session_id,
        "actions": list[dict[str, Any]],
    }

    if welcome_message:
        prompt_action: dict[str, Any] = {
            "type": "playPrompt",
            "prompts": [{
                "@odata.type": "#microsoft.graph.mediaPrompt",
                "mediaInfo": {
                    "uri": "about:blank",
                    "resourceId": str(uuid.uuid4()),
                },
            }],
            "text": welcome_message,
            "language": "en-GB",
        }
        response["actions"].append(prompt_action)

    if gather_speech and action_url:
        record_action: dict[str, Any] = {
            "type": "recordResponse",
            "callbackUri": action_url,
            "initialSilenceTimeoutInSeconds": speech_timeout,
            "language": "en-GB",
        }
        response["actions"].append(record_action)

    return json.dumps(response)


def get_webhook_paths() -> dict[str, str]:
    """Get the webhook paths for Microsoft Teams.

    Returns:
        Dictionary mapping event types to webhook paths.
    """
    return {
        "voice": "/telephony/teams/voice",
        "status": "/telephony/teams/status",
        "callback": "/telephony/teams/callback",
        "notification": "/telephony/teams/notification",
    }
