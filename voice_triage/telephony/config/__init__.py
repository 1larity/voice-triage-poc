"""Telephony configuration module.

This module provides configuration management for all telephony providers.
Each provider has its own configuration class in a separate file.

Example usage:
    from voice_triage.telephony.config import TwilioConfig, TelephonySettings

    # Load Twilio config from environment
    twilio_config = TwilioConfig.from_env()

    # Load all telephony settings
    settings = TelephonySettings.from_env()
"""

from voice_triage.telephony.config.avaya import AvayaConfig
from voice_triage.telephony.config.base import _env_bool
from voice_triage.telephony.config.circleloop import CircleLoopConfig
from voice_triage.telephony.config.discord import DiscordConfig
from voice_triage.telephony.config.nfon import NFONConfig
from voice_triage.telephony.config.ringcentral import RingCentralConfig
from voice_triage.telephony.config.settings import (
    TelephonySettings,
    load_telephony_settings,
)
from voice_triage.telephony.config.sip import BTConfig, GammaConfig, SIPConfig
from voice_triage.telephony.config.teams import TeamsConfig
from voice_triage.telephony.config.twilio import TwilioConfig
from voice_triage.telephony.config.vonage import VonageConfig
from voice_triage.telephony.config.zoom import ZoomConfig

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
