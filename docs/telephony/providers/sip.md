# SIP (Generic) Integration

This provider expects a SIP edge/SBC/gateway that converts SIP signaling/events into HTTP webhooks.

## What You Need

- SIP trunk from your carrier.
- SBC/gateway (for example Asterisk, FreeSWITCH, Kamailio + webhook bridge).
- Public HTTPS endpoint reachable by your SBC/gateway.

## App Configuration

```bash
TELEPHONY_ENABLED=true

SIP_SERVER=sip.provider.example
SIP_PORT=5060
SIP_USERNAME=...
SIP_PASSWORD=...
SIP_DOMAIN=provider.example
SIP_TRANSPORT=udp
SIP_WEBHOOK_BASE_URL=https://your-public-host
SIP_WEBHOOK_SECRET=shared-secret
SIP_DEFAULT_FROM_NUMBER=+44...
SIP_ALLOWED_WEBHOOK_IPS=198.51.100.10,203.0.113.0/24
```

## Gateway / Target System Configuration

1. Route inbound DID calls to your IVR/webhook bridge.
2. Configure bridge to POST inbound events to:
   - `https://your-public-host/telephony/sip/voice`
3. Include headers:
   - `X-SIP-Secret: <SIP_WEBHOOK_SECRET>` (if set)
   - `X-Forwarded-For` or `X-Source-IP` for allowlist checks
4. Send JSON with at least:
   - `call_id`, `from`, `to`, `status`

## End-to-End Verification

1. Start app.
2. Place inbound call to SIP DID.
3. Confirm call reaches app and assistant prompt plays.

## Local Webhook Smoke Test

```bash
curl -i http://127.0.0.1:8000/telephony/sip/voice \
  -H "Content-Type: application/json" \
  -H "X-SIP-Secret: shared-secret" \
  -H "X-Source-IP: 198.51.100.10" \
  -d '{"call_id":"sip-1","from":"sip:+447700900001@example.com","to":"sip:+447700900002@example.com","status":180}'
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
