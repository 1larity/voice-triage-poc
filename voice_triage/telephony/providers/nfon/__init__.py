"""NFON telephony provider package.

This package provides NFON Cloud PBX integration.
"""

from voice_triage.telephony.providers.nfon.client import (
    NFON_API_URL,
    NFON_UK_API_URL,
    NFONClient,
)
from voice_triage.telephony.providers.nfon.parser import (
    NFON_STATUS_MAP,
    parse_call_status_data,
    parse_inbound_call,
)
from voice_triage.telephony.providers.nfon.provider import NFONProvider

__all__ = [
    "NFON_API_URL",
    "NFON_STATUS_MAP",
    "NFON_UK_API_URL",
    "NFONClient",
    "NFONProvider",
    "parse_call_status_data",
    "parse_inbound_call",
]
