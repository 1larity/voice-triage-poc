# First-Call Acceptance Checklists

Use these checklists when bringing a provider live for the first time.

## Global Preconditions

- App reachable on public HTTPS endpoint.
- `TELEPHONY_ENABLED=true`.
- Provider appears in `GET /telephony/health` and `GET /telephony/capabilities`.
- Provider webhook secret/token loaded from environment.

## Twilio

- [ ] Inbound number voice URL is `POST /telephony/twilio/voice`.
- [ ] Valid signed webhook returns call-control response (not `403`).
- [ ] Live inbound call creates session and welcome prompt plays.
- [ ] Follow-up speech posts to `/telephony/twilio/voice/{call_id}`.
- [ ] Completed call posts status callback and session cleanup occurs.

## Vonage / Nexmo

- [ ] Answer URL points to `/telephony/vonage/voice`.
- [ ] Event URL points to `/telephony/vonage/event/{call_id}`.
- [ ] Signature or bearer validation succeeds; invalid token is rejected.
- [ ] Multi-turn speech loop confirmed from live call.
- [ ] Terminal call status removes active session mapping.

## SIP (Generic)

- [ ] Webhook URL points to `/telephony/sip/voice`.
- [ ] `X-SIP-Secret` required and validated.
- [ ] Source IP allowlist blocks non-allowlisted origin.
- [ ] Inbound call payload fields (`call_id`, `from`, `to`) parse correctly.
- [ ] Status callback cleanup works for terminal states.

## Gamma

- [ ] Webhook URL points to `/telephony/gamma/voice`.
- [ ] `X-Gamma-Signature` validation works with configured secret.
- [ ] Inbound call enters voice loop and transcript is processed.
- [ ] Terminal event updates clear session.

## BT

- [ ] Webhook URL points to `/telephony/bt/voice`.
- [ ] Bearer token auth (`Authorization`) validates with `BT_WEBHOOK_TOKEN`.
- [ ] Inbound flow and follow-up prompts work end-to-end.
- [ ] Status cleanup confirmed on call completion/failure.

## RingCentral

- [ ] Event URL points to `/telephony/ringcentral/voice`.
- [ ] `Verification-Token` matches `RINGCENTRAL_WEBHOOK_SECRET`.
- [ ] Inbound event data creates a session and first prompt.
- [ ] Follow-up speech/event route stays on same call/session.
- [ ] Terminal state cleanup observed.

## Zoom Phone

- [ ] Webhook URL points to `/telephony/zoom/voice`.
- [ ] `x-zm-signature` validates with `ZOOM_WEBHOOK_SECRET`.
- [ ] Inbound event starts conversation and assistant speaks.
- [ ] Transcript extraction works for your Zoom payload shape.
- [ ] Completed/disconnected state cleans session.

## Microsoft Teams Direct Routing

- [ ] Graph notification URL points to `/telephony/teams/voice`.
- [ ] Graph validation token challenge is echoed successfully.
- [ ] `clientState` equals `TEAMS_WEBHOOK_SECRET` and validates.
- [ ] Inbound call notification starts session and conversation loop.
- [ ] Disconnected/terminated state cleans session.

## CircleLoop

- [ ] Webhook URL points to `/telephony/circleloop/voice`.
- [ ] `X-CircleLoop-Signature` validates.
- [ ] Inbound call and follow-up turn loop verified.
- [ ] `call_status` terminal updates remove session mapping.

## NFON

- [ ] Webhook URL points to `/telephony/nfon/voice`.
- [ ] `X-NFON-Signature` validates.
- [ ] Inbound payload parses call details and starts session.
- [ ] Follow-up turn processing remains stable for same call ID.
- [ ] Terminal call status cleanup verified.

## Discord

- [ ] Interaction/webhook URL points to `/telephony/discord/voice`.
- [ ] Ed25519 validation succeeds (or HMAC fallback with `X-Discord-Signature`).
- [ ] Session starts from inbound interaction payload.
- [ ] Follow-up webhook route works with generated call ID.
- [ ] Current limitation acknowledged: true live voice-channel bridge is pending.

## Avaya

- [ ] Webhook URL points to `/telephony/avaya/voice`.
- [ ] HMAC (`X-Avaya-Signature`/`X-Webhook-Signature`) validates.
- [ ] Basic auth fallback validates only configured credentials.
- [ ] Inbound call starts session and multi-turn loop.
- [ ] Terminal state cleanup verified from status callback.
