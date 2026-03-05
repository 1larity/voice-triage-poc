"""Teams provider module exports.

This module provides the Microsoft Teams telephony provider and related utilities.
"""

from voice_triage.telephony.providers.teams.client import (
    GRAPH_API_URL,
    TeamsGraphClient,
)
from voice_triage.telephony.providers.teams.parser import (
    TEAMS_STATUS_MAP,
    generate_teams_response,
    get_webhook_paths,
    parse_call_status_data,
    parse_inbound_call,
)
from voice_triage.telephony.providers.teams.provider import (
    TeamsDirectRoutingProvider,
    TeamsUKProvider,
)

__all__ = [
    "GRAPH_API_URL",
    "TEAMS_STATUS_MAP",
    "TeamsDirectRoutingProvider",
    "TeamsGraphClient",
    "TeamsUKProvider",
    "generate_teams_response",
    "get_webhook_paths",
    "parse_call_status_data",
    "parse_inbound_call",
]
