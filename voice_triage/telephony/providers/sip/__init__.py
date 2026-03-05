"""SIP trunking telephony provider package.

This package provides SIP trunking integration for voice triage.
Supports UK SIP trunking providers such as Gamma, BT, Virgin Media, and TalkTalk.
"""

from voice_triage.telephony.providers.sip.parser import (
    SIP_STATUS_MAP,
    extract_phone_from_sip_uri,
    parse_call_status,
    parse_inbound_call,
)
from voice_triage.telephony.providers.sip.provider import (
    BTProvider,
    GammaProvider,
    SIPProvider,
    TalkTalkProvider,
    VirginMediaProvider,
)
from voice_triage.telephony.providers.sip.response import (
    generate_call_control_response,
)

__all__ = [
    "SIP_STATUS_MAP",
    "BTProvider",
    "GammaProvider",
    "SIPProvider",
    "TalkTalkProvider",
    "VirginMediaProvider",
    "extract_phone_from_sip_uri",
    "generate_call_control_response",
    "parse_call_status",
    "parse_inbound_call",
]
