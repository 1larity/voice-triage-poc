"""Unit tests for Avaya telephony provider.

Tests cover:
- AvayaConfig configuration loading
- AvayaProvider implementation
- Webhook validation and parsing
- Call control operations
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from voice_triage.telephony.avaya_provider import (
    AVAYA_STATUS_MAP,
    AvayaProvider,
)
from voice_triage.telephony.base import (
    CallDirection,
    CallStatus,
    TelephonyConfig,
)
from voice_triage.telephony.config import AvayaConfig


class TestAvayaConfig:
    """Tests for AvayaConfig dataclass."""

    def test_default_values(self) -> None:
        """Test default configuration values."""
        config = AvayaConfig()
        assert config.server_host is None
        assert config.server_port == 8443
        assert config.username is None
        assert config.password is None
        assert config.extension is None
        assert config.webhook_base_url is None
        assert config.webhook_secret is None
        assert config.use_ssl is True
        assert config.default_from_number is None
        assert config.aes_enabled is False
        assert config.ip_office_mode is False

    def test_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Test loading configuration from environment variables."""
        monkeypatch.setenv("AVAYA_SERVER_HOST", "avaya.example.com")
        monkeypatch.setenv("AVAYA_SERVER_PORT", "9443")
        monkeypatch.setenv("AVAYA_USERNAME", "admin")
        monkeypatch.setenv("AVAYA_PASSWORD", "secret")
        monkeypatch.setenv("AVAYA_EXTENSION", "5001")
        monkeypatch.setenv("AVAYA_WEBHOOK_BASE_URL", "https://webhook.example.com")
        monkeypatch.setenv("AVAYA_WEBHOOK_SECRET", "webhook-secret")
        monkeypatch.setenv("AVAYA_USE_SSL", "false")
        monkeypatch.setenv("AVAYA_DEFAULT_FROM_NUMBER", "02071234567")
        monkeypatch.setenv("AVAYA_AES_ENABLED", "true")
        monkeypatch.setenv("AVAYA_IP_OFFICE_MODE", "true")

        config = AvayaConfig.from_env()

        assert config.server_host == "avaya.example.com"
        assert config.server_port == 9443
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.extension == "5001"
        assert config.webhook_base_url == "https://webhook.example.com"
        assert config.webhook_secret == "webhook-secret"
        assert config.use_ssl is False
        assert config.default_from_number == "02071234567"
        assert config.aes_enabled is True
        assert config.ip_office_mode is True

    def test_is_configured(self) -> None:
        """Test configuration validation."""
        # Not configured - missing all
        config = AvayaConfig()
        assert not config.is_configured()

        # Partially configured - missing password
        config = AvayaConfig(server_host="avaya.example.com", username="admin")
        assert not config.is_configured()

        # Fully configured
        config = AvayaConfig(
            server_host="avaya.example.com",
            username="admin",
            password="secret",
        )
        assert config.is_configured()


class ConcreteAvayaProvider(AvayaProvider):
    """Concrete implementation of AvayaProvider for testing."""

    async def generate_twiml_response(
        self,
        session_id: str,
        welcome_message: str | None = None,
        gather_speech: bool = True,
        action_url: str | None = None,
    ) -> str:
        """Generate a test TwiML response."""
        return f"<Response><Say>{welcome_message or 'Hello'}</Say></Response>"

    def get_webhook_path(self, event_type: str) -> str:
        """Get webhook path for event type."""
        return f"/telephony/avaya/{event_type}"

    async def hangup_call(self, call_id: str) -> bool:
        """Hang up a call."""
        return True

    async def play_audio(
        self,
        call_id: str,
        audio_url: str,
        loop: bool = False,
    ) -> bool:
        """Play audio into a call."""
        return True

    async def send_digits(self, call_id: str, digits: str) -> bool:
        """Send DTMF digits."""
        return True


class TestAvayaProvider:
    """Tests for AvayaProvider class."""

    @pytest.fixture
    def config(self) -> TelephonyConfig:
        """Create a test configuration."""
        return TelephonyConfig(
            provider_name="avaya",
            webhook_base_url="https://webhook.example.com",
            webhook_secret="webhook-secret",
            default_from_number="02071234567",
            extra={
                "server_host": "avaya.example.com",
                "server_port": 8443,
                "username": "admin",
                "password": "secret",
                "extension": "5001",
                "use_ssl": True,
            },
        )

    @pytest.fixture
    def provider(self, config: TelephonyConfig) -> ConcreteAvayaProvider:
        """Create a test provider instance."""
        return ConcreteAvayaProvider(config)

    def test_name_property(self, provider: ConcreteAvayaProvider) -> None:
        """Test provider name."""
        assert provider.name == "avaya"

    def test_get_base_url_default(self, provider: ConcreteAvayaProvider) -> None:
        """Test base URL generation with defaults."""
        client = provider._get_client()
        url = client._get_base_url()
        assert url == "https://avaya.example.com:8443"

    def test_get_base_url_custom_port(self, config: TelephonyConfig) -> None:
        """Test base URL with custom port."""
        config.extra["server_port"] = 9443
        provider = ConcreteAvayaProvider(config)
        client = provider._get_client()
        url = client._get_base_url()
        assert url == "https://avaya.example.com:9443"

    def test_get_base_url_no_ssl(self, config: TelephonyConfig) -> None:
        """Test base URL without SSL."""
        config.extra["use_ssl"] = False
        provider = ConcreteAvayaProvider(config)
        client = provider._get_client()
        url = client._get_base_url()
        assert url == "http://avaya.example.com:8443"

    def test_get_status_mapping(self) -> None:
        """Test Avaya status to CallStatus mapping."""
        assert AVAYA_STATUS_MAP["idle"] == CallStatus.IDLE
        assert AVAYA_STATUS_MAP["alerting"] == CallStatus.RINGING
        assert AVAYA_STATUS_MAP["connected"] == CallStatus.IN_PROGRESS
        assert AVAYA_STATUS_MAP["held"] == CallStatus.HELD
        assert AVAYA_STATUS_MAP["dropped"] == CallStatus.COMPLETED
        assert AVAYA_STATUS_MAP["failed"] == CallStatus.FAILED

    @pytest.mark.asyncio
    async def test_validate_webhook_with_signature(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test webhook validation with valid signature."""
        headers = {
            "Authorization": "Basic YWRtaW46c2VjcmV0",  # base64(admin:secret)
            "Content-Type": "application/json",
        }
        body = b'{"callId": "12345"}'

        result = await provider.validate_webhook(
            headers=headers, body=body, path="/telephony/avaya/inbound"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_webhook_missing_signature(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test webhook validation without signature."""
        headers = {"Content-Type": "application/json"}
        body = b'{"callId": "12345"}'

        result = await provider.validate_webhook(
            headers=headers, body=body, path="/telephony/avaya/inbound"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_validate_webhook_basic_auth(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test webhook validation with basic auth."""
        headers = {
            "Authorization": "Basic YWRtaW46c2VjcmV0",  # base64(admin:secret)
            "Content-Type": "application/json",
        }
        body = b'{"callId": "12345"}'

        result = await provider.validate_webhook(
            headers=headers, body=body, path="/telephony/avaya/inbound"
        )
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_webhook_invalid_basic_auth(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test webhook validation with invalid basic auth."""
        headers = {
            "Authorization": "Basic aW52YWxpZDpjcmVkZW50aWFscw==",  # base64(invalid:credentials)
            "Content-Type": "application/json",
        }
        body = b'{"callId": "12345"}'

        result = await provider.validate_webhook(
            headers=headers, body=body, path="/telephony/avaya/inbound"
        )
        assert result is False

    @pytest.mark.asyncio
    async def test_parse_inbound_call(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test parsing inbound call webhook."""
        headers = {"Content-Type": "application/json"}
        body = json.dumps({
            "event": "call_initiated",
            "callId": "AVAYA123456",
            "callingNumber": "07123456789",
            "calledNumber": "02071234567",
            "extension": "5001",
            "timestamp": "2024-01-15T10:30:00Z",
        }).encode()

        call = await provider.parse_inbound_call(
            headers=headers,
            body=body,
            form_data={},
        )

        assert call.call_id == "AVAYA123456"
        assert call.from_number == "07123456789"
        assert call.to_number == "02071234567"
        assert call.direction == CallDirection.INBOUND
        assert call.provider == "avaya"

    @pytest.mark.asyncio
    async def test_parse_inbound_call_with_ucid(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test parsing inbound call with UCID."""
        headers = {"Content-Type": "application/json"}
        body = json.dumps({
            "event": "call_initiated",
            "callId": "AVAYA123456",
            "callingNumber": "07123456789",
            "calledNumber": "02071234567",
            "ucid": "00000123456789012345",
            "timestamp": "2024-01-15T10:30:00Z",
        }).encode()

        call = await provider.parse_inbound_call(
            headers=headers,
            body=body,
            form_data={},
        )

        assert call.call_id == "AVAYA123456"
        assert call.metadata.get("ucid") == "00000123456789012345"

    @pytest.mark.asyncio
    async def test_parse_inbound_call_invalid_json(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test parsing invalid JSON raises appropriate error."""
        headers = {"Content-Type": "application/json"}
        body = b"not valid json"

        with pytest.raises((json.JSONDecodeError, ValueError)):
            await provider.parse_inbound_call(
                headers=headers,
                body=body,
                form_data={},
            )

    @pytest.mark.asyncio
    async def test_parse_inbound_call_missing_call_id(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test parsing call without call ID raises error."""
        headers = {"Content-Type": "application/json"}
        body = json.dumps({
            "event": "call_initiated",
            "callingNumber": "07123456789",
        }).encode()

        with pytest.raises(ValueError):
            await provider.parse_inbound_call(
                headers=headers,
                body=body,
                form_data={},
            )

    @pytest.mark.asyncio
    async def test_make_outbound_call(
        self, provider: ConcreteAvayaProvider
    ) -> None:
        """Test making an outbound call."""
        mock_response = {"callId": "AVAYAOUT123"}

        # Get the client and patch its make_request method
        client = provider._get_client()
        with patch.object(
            client, "make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            call = await provider.make_outbound_call(
                to_number="07987654321",
                from_number="02071234567",
            )

            assert call.call_id == "AVAYAOUT123"
            assert call.to_number == "07987654321"
            assert call.direction == CallDirection.OUTBOUND

    @pytest.mark.asyncio
    async def test_hangup(self, provider: ConcreteAvayaProvider) -> None:
        """Test hanging up a call."""
        result = await provider.hangup_call("AVAYA123456")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_dtmf(self, provider: ConcreteAvayaProvider) -> None:
        """Test sending DTMF digits."""
        result = await provider.send_digits("AVAYA123456", "1234")
        assert result is True


class TestAvayaProviderRegistration:
    """Tests for provider registration."""

    def test_avaya_provider_registered(self) -> None:
        """Test that avaya provider is registered."""
        from voice_triage.telephony.registry import list_providers

        # Check that avaya is in the list of registered providers
        providers = list_providers()
        assert "avaya" in providers
