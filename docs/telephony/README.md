# Telephony How-To Guides

This folder contains provider-specific setup guides.

## Start Here

1. Enable telephony globally:

```bash
TELEPHONY_ENABLED=true
TELEPHONY_DEFAULT_PROVIDER=twilio
TELEPHONY_WEBHOOK_RATE_LIMIT_PER_MINUTE=120
TELEPHONY_WEBHOOK_REPLAY_WINDOW_SECONDS=300
```

2. Start the app:

```bash
uv run voice_triage web
# or
uv run voice_triage api
```

3. Verify routes/providers:

```bash
curl -s http://127.0.0.1:8000/telephony/providers
curl -s http://127.0.0.1:8000/telephony/health
curl -s http://127.0.0.1:8000/telephony/capabilities
```

## Provider Guides

- [Twilio](./providers/twilio.md)
- [Vonage / Nexmo](./providers/vonage.md)
- [SIP (Generic)](./providers/sip.md)
- [Gamma](./providers/gamma.md)
- [BT](./providers/bt.md)
- [RingCentral](./providers/ringcentral.md)
- [Zoom Phone](./providers/zoom.md)
- [Microsoft Teams](./providers/teams.md)
- [CircleLoop](./providers/circleloop.md)
- [NFON](./providers/nfon.md)
- [Discord](./providers/discord.md)
- [Avaya](./providers/avaya.md)

## Session Lifecycle (All Providers)

- `POST /telephony/{provider}/voice` creates a new conversation session.
- Provider webhook payload is parsed into a `PhoneCall`.
- Session metadata includes `call_id`, `from_number`, `to_number`, and `provider`.
- Follow-up turns should post to `POST /telephony/{provider}/voice/{call_id}`.
- Status/events should post to `/telephony/{provider}/status/{call_id}` or `/event/{call_id}`.

## Verification

- Contract fixtures: `tests/fixtures/telephony_webhooks/`
- Contract tests: `uv run pytest -q tests/test_telephony_webhook_contract_fixtures.py`
- Smoke runner: [Telephony Smoke Tests](./SMOKE_TESTS.md)
- Portal mappings + screenshot pack: [Portal Field Mappings](./PORTAL_FIELD_MAPPINGS.md)
- First-call sign-off: [First-Call Acceptance](./FIRST_CALL_ACCEPTANCE.md)
- Incident diagnosis: [Troubleshooting Decision Trees](./TROUBLESHOOTING.md)
- Secret/token operations: [Operations Runbook](./OPERATIONS_RUNBOOK.md)

## Readiness Gaps

See [Provider Functional Gaps](./PROVIDER_GAPS.md).
