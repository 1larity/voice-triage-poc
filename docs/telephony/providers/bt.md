# BT Integration

BT runs through the SIP provider with BT bearer-token validation.

## App Configuration

```bash
TELEPHONY_ENABLED=true

BT_SIP_SERVER=...
BT_SIP_PORT=5060
BT_SIP_USERNAME=...
BT_SIP_PASSWORD=...
BT_SIP_DOMAIN=...
BT_SIP_TRANSPORT=tls
BT_WEBHOOK_BASE_URL=https://your-public-host
BT_WEBHOOK_TOKEN=your-bt-token
BT_DEFAULT_FROM_NUMBER=+44...
SIP_ALLOWED_WEBHOOK_IPS=...
```

## BT / SBC Configuration

1. Configure BT SIP trunk into SBC.
2. Configure webhook bridge target:
   - `https://your-public-host/telephony/bt/voice`
3. Configure auth header on webhook requests:
   - `Authorization: Bearer <BT_WEBHOOK_TOKEN>`
4. Pass source IP for allowlist controls.

## End-to-End Verification

- Call BT DID.
- Confirm call is answered and multi-turn responses continue.

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
