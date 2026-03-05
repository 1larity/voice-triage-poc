# Telephony OOB Execution Checklist

Goal: every provider can be configured from docs and support a real multi-turn voice conversation end-to-end.

Last updated: 2026-03-05

## Phase 0 - Tracking + Baseline

- [x] Split provider setup into one doc per provider.
- [x] Add provider functional gaps doc.
- [x] Add Discord step-by-step target-system setup guide.
- [x] Add machine-readable provider capability matrix in code.
- [x] Add `/telephony/capabilities` endpoint for runtime visibility.
- [x] Add per-provider go-live checklist blocks in docs.

## Phase 1 - Security + Webhook Correctness

- [x] Case-insensitive header lookup helper for webhook auth.
- [x] Harden Vonage webhook validation (no permissive auth pass).
- [x] Harden Discord HMAC fallback validation.
- [x] Echo Teams validation token challenge.
- [x] Enforce SIP source IP allowlist.
- [x] Add replay-window validation for signed webhooks (timestamp/nonce where available).
- [x] Add rate limiting controls for telephony webhook routes.

## Phase 2 - Core Conversation Loop Reliability

- [x] Confirm generic route loop `/voice` -> `/voice/{call_id}` works across providers.
- [x] Improve transcript extraction for RingCentral/Zoom/Teams/CircleLoop/Avaya.
- [x] Add strict inbound payload validation guardrails (required call fields).
- [x] Add provider-specific missing-field diagnostics (422 with actionable detail).
- [x] Add robust session cleanup on provider-specific terminal states.

## Phase 3 - Provider E2E Enablement

### Wave 1 (Twilio, Vonage, SIP/Gamma/BT)
- [ ] Validate full live inbound call path with real provider accounts.
- [ ] Validate speech callback loop and transcript extraction against real payloads.
- [ ] Validate outbound call + hangup path against real accounts.

### Wave 2 (RingCentral, Zoom, NFON, CircleLoop)
- [ ] Validate inbound event to full conversation loop with real payloads.
- [ ] Validate outbound call and status flow with real accounts.

### Wave 3 (Teams, Discord)
- [ ] Teams: production Graph subscription lifecycle and media flow validation.
- [ ] Discord: implement true voice channel conversation bridge (live audio in/out + transcription loop).

## Phase 4 - Test Harness + Fixtures

- [x] Add webhook security-focused tests.
- [x] Add provider contract fixtures (signed webhook payload corpus per provider).
- [x] Add smoke test runner scripts per provider (local and remote URL modes).
- [x] Add CI job for telephony contract test subset.

## Phase 5 - Documentation Completion

- [x] Add explicit target-portal screenshots/field mappings (where possible).
- [x] Add per-provider first-call acceptance checklist.
- [x] Add provider-specific troubleshooting decision trees.
- [x] Add operator runbook for rotation of secrets and token expiry.

## Current Sprint (active)

- [x] Implement provider capability matrix + endpoint.
- [x] Add strict payload validation framework and wire first providers.
- [x] Expand provider docs with go-live checklist blocks.
- [x] Implement signed-webhook replay protection strategy.
- [x] Add telephony route-level rate limiting controls.
- [x] Add provider-specific terminal-state session cleanup.
- [x] Add signed webhook contract fixture corpus and execution harness.
- [x] Add smoke runner for local contract mode and remote URL mode.
- [x] Add telephony operations docs set (mappings, acceptance, troubleshooting, runbook).
