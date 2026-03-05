# Telephony Portal Field Mappings

Use this as the source-of-truth mapping from each provider portal into app configuration.

## Screenshot Capture Pack

For each provider section below, capture screenshots for:

1. Credential/app page (client ID/key location).
2. Webhook/callback URL configuration page.
3. Security/signature/token page.
4. Number/routing assignment page.

Store captures under `docs/telephony/screenshots/<provider>/`.

## Twilio

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| Phone Numbers -> Active numbers -> Voice | A call comes in URL | `https://<public-host>/telephony/twilio/voice` |
| Phone Numbers -> Active numbers -> Voice | HTTP Method | `POST` |
| Account -> API keys/tokens | Account SID | `TWILIO_ACCOUNT_SID` |
| Account -> API keys/tokens | Auth Token | `TWILIO_AUTH_TOKEN` |
| Number settings | Voice-capable number | `TWILIO_DEFAULT_FROM_NUMBER` |

## Vonage / Nexmo

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| Voice app -> Webhooks | Answer URL | `https://<public-host>/telephony/vonage/voice` |
| Voice app -> Webhooks | Event URL | `https://<public-host>/telephony/vonage/event/{call_id}` |
| API settings | API Key | `VONAGE_API_KEY` |
| API settings | API Secret | `VONAGE_API_SECRET` |
| Voice app security | Signing/bearer secret | `VONAGE_WEBHOOK_SECRET` |

## SIP (Generic)

| Provider Portal / SBC | Portal Field | App Config / Value |
|---|---|---|
| SIP gateway webhook settings | Inbound webhook URL | `https://<public-host>/telephony/sip/voice` |
| SIP gateway webhook security | Shared secret | `SIP_WEBHOOK_SECRET` |
| SIP gateway allowlist | Allowed source IP/CIDR | `SIP_ALLOWED_WEBHOOK_IPS` |
| SIP trunk config | Server/peer host | `SIP_SERVER` |
| SIP trunk config | Port/transport/domain | `SIP_PORT`, `SIP_TRANSPORT`, `SIP_DOMAIN` |

## Gamma

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| Gamma SIP trunk eventing | Webhook URL | `https://<public-host>/telephony/gamma/voice` |
| Gamma webhook security | HMAC signing secret | `GAMMA_WEBHOOK_SECRET` |
| Gamma trunk config | SIP server and routing | `GAMMA_SIP_SERVER`, `GAMMA_SIP_DOMAIN` |

## BT

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| BT business voice webhooks | Webhook URL | `https://<public-host>/telephony/bt/voice` |
| BT webhook auth | Bearer token | `BT_WEBHOOK_TOKEN` |
| BT number assignment | Default from number | `BT_DEFAULT_FROM_NUMBER` |

## RingCentral

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| Developer app -> Subscriptions | Event delivery URL | `https://<public-host>/telephony/ringcentral/voice` |
| Developer app -> Security | Verification token | `RINGCENTRAL_WEBHOOK_SECRET` |
| Developer app -> Credentials | Client ID | `RINGCENTRAL_API_KEY` |
| Developer app -> Credentials | Client secret | `RINGCENTRAL_API_SECRET` |
| Account/extension settings | Account ID | `RINGCENTRAL_ACCOUNT_ID` (`account_sid`) |

## Zoom Phone

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| Zoom Marketplace app -> Webhooks | Event endpoint URL | `https://<public-host>/telephony/zoom/voice` |
| Zoom Marketplace app -> Webhooks | Secret token | `ZOOM_WEBHOOK_SECRET` |
| Zoom app credentials | Client ID | `ZOOM_API_KEY` |
| Zoom app credentials | Client Secret | `ZOOM_API_SECRET` |
| Zoom account settings | Account ID | `ZOOM_ACCOUNT_ID` (`account_sid`) |

## Microsoft Teams Direct Routing

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| Azure App Registration | Application (client) ID | `TEAMS_CLIENT_ID` |
| Azure App Registration | Client secret | `TEAMS_CLIENT_SECRET` |
| Azure tenant overview | Directory (tenant) ID | `TEAMS_TENANT_ID` |
| Graph subscription config | Notification URL | `https://<public-host>/telephony/teams/voice` |
| Graph subscription config | Client state | `TEAMS_WEBHOOK_SECRET` |
| Teams Direct Routing/SBC | SBC FQDN + SIP domain | `TEAMS_SBC_FQDN`, `TEAMS_SIP_DOMAIN` |

## CircleLoop

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| CircleLoop app/webhooks | Inbound webhook URL | `https://<public-host>/telephony/circleloop/voice` |
| CircleLoop app/webhooks | Signature secret | `CIRCLELOOP_WEBHOOK_SECRET` |
| CircleLoop developer settings | API key | `CIRCLELOOP_API_KEY` |
| CircleLoop developer settings | API secret | `CIRCLELOOP_API_SECRET` |

## NFON

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| NFON API/webhooks | Inbound webhook URL | `https://<public-host>/telephony/nfon/voice` |
| NFON API/webhooks | Signature secret | `NFON_WEBHOOK_SECRET` |
| NFON API credentials | API key | `NFON_API_KEY` |
| NFON API credentials | API secret | `NFON_API_SECRET` |

## Discord

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| Discord Developer Portal -> General | Application ID | `DISCORD_APPLICATION_ID` |
| Discord Developer Portal -> General | Public Key | `DISCORD_PUBLIC_KEY` |
| Discord Developer Portal -> Bot | Bot token | `DISCORD_BOT_TOKEN` |
| Interactions endpoint | Interaction URL | `https://<public-host>/telephony/discord/voice` |
| Guild/channel config | Guild/voice/text channel IDs | `DISCORD_GUILD_ID`, `DISCORD_VOICE_CHANNEL_ID`, `DISCORD_TEXT_CHANNEL_ID` |
| Optional webhook security | HMAC shared secret | `DISCORD_WEBHOOK_SECRET` |

## Avaya

| Provider Portal | Portal Field | App Config / Value |
|---|---|---|
| Avaya app/eventing | Inbound webhook URL | `https://<public-host>/telephony/avaya/voice` |
| Avaya app/security | HMAC secret | `AVAYA_WEBHOOK_SECRET` |
| Avaya app/security | Basic auth username/password | `AVAYA_USERNAME`, `AVAYA_PASSWORD` |
| Avaya routing | Default from number/endpoint | `AVAYA_DEFAULT_FROM_NUMBER` |
