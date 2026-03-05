# Microsoft Teams Direct Routing Integration

## What You Need

- Microsoft 365 tenant with Teams Phone / Direct Routing.
- SBC configured for Direct Routing.
- Azure app registration with Graph cloud-communications permissions.

## App Configuration

```bash
TELEPHONY_ENABLED=true

TEAMS_TENANT_ID=...
TEAMS_CLIENT_ID=...
TEAMS_CLIENT_SECRET=...
TEAMS_WEBHOOK_BASE_URL=https://your-public-host
TEAMS_WEBHOOK_SECRET=client-state-secret
TEAMS_DEFAULT_FROM_NUMBER=+44...
TEAMS_SIP_DOMAIN=...
TEAMS_SBC_FQDN=...
```

## Teams / Azure Configuration

1. Register Azure app for Graph communications APIs.
2. Grant and admin-consent required Graph permissions.
3. Configure webhook/notification URL in your Teams call integration flow:
   - `https://your-public-host/telephony/teams/voice`
4. Use `clientState` value equal to `TEAMS_WEBHOOK_SECRET`.
5. Configure Direct Routing/SBC to route target numbers into Teams call flow.

## Validation Token Challenge

- The webhook handler now echoes `validationToken` query values for Graph validation challenges.

## End-to-End Verification

1. Trigger Teams notification to `/telephony/teams/voice`.
2. Confirm session starts and follow-up prompts continue.

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
