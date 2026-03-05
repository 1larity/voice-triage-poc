# Discord Integration (Step-by-Step)

This setup maps Discord interactions to the telephony webhook contract used by the app.

## What You Need

- Discord application + bot.
- Target Discord server (guild).
- One voice channel and one text channel.
- Public HTTPS URL for interaction/webhook traffic.

## App Configuration

```bash
TELEPHONY_ENABLED=true

DISCORD_BOT_TOKEN=...
DISCORD_APPLICATION_ID=...
DISCORD_PUBLIC_KEY=... # required for Ed25519 interaction validation
DISCORD_WEBHOOK_BASE_URL=https://your-public-host
DISCORD_WEBHOOK_SECRET=optional-fallback-secret
DISCORD_GUILD_ID=...
DISCORD_VOICE_CHANNEL_ID=...
DISCORD_TEXT_CHANNEL_ID=...
```

## 1. Create Discord App + Bot

1. Open Discord Developer Portal.
2. Create application.
3. Copy:
   - Application ID -> `DISCORD_APPLICATION_ID`
   - Public Key -> `DISCORD_PUBLIC_KEY`
4. Create bot user and copy token -> `DISCORD_BOT_TOKEN`.

## 2. Invite Bot To Guild

1. `OAuth2 > URL Generator`:
   - Scopes: `bot`, `applications.commands`
   - Bot permissions: View Channels, Send Messages, Connect, Speak
2. Open generated URL and add bot to your guild.

## 3. Create/Select Channels And IDs

1. Enable Developer Mode in Discord client.
2. Create/select:
   - voice channel for conversation
   - text channel for interaction messages
3. Copy IDs:
   - guild ID -> `DISCORD_GUILD_ID`
   - voice channel ID -> `DISCORD_VOICE_CHANNEL_ID`
   - text channel ID -> `DISCORD_TEXT_CHANNEL_ID`

## 4. Configure Discord Callback

Set Discord webhook/interaction target to:

- `https://your-public-host/telephony/discord/voice`

## 5. How Session Start Works

- Incoming Discord payload to `/telephony/discord/voice` is parsed into a `PhoneCall`.
- Call ID format: `discord_{guild_id}_{channel_id}_{timestamp}`.
- Handler creates a new conversation session and stores mapping `call_id -> session_id`.

## 6. How Follow-Up Turns Work

- Follow-up route: `POST /telephony/discord/voice/{call_id}`.
- Transcript fields: `transcript` or `speech` (extend parser if your Discord bridge sends different shape).

## 7. Security Modes

- Preferred: Discord interaction Ed25519 headers:
  - `X-Signature-Ed25519`
  - `X-Signature-Timestamp`
  - `DISCORD_PUBLIC_KEY` must be configured (automatic public-key fetch is not implemented).
- Fallback: HMAC mode with:
  - `DISCORD_WEBHOOK_SECRET`
  - `X-Discord-Signature` header

## 8. Minimal Local Test

```bash
curl -i http://127.0.0.1:8000/telephony/discord/voice \
  -H "Content-Type: application/json" \
  -H "X-Discord-Signature: $(printf '{"type":2}' | openssl dgst -sha256 -hmac "$DISCORD_WEBHOOK_SECRET" | sed 's/^.* //')" \
  -d '{"type":2}'
```

## Go-Live Checklist

- [ ] Provider account/app credentials created.
- [ ] Public HTTPS webhook URL reachable from provider.
- [ ] Inbound webhook configured to `/telephony/{provider}/voice` equivalent.
- [ ] Webhook auth/signature configured and verified.
- [ ] One successful inbound session created.
- [ ] Multi-turn speech loop verified (`/voice/{call_id}`).
- [ ] Terminal status/event cleanup path verified.
- [ ] Secrets stored securely and rotated in ops runbook.

## Shared Operations References

- [First-Call Acceptance](../FIRST_CALL_ACCEPTANCE.md)
- [Troubleshooting Decision Trees](../TROUBLESHOOTING.md)
- [Operations Runbook](../OPERATIONS_RUNBOOK.md)
- [Portal Field Mappings](../PORTAL_FIELD_MAPPINGS.md)
