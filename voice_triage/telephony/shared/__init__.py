"""Shared utilities for telephony providers.

This module provides common utilities used across multiple
telephony providers.
"""

from voice_triage.telephony.shared.auth import (
    compute_hmac,
    validate_basic_auth,
)
from voice_triage.telephony.shared.parsing import (
    normalize_phone_number,
    parse_uk_date,
)
from voice_triage.telephony.shared.validation import (
    validate_twilio_signature,
    validate_webhook_signature,
)

__all__ = [
    "compute_hmac",
    "normalize_phone_number",
    "parse_uk_date",
    "validate_basic_auth",
    "validate_twilio_signature",
    "validate_webhook_signature",
]
