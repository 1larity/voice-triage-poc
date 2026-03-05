# Twilio Integration

## What You Need

- Twilio account with a voice-capable number.
- Public HTTPS URL reachable by Twilio.
- App running with telephony enabled.

## App Configuration

```bash
TELEPHONY_ENABLED=true
TELEPHONY_DEFAULT_PROVIDER=twilio

TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WEBHOOK_BASE_URL=https://your-public-host
TWILIO_DEFAULT_FROM_NUMBER=+44...
```

## Twilio Console Configuration

1. Buy or select a voice-capable number.
2. Open the number settings.
3. Under `Voice` / `A call comes in`:
   - Webhook URL: `https://your-public-host/telephony/twilio/voice`
   - Method: `HTTP POST`
4. Save.

Twilio receives call-control XML from the app. The app then sets follow-up speech callbacks to `/telephony/twilio/voice/{call_id}` automatically.

## End-to-End Verification

1. Start app: `uv run voice_triage web`.
2. Confirm provider registration:
   - `curl -s http://127.0.0.1:8000/telephony/health`
3. Call the Twilio number.
4. Confirm:
   - Welcome message plays.
   - Your spoken response is processed.
   - Follow-up prompt is returned.

## Local Signature Smoke Test

```bash
BODY='CallSid=CA123&From=%2B447700900001&To=%2B447700900002&CallStatus=ringing&Direction=inbound'
URL="${TWILIO_WEBHOOK_BASE_URL%/}/telephony/twilio/voice"
SIG="$(printf "%s%s" "$URL" "$BODY" | openssl dgst -sha1 -hmac "$TWILIO_AUTH_TOKEN" -binary | openssl base64)"
curl -i "$URL" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -H "X-Twilio-Signature: $SIG" \
  --data "$BODY"
```

## Troubleshooting

- `403 Invalid webhook signature`:
  - `TWILIO_WEBHOOK_BASE_URL` must exactly match public URL Twilio calls.
- Inbound call rings but no voice flow:
  - Ensure number webhook points to `/telephony/twilio/voice`.

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
