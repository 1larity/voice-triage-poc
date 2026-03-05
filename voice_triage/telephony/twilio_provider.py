"""Twilio telephony provider implementation.

This module re-exports the decomposed Twilio provider components for
backward compatibility. The actual implementation is in the providers/twilio/
subdirectory.

Twilio is one of the most popular telephony solutions in the UK, offering:
- Voice calls (inbound/outbound)
- SIP trunking
- Programmable voice with TwiML
- Real-time media streams
- Call recording

Documentation: https://www.twilio.com/docs/voice
"""

from voice_triage.telephony.providers.twilio import (
    TWILIO_STATUS_MAP,
    TwilioClient,
    TwilioProvider,
    generate_gather_twiml,
    generate_say_twiml,
    parse_call_status,
    parse_direction,
    twiml_to_string,
)

__all__ = [
    "TWILIO_STATUS_MAP",
    "TwilioClient",
    "TwilioProvider",
    "generate_gather_twiml",
    "generate_say_twiml",
    "parse_call_status",
    "parse_direction",
    "twiml_to_string",
]
