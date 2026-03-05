"""RingCentral telephony provider implementation.

This module re-exports the decomposed RingCentral provider components
for backward compatibility. The actual implementation is in the
providers/ringcentral/ subdirectory.
"""

from voice_triage.telephony.providers.ringcentral import (
    RINGCENTRAL_STATUS_MAP,
    RingCentralClient,
    RingCentralProvider,
    generate_call_control_response,
    parse_call_status,
    parse_inbound_call,
)

__all__ = [
    "RINGCENTRAL_STATUS_MAP",
    "RingCentralClient",
    "RingCentralProvider",
    "generate_call_control_response",
    "parse_call_status",
    "parse_inbound_call",
]
