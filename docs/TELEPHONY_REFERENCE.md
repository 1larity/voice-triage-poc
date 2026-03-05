# Telephony Integration Reference

Provider setup has been split into separate guides under [`docs/telephony/`](./telephony/README.md).

## Provider How-Tos

- [Twilio](./telephony/providers/twilio.md)
- [Vonage / Nexmo](./telephony/providers/vonage.md)
- [SIP (Generic)](./telephony/providers/sip.md)
- [Gamma](./telephony/providers/gamma.md)
- [BT](./telephony/providers/bt.md)
- [RingCentral](./telephony/providers/ringcentral.md)
- [Zoom Phone](./telephony/providers/zoom.md)
- [Microsoft Teams](./telephony/providers/teams.md)
- [CircleLoop](./telephony/providers/circleloop.md)
- [NFON](./telephony/providers/nfon.md)
- [Discord](./telephony/providers/discord.md)
- [Avaya](./telephony/providers/avaya.md)

## Shared Runtime Behavior

- Telephony routes are mounted under `/telephony`.
- A provider session is created when `POST /telephony/{provider}/voice` is called.
- Follow-up turns should post to `POST /telephony/{provider}/voice/{call_id}`.
- Status/event updates should post to `/telephony/{provider}/status/{call_id}` or `/event/{call_id}`.

## Global Configuration

```bash
TELEPHONY_ENABLED=true
TELEPHONY_DEFAULT_PROVIDER=twilio
TELEPHONY_WELCOME_MESSAGE="Hello, and welcome to the council services helpline. How can I help you today?"
TELEPHONY_SPEECH_LANGUAGE=en-GB
TELEPHONY_SPEECH_TIMEOUT=5
TELEPHONY_MAX_CALL_DURATION_SECONDS=3600
TELEPHONY_WEBHOOK_RATE_LIMIT_PER_MINUTE=120
TELEPHONY_WEBHOOK_REPLAY_WINDOW_SECONDS=300
```

## Route Discovery

```bash
curl -s http://127.0.0.1:8000/telephony/providers
curl -s http://127.0.0.1:8000/telephony/health
curl -s http://127.0.0.1:8000/telephony/capabilities
```

## Contract Fixtures

- Signed webhook contract fixtures live in `tests/fixtures/telephony_webhooks/`.
- Validate them with:

```bash
uv run pytest -q tests/test_telephony_webhook_contract_fixtures.py
```

## Smoke Runner

- Fixture-driven local and remote smoke checks are documented in [Telephony Smoke Tests](./telephony/SMOKE_TESTS.md).

## Operations Docs

- Provider portal mappings: [Portal Field Mappings](./telephony/PORTAL_FIELD_MAPPINGS.md)
- First-call sign-off by provider: [First-Call Acceptance](./telephony/FIRST_CALL_ACCEPTANCE.md)
- Provider-specific incident trees: [Troubleshooting Decision Trees](./telephony/TROUBLESHOOTING.md)
- Secret/token lifecycle procedures: [Operations Runbook](./telephony/OPERATIONS_RUNBOOK.md)

## Functional Gaps

Before production rollout, review [Provider Functional Gaps](./telephony/PROVIDER_GAPS.md).
