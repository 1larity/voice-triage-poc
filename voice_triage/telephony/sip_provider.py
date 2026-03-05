"""SIP trunking telephony provider implementation.

This module re-exports the decomposed SIP provider components for
backward compatibility. The actual implementation is in the providers/sip/
subdirectory.
"""

from voice_triage.telephony.providers.sip import (
    SIP_STATUS_MAP,
    BTProvider,
    GammaProvider,
    SIPProvider,
    TalkTalkProvider,
    VirginMediaProvider,
    extract_phone_from_sip_uri,
    parse_call_status,
    parse_inbound_call,
)

__all__ = [
    "SIP_STATUS_MAP",
    "BTProvider",
    "GammaProvider",
    "SIPProvider",
    "TalkTalkProvider",
    "VirginMediaProvider",
    "extract_phone_from_sip_uri",
    "parse_call_status",
    "parse_inbound_call",
]
