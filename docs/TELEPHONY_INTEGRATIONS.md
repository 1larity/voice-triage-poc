# UK Telephony Integration Progress

This document tracks the implementation status of UK business phone system integrations.

## Overview

Integrating with existing business phone infrastructure used by UK councils to handle incoming customer calls.

## Integration Status

| Provider | Config | Implementation | Tests | Status |
|----------|--------|----------------|-------|--------|
| Discord | [ ] | [ ] | [ ] | Not Started |
| Avaya | [ ] | [ ] | [ ] | Not Started |
| Cisco CUCM | [ ] | [ ] | [ ] | Not Started |
| Mitel | [ ] | [ ] | [ ] | Not Started |

---

## 1. Discord Integration

**Purpose:** Enable voice triage for councils with Discord community presence.

**Integration Type:** WebSocket-based voice client with Bot API

**Technical Requirements:**
- Discord Bot token authentication
- Voice WebSocket for real-time audio
- Opus codec support
- Gateway connection for events

**Files:**
- [x] `voice_triage/telephony/discord_provider.py`
- [x] `voice_triage/telephony/config.py` (DiscordConfig)
- [x] `tests/test_telephony_discord.py`

**Status:** Completed

**Notes:**
- Requires `discord.py` package (optional dependency)
- Supports text and voice channel interactions
- Ed25519 signature validation for webhooks
- 39 tests passing, 2 skipped (discord.py not installed)

---

## 2. Avaya Integration

**Purpose:** Connect to Avaya PBX systems commonly used in UK councils.

**Integration Type:** SIP trunking with Avaya-specific webhook APIs

**Technical Requirements:**
- SIP trunk connectivity
- Avaya Aura Contact Center API
- Webhook event handling

**Files:**
- [ ] `voice_triage/telephony/avaya_provider.py`
- [ ] `voice_triage/telephony/config.py` (AvayaConfig)
- [ ] `tests/test_telephony_avaya.py`

**Status:** Not Started

---

## 3. Cisco CUCM Integration

**Purpose:** Connect to Cisco Unified Communications Manager deployments.

**Integration Type:** Cisco Webex Calling API / SIP trunking

**Technical Requirements:**
- Cisco Webex API authentication
- CUCM SIP trunk configuration
- UCCX/UCCCE webhook support

**Files:**
- [ ] `voice_triage/telephony/cisco_provider.py`
- [ ] `voice_triage/telephony/config.py` (CiscoConfig)
- [ ] `tests/test_telephony_cisco.py`

**Status:** Not Started

---

## 4. Mitel Integration

**Purpose:** Connect to Mitel phone systems used by mid-sized councils.

**Integration Type:** MiCloud API / SIP trunking

**Technical Requirements:**
- Mitel MiCloud Connect API
- SIP trunk fallback
- MiVoice Business integration

**Files:**
- [ ] `voice_triage/telephony/mitel_provider.py`
- [ ] `voice_triage/telephony/config.py` (MitelConfig)
- [ ] `tests/test_telephony_mitel.py`

**Status:** Not Started

---

## Completed Integrations

### Existing Providers (Pre-installed)

| Provider | Type | UK Council Usage |
|----------|------|------------------|
| Microsoft Teams | Direct Routing | High |
| Generic SIP | SIP Trunking | High |
| Gamma Telecom | UK SIP | High |
| BT | UK SIP | High |
| RingCentral | Cloud UC | Medium |
| NFON | Cloud PBX | Medium |
| CircleLoop | UK Cloud | Low |
| Zoom Phone | Cloud UC | Low |
| Twilio | Cloud API | Variable |
| Vonage | Cloud API | Variable |

---

## Notes

- All integrations must pass `ruff check`, `mypy`, and `pytest`
- Docstring coverage must be 100% for new modules
- Follow existing provider patterns in `voice_triage/telephony/`
