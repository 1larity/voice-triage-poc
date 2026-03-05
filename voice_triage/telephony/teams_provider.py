"""Microsoft Teams telephony provider implementation.

This module re-exports the decomposed Teams provider components for
backward compatibility. The actual implementation is in the providers/teams/
subdirectory.

Microsoft Teams Direct Routing enables UK organizations to:
- Use existing SIP trunks with Microsoft Teams
- Make/receive PSTN calls through Teams
- Integrate with existing PBX systems
- Support UK emergency calling (999/112)

Documentation: https://learn.microsoft.com/microsoft-365/
"""

from voice_triage.telephony.providers.teams import (
    GRAPH_API_URL,
    TEAMS_STATUS_MAP,
    TeamsDirectRoutingProvider,
    TeamsGraphClient,
    TeamsUKProvider,
    generate_teams_response,
    get_webhook_paths,
    parse_call_status_data,
    parse_inbound_call,
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
