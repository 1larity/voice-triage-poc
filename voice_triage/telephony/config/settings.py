"""Aggregated telephony settings for all providers.

This module provides the TelephonySettings class that aggregates
configuration for all telephony providers.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from voice_triage.telephony.config.avaya import AvayaConfig
from voice_triage.telephony.config.base import _env_bool
from voice_triage.telephony.config.circleloop import CircleLoopConfig
from voice_triage.telephony.config.discord import DiscordConfig
from voice_triage.telephony.config.nfon import NFONConfig
from voice_triage.telephony.config.ringcentral import RingCentralConfig
from voice_triage.telephony.config.sip import BTConfig, GammaConfig, SIPConfig
from voice_triage.telephony.config.teams import TeamsConfig
from voice_triage.telephony.config.twilio import TwilioConfig
from voice_triage.telephony.config.vonage import VonageConfig
from voice_triage.telephony.config.zoom import ZoomConfig


@dataclass
class TelephonySettings:
    """Aggregated telephony settings for all providers."""

    enabled: bool = False
    """Whether telephony integration is enabled."""

    default_provider: str = "twilio"
    """Default provider to use for outbound calls."""

    twilio: TwilioConfig = field(default_factory=TwilioConfig)
    """Twilio configuration."""

    vonage: VonageConfig = field(default_factory=VonageConfig)
    """Vonage configuration."""

    sip: SIPConfig = field(default_factory=SIPConfig)
    """Generic SIP configuration."""

    gamma: GammaConfig = field(default_factory=GammaConfig)
    """Gamma Telecom configuration."""

    bt: BTConfig = field(default_factory=BTConfig)
    """BT configuration."""

    ringcentral: RingCentralConfig = field(default_factory=RingCentralConfig)
    """RingCentral configuration."""

    zoom: ZoomConfig = field(default_factory=ZoomConfig)
    """Zoom Phone configuration."""

    teams: TeamsConfig = field(default_factory=TeamsConfig)
    """Microsoft Teams Direct Routing configuration."""

    circleloop: CircleLoopConfig = field(default_factory=CircleLoopConfig)
    """CircleLoop configuration."""

    nfon: NFONConfig = field(default_factory=NFONConfig)
    """NFON configuration."""

    discord: DiscordConfig = field(default_factory=DiscordConfig)
    """Discord configuration."""

    avaya: AvayaConfig = field(default_factory=AvayaConfig)
    """Avaya configuration."""

    welcome_message: str = (
        "Hello, and welcome to the council services helpline. "
        "How can I help you today?"
    )
    """Default welcome message for inbound calls."""

    speech_language: str = "en-GB"
    """Language for speech recognition."""

    speech_timeout: int = 5
    """Timeout in seconds for speech input."""

    max_call_duration_seconds: int = 3600
    """Maximum call duration in seconds (default: 1 hour)."""

    webhook_rate_limit_per_minute: int = 120
    """Per-provider/source-IP webhook request limit per minute."""

    webhook_replay_window_seconds: int = 300
    """Window for webhook replay detection and timestamp freshness checks."""

    @classmethod
    def from_env(cls) -> TelephonySettings:
        """Load all telephony settings from environment variables.

        Returns:
            TelephonySettings instance populated from environment variables.
        """
        enabled = _env_bool("TELEPHONY_ENABLED", default=False)

        return cls(
            enabled=enabled,
            default_provider=os.getenv("TELEPHONY_DEFAULT_PROVIDER", "twilio"),
            twilio=TwilioConfig.from_env(),
            vonage=VonageConfig.from_env(),
            sip=SIPConfig.from_env(),
            gamma=GammaConfig.from_env(),
            bt=BTConfig.from_env(),
            ringcentral=RingCentralConfig.from_env(),
            zoom=ZoomConfig.from_env(),
            teams=TeamsConfig.from_env(),
            circleloop=CircleLoopConfig.from_env(),
            nfon=NFONConfig.from_env(),
            discord=DiscordConfig.from_env(),
            avaya=AvayaConfig.from_env(),
            welcome_message=os.getenv(
                "TELEPHONY_WELCOME_MESSAGE",
                "Hello, and welcome to the council services helpline. How can I help you today?",
            ),
            speech_language=os.getenv("TELEPHONY_SPEECH_LANGUAGE", "en-GB"),
            speech_timeout=int(os.getenv("TELEPHONY_SPEECH_TIMEOUT", "5")),
            max_call_duration_seconds=int(os.getenv("TELEPHONY_MAX_CALL_DURATION_SECONDS", "3600")),
            webhook_rate_limit_per_minute=int(
                os.getenv("TELEPHONY_WEBHOOK_RATE_LIMIT_PER_MINUTE", "120")
            ),
            webhook_replay_window_seconds=int(
                os.getenv("TELEPHONY_WEBHOOK_REPLAY_WINDOW_SECONDS", "300")
            ),
        )

    @classmethod
    def from_file(cls, path: Path) -> TelephonySettings:
        """Load settings from a JSON configuration file.

        Args:
            path: Path to the configuration file.

        Returns:
            TelephonySettings instance.
        """
        if not path.exists():
            return cls()

        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            enabled=data.get("enabled", False),
            default_provider=data.get("default_provider", "twilio"),
            twilio=TwilioConfig(**data.get("twilio", {})),
            vonage=VonageConfig(**data.get("vonage", {})),
            sip=SIPConfig(**data.get("sip", {})),
            gamma=GammaConfig(**data.get("gamma", {})),
            bt=BTConfig(**data.get("bt", {})),
            ringcentral=RingCentralConfig(**data.get("ringcentral", {})),
            zoom=ZoomConfig(**data.get("zoom", {})),
            teams=TeamsConfig(**data.get("teams", {})),
            circleloop=CircleLoopConfig(**data.get("circleloop", {})),
            nfon=NFONConfig(**data.get("nfon", {})),
            discord=DiscordConfig(**data.get("discord", {})),
            avaya=AvayaConfig(**data.get("avaya", {})),
            welcome_message=data.get(
                "welcome_message",
                "Hello, and welcome to the council services helpline. How can I help you today?",
            ),
            speech_language=data.get("speech_language", "en-GB"),
            speech_timeout=data.get("speech_timeout", 5),
            max_call_duration_seconds=data.get("max_call_duration_seconds", 3600),
            webhook_rate_limit_per_minute=data.get("webhook_rate_limit_per_minute", 120),
            webhook_replay_window_seconds=data.get("webhook_replay_window_seconds", 300),
        )

    def get_configured_providers(self) -> list[str]:
        """Get list of providers that are properly configured.

        Returns:
            List of provider names that have valid configuration.
        """
        configured = []
        if self.twilio.is_configured():
            configured.append("twilio")
        if self.vonage.is_configured():
            configured.extend(["vonage", "nexmo"])
        if self.sip.is_configured():
            configured.append("sip")
        if self.gamma.is_configured():
            configured.append("gamma")
        if self.bt.is_configured():
            configured.append("bt")
        if self.ringcentral.is_configured():
            configured.append("ringcentral")
        if self.zoom.is_configured():
            configured.append("zoom")
        if self.teams.is_configured():
            configured.append("teams")
        if self.circleloop.is_configured():
            configured.append("circleloop")
        if self.nfon.is_configured():
            configured.append("nfon")
        if self.discord.is_configured():
            configured.append("discord")
        if self.avaya.is_configured():
            configured.extend(["avaya", "avaya_aes", "avaya_ip_office"])
        return configured

    def to_provider_configs(self) -> dict[str, dict[str, Any]]:
        """Convert to provider configuration dictionaries.

        Returns:
            Dictionary mapping provider names to their configurations.
        """
        configs: dict[str, dict[str, Any]] = {}

        if self.twilio.is_configured():
            configs["twilio"] = {
                "account_sid": self.twilio.account_sid,
                "auth_token": self.twilio.auth_token,
                "webhook_base_url": self.twilio.webhook_base_url,
                "default_from_number": self.twilio.default_from_number,
            }

        if self.vonage.is_configured():
            configs["vonage"] = {
                "api_key": self.vonage.api_key,
                "api_secret": self.vonage.api_secret,
                "webhook_base_url": self.vonage.webhook_base_url,
                "default_from_number": self.vonage.default_from_number,
                "webhook_secret": self.vonage.webhook_secret,
                "extra": {
                    "application_id": self.vonage.application_id,
                    "private_key_path": self.vonage.private_key_path,
                    "webhook_secret": self.vonage.webhook_secret,
                },
            }
            configs["nexmo"] = {
                **configs["vonage"],
                "extra": dict(configs["vonage"].get("extra", {})),
            }

        if self.sip.is_configured():
            configs["sip"] = {
                "webhook_base_url": self.sip.webhook_base_url,
                "default_from_number": self.sip.default_from_number,
                "extra": {
                    "sip_server": self.sip.sip_server,
                    "sip_port": self.sip.sip_port,
                    "sip_username": self.sip.sip_username,
                    "sip_password": self.sip.sip_password,
                    "sip_domain": self.sip.sip_domain,
                    "sip_transport": self.sip.sip_transport,
                    "webhook_secret": self.sip.webhook_secret,
                    "allowed_webhook_ips": self.sip.allowed_webhook_ips,
                },
            }

        if self.gamma.is_configured():
            configs["gamma"] = {
                "webhook_base_url": self.gamma.webhook_base_url,
                "default_from_number": self.gamma.default_from_number,
                "extra": {
                    "sip_server": self.gamma.sip_server,
                    "sip_port": self.gamma.sip_port,
                    "sip_username": self.gamma.sip_username,
                    "sip_password": self.gamma.sip_password,
                    "sip_domain": self.gamma.sip_domain,
                    "sip_transport": self.gamma.sip_transport,
                    "webhook_secret": self.gamma.webhook_secret,
                    "allowed_webhook_ips": self.gamma.allowed_webhook_ips,
                },
            }

        if self.bt.is_configured():
            configs["bt"] = {
                "webhook_base_url": self.bt.webhook_base_url,
                "default_from_number": self.bt.default_from_number,
                "extra": {
                    "sip_server": self.bt.sip_server,
                    "sip_port": self.bt.sip_port,
                    "sip_username": self.bt.sip_username,
                    "sip_password": self.bt.sip_password,
                    "sip_domain": self.bt.sip_domain,
                    "sip_transport": self.bt.sip_transport,
                    "webhook_secret": self.bt.webhook_secret,
                    "webhook_token": self.bt.webhook_token,
                    "allowed_webhook_ips": self.bt.allowed_webhook_ips,
                },
            }

        if self.ringcentral.is_configured():
            configs["ringcentral"] = {
                "api_key": self.ringcentral.client_id,
                "api_secret": self.ringcentral.client_secret,
                "account_sid": self.ringcentral.account_id,
                "webhook_base_url": self.ringcentral.webhook_base_url,
                "default_from_number": self.ringcentral.default_from_number,
                "extra": {
                    "account_id": self.ringcentral.account_id,
                    "jwt_token": self.ringcentral.jwt_token,
                    "username": self.ringcentral.username,
                    "password": self.ringcentral.password,
                    "extension": self.ringcentral.extension,
                    "webhook_secret": self.ringcentral.webhook_secret,
                    "use_uk_endpoint": self.ringcentral.use_uk_endpoint,
                },
            }

        if self.zoom.is_configured():
            configs["zoom"] = {
                "api_key": self.zoom.client_id,
                "api_secret": self.zoom.client_secret,
                "account_sid": self.zoom.account_id,
                "webhook_base_url": self.zoom.webhook_base_url,
                "default_from_number": self.zoom.default_from_number,
                "extra": {
                    "account_id": self.zoom.account_id,
                    "webhook_secret": self.zoom.webhook_secret,
                },
            }

        if self.teams.is_configured():
            configs["teams"] = {
                "api_key": self.teams.client_id,
                "api_secret": self.teams.client_secret,
                "account_sid": self.teams.tenant_id,
                "webhook_base_url": self.teams.webhook_base_url,
                "default_from_number": self.teams.default_from_number,
                "extra": {
                    "tenant_id": self.teams.tenant_id,
                    "sip_domain": self.teams.sip_domain,
                    "sbc_fqdn": self.teams.sbc_fqdn,
                    "webhook_secret": self.teams.webhook_secret,
                },
            }

        if self.circleloop.is_configured():
            configs["circleloop"] = {
                "api_key": self.circleloop.api_key,
                "api_secret": self.circleloop.api_secret,
                "webhook_base_url": self.circleloop.webhook_base_url,
                "default_from_number": self.circleloop.default_from_number,
                "extra": {
                    "webhook_secret": self.circleloop.webhook_secret,
                },
            }

        if self.nfon.is_configured():
            configs["nfon"] = {
                "api_key": self.nfon.client_id,
                "api_secret": self.nfon.client_secret,
                "account_sid": self.nfon.account_id,
                "webhook_base_url": self.nfon.webhook_base_url,
                "default_from_number": self.nfon.default_from_number,
                "extra": {
                    "tenant_id": self.nfon.account_id,
                    "webhook_secret": self.nfon.webhook_secret,
                    "use_uk_endpoint": self.nfon.use_uk_endpoint,
                },
            }

        if self.discord.is_configured():
            configs["discord"] = {
                "api_key": self.discord.bot_token,
                "webhook_base_url": self.discord.webhook_base_url,
                "webhook_secret": self.discord.webhook_secret,
                "extra": {
                    "application_id": self.discord.application_id,
                    "public_key": self.discord.public_key,
                    "guild_id": self.discord.guild_id,
                    "voice_channel_id": self.discord.voice_channel_id,
                    "text_channel_id": self.discord.text_channel_id,
                },
            }

        if self.avaya.is_configured():
            configs["avaya"] = {
                "webhook_base_url": self.avaya.webhook_base_url,
                "webhook_secret": self.avaya.webhook_secret,
                "default_from_number": self.avaya.default_from_number,
                "extra": {
                    "server_host": self.avaya.server_host,
                    "server_port": self.avaya.server_port,
                    "username": self.avaya.username,
                    "password": self.avaya.password,
                    "extension": self.avaya.extension,
                    "use_ssl": self.avaya.use_ssl,
                    "aes_enabled": self.avaya.aes_enabled,
                    "ip_office_mode": self.avaya.ip_office_mode,
                },
            }
            configs["avaya_aes"] = {
                **configs["avaya"],
                "extra": dict(configs["avaya"].get("extra", {})),
            }
            configs["avaya_ip_office"] = {
                **configs["avaya"],
                "extra": dict(configs["avaya"].get("extra", {})),
            }

        return configs


def load_telephony_settings(
    config_path: Path | None = None,
) -> TelephonySettings:
    """Load telephony settings from file and environment.

    Environment variables take precedence over file configuration.

    Args:
        config_path: Optional path to configuration file.

    Returns:
        TelephonySettings instance.
    """
    # Start with file-based config
    if config_path and config_path.exists():
        settings = TelephonySettings.from_file(config_path)
    else:
        settings = TelephonySettings()

    # Override with environment variables
    env_settings = TelephonySettings.from_env()

    # Merge: environment takes precedence
    if os.getenv("TELEPHONY_ENABLED") is not None:
        settings.enabled = env_settings.enabled
    if os.getenv("TELEPHONY_DEFAULT_PROVIDER") is not None:
        settings.default_provider = env_settings.default_provider
    if os.getenv("TELEPHONY_WEBHOOK_RATE_LIMIT_PER_MINUTE") is not None:
        settings.webhook_rate_limit_per_minute = env_settings.webhook_rate_limit_per_minute
    if os.getenv("TELEPHONY_WEBHOOK_REPLAY_WINDOW_SECONDS") is not None:
        settings.webhook_replay_window_seconds = env_settings.webhook_replay_window_seconds

    # Merge provider configs
    if env_settings.twilio.is_configured():
        settings.twilio = env_settings.twilio
    if env_settings.vonage.is_configured():
        settings.vonage = env_settings.vonage
    if env_settings.sip.is_configured():
        settings.sip = env_settings.sip
    if env_settings.gamma.is_configured():
        settings.gamma = env_settings.gamma
    if env_settings.bt.is_configured():
        settings.bt = env_settings.bt
    if env_settings.ringcentral.is_configured():
        settings.ringcentral = env_settings.ringcentral
    if env_settings.zoom.is_configured():
        settings.zoom = env_settings.zoom
    if env_settings.teams.is_configured():
        settings.teams = env_settings.teams
    if env_settings.circleloop.is_configured():
        settings.circleloop = env_settings.circleloop
    if env_settings.nfon.is_configured():
        settings.nfon = env_settings.nfon
    if env_settings.discord.is_configured():
        settings.discord = env_settings.discord
    if env_settings.avaya.is_configured():
        settings.avaya = env_settings.avaya

    return settings
