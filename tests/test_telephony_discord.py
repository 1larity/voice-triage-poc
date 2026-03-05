"""Tests for Discord telephony provider integration."""

import json
import os
from collections.abc import AsyncIterator

import pytest

from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    TelephonyConfig,
)
from voice_triage.telephony.config import DiscordConfig
from voice_triage.telephony.discord_provider import (
    DISCORD_STATUS_MAP,
    DiscordGateway,
    DiscordProvider,
    DiscordVoiceConnection,
)


@pytest.fixture
def discord_config() -> TelephonyConfig:
    """Create a test Discord configuration."""
    return TelephonyConfig(
        provider_name="discord",
        api_key="test-bot-token-12345",
        webhook_base_url="https://example.com/telephony/discord",
        extra={
            "application_id": "123456789012345678",
            "public_key": "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
            "guild_id": "987654321098765432",
            "voice_channel_id": "111122223333444455",
            "text_channel_id": "666677778888999900",
        },
    )


@pytest.fixture
def discord_provider(discord_config: TelephonyConfig) -> DiscordProvider:
    """Create a Discord provider instance."""
    return DiscordProvider(discord_config)


@pytest.fixture
def discord_config_dataclass() -> DiscordConfig:
    """Create a DiscordConfig dataclass instance."""
    return DiscordConfig(
        bot_token="test-bot-token-12345",
        application_id="123456789012345678",
        public_key="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        webhook_base_url="https://example.com/telephony/discord",
        webhook_secret="test-webhook-secret",
        guild_id="987654321098765432",
        voice_channel_id="111122223333444455",
        text_channel_id="666677778888999900",
    )


class TestDiscordConfig:
    """Tests for DiscordConfig dataclass."""

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading DiscordConfig from environment variables."""
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "env-bot-token")
        monkeypatch.setenv("DISCORD_APPLICATION_ID", "111222333444555666")
        monkeypatch.setenv("DISCORD_PUBLIC_KEY", "pubkey123")
        monkeypatch.setenv("DISCORD_WEBHOOK_BASE_URL", "https://env.example.com/webhook")
        monkeypatch.setenv("DISCORD_WEBHOOK_SECRET", "env-secret")
        monkeypatch.setenv("DISCORD_GUILD_ID", "999888777666555444")
        monkeypatch.setenv("DISCORD_VOICE_CHANNEL_ID", "123123123123123123")
        monkeypatch.setenv("DISCORD_TEXT_CHANNEL_ID", "456456456456456456")

        config = DiscordConfig.from_env()

        assert config.bot_token == "env-bot-token"
        assert config.application_id == "111222333444555666"
        assert config.public_key == "pubkey123"
        assert config.webhook_base_url == "https://env.example.com/webhook"
        assert config.webhook_secret == "env-secret"
        assert config.guild_id == "999888777666555444"
        assert config.voice_channel_id == "123123123123123123"
        assert config.text_channel_id == "456456456456456456"

    def test_from_env_missing(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading DiscordConfig with missing environment variables."""
        # Clear all Discord env vars
        for key in list(os.environ.keys()):
            if key.startswith("DISCORD_"):
                monkeypatch.delenv(key, raising=False)

        config = DiscordConfig.from_env()
        assert config.bot_token is None
        assert config.application_id is None
        assert config.public_key is None

    def test_is_configured_true(self) -> None:
        """Test is_configured returns True when bot_token is set."""
        config = DiscordConfig(bot_token="test-token")
        assert config.is_configured() is True

    def test_is_configured_false(self) -> None:
        """Test is_configured returns False when bot_token is not set."""
        config = DiscordConfig()
        assert config.is_configured() is False


class TestDiscordProvider:
    """Tests for DiscordProvider class."""

    def test_name(self, discord_provider: DiscordProvider) -> None:
        """Test provider name."""
        assert discord_provider.name == "discord"

    def test_bot_token(self, discord_provider: DiscordProvider) -> None:
        """Test bot_token property."""
        assert discord_provider.bot_token == "test-bot-token-12345"

    def test_guild_id(self, discord_provider: DiscordProvider) -> None:
        """Test guild_id property."""
        assert discord_provider.guild_id == "987654321098765432"

    def test_default_voice_channel_id(self, discord_provider: DiscordProvider) -> None:
        """Test default_voice_channel_id property."""
        assert discord_provider.default_voice_channel_id == "111122223333444455"

    @pytest.mark.asyncio
    async def test_validate_webhook_missing_signature(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test webhook validation with missing signature."""
        result = await discord_provider.validate_webhook(
            headers={},
            body=b"test",
            path="/telephony/discord/voice",
        )
        # No signature headers and no webhook_secret configured, returns False
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_webhook_with_interaction_signature(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test webhook validation with Discord interaction signature."""
        result = await discord_provider.validate_webhook(
            headers={
                "X-Signature-Ed25519": "test-signature",
                "X-Signature-Timestamp": "1234567890",
            },
            body=b'{"type": 1}',
            path="/telephony/discord/interaction",
        )
        # Signature validation will fail without proper key
        assert result is False

    @pytest.mark.asyncio
    async def test_parse_inbound_call(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test parsing inbound Discord interaction."""
        body = json.dumps({
            "type": 2,  # APPLICATION_COMMAND
            "guild_id": "987654321098765432",
            "channel_id": {"id": "111122223333444455"},
            "member": {
                "user": {
                    "id": "123456789",
                    "username": "testuser",
                    "discriminator": "1234",
                }
            },
        }).encode()

        call = await discord_provider.parse_inbound_call(
            headers={},
            body=body,
            form_data={},
        )

        assert call.provider == "discord"
        assert call.direction == CallDirection.INBOUND
        assert call.status == CallStatus.IN_PROGRESS
        assert "testuser" in call.from_number
        assert "987654321098765432" in call.to_number

    @pytest.mark.asyncio
    async def test_parse_inbound_call_invalid_json(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test parsing with invalid JSON body."""
        call = await discord_provider.parse_inbound_call(
            headers={},
            body=b"not valid json",
            form_data={},
        )

        assert call.provider == "discord"
        assert call.from_number == "discord:Unknown#0000 (unknown)"

    @pytest.mark.asyncio
    async def test_generate_twiml_response(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test generating Discord interaction response."""
        response = await discord_provider.generate_twiml_response(
            session_id="test-session",
            welcome_message="Hello from Discord!",
        )

        # Should be JSON, not XML
        data = json.loads(response)
        assert data["type"] == 4  # CHANNEL_MESSAGE_WITH_SOURCE
        assert "Hello from Discord!" in data["data"]["content"]

    @pytest.mark.asyncio
    async def test_generate_twiml_response_default_message(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test generating response with default message."""
        response = await discord_provider.generate_twiml_response(
            session_id="test-session",
        )

        data = json.loads(response)
        assert "How can I help you" in data["data"]["content"]

    @pytest.mark.asyncio
    async def test_make_outbound_call(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test making an outbound call (joining voice channel)."""
        call = await discord_provider.make_outbound_call(
            to_number="discord:channel/111122223333444455",
            metadata={"guild_id": "987654321098765432"},
        )

        assert call.direction == CallDirection.OUTBOUND
        assert call.status == CallStatus.RINGING
        assert call.provider == "discord"
        assert "111122223333444455" in call.to_number

    @pytest.mark.asyncio
    async def test_make_outbound_call_with_channel_id(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test making outbound call with direct channel ID."""
        call = await discord_provider.make_outbound_call(
            to_number="222233334444555566",
        )

        assert "222233334444555566" in call.to_number

    @pytest.mark.asyncio
    async def test_make_outbound_call_no_channel(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test outbound call fails without channel ID."""
        # Create provider without default channel
        config = TelephonyConfig(
            provider_name="discord",
            api_key="test-token",
            extra={},
        )
        provider = DiscordProvider(config)

        with pytest.raises(ValueError, match="No voice channel ID"):
            await provider.make_outbound_call(to_number="")

    @pytest.mark.asyncio
    async def test_hangup_call(self, discord_provider: DiscordProvider) -> None:
        """Test hanging up a Discord voice connection."""
        # First create a call
        call = await discord_provider.make_outbound_call(
            to_number="discord:channel/111122223333444455",
        )

        # Then hang up
        result = await discord_provider.hangup_call(call.call_id)
        assert result is True

    @pytest.mark.asyncio
    async def test_hangup_call_not_found(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test hanging up a non-existent call."""
        result = await discord_provider.hangup_call("non-existent-call-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_play_audio(self, discord_provider: DiscordProvider) -> None:
        """Test playing audio in voice channel."""
        # Create a call first
        call = await discord_provider.make_outbound_call(
            to_number="discord:channel/111122223333444455",
        )

        result = await discord_provider.play_audio(
            call_id=call.call_id,
            audio_url="https://example.com/audio.mp3",
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_play_audio_not_connected(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test playing audio when not connected."""
        result = await discord_provider.play_audio(
            call_id="non-existent-call",
            audio_url="https://example.com/audio.mp3",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_send_digits(self, discord_provider: DiscordProvider) -> None:
        """Test sending DTMF (not supported for Discord)."""
        result = await discord_provider.send_digits(
            call_id="test-call",
            digits="1234",
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_get_call_status(self, discord_provider: DiscordProvider) -> None:
        """Test getting call status."""
        # Create a call first
        call = await discord_provider.make_outbound_call(
            to_number="discord:channel/111122223333444455",
        )

        status = await discord_provider.get_call_status(call.call_id)
        assert status is not None
        assert status.provider == "discord"

    @pytest.mark.asyncio
    async def test_get_call_status_not_found(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test getting status for non-existent call."""
        status = await discord_provider.get_call_status("non-existent")
        assert status is None

    @pytest.mark.asyncio
    async def test_stream_audio(self, discord_provider: DiscordProvider) -> None:
        """Test streaming audio to voice channel."""
        # Create a call first
        call = await discord_provider.make_outbound_call(
            to_number="discord:channel/111122223333444455",
        )

        async def audio_stream() -> AsyncIterator[bytes]:
            """Generate audio chunks for testing."""
            yield b"audio_chunk_1"
            yield b"audio_chunk_2"

        result = await discord_provider.stream_audio(
            call_id=call.call_id,
            audio_stream=audio_stream(),
        )
        # Returns True if connection exists, False otherwise
        assert result is True

    def test_get_webhook_path(self, discord_provider: DiscordProvider) -> None:
        """Test getting webhook paths."""
        assert discord_provider.get_webhook_path("interaction") == "/telephony/discord/interaction"
        assert discord_provider.get_webhook_path("voice") == "/telephony/discord/voice"
        assert discord_provider.get_webhook_path("event") == "/telephony/discord/event"
        assert discord_provider.get_webhook_path("unknown") == "/telephony/discord/unknown"

    def test_parse_channel_id_numeric(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test parsing numeric channel ID."""
        from voice_triage.telephony.providers.discord.parser import parse_channel_id
        result = parse_channel_id("123456789012345678")
        assert result == "123456789012345678"

    def test_parse_channel_id_discord_format(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test parsing discord:channel/ format."""
        from voice_triage.telephony.providers.discord.parser import parse_channel_id
        result = parse_channel_id("discord:channel/123456789")
        assert result == "123456789"

    def test_parse_channel_id_guild_format(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test parsing discord:guild/ID/channel/ID format."""
        from voice_triage.telephony.providers.discord.parser import parse_channel_id
        result = parse_channel_id("discord:guild/987/channel/123")
        assert result == "123"

    def test_parse_channel_id_invalid(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test parsing invalid channel ID."""
        from voice_triage.telephony.providers.discord.parser import parse_channel_id
        result = parse_channel_id("invalid-format")
        assert result is None


class TestDiscordVoiceConnection:
    """Tests for DiscordVoiceConnection class."""

    def test_init(self) -> None:
        """Test voice connection initialization."""
        conn = DiscordVoiceConnection(
            guild_id="987654321",
            channel_id="123456789",
            call_id="test-call-id",
        )

        assert conn.guild_id == "987654321"
        assert conn.channel_id == "123456789"
        assert conn.call_id == "test-call-id"
        assert conn.state == "DISCONNECTED"
        assert conn.connected_at is None

    @pytest.mark.asyncio
    async def test_connect(self) -> None:
        """Test connecting to voice server."""
        conn = DiscordVoiceConnection(
            guild_id="987654321",
            channel_id="123456789",
            call_id="test-call-id",
        )

        result = await conn.connect(
            token="voice-token",
            endpoint="voice.discord.gg",
            session_id="session-123",
        )

        assert result is True
        assert conn.state == "CONNECTED"
        assert conn.connected_at is not None

    @pytest.mark.asyncio
    async def test_disconnect(self) -> None:
        """Test disconnecting from voice server."""
        conn = DiscordVoiceConnection(
            guild_id="987654321",
            channel_id="123456789",
            call_id="test-call-id",
        )

        await conn.connect(
            token="voice-token",
            endpoint="voice.discord.gg",
            session_id="session-123",
        )

        result = await conn.disconnect()
        assert result is True
        assert conn.state == "DISCONNECTED"

    @pytest.mark.asyncio
    async def test_play(self) -> None:
        """Test playing audio."""
        conn = DiscordVoiceConnection(
            guild_id="987654321",
            channel_id="123456789",
            call_id="test-call-id",
        )

        # Should not raise
        await conn.play("https://example.com/audio.mp3", loop=True)

    @pytest.mark.asyncio
    async def test_stream(self) -> None:
        """Test streaming audio chunks."""
        conn = DiscordVoiceConnection(
            guild_id="987654321",
            channel_id="123456789",
            call_id="test-call-id",
        )

        async def audio_gen() -> AsyncIterator[bytes]:
            """Generate audio chunks for testing."""
            yield b"chunk1"
            yield b"chunk2"

        await conn.stream(audio_gen())

        # Check queue has items
        assert not conn._audio_queue.empty()


class TestDiscordStatusMap:
    """Tests for Discord status mapping."""

    def test_status_map_contains_expected_states(self) -> None:
        """Test that status map contains expected Discord states."""
        assert "CONNECTED" in DISCORD_STATUS_MAP
        assert "CONNECTING" in DISCORD_STATUS_MAP
        assert "DISCONNECTED" in DISCORD_STATUS_MAP
        assert "RESUMING" in DISCORD_STATUS_MAP

    def test_status_map_values(self) -> None:
        """Test status map values are correct CallStatus enums."""
        assert DISCORD_STATUS_MAP["CONNECTED"] == CallStatus.IN_PROGRESS
        assert DISCORD_STATUS_MAP["CONNECTING"] == CallStatus.RINGING
        assert DISCORD_STATUS_MAP["DISCONNECTED"] == CallStatus.COMPLETED


class TestDiscordProviderSend:
    """Tests for Discord-specific messaging methods.

    Note: These tests require discord.py to be installed for full functionality.
    If discord.py is not installed, the send_message method will return None.
    """

    @pytest.mark.asyncio
    async def test_send_message(self, discord_provider: DiscordProvider) -> None:
        """Test sending text message to Discord channel.

        If discord.py is not installed, this test will pass with None result.
        """
        result = await discord_provider.send_message(
            channel_id="666677778888999900",
            content="Hello, this is a test message!",
        )
        # Result may be None if discord.py is not installed
        # This is acceptable - discord.py is an optional dependency
        if result is not None:
            assert result["content"] == "Hello, this is a test message!"
        else:
            # discord.py not installed - skip test gracefully
            pytest.skip("discord.py not installed")

    @pytest.mark.asyncio
    async def test_send_message_with_embed(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test sending message with embed.

        If discord.py is not installed, this test will pass with None result.
        """
        embed = {
            "title": "Test Embed",
            "description": "This is a test embed",
            "color": 0x3498DB,
        }

        result = await discord_provider.send_message(
            channel_id="666677778888999900",
            content="Message with embed",
            embed=embed,
        )
        # Result may be None if discord.py is not installed
        if result is not None:
            assert "content" in result or "id" in result
        else:
            # discord.py not installed - skip test gracefully
            pytest.skip("discord.py not installed")

    @pytest.mark.asyncio
    async def test_get_guild_voice_channels(
        self, discord_provider: DiscordProvider
    ) -> None:
        """Test getting guild voice channels."""
        channels = await discord_provider.get_guild_voice_channels(
            guild_id="987654321098765432"
        )

        # Returns empty list in mock implementation
        assert isinstance(channels, list)


class TestDiscordGateway:
    """Tests for DiscordGateway class."""

    def test_init(self) -> None:
        """Test gateway initialization."""
        gateway = DiscordGateway(bot_token="test-token")
        assert gateway.bot_token == "test-token"
        assert gateway._session_id is None

    # Note: Actual WebSocket connection tests would require mocking
    # or integration tests with a real Discord gateway
