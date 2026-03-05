# Provider Functional Gaps

This is a code-level gap list for improving real-world OOB success.

## Recently Closed

- Vonage webhook validation is no longer permissive for arbitrary `Authorization` headers.
- Discord HMAC fallback now validates `X-Discord-Signature` digest.
- Teams Graph validation-token challenge is now echoed by webhook handler.
- SIP allowlist is now enforced from webhook source IP headers.
- Provider webhook contract fixtures now exist for all primary providers under `tests/fixtures/telephony_webhooks/`.

## Remaining High Priority

- **Discord conversational loop is not fully wired to native Discord events**
  - Session creation works, but robust live voice stream + transcription bridge to follow-up turns still needs implementation.
- **Stronger payload schema validation needed**
  - Inbound payload parsing is permissive; stricter validation would reduce production surprises.

## Lower Priority / Quality

- **Real-time streaming methods are placeholders for multiple providers**
  - `stream_audio` often logs warnings and returns `False`.
- **Outbound provisioning checks**
  - Some providers could pre-validate required numbers/resources before attempting outbound calls.
- **End-to-end provider simulation fixtures**
  - Extend signed fixture corpus with full inbound/event payload variants from live provider captures.

## Suggested Next Implementation Order

1. Expand Discord native voice event flow into stable multi-turn transcript callbacks.
2. Add strict JSON schema validation for inbound provider webhook payloads.
3. Extend provider simulation fixture suites from signature validation to full parse/response loops.
4. Improve streaming support where current implementations are placeholders.
