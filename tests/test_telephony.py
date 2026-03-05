"""Tests for telephony integration."""

from collections.abc import AsyncIterator

import pytest

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    PhoneCall,
    TelephonyConfig,
    TelephonyProvider,
)
from voice_triage.telephony.registry import (
    TelephonyRegistry,
    get_provider,
    register_provider,
)


class MockProvider(TelephonyProvider):
    """Mock telephony provider for testing."""

    def __init__(self, config: TelephonyConfig) -> None:
        """Initialize the mock provider.

        Args:
            config: Configuration for the provider.
        """
        self._config = config
        self.calls: dict[str, PhoneCall] = {}

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "mock"

    async def validate_webhook(
        self, headers: dict[str, str], body: bytes, path: str
    ) -> bool:
        """Validate a webhook request.

        Args:
            headers: HTTP headers from the request.
            body: Raw request body.
            path: Request path.

        Returns:
            Always returns True for mock provider.
        """
        return True

    async def parse_inbound_call(
        self, headers: dict[str, str], body: bytes, form_data: dict[str, str]
    ) -> PhoneCall:
        """Parse an inbound call webhook.

        Args:
            headers: HTTP headers from the request.
            body: Raw request body.
            form_data: Parsed form data from the request.

        Returns:
            A PhoneCall object representing the inbound call.
        """
        return PhoneCall(
            call_id=form_data.get("call_id", "test-call"),
            from_number=form_data.get("from", "+441111111111"),
            to_number=form_data.get("to", "+442222222222"),
            direction=CallDirection.INBOUND,
            status=CallStatus.RINGING,
            provider="mock",
        )

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate a TwiML-like response.

        Args:
            session_id: Session ID for this conversation.
            welcome_message: Optional welcome message to play.
            gather_speech: Whether to gather speech input.
            action_url: URL to post gathered input to.

        Returns:
            Response markup string.
        """
        return f'<Response><Say>{welcome_message}</Say></Response>'

    async def make_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
        metadata: dict | None = None,
    ) -> PhoneCall:
        """Initiate an outbound call.

        Args:
            to_number: Destination phone number.
            from_number: Source phone number.
            webhook_url: URL for call status webhooks.
            metadata: Additional metadata.

        Returns:
            A PhoneCall object representing the initiated call.
        """
        call = PhoneCall(
            call_id="test-call-id",
            from_number=from_number or "+441111111111",
            to_number=to_number,
            direction=CallDirection.OUTBOUND,
            status=CallStatus.RINGING,
            provider="mock",
        )
        self.calls[call.call_id] = call
        return call

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up an active call.

        Args:
            call_id: The provider's call ID to hang up.

        Returns:
            True if successful.
        """
        return True

    async def play_audio(
        self, call_id: str, audio_url: str, loop: bool = False
    ) -> bool:
        """Play audio into a call.

        Args:
            call_id: The provider's call ID.
            audio_url: URL of the audio to play.
            loop: Whether to loop the audio.

        Returns:
            True if successful.
        """
        return True

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits into a call.

        Args:
            call_id: The provider's call ID.
            digits: DTMF digits to send.

        Returns:
            True if successful.
        """
        return True

    async def get_call_status(self, call_id: str) -> PhoneCall | None:
        """Get the current status of a call.

        Args:
            call_id: The provider's call ID.

        Returns:
            PhoneCall object if found, None otherwise.
        """
        return self.calls.get(call_id)

    async def stream_audio(
        self, call_id: str, audio_stream: AsyncIterator[bytes]
    ) -> bool:
        """Stream audio into a call in real-time.

        Args:
            call_id: The provider's call ID.
            audio_stream: Async iterator of audio chunks.

        Returns:
            True if successful.
        """
        return True

    def get_webhook_path(self, event_type: str) -> str:
        """Get the webhook path for a specific event type.

        Args:
            event_type: Type of webhook event.

        Returns:
            The path portion of the webhook URL.
        """
        return f"/telephony/mock/{event_type}"


# Register the mock provider
register_provider("mock")(MockProvider)


class TestTelephonyRegistry:
    """Tests for TelephonyRegistry class."""

    def test_register_and_get(self) -> None:
        """Test registering and retrieving a provider."""
        registry = TelephonyRegistry()
        config = TelephonyConfig(provider_name="mock")
        provider = MockProvider(config)
        registry.register(provider)

        assert "mock" in registry.list_registered()
        assert registry.get("mock") is not None
        assert registry.get("nonexistent") is None

    def test_clear(self) -> None:
        """Test clearing the registry."""
        registry = TelephonyRegistry()
        config = TelephonyConfig(provider_name="mock")
        provider = MockProvider(config)
        registry.register(provider)

        registry.clear()
        assert len(registry.list_registered()) == 0


class TestGetProvider:
    """Tests for get_provider factory function."""

    def test_get_registered_provider(self) -> None:
        """Test getting a registered provider."""
        config = TelephonyConfig(provider_name="mock")
        provider = get_provider(config)
        assert isinstance(provider, MockProvider)
        assert provider.name == "mock"

    def test_get_unregistered_provider(self) -> None:
        """Test getting an unregistered provider raises error."""
        config = TelephonyConfig(provider_name="nonexistent")
        with pytest.raises(ValueError, match="Unknown telephony provider"):
            get_provider(config)


class TestMockProvider:
    """Tests for MockProvider class."""

    @pytest.fixture
    def provider(self) -> MockProvider:
        """Create a mock provider instance."""
        config = TelephonyConfig(provider_name="mock")
        return MockProvider(config)

    @pytest.mark.asyncio
    async def test_validate_webhook(self, provider: MockProvider) -> None:
        """Test webhook validation."""
        result = await provider.validate_webhook({}, b"", "/test")
        assert result is True

    @pytest.mark.asyncio
    async def test_parse_inbound_call(self, provider: MockProvider) -> None:
        """Test parsing inbound call."""
        call = await provider.parse_inbound_call(
            headers={},
            body=b"",
            form_data={"call_id": "test-123", "from": "+441111111111"},
        )
        assert call.call_id == "test-123"
        assert call.from_number == "+441111111111"
        assert call.direction == CallDirection.INBOUND

    @pytest.mark.asyncio
    async def test_generate_twiml_response(self, provider: MockProvider) -> None:
        """Test generating TwiML response."""
        response = await provider.generate_twiml_response(
            session_id="test-session",
            welcome_message="Hello",
            gather_speech=True,
            action_url="/action",
        )
        assert "<Response>" in response
        assert "<Say>Hello</Say>" in response

    @pytest.mark.asyncio
    async def test_make_outbound_call(self, provider: MockProvider) -> None:
        """Test making an outbound call."""
        call = await provider.make_outbound_call(
            to_number="+442222222222",
            from_number="+441111111111",
        )
        assert call.to_number == "+442222222222"
        assert call.from_number == "+441111111111"
        assert call.direction == CallDirection.OUTBOUND

    @pytest.mark.asyncio
    async def test_hangup_call(self, provider: MockProvider) -> None:
        """Test hanging up a call."""
        result = await provider.hangup_call("test-call-id")
        assert result is True

    @pytest.mark.asyncio
    async def test_play_audio(self, provider: MockProvider) -> None:
        """Test playing audio."""
        result = await provider.play_audio("test-call-id", "http://example.com/audio.wav")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_digits(self, provider: MockProvider) -> None:
        """Test sending DTMF digits."""
        result = await provider.send_digits("test-call-id", "1234")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_call_status(self, provider: MockProvider) -> None:
        """Test getting call status."""
        # First make a call to add it to the registry
        call = await provider.make_outbound_call(to_number="+442222222222")

        # Now get the status
        status = await provider.get_call_status(call.call_id)
        assert status is not None
        assert status.call_id == call.call_id

    @pytest.mark.asyncio
    async def test_get_call_status_not_found(self, provider: MockProvider) -> None:
        """Test getting status for non-existent call."""
        status = await provider.get_call_status("nonexistent")
        assert status is None

    @pytest.mark.asyncio
    async def test_stream_audio(self, provider: MockProvider) -> None:
        """Test streaming audio."""

        async def audio_stream() -> AsyncIterator[bytes]:
            yield b"audio_chunk_1"
            yield b"audio_chunk_2"

        result = await provider.stream_audio("test-call-id", audio_stream())
        assert result is True

    def test_get_webhook_path(self, provider: MockProvider) -> None:
        """Test getting webhook path."""
        path = provider.get_webhook_path("voice")
        assert path == "/telephony/mock/voice"
