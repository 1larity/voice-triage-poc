"""Avaya telephony provider implementation.

This module re-exports the decomposed Avaya provider components for
backward compatibility. The actual implementation is in the providers/avaya/
subdirectory.

Avaya is a major enterprise telephony provider in the UK, offering:
- Avaya IP Office for small/medium businesses
- Avaya Aura for large enterprises
- Avaya Experience Platform (AXP) for contact centers
- SIP trunking
- Unified communications

Documentation: https://documentation.avaya.com/
"""

from voice_triage.telephony.providers.avaya import (
    AVAYA_STATUS_MAP,
    AvayaAESProvider,
    AvayaClient,
    AvayaIPOfficeProvider,
    AvayaProvider,
    parse_inbound_call,
    validate_avaya_signature,
    validate_basic_auth,
)

__all__ = [
    "AVAYA_STATUS_MAP",
    "AvayaAESProvider",
    "AvayaClient",
    "AvayaIPOfficeProvider",
    "AvayaProvider",
    "parse_inbound_call",
    "validate_avaya_signature",
    "validate_basic_auth",
]
