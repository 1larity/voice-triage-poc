"""Vonage telephony provider implementation.

This module re-exports the decomposed Vonage provider components for
backward compatibility. The actual implementation is in the providers/vonage/
subdirectory.

Vonage (formerly Nexmo) is a major UK telephony provider offering:
- Voice calls (inbound/outbound)
- SIP trunking
- Programmable voice with NCCO
- Call recording
- Number provisioning

Documentation: https://developer.vonage.com/voice/voice-api
"""

from voice_triage.telephony.providers.vonage import (
    VONAGE_STATUS_MAP,
    NexmoProvider,
    VonageClient,
    VonageProvider,
    generate_answer_ncco,
    generate_connect_ncco,
    generate_gather_ncco,
    generate_input_ncco,
    generate_stream_ncco,
    generate_talk_ncco,
    generate_transfer_ncco,
    generate_websocket_ncco,
    ncco_to_json,
    parse_call_status_response,
    parse_inbound_call,
    parse_vonage_time,
    validate_vonage_signature,
)

__all__ = [
    "VONAGE_STATUS_MAP",
    "NexmoProvider",
    "VonageClient",
    "VonageProvider",
    "generate_answer_ncco",
    "generate_connect_ncco",
    "generate_gather_ncco",
    "generate_input_ncco",
    "generate_stream_ncco",
    "generate_talk_ncco",
    "generate_transfer_ncco",
    "generate_websocket_ncco",
    "ncco_to_json",
    "parse_call_status_response",
    "parse_inbound_call",
    "parse_vonage_time",
    "validate_vonage_signature",
]
