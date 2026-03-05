# Zoom Phone Integration

## What You Need

- Zoom Phone license.
- Server-to-Server OAuth app.
- Webhook secret configured in Zoom.

## App Configuration

```bash
TELEPHONY_ENABLED=true

ZOOM_ACCOUNT_ID=...
ZOOM_CLIENT_ID=...
ZOOM_CLIENT_SECRET=...
ZOOM_WEBHOOK_BASE_URL=https://your-public-host
ZOOM_WEBHOOK_SECRET=...
ZOOM_DEFAULT_FROM_NUMBER=+44...
```

## Zoom Marketplace / Admin Configuration

1. Create Server-to-Server OAuth app.
2. Grant required Zoom Phone scopes.
3. Configure webhook endpoint:
   - `https://your-public-host/telephony/zoom/voice`
4. Configure webhook secret to match `ZOOM_WEBHOOK_SECRET`.

## End-to-End Verification

- Trigger Zoom Phone inbound event.
- Confirm response and continued turn handling.

## Local Signature Smoke Test

```bash
BODY='{"event":"phone.callee_answered","payload":{"object":{"call_id":"zoom-1","from":"+447700900001","to":"+447700900002","status":"ringing","direction":"inbound"}}}'
SIG="v0=$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$ZOOM_WEBHOOK_SECRET" | sed 's/^.* //')"
curl -i http://127.0.0.1:8000/telephony/zoom/voice \
  -H "Content-Type: application/json" \
  -H "x-zm-signature: $SIG" \
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
