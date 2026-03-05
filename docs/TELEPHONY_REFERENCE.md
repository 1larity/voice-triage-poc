# Telephony Integration Reference

This document describes the telephony integration module for the Voice Triage POC, which enables the application to handle phone calls from popular UK telephony providers.

## Supported Providers

The following UK-popular telephony solutions are supported:

| Provider | Type | Description |
|----------|------|-------------|
| **Twilio** | Cloud API | Programmable voice platform with extensive UK coverage |
| **Vonage/Nexmo** | Cloud API | Cloud communications API (formerly Nexmo) |
| **SIP Trunking** | SIP | Generic SIP trunking for any provider |
| **Gamma Telecom** | SIP Trunking | Major UK SIP trunking provider |
| **BT** | SIP Trunking | British Telecom SIP trunking |
| **Virgin Media** | SIP Trunking | Virgin Media Business SIP |
| **TalkTalk** | SIP Trunking | TalkTalk Business SIP |

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Phone Call     │────▶│  Telephony       │────▶│  Conversation   │
│  (PSTN/VoIP)    │     │  Provider        │     │  Engine         │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Webhook         │
                        │  Endpoints       │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │  Voice Triage    │
                        │  REST API        │
                        └──────────────────┘
```

## Configuration

### Environment Variables

#### Enable Telephony

```bash
TELEPHONY_ENABLED=true
TELEPHONY_DEFAULT_PROVIDER=twilio
```

#### Twilio Configuration

```bash
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_WEBHOOK_BASE_URL=https://your-domain.com
TWILIO_DEFAULT_FROM_NUMBER=+441234567890
```

#### Vonage Configuration

```bash
VONAGE_API_KEY=your_api_key
VONAGE_API_SECRET=your_api_secret
VONAGE_WEBHOOK_BASE_URL=https://your-domain.com
VONAGE_DEFAULT_FROM_NUMBER=+441234567890
VONAGE_APPLICATION_ID=your_application_id
VONAGE_PRIVATE_KEY_PATH=/path/to/private.key
```

#### SIP Trunking Configuration

```bash
# Generic SIP
SIP_SERVER=sip.provider.com
SIP_PORT=5060
SIP_USERNAME=your_username
SIP_PASSWORD=your_password
SIP_DOMAIN=provider.com
SIP_TRANSPORT=udp  # udp, tcp, or tls
SIP_WEBHOOK_BASE_URL=https://your-domain.com
SIP_WEBHOOK_SECRET=your_webhook_secret
SIP_DEFAULT_FROM_NUMBER=+441234567890
SIP_ALLOWED_WEBHOOK_IPS=192.168.1.1,10.0.0.1

# Gamma Telecom (overrides SIP_*)
GAMMA_SIP_SERVER=gamma.sip.uk
GAMMA_SIP_USERNAME=your_gamma_username
# ... other GAMMA_* variables

# BT (overrides SIP_*)
BT_SIP_SERVER=bt.sip.uk
BT_WEBHOOK_TOKEN=your_bearer_token
# ... other BT_* variables
```

#### General Settings

```bash
TELEPHONY_WELCOME_MESSAGE="Hello, and welcome to the council services helpline."
TELEPHONY_SPEECH_LANGUAGE=en-GB
TELEPHONY_SPEECH_TIMEOUT=5
TELEPHONY_MAX_CALL_DURATION_SECONDS=3600
```

### Configuration File

Alternatively, use a JSON configuration file:

```json
{
  "enabled": true,
  "default_provider": "twilio",
  "twilio": {
    "account_sid": "your_account_sid",
    "auth_token": "your_auth_token",
    "webhook_base_url": "https://your-domain.com",
    "default_from_number": "+441234567890"
  },
  "vonage": {
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  },
  "welcome_message": "Hello, and welcome to the council services helpline.",
  "speech_language": "en-GB",
  "speech_timeout": 5
}
```

## API Endpoints

### Webhook Endpoints

All webhook endpoints are mounted under `/telephony/`:

#### Twilio

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telephony/twilio/voice` | POST | Handle inbound voice calls |
| `/telephony/twilio/voice/{call_id}` | POST | Handle speech input |
| `/telephony/twilio/status/{call_id}` | POST | Call status callbacks |

#### Vonage/Nexmo

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telephony/vonage/voice` | POST | Handle inbound voice calls |
| `/telephony/vonage/voice/{call_id}` | POST | Handle speech input |
| `/telephony/vonage/event/{call_id}` | POST | Event callbacks |
| `/telephony/nexmo/voice` | POST | Alias for Vonage |

#### SIP/Gamma/BT

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telephony/sip/voice` | POST | Handle inbound SIP calls |
| `/telephony/sip/voice/{call_id}` | POST | Handle speech input |
| `/telephony/sip/status/{call_id}` | POST | Status callbacks |
| `/telephony/gamma/voice` | POST | Gamma-specific endpoint |
| `/telephony/bt/voice` | POST | BT-specific endpoint |

#### Utility Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/telephony/health` | GET | Health check |
| `/telephony/providers` | GET | List available providers |

## Usage

### Integrating with FastAPI

```python
from fastapi import FastAPI
from voice_triage.telephony.config import load_telephony_settings
from voice_triage.telephony.webhooks import create_telephony_handler, create_telephony_router

app = FastAPI()

# Load settings
settings = load_telephony_settings()

# Create handler
handler = await create_telephony_handler(
    conversation_handler=your_conversation_handler,
    provider_configs=settings.to_provider_configs(),
)

# Mount telephony router
telephony_router = create_telephony_router(handler)
app.include_router(telephony_router)
```

### Making Outbound Calls

```python
from voice_triage.telephony.base import TelephonyConfig
from voice_triage.telephony.registry import get_provider

# Configure provider
config = TelephonyConfig(
    provider_name="twilio",
    account_sid="your_sid",
    auth_token="your_token",
    default_from_number="+441234567890",
)

# Get provider instance
provider = get_provider(config)

# Make a call
call = await provider.make_outbound_call(
    to_number="+449876543210",
    webhook_url="https://your-domain.com/telephony/twilio/voice",
)

print(f"Call initiated: {call.call_id}")
```

### Using Provider-Specific Features

#### Twilio Media Streams

```python
# Create real-time audio stream
stream_sid = await twilio_provider.create_media_stream(
    call_id="CA123...",
    websocket_url="wss://your-domain.com/media",
)
```

#### Vonage WebSocket Streaming

```python
# Create WebSocket stream for bidirectional audio
await vonage_provider.create_websocket_stream(
    call_id="uuid...",
    websocket_url="wss://your-domain.com/stream",
    sample_rate=8000,
)
```

## Provider-Specific Notes

### Twilio

- Uses TwiML (XML) for call control
- Supports real-time media streams via WebSocket
- Webhooks are signed with X-Twilio-Signature header
- Requires `twilio` Python package: `pip install twilio`

### Vonage/Nexmo

- Uses NCCO (JSON) for call control
- Supports WebSocket streaming
- Webhooks use JWT or HMAC signature validation
- Requires `vonage` Python package: `pip install vonage`

### SIP Trunking (Gamma, BT, etc.)

- Requires a SIP gateway that converts SIP events to HTTP webhooks
- Generic SIP provider can be customized for any SIP trunking service
- Supports UDP, TCP, and TLS transports
- DTMF via RFC 2833

## UK Phone Number Format

All phone numbers should be in E.164 format:

- UK mobile: `+447700900000`
- UK landline: `+441234567890`
- UK toll-free: `+448001234567`

## Security Considerations

1. **Webhook Validation**: Always validate webhook signatures in production
2. **HTTPS**: Use HTTPS for all webhook URLs
3. **IP Whitelisting**: Configure `SIP_ALLOWED_WEBHOOK_IPS` for SIP providers
4. **Secrets Management**: Store API keys and tokens securely (environment variables, vault, etc.)
5. **Rate Limiting**: Consider rate limiting webhook endpoints

## Troubleshooting

### Common Issues

1. **Webhook signature validation fails**
   - Verify `WEBHOOK_BASE_URL` matches your public URL
   - Check that auth tokens are correct

2. **Calls not connecting**
   - Verify phone numbers are in E.164 format
   - Check that from_number is provisioned with your provider

3. **Speech recognition not working**
   - Ensure `TELEPHONY_SPEECH_LANGUAGE` is set correctly (default: `en-GB`)
   - Check provider-specific speech settings

### Logging

Enable debug logging for telephony:

```python
import logging
logging.getLogger("voice_triage.telephony").setLevel(logging.DEBUG)
```

## Dependencies

The telephony module has optional dependencies based on provider:

```bash
# For Twilio
pip install twilio

# For Vonage
pip install vonage

# For SIP (requires SIP stack)
pip install pyvoip  # or similar SIP library
```

## License

This module is part of the Voice Triage POC project.
