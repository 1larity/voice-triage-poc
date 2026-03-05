"""RingCentral telephony provider package.

This package provides RingCentral integration for voice triage.
RingCentral is a major UC telephony provider offering cloud PBX services.
"""

from voice_triage.telephony.providers.ringcentral.client import RingCentralClient
from voice_triage.telephony.providers.ringcentral.parser import (
    RINGCENTRAL_STATUS_MAP,
    parse_call_status,
    parse_inbound_call,
)
from voice_triage.telephony.providers.ringcentral.provider import RingCentralProvider
from voice_triage.telephony.providers.ringcentral.response import (
    generate_call_control_response,
)

__all__ = [
    "RINGCENTRAL_STATUS_MAP",
    "RingCentralClient",
    "RingCentralProvider",
    "generate_call_control_response",
    "parse_call_status",
    "parse_inbound_call",
]
