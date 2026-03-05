"""Base abstractions for telephony providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any


class CallDirection(StrEnum):
    """Direction of a phone call."""

    INBOUND = "inbound"
    OUTBOUND = "outbound"


class CallStatus(StrEnum):
    """Status of a phone call."""

    RINGING = "ringing"
    DIALING = "dialing"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BUSY = "busy"
    NO_ANSWER = "no_answer"
    CANCELED = "canceled"
    QUEUED = "queued"
    HELD = "held"
    IDLE = "idle"
    UNKNOWN = "unknown"


@dataclass
class PhoneCall:
    """Represents a phone call from a telephony provider."""

    call_id: str
    """Unique identifier for the call from the provider."""

    from_number: str
    """The caller's phone number in E.164 format."""

    to_number: str
    """The destination phone number in E.164 format."""

    direction: CallDirection
    """Whether the call is inbound or outbound."""

    status: CallStatus
    """Current status of the call."""

    provider: str
    """Name of the telephony provider."""

    started_at: datetime | None = None
    """When the call started."""

    ended_at: datetime | None = None
    """When the call ended."""

    duration_seconds: int | None = None
    """Duration of the call in seconds."""

    recording_url: str | None = None
    """URL to the call recording if available."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Additional provider-specific metadata."""


@dataclass
class CallEvent:
    """Event related to a phone call."""

    event_type: str
    """Type of event (e.g., 'answer', 'hangup', 'dtmf', 'recording')."""

    call: PhoneCall
    """The call this event relates to."""

    timestamp: datetime
    """When the event occurred."""

    data: dict[str, Any] = field(default_factory=dict)
    """Additional event-specific data."""


@dataclass
class TelephonyConfig:
    """Configuration for a telephony provider."""

    provider_name: str
    """Name of the provider."""

    account_sid: str | None = None
    """Account SID (Twilio) or equivalent."""

    auth_token: str | None = None
    """Authentication token."""

    api_key: str | None = None
    """API key for authentication."""

    api_secret: str | None = None
    """API secret for authentication."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    default_from_number: str | None = None
    """Default phone number to use for outbound calls."""

    webhook_secret: str | None = None
    """Secret for webhook signature validation."""

    region: str = "GB"
    """Region for the provider (default: UK)."""

    extra: dict[str, Any] = field(default_factory=dict)
    """Additional provider-specific configuration."""


class TelephonyProvider(ABC):
    """Abstract base class for telephony providers."""

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the provider with configuration."""
        self.config = config

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the name of this provider."""
        ...

    @abstractmethod
    async def validate_webhook(
        self,
        headers: dict[str, str],
        body: bytes,
        path: str,
    ) -> bool:
        """Validate that a webhook request is authentic.

        Args:
            headers: HTTP headers from the request.
            body: Raw request body.
            path: Request path.

        Returns:
            True if the webhook is authentic, False otherwise.
        """
        ...

    @abstractmethod
    async def parse_inbound_call(
        self,
        headers: dict[str, str],
        body: bytes,
        form_data: dict[str, str],
    ) -> PhoneCall:
        """Parse an inbound call webhook.

        Args:
            headers: HTTP headers from the request.
            body: Raw request body.
            form_data: Parsed form data from the request.

        Returns:
            A PhoneCall object representing the inbound call.
        """
        ...

    @abstractmethod
    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate a TwiML-like response for call control.

        This method generates XML/JSON response markup that the provider
        can understand to control the call flow.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to play.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            Response markup (TwiML, Nexmo Call Control, etc.).
        """
        ...

    @abstractmethod
    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PhoneCall:
        """Initiate an outbound call.

        Args:
            to_number: Destination phone number in E.164 format.
            from_number: Source phone number (uses default if not provided).
            webhook_url: URL for call status webhooks.
            metadata: Additional metadata to attach to the call.

        Returns:
            A PhoneCall object representing the initiated call.
        """
        ...

    @abstractmethod
    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active call.

        Args:
            call_id: The provider's call ID to hang up.

        Returns:
            True if the call was hung up successfully.
        """
        ...

    @abstractmethod
    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a call.

        Args:
            call_id: The provider's call ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            True if audio started playing successfully.
        """
        ...

    @abstractmethod
    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a call.

        Args:
            call_id: The provider's call ID.
            digits: DTMF digits to send.

        Returns:
            True if digits were sent successfully.
        """
        ...

    @abstractmethod
    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a call.

        Args:
            call_id: The provider's call ID.

        Returns:
            PhoneCall object if found, None otherwise.
        """
        ...

    @abstractmethod
    async def stream_audio(
        self,
        call_id: str,
        audio_stream: AsyncIterator[bytes],
    ) -> bool:
        """Stream audio into a call in real-time.

        Args:
            call_id: The provider's call ID.
            audio_stream: Async iterator of audio chunks (PCM 16-bit, 8kHz).

        Returns:
            True if streaming completed successfully.
        """
        ...

    @abstractmethod
    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event (e.g., 'voice', 'status').

        Returns:
            The path portion of the webhook URL.
        """
        ...

    def extract_transcript(self, data: dict[str, Any]) -> str:
        """Extract transcript from provider-specific webhook data.

        Args:
            data: Parsed request data from the webhook.

        Returns:
            Extracted transcript string, or empty string if not found.
        """
        # Default implementation - override in subclasses
        return data.get("transcript", data.get("speech", ""))

    def get_response_content_type(self) -> str:
        """Get the content type for call control responses.

        Returns:
            MIME type for response content (e.g., 'application/xml', 'application/json').
        """
        # Default to JSON - override in subclasses
        return "application/json"

    def get_validation_response(self, headers: dict[str, str]) -> str | None:
        """Return provider-specific webhook validation response when required.

        Some providers perform webhook verification challenges where the server
        must echo a token from the incoming request.

        Args:
            headers: HTTP headers from the request.

        Returns:
            Validation response body when a challenge is present, else None.
        """
        del headers
        return None
