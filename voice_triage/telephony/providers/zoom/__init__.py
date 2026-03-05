"""Zoom Phone telephony provider package.

This package provides Zoom Phone integration for voice triage.
Supports Zoom Phone UK with OAuth authentication.
"""

from voice_triage.telephony.providers.zoom.parser import (
    ZOOM_STATUS_MAP,
    parse_call_data,
    parse_call_status,
    parse_inbound_call,
    parse_phone_number,
    parse_timestamp,
    validate_webhook_signature,
)
from voice_triage.telephony.providers.zoom.provider import (
    ZoomPhoneProvider,
    ZoomPhoneUKProvider,
)
from voice_triage.telephony.providers.zoom.response import (
    generate_call_control_response,
    generate_gather_action,
    generate_hangup_action,
    generate_play_action,
    generate_say_action,
    generate_transfer_action,
)

__all__ = [
    "ZOOM_STATUS_MAP",
    "ZoomPhoneProvider",
    "ZoomPhoneUKProvider",
    "generate_call_control_response",
    "generate_gather_action",
    "generate_hangup_action",
    "generate_play_action",
    "generate_say_action",
    "generate_transfer_action",
    "parse_call_data",
    "parse_call_status",
    "parse_inbound_call",
    "parse_phone_number",
    "parse_timestamp",
    "validate_webhook_signature",
]
