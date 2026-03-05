"""CircleLoop telephony provider implementation.

This module re-exports the decomposed CircleLoop provider components for
backward compatibility. The actual implementation is in the providers/circleloop/
subdirectory.
"""

from voice_triage.telephony.providers.circleloop import (
    CIRCLELOOP_STATUS_MAP,
    CircleLoopClient,
    CircleLoopProvider,
    generate_call_control_response,
    parse_call_status,
    parse_inbound_call,
)

__all__ = [
    "CIRCLELOOP_STATUS_MAP",
    "CircleLoopClient",
    "CircleLoopProvider",
    "generate_call_control_response",
    "parse_call_status",
    "parse_inbound_call",
]
