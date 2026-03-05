"""Microsoft Teams Direct Routing telephony provider implementation.

Microsoft Teams Direct Routing allows organizations to connect through
existing telephony infrastructure using Microsoft Teams, enabling:
- Voice calls (inbound/outbound) via existing SIP trunks
- Integration with Microsoft 365 ecosystem
- Auto attendants and call queues
- Call recording and compliance

Direct Routing is popular in the UK for enterprises that want to
leverage Microsoft Teams while maintaining their existing carrier
relationships (e.g., BT, Gamma, Virgin Media Business).

Documentation: https://learn.microsoft.com/en-us/microsoftteams/direct-routing-landing-page
"""

from __future__ import annotations

import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
    TelephonyConfig,
    TelephonyProvider,
)
from voice_triage.telephony.providers.teams.client import (
    GRAPH_API_URL,
    TeamsGraphClient,
)
from voice_triage.telephony.providers.teams.parser import (
    generate_teams_response,
    get_webhook_paths,
    parse_call_status_data,
    parse_inbound_call,
)
from voice_triage.telephony.registry import register_provider
from voice_triage.telephony.shared.auth import get_header

logger = logging.getLogger(__name__)


@register_provider("teams")
@register_provider("microsoft_teams")
@register_provider("teams_direct_routing")
class TeamsDirectRoutingProvider(TelephonyProvider):
    """Microsoft Teams Direct Routing telephony provider implementation.

    This provider integrates with Microsoft Teams via:
    1. Microsoft Graph API for call control
    2. Webhook subscriptions for call notifications
    3. Direct Routing SBC (Session Border Controller) integration

    For UK deployments, this typically works with SBCs connected to
    UK carriers like BT, Gamma Telecom, and Virgin Media Business.
    """

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the Teams Direct Routing provider.

        Args:
            config: Configuration containing:
                - api_key: Azure AD Client ID (Application ID)
                - api_secret: Azure AD Client Secret
                - account_sid: Azure Tenant ID
                - webhook_base_url: Base URL for webhooks
                - default_from_number: Default Teams phone number
                - extra:
                    - tenant_id: Azure Tenant ID (alternative to account_sid)
                    - subscription_id: Azure Subscription ID
                    - resource_group: Azure resource group
                    - sbc_fqdn: Session Border Controller FQDN
                    - webhook_secret: Secret for webhook validation
                    - use_cloud_communications: Use Cloud Communications API
        """
        super().__init__(config)
        self._client: TeamsGraphClient | None = None

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "teams"

    @property
    def tenant_id(self) -> str:
        """Get the Azure Tenant ID."""
        return self.config.account_sid or self.config.extra.get("tenant_id", "")

    def _get_client(self) -> TeamsGraphClient:
        """Get or create the Teams Graph client.

        Returns:
            TeamsGraphClient instance.
        """
        if self._client is None:
            self._client = TeamsGraphClient(
                tenant_id=self.tenant_id,
                client_id=self.config.api_key or "",
                client_secret=self.config.api_secret or "",
            )
        return self._client

    async def _get_access_token(self) -> str:
        """Get a valid Microsoft Graph access token.

        Returns:
            Valid OAuth access token.

        Raises:
            RuntimeError: If authentication fails.
        """
        return await self._get_client().get_access_token()

    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate a Microsoft Teams webhook signature.

        Microsoft Graph webhooks use validation tokens for initial
        subscription validation and HMAC signatures for notifications.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            path: Request path.

        Returns:
            True if signature is valid.
        """
        # Check for validation request (initial subscription)
        validation_token = get_header(headers, "validationtoken")
        if validation_token:
            # Validation requests are always valid
            # The response should echo back the token
            return True

        # Get client state for validation
        client_state = self.config.extra.get("webhook_secret")
        if not client_state:
            logger.warning("No webhook_secret configured for Teams webhook validation")
            return True  # Accept if no validation configured

        try:
            data = json.loads(body.decode("utf-8"))
            webhook_client_state = data.get("clientState")
            if webhook_client_state is None:
                notifications = data.get("value", [])
                if notifications and isinstance(notifications[0], dict):
                    webhook_client_state = notifications[0].get("clientState")

            # Verify client state matches
            if webhook_client_state == client_state:
                return True

            logger.warning("Teams webhook client state mismatch")
            return False
        except json.JSONDecodeError:
            logger.warning("Failed to parse Teams webhook body")
            return False

    def get_validation_response(self, headers: dict[str, str]) -> str | None:
        """Get the response for a webhook validation request.

        Microsoft Graph requires the validation token to be echoed back.

        Args:
            headers: HTTP headers containing validationtoken.

        Returns:
            Validation token if present, None otherwise.
        """
        token = get_header(headers, "validationtoken")
        return token or None

    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call webhook from Microsoft Teams.

        Args:
            headers: HTTP headers.
            body: Raw request body.
            form_data: Parsed form data from the request.

        Returns:
            A PhoneCall object representing the inbound call.
        """
        return parse_inbound_call(headers, body, form_data)

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate a Microsoft Teams call control response.

        Microsoft Teams uses the Cloud Communications API which handles
        call control through API calls rather than markup responses.
        This method returns a JSON structure for reference.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to play.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            JSON response describing the call flow.
        """
        speech_timeout = self.config.extra.get("speech_timeout", 5)
        return generate_teams_response(
            session_id=session_id,
            welcome_message=welcome_message,
            gather_speech=gather_speech,
            action_url=action_url,
            speech_timeout=speech_timeout,
        )

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Initiate an outbound call via Microsoft Teams.

        Args:
            to_number: Destination phone number in E.164 format.
            from_number: Source phone number (uses default if not provided).
            webhook_url: URL for call status webhooks.
            metadata: Additional metadata to attach to the call.

        Returns:
            A PhoneCall object representing the initiated call.
        """
        access_token = await self._get_access_token()
        from_number = from_number or self.config.default_from_number

        if not from_number:
            raise ValueError("No from_number provided and no default configured")

        try:
            import httpx

            callback_uri = webhook_url
            if not callback_uri:
                base_url = self.config.webhook_base_url
                callback_uri = f"{base_url}/telephony/teams/callback"

            # Build request body for Microsoft Graph Cloud Communications API
            request_body: dict[str, Any] = {
                "@odata.type": "#microsoft.graph.call",
                "direction": "outgoing",
                "subject": "Voice Triage Call",
                "callbackUri": callback_uri,
                "source": {
                    "@odata.type": "#microsoft.graph.participantInfo",
                    "identity": {
                        "@odata.type": "#microsoft.graph.identitySet",
                        "phone": {
                            "@odata.type": "#microsoft.graph.identity",
                            "id": from_number,
                        },
                    },
                },
                "targets": [{
                    "@odata.type": "#microsoft.graph.invitationParticipantInfo",
                    "identity": {
                        "@odata.type": "#microsoft.graph.identitySet",
                        "phone": {
                            "@odata.type": "#microsoft.graph.identity",
                            "id": to_number,
                        },
                    },
                    "requestedModalities": ["audio"],
                    "mediaConfig": {
                        "@odata.type": "#microsoft.graph.serviceHostedMediaConfig",
                    },
                }],
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GRAPH_API_URL}/communications/calls",
                    json=request_body,
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )

                response.raise_for_status()
                data = response.json()

                call_id = data.get("id", "")

                return PhoneCall(
                    call_id=call_id,
                    from_number=from_number,
                    to_number=to_number,
                    direction=CallDirection.OUTBOUND,
                    status=CallStatus.RINGING,
                    provider="teams",
                    metadata={
                        "call_data": data,
                        "custom_metadata": metadata,
                    },
                )

        except Exception as exc:
            logger.error(f"Failed to make outbound call via Teams: {exc}")
            raise RuntimeError(f"Teams outbound call failed: {exc}") from exc

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active Microsoft Teams call.

        Args:
            call_id: The Teams call ID.

        Returns:
            True if the call was hung up successfully.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            base_url = self.config.webhook_base_url
            callback_uri = f"{base_url}/telephony/teams/callback"

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GRAPH_API_URL}/communications/calls/{call_id}/hangup",
                    json={"callbackUri": callback_uri},
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )

                return response.status_code in (200, 204, 404)
        except Exception as exc:
            logger.error(f"Failed to hang up Teams call: {exc}")
            return False

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a Microsoft Teams call.

        Args:
            call_id: The Teams call ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            True if audio started playing successfully.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GRAPH_API_URL}/communications/calls/{call_id}/playPrompt",
                    json={
                        "clientContext": str(uuid.uuid4()),
                        "prompts": [{
                            "@odata.type": "#microsoft.graph.mediaPrompt",
                            "mediaInfo": {
                                "uri": audio_url,
                                "resourceId": str(uuid.uuid4()),
                            },
                        }],
                        "loop": loop,
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )

                return response.status_code == 200
        except Exception as exc:
            logger.error(f"Failed to play audio via Teams: {exc}")
            return False

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a Microsoft Teams call.

        Args:
            call_id: The Teams call ID.
            digits: DTMF digits to send.

        Returns:
            True if digits were sent successfully.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            # Map digits to tones
            tones = []
            tone_map = {
                "0": "tone0", "1": "tone1", "2": "tone2",
                "3": "tone3", "4": "tone4", "5": "tone5",
                "6": "tone6", "7": "tone7", "8": "tone8",
                "9": "tone9", "*": "star", "#": "pound",
            }
            for d in digits:
                tones.append(tone_map.get(d, "tone0"))

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GRAPH_API_URL}/communications/calls/{call_id}/sendDtmfTones",
                    json={
                        "clientContext": str(uuid.uuid4()),
                        "tones": tones,
                        "delayBetweenTonesMs": 500,
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )

                return response.status_code == 200
        except Exception as exc:
            logger.error(f"Failed to send digits via Teams: {exc}")
            return False

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a Microsoft Teams call.

        Args:
            call_id: The Teams call ID.

        Returns:
            PhoneCall object if found, None otherwise.
        """
        access_token = await self._get_access_token()

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{GRAPH_API_URL}/communications/calls/{call_id}",
                    headers={
                        "Authorization": f"Bearer {access_token}",
                    },
                )

                if response.status_code == 404:
                    return None

                response.raise_for_status()
                data = response.json()

                return parse_call_status_data(data)

        except Exception as exc:
            logger.error(f"Failed to get Teams call status: {exc}")
            return None

    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a Microsoft Teams call in real-time.

        Microsoft Teams supports real-time audio streaming via
        App-Hosted Media or Service-Hosted Media configurations.

        Args:
            call_id: The Teams call ID.
            audio_stream: Async iterator of audio chunks (PCM 16-bit, 8kHz).

        Returns:
            True if streaming completed successfully.
        """
        # Teams requires App-Hosted Media for real-time streaming
        # This is a simplified implementation
        logger.warning(
            "Microsoft Teams real-time audio streaming requires App-Hosted Media setup. "
            "Consider using pre-recorded audio with play_audio() instead."
        )
        return False

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract transcript text from Teams notification payloads."""
        if not isinstance(data, dict):
            return ""

        # Graph webhook notifications commonly wrap payload in value[].
        notifications = data.get("value")
        if isinstance(notifications, list) and notifications:
            first = notifications[0]
            if isinstance(first, dict):
                resource_data = first.get("resourceData", {})
                if isinstance(resource_data, dict):
                    for key in ("transcript", "speech", "text"):
                        value = resource_data.get(key)
                        if isinstance(value, str):
                            return value
                        if isinstance(value, dict):
                            nested = value.get("text") or value.get("transcript")
                            if isinstance(nested, str):
                                return nested

        for key in ("transcript", "speech", "text"):
            value = data.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict):
                nested = value.get("text") or value.get("transcript")
                if isinstance(nested, str):
                    return nested
        return ""

    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event (e.g., 'voice', 'status').

        Returns:
            The path portion of the webhook URL.
        """
        paths = get_webhook_paths()
        return paths.get(event_type, f"/telephony/teams/{event_type}")

    async def create_subscription(
        self,
        change_type: str = "created,updated,deleted",
        expiration_datetime: datetime | None = None,
    ) -> dict[str, Any]:
        """Create a Graph API subscription for call notifications.

        Args:
            change_type: Types of changes to subscribe to.
            expiration_datetime: When the subscription expires (max 3 days).

        Returns:
            Subscription details including subscription_id.
        """
        access_token = await self._get_access_token()

        if not expiration_datetime:
            # Default to 3 days (max allowed)
            expiration_datetime = datetime.now(UTC) + timedelta(days=3)

        try:
            import httpx

            base_url = self.config.webhook_base_url
            if base_url is None:
                raise ValueError("webhook_base_url is required for Teams subscription")
            notification_url = base_url + self.get_webhook_path("notification")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{GRAPH_API_URL}/subscriptions",
                    json={
                        "changeType": change_type,
                        "notificationUrl": notification_url,
                        "resource": "/communications/calls",
                        "expirationDateTime": expiration_datetime.isoformat(),
                        "clientState": self.config.extra.get("webhook_secret", ""),
                    },
                    headers={
                        "Authorization": f"Bearer {access_token}",
                        "Content-Type": "application/json",
                    },
                )
                response.raise_for_status()
                return response.json()
        except Exception as exc:
            logger.error(f"Failed to create Teams subscription: {exc}")
            raise RuntimeError(f"Teams subscription creation failed: {exc}") from exc


@register_provider("teams_uk")
class TeamsUKProvider(TeamsDirectRoutingProvider):
    """Microsoft Teams UK-specific provider with UK defaults.

    This is a convenience class that sets UK-specific defaults.
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "teams_uk"

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize with UK defaults.

        Args:
            config: Configuration (region will be set to GB).
        """
        config.region = "GB"
        super().__init__(config)
