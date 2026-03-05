"""Telephony configuration settings.

This module provides configuration management for telephony providers,
supporting environment variables and configuration files.

.. deprecated::
    Import from voice_triage.telephony.config instead.
    This module maintains backward compatibility by re-exporting all symbols.
"""

from voice_triage.telephony.config import (
    AvayaConfig,
    BTConfig,
    CircleLoopConfig,
    DiscordConfig,
    GammaConfig,
    NFONConfig,
    RingCentralConfig,
    SIPConfig,
    TeamsConfig,
    TelephonySettings,
    TwilioConfig,
    VonageConfig,
    ZoomConfig,
    _env_bool,
    load_telephony_settings,
)

__all__ = [
    "AvayaConfig",
    "BTConfig",
    "CircleLoopConfig",
    "DiscordConfig",
    "GammaConfig",
    "NFONConfig",
    "RingCentralConfig",
    "SIPConfig",
    "TeamsConfig",
    "TelephonySettings",
    "TwilioConfig",
    "VonageConfig",
    "ZoomConfig",
    "_env_bool",
    "load_telephony_settings",
]
