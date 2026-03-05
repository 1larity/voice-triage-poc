# Telephony Smoke Tests

This project provides a fixture-driven smoke runner for telephony webhooks:

- Script: `scripts/telephony_smoke_runner.py`
- Fixture corpus: `tests/fixtures/telephony_webhooks/`

## Local Provider Mode

Runs provider `validate_webhook(...)` logic directly (no web server required):

```bash
uv run python scripts/telephony_smoke_runner.py --mode local
```

Optional provider filter:

```bash
uv run python scripts/telephony_smoke_runner.py --mode local --provider twilio --provider vonage
```

## Remote Endpoint Mode

Posts fixture payloads to live webhook routes (local app or remote URL):

```bash
uv run python scripts/telephony_smoke_runner.py --mode remote --base-url http://127.0.0.1:8000
```

For public tunnel / non-local target:

```bash
uv run python scripts/telephony_smoke_runner.py --mode remote --base-url https://your-public-host
```

Notes:

- In remote mode, expected-valid fixtures accept `200` or `422` (signature passed, payload may still fail strict schema checks).
- Expected-invalid fixtures require `403`.
- Use `--only-valid` to skip expected-invalid signature cases.
