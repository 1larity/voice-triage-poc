"""Telephony providers package.

This package provides all telephony provider implementations.
Each provider is organized in its own subpackage.
"""

from voice_triage.telephony.providers.avaya import (
    AVAYA_STATUS_MAP,
    AvayaAESProvider,
    AvayaClient,
    AvayaIPOfficeProvider,
    AvayaProvider,
    validate_avaya_signature,
    validate_basic_auth,
)
from voice_triage.telephony.providers.avaya import (
    parse_inbound_call as parse_avaya_inbound_call,
)
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
from voice_triage.telephony.providers.vonage import (
    VONAGE_STATUS_MAP,
    NexmoProvider,
    VonageClient,
    VonageProvider,
    generate_answer_ncco,
    generate_connect_ncco,
    generate_gather_ncco,
    generate_input_ncco,
    generate_stream_ncco,
    generate_talk_ncco,
    generate_transfer_ncco,
    generate_websocket_ncco,
    ncco_to_json,
    parse_vonage_time,
    validate_vonage_signature,
)
from voice_triage.telephony.providers.vonage import (
    parse_call_status_response as parse_vonage_call_status,
)
from voice_triage.telephony.providers.vonage import (
    parse_inbound_call as parse_vonage_inbound_call,
)

__all__ = [
    "AVAYA_STATUS_MAP",
    "TWILIO_STATUS_MAP",
    "VONAGE_STATUS_MAP",
    "AvayaAESProvider",
    "AvayaClient",
    "AvayaIPOfficeProvider",
    "AvayaProvider",
    "NexmoProvider",
    "TwilioClient",
    "TwilioProvider",
    "VonageClient",
    "VonageProvider",
    "generate_answer_ncco",
    "generate_connect_ncco",
    "generate_gather_ncco",
    "generate_gather_twiml",
    "generate_input_ncco",
    "generate_say_twiml",
    "generate_stream_ncco",
    "generate_talk_ncco",
    "generate_transfer_ncco",
    "generate_websocket_ncco",
    "ncco_to_json",
    "parse_avaya_inbound_call",
    "parse_call_status",
    "parse_direction",
    "parse_vonage_call_status",
    "parse_vonage_inbound_call",
    "parse_vonage_time",
    "twiml_to_string",
    "validate_avaya_signature",
    "validate_basic_auth",
    "validate_vonage_signature",
]
