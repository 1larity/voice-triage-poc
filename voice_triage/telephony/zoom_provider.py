"""Zoom Phone telephony provider implementation.

This module re-exports the decomposed Zoom provider components for
backward compatibility. The actual implementation is in the providers/zoom/
subdirectory.
"""

from voice_triage.telephony.providers.zoom import (
    ZOOM_STATUS_MAP,
    ZoomPhoneProvider,
    ZoomPhoneUKProvider,
    generate_call_control_response,
    generate_gather_action,
    generate_hangup_action,
    generate_play_action,
    generate_say_action,
    generate_transfer_action,
    parse_call_data,
    parse_call_status,
    parse_inbound_call,
    parse_phone_number,
    parse_timestamp,
    validate_webhook_signature,
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
