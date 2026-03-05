# Telephony Operations Runbook

This runbook covers secret rotation, token expiry handling, and incident rollback.

## Secret Inventory

| Provider | Secrets / Tokens |
|---|---|
| Twilio | `TWILIO_AUTH_TOKEN` |
| Vonage | `VONAGE_API_SECRET`, `VONAGE_WEBHOOK_SECRET` |
| SIP | `SIP_WEBHOOK_SECRET` |
| Gamma | `GAMMA_WEBHOOK_SECRET` |
| BT | `BT_WEBHOOK_TOKEN` |
| RingCentral | `RINGCENTRAL_API_SECRET`, `RINGCENTRAL_WEBHOOK_SECRET` |
| Zoom | `ZOOM_API_SECRET`, `ZOOM_WEBHOOK_SECRET` |
| Teams | `TEAMS_CLIENT_SECRET`, `TEAMS_WEBHOOK_SECRET` |
| CircleLoop | `CIRCLELOOP_API_SECRET`, `CIRCLELOOP_WEBHOOK_SECRET` |
| NFON | `NFON_API_SECRET`, `NFON_WEBHOOK_SECRET` |
| Discord | `DISCORD_BOT_TOKEN`, `DISCORD_WEBHOOK_SECRET` |
| Avaya | `AVAYA_WEBHOOK_SECRET`, `AVAYA_PASSWORD` |

## Rotation Cadence

- High-risk production secrets: every 30 days.
- Standard provider secrets/tokens: every 90 days.
- Immediate rotation after suspected leakage, operator offboarding, or failed auth anomalies.

## Standard Rotation Procedure

1. Create a maintenance window and identify affected providers.
2. Generate new secret/token in provider portal.
3. Update secret store/environment values.
4. Restart service instance to load new values.
5. Run smoke checks:
   - `make telephony-contract`
   - `make telephony-smoke-local`
   - For live endpoint: `make telephony-smoke-remote BASE_URL=https://<public-host>`
6. Place a first-call verification using [First-Call Acceptance](./FIRST_CALL_ACCEPTANCE.md).
7. Revoke old provider secret/token only after successful verification.
8. Record rotation in ops change log.

## Token Expiry Runbook

Use for OAuth-style credentials (Teams, Zoom, RingCentral, potentially others).

1. Detect expiry symptoms:
   - repeated 401/403 from provider APIs,
   - subscription renewals failing,
   - outbound call API failures.
2. Verify client credentials in portal are valid and not revoked.
3. Rotate client secret if near expiry or unknown status.
4. Re-run provider-specific acceptance checks.
5. If still failing, capture provider request/response IDs and escalate to provider support.

## Emergency Rollback

1. Restore last known-good secret values from secure vault history.
2. Restart service.
3. Validate inbound webhooks for affected providers.
4. If needed, temporarily disable affected provider in environment and keep others active.
5. Open incident timeline with:
   - time detected,
   - providers impacted,
   - mitigation actions,
   - recovery time.

## Monitoring Signals

Track these as alerts:

- webhook `403` spike per provider,
- webhook `422` spike per provider,
- sudden drop in inbound session creation,
- repeated provider auth failures during outbound/status operations,
- call sessions not being cleaned up after terminal statuses.

## On-Call Quick Commands

```bash
curl -s http://127.0.0.1:8000/telephony/health
curl -s http://127.0.0.1:8000/telephony/providers
curl -s http://127.0.0.1:8000/telephony/capabilities
make telephony-contract
make telephony-smoke-local
```
