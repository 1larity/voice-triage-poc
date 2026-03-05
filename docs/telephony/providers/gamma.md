# Gamma Integration

Gamma runs through the SIP provider with Gamma-specific signature validation.

## App Configuration

```bash
TELEPHONY_ENABLED=true

GAMMA_SIP_SERVER=...
GAMMA_SIP_PORT=5060
GAMMA_SIP_USERNAME=...
GAMMA_SIP_PASSWORD=...
GAMMA_SIP_DOMAIN=...
GAMMA_SIP_TRANSPORT=tcp
GAMMA_WEBHOOK_BASE_URL=https://your-public-host
GAMMA_WEBHOOK_SECRET=...
GAMMA_DEFAULT_FROM_NUMBER=+44...
SIP_ALLOWED_WEBHOOK_IPS=...
```

## Gamma / SBC Configuration

1. Configure Gamma SIP trunk to terminate on your SBC.
2. Configure SBC webhook bridge to post inbound events to:
   - `https://your-public-host/telephony/gamma/voice`
3. Add signature header:
   - `X-Gamma-Signature = HMAC-SHA256(raw_body, GAMMA_WEBHOOK_SECRET)`
4. Pass source IP via `X-Forwarded-For` or `X-Source-IP`.

## Local Signature Smoke Test

```bash
BODY='{"call_id":"gamma-1","from":"+447700900001","to":"+447700900002","status":180}'
SIG="$(printf "%s" "$BODY" | openssl dgst -sha256 -hmac "$GAMMA_WEBHOOK_SECRET" | sed 's/^.* //')"
curl -i http://127.0.0.1:8000/telephony/gamma/voice \
  -H "Content-Type: application/json" \
  -H "X-Gamma-Signature: $SIG" \
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
