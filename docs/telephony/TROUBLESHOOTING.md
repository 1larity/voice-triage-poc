# Telephony Troubleshooting Decision Trees

Use these trees in order: Global first, then provider-specific.

## Global Decision Tree

1. Does `GET /telephony/health` list the provider?
   - No: fix env vars, provider config, restart app.
   - Yes: continue.
2. Does inbound webhook return `403`?
   - Yes: signature/auth mismatch -> go to provider-specific auth tree.
   - No: continue.
3. Does inbound webhook return `422`?
   - Yes: payload schema mismatch -> compare provider payload with required `call_id/from/to` paths.
   - No: continue.
4. Session created but no follow-up turn?
   - Check callback route is `/telephony/{provider}/voice/{call_id}`.
5. Session never cleaned?
   - Ensure provider sends terminal status field and callback is wired to `/status/{call_id}` or `/event/{call_id}`.

## Twilio

1. `403 Invalid webhook signature`?
   - Verify `TWILIO_WEBHOOK_BASE_URL` exactly matches URL Twilio calls (scheme, host, path).
   - Confirm `TWILIO_AUTH_TOKEN` is current.
2. Call connects but no loop?
   - Confirm Twilio number voice URL points to `/telephony/twilio/voice`.

## Vonage / Nexmo

1. `403` on inbound?
   - If using signature mode, verify `X-Vonage-Signature` uses correct API secret.
   - If using bearer mode, verify `Authorization: Bearer ...` matches `VONAGE_WEBHOOK_SECRET`.
2. No status cleanup?
   - Verify event URL points to `/telephony/vonage/event/{call_id}`.

## SIP (Generic)

1. `403` immediately?
   - Confirm `X-SIP-Secret` value.
   - Confirm source IP is in `SIP_ALLOWED_WEBHOOK_IPS` (or remove allowlist for test).
2. `422` payload errors?
   - Ensure payload includes `call_id`, `from`, `to`.

## Gamma

1. Signature fail?
   - Confirm `X-Gamma-Signature` HMAC SHA256 matches `GAMMA_WEBHOOK_SECRET`.
2. Payload accepted but no conversation?
   - Validate callback path is `/telephony/gamma/voice`.

## BT

1. `403` on inbound?
   - Check `Authorization` bearer token equals `BT_WEBHOOK_TOKEN`.
2. Call received but no follow-up?
   - Confirm callback remains on `/telephony/bt/voice/{call_id}`.

## RingCentral

1. Validation fail?
   - Confirm `Verification-Token` equals `RINGCENTRAL_WEBHOOK_SECRET`.
2. Session not created?
   - Inspect payload field paths for `body.id` / `body.sessionId` and adjust mapping if tenant payload differs.

## Zoom Phone

1. Signature fail?
   - Ensure header format is `x-zm-signature: v0=<digest>`.
   - Confirm secret matches Zoom app webhook secret.
2. No transcript?
   - Compare payload with expected transcript paths and extend parser if required.

## Microsoft Teams Direct Routing

1. Graph validation challenge fails?
   - Ensure request includes `validationToken` and app endpoint is publicly reachable.
2. Notification rejected?
   - Confirm `clientState` equals `TEAMS_WEBHOOK_SECRET`.
3. Voice media issues?
   - Validate Graph permissions, subscription lifecycle, and SBC routing separately.

## CircleLoop

1. `403` on webhook?
   - Verify `X-CircleLoop-Signature` computed from raw body with `CIRCLELOOP_WEBHOOK_SECRET`.
2. No session cleanup?
   - Check terminal status values in callback payload (`completed`, `failed`, `busy`, etc.).

## NFON

1. Signature validation fails?
   - Validate `X-NFON-Signature` HMAC SHA256 against exact raw body.
2. Session not starting?
   - Ensure payload contains call object with stable call ID path (`call.callId`).

## Discord

1. Interaction validation fails?
   - Prefer Ed25519 headers (`X-Signature-Ed25519`, `X-Signature-Timestamp`) with valid `DISCORD_PUBLIC_KEY`.
   - Fallback path requires `X-Discord-Signature` and `DISCORD_WEBHOOK_SECRET`.
2. Can I do full voice conversation today?
   - Not yet. Native live voice-channel bridge is still a tracked gap.

## Avaya

1. Signature failures?
   - Validate `X-Avaya-Signature`/`X-Webhook-Signature` using `AVAYA_WEBHOOK_SECRET`.
2. Basic auth fallback fails?
   - Confirm header uses exact `AVAYA_USERNAME:AVAYA_PASSWORD` credentials.
3. Session not cleaned?
   - Verify status callback contains terminal state and reaches `/telephony/avaya/status/{call_id}`.
