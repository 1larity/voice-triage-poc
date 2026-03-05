# Avaya Integration

## What You Need

- Avaya Aura/AES or IP Office API access.
- Service account credentials.
- Public HTTPS callback endpoint.

## App Configuration

```bash
TELEPHONY_ENABLED=true

AVAYA_SERVER_HOST=...
AVAYA_SERVER_PORT=8443
AVAYA_USERNAME=...
AVAYA_PASSWORD=...
AVAYA_EXTENSION=5001
AVAYA_WEBHOOK_BASE_URL=https://your-public-host
AVAYA_WEBHOOK_SECRET=optional-hmac-secret
AVAYA_USE_SSL=true
AVAYA_DEFAULT_FROM_NUMBER=+44...
AVAYA_AES_ENABLED=false
AVAYA_IP_OFFICE_MODE=false
```

## Avaya Target System Configuration

1. Create integration/service user with call-control permissions.
2. Configure Avaya event/webhook delivery to:
   - `https://your-public-host/telephony/avaya/voice`
3. Choose auth mode:
   - HMAC signature (`X-Avaya-Signature` or `X-Webhook-Signature`) using `AVAYA_WEBHOOK_SECRET`
   - or HTTP Basic auth using `AVAYA_USERNAME` / `AVAYA_PASSWORD`
4. Ensure payload includes call identifiers (`callId` or `ucid`).

## End-to-End Verification

- Trigger inbound call to monitored extension/queue.
- Confirm session starts and call control response is returned.

## Local Basic Auth Smoke Test

```bash
curl -i http://127.0.0.1:8000/telephony/avaya/voice \
  -H "Content-Type: application/json" \
  -u "$AVAYA_USERNAME:$AVAYA_PASSWORD" \
  -d '{"event":"call_initiated","callId":"avaya-1","callingNumber":"+447700900001","calledNumber":"+447700900002","state":"alerting"}'
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
