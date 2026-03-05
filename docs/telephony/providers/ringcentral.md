# RingCentral Integration

## What You Need

- RingCentral developer app credentials.
- Account/extension with call permissions.
- Public HTTPS URL for webhook callbacks.

## App Configuration

```bash
TELEPHONY_ENABLED=true

RINGCENTRAL_CLIENT_ID=...
RINGCENTRAL_CLIENT_SECRET=...
RINGCENTRAL_ACCOUNT_ID=...
RINGCENTRAL_JWT_TOKEN=...      # or username/password flow
RINGCENTRAL_USERNAME=...
RINGCENTRAL_PASSWORD=...
RINGCENTRAL_EXTENSION=
RINGCENTRAL_WEBHOOK_BASE_URL=https://your-public-host
RINGCENTRAL_WEBHOOK_SECRET=verification-token
RINGCENTRAL_DEFAULT_FROM_NUMBER=+44...
RINGCENTRAL_USE_UK_ENDPOINT=true
```

## RingCentral Portal Configuration

1. Create RingCentral app and grant telephony/webhook scopes.
2. Create webhook subscription for inbound call/session events.
3. Set event delivery URL to:
   - `https://your-public-host/telephony/ringcentral/voice`
4. Set verification token to match `RINGCENTRAL_WEBHOOK_SECRET`.

## End-to-End Verification

- Trigger inbound call event.
- Confirm app accepts webhook and returns call-control JSON.

## Security Notes

- If `RINGCENTRAL_WEBHOOK_SECRET` is set, requests must include matching `Verification-Token` header.

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
