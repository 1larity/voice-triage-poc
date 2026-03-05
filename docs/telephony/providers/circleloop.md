# CircleLoop Integration

## What You Need

- CircleLoop API credentials.
- Public HTTPS callback URL.

## App Configuration

```bash
TELEPHONY_ENABLED=true

CIRCLELOOP_API_KEY=...
CIRCLELOOP_API_SECRET=...
CIRCLELOOP_WEBHOOK_BASE_URL=https://your-public-host
CIRCLELOOP_WEBHOOK_SECRET=...
CIRCLELOOP_DEFAULT_FROM_NUMBER=+44...
```

## CircleLoop Configuration

1. Create API app credentials.
2. Set webhook endpoint:
   - `https://your-public-host/telephony/circleloop/voice`
3. Configure signing secret to match `CIRCLELOOP_WEBHOOK_SECRET`.
4. Ensure events include `X-CircleLoop-Signature` (HMAC-SHA256 hex over raw body).

## End-to-End Verification

- Trigger inbound call webhook from CircleLoop.
- Confirm call session creation and prompt playback.

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
