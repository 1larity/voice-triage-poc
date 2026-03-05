"""NFON telephony provider implementation.

This module re-exports the decomposed NFON provider components for
backward compatibility. The actual implementation is in the providers/nfon/
subdirectory.
"""

from __future__ import annotations

from voice_triage.telephony.providers.nfon import (
    NFON_API_URL,
    NFON_STATUS_MAP,
    NFON_UK_API_URL,
    NFONClient,
    NFONProvider,
    parse_call_status_data,
    parse_inbound_call,
)

__all__ = [
    "NFON_API_URL",
    "NFON_STATUS_MAP",
    "NFON_UK_API_URL",
    "NFONClient",
    "NFONProvider",
    "parse_call_status_data",
    "parse_inbound_call",
]
