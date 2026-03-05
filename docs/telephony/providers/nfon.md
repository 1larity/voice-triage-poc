# NFON Integration

## What You Need

- NFON API client credentials.
- Account/tenant identifier.
- Public HTTPS callback URL.

## App Configuration

```bash
TELEPHONY_ENABLED=true

NFON_CLIENT_ID=...
NFON_CLIENT_SECRET=...
NFON_ACCOUNT_ID=...
NFON_WEBHOOK_BASE_URL=https://your-public-host
NFON_WEBHOOK_SECRET=...
NFON_DEFAULT_FROM_NUMBER=+44...
NFON_USE_UK_ENDPOINT=true
```

## NFON Portal Configuration

1. Create integration app and webhook subscription.
2. Set webhook endpoint:
   - `https://your-public-host/telephony/nfon/voice`
3. Set signing secret to match `NFON_WEBHOOK_SECRET`.
4. Ensure `X-NFON-Signature` is sent (HMAC-SHA256 hex over raw body).

## End-to-End Verification

- Trigger inbound call event.
- Confirm session start and speech turn routing.

## Local Signature Smoke Test

```bash
BODY='{"call":{"callId":"nfon-1","from":"+447700900001","to":"+447700900002","status":"ringing","direction":"inbound"}}'
SIG="$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$NFON_WEBHOOK_SECRET" | sed 's/^.* //')"
curl -i http://127.0.0.1:8000/telephony/nfon/voice \
  -H "Content-Type: application/json" \
  -H "X-NFON-Signature: $SIG" \
  -d "$BODY"
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
