# Vonage / Nexmo Integration

## What You Need

- Vonage account with Voice API enabled.
- Vonage application and linked number.
- Public HTTPS URL reachable by Vonage.

## App Configuration

```bash
TELEPHONY_ENABLED=true

VONAGE_API_KEY=...
VONAGE_API_SECRET=...
VONAGE_WEBHOOK_BASE_URL=https://your-public-host
VONAGE_DEFAULT_FROM_NUMBER=+44...
VONAGE_APPLICATION_ID=...
VONAGE_PRIVATE_KEY_PATH=/path/to/private.key

# Optional bearer-token webhook validation (for gateway/proxy setups)
VONAGE_WEBHOOK_SECRET=
```

## Vonage Dashboard Configuration

1. Create or open a Vonage Voice application.
2. Configure application webhooks:
   - Answer URL: `https://your-public-host/telephony/vonage/voice`
   - Event URL: `https://your-public-host/telephony/vonage/event/{call_id}`
3. Link your virtual number to this application.
4. Enable webhook signing (recommended) so requests include `X-Vonage-Signature`.

## End-to-End Verification

1. Start app.
2. Call your Vonage number.
3. Confirm:
   - App answers with NCCO.
   - Speech input is posted back and processed.

## Local Webhook Smoke Test

```bash
curl -i http://127.0.0.1:8000/telephony/vonage/voice \
  -H "Content-Type: application/json" \
  -d '{"uuid":"uuid-1","from":"+447700900001","to":"+447700900002","status":"ringing","direction":"inbound"}'
```

## Security Notes

- Preferred: `X-Vonage-Signature` validation (HMAC with `VONAGE_API_SECRET`).
- Optional: bearer-token validation via `VONAGE_WEBHOOK_SECRET`.

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
