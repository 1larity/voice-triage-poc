# Telephony Integration Status

Current implementation status for provider modules in this repository.

## Implemented Providers

These are present in the provider registry and have configuration wiring in
`voice_triage/telephony/config/settings.py`:

- Twilio
- Vonage (`nexmo` alias)
- SIP (generic)
- Gamma
- BT
- RingCentral
- Zoom Phone
- Microsoft Teams Direct Routing
- CircleLoop
- NFON
- Discord
- Avaya (`avaya_aes` and `avaya_ip_office` aliases)

Provider guides:

- [Telephony Guide Index](./telephony/README.md)
- [Twilio](./telephony/providers/twilio.md)
- [Vonage / Nexmo](./telephony/providers/vonage.md)
- [SIP](./telephony/providers/sip.md)
- [Gamma](./telephony/providers/gamma.md)
- [BT](./telephony/providers/bt.md)
- [RingCentral](./telephony/providers/ringcentral.md)
- [Zoom](./telephony/providers/zoom.md)
- [Teams](./telephony/providers/teams.md)
- [CircleLoop](./telephony/providers/circleloop.md)
- [NFON](./telephony/providers/nfon.md)
- [Discord](./telephony/providers/discord.md)
- [Avaya](./telephony/providers/avaya.md)
- [Provider Functional Gaps](./telephony/PROVIDER_GAPS.md)
- [Telephony Smoke Tests](./telephony/SMOKE_TESTS.md)
- [Portal Field Mappings](./telephony/PORTAL_FIELD_MAPPINGS.md)
- [First-Call Acceptance](./telephony/FIRST_CALL_ACCEPTANCE.md)
- [Troubleshooting Decision Trees](./telephony/TROUBLESHOOTING.md)
- [Operations Runbook](./telephony/OPERATIONS_RUNBOOK.md)

## Not Implemented

No first-class provider modules exist yet for:

- Cisco CUCM
- Mitel

## Notes

- Runtime provider registration is visible at `GET /telephony/health`.
- Full list of compiled-in provider names is visible at `GET /telephony/providers`.
