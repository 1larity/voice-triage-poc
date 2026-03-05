"""CircleLoop telephony provider package.

This package provides CircleLoop integration for voice triage.
CircleLoop is a UK-based cloud phone system provider.
"""

from voice_triage.telephony.providers.circleloop.client import CircleLoopClient
from voice_triage.telephony.providers.circleloop.parser import (
    CIRCLELOOP_STATUS_MAP,
    parse_call_status,
    parse_inbound_call,
)
from voice_triage.telephony.providers.circleloop.provider import CircleLoopProvider
from voice_triage.telephony.providers.circleloop.response import (
    generate_call_control_response,
)

__all__ = [
    "CIRCLELOOP_STATUS_MAP",
    "CircleLoopClient",
    "CircleLoopProvider",
    "generate_call_control_response",
    "parse_call_status",
    "parse_inbound_call",
]
