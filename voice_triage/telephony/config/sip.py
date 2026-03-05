"""SIP-based telephony provider configurations.

This module provides configuration management for generic SIP trunking and
SIP-based providers including Gamma Telecom and BT (British Telecom).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class SIPConfig:
    """Configuration for generic SIP trunking provider."""

    sip_server: str | None = None
    """SIP server hostname or IP address."""

    sip_port: int = 5060
    """SIP server port."""

    sip_username: str | None = None
    """SIP authentication username."""

    sip_password: str | None = None
    """SIP authentication password."""

    sip_domain: str | None = None
    """SIP domain/realm."""

    sip_transport: str = "udp"
    """SIP transport protocol (udp, tcp, tls)."""

    webhook_base_url: str | None = None
    """Base URL for webhooks."""

    webhook_secret: str | None = None
    """Secret for webhook validation."""

    default_from_number: str | None = None
    """Default phone number for outbound calls."""

    allowed_webhook_ips: list[str] = field(default_factory=list)
    """IP addresses allowed to send webhooks."""

    @classmethod
    def from_env(cls) -> SIPConfig:
        """Load configuration from environment variables.

        Returns:
            SIPConfig instance populated from environment variables.
        """
        allowed_ips_raw = os.getenv("SIP_ALLOWED_WEBHOOK_IPS", "")
        allowed_ips = [ip.strip() for ip in allowed_ips_raw.split(",") if ip.strip()]

        return cls(
            sip_server=os.getenv("SIP_SERVER"),
            sip_port=int(os.getenv("SIP_PORT", "5060")),
            sip_username=os.getenv("SIP_USERNAME"),
            sip_password=os.getenv("SIP_PASSWORD"),
            sip_domain=os.getenv("SIP_DOMAIN"),
            sip_transport=os.getenv("SIP_TRANSPORT", "udp"),
            webhook_base_url=os.getenv("SIP_WEBHOOK_BASE_URL"),
            webhook_secret=os.getenv("SIP_WEBHOOK_SECRET"),
            default_from_number=os.getenv("SIP_DEFAULT_FROM_NUMBER"),
            allowed_webhook_ips=allowed_ips,
        )

    def is_configured(self) -> bool:
        """Check if SIP is properly configured.

        Returns:
            True if sip_server, sip_username, and sip_password are set.
        """
        return all([self.sip_server, self.sip_username, self.sip_password])


@dataclass
class GammaConfig(SIPConfig):
    """Configuration for Gamma Telecom provider."""

    provider_code: str = "gamma"
    """Provider identifier."""

    @classmethod
    def from_env(cls) -> GammaConfig:
        """Load configuration from environment variables.

        Returns:
            GammaConfig instance populated from environment variables.
        """
        base_config = SIPConfig.from_env()
        return cls(
            sip_server=os.getenv("GAMMA_SIP_SERVER", base_config.sip_server),
            sip_port=int(os.getenv("GAMMA_SIP_PORT", str(base_config.sip_port))),
            sip_username=os.getenv("GAMMA_SIP_USERNAME", base_config.sip_username),
            sip_password=os.getenv("GAMMA_SIP_PASSWORD", base_config.sip_password),
            sip_domain=os.getenv("GAMMA_SIP_DOMAIN", base_config.sip_domain),
            sip_transport=os.getenv("GAMMA_SIP_TRANSPORT", base_config.sip_transport),
            webhook_base_url=os.getenv(
                "GAMMA_WEBHOOK_BASE_URL", base_config.webhook_base_url
            ),
            webhook_secret=os.getenv(
                "GAMMA_WEBHOOK_SECRET", base_config.webhook_secret
            ),
            default_from_number=os.getenv(
                "GAMMA_DEFAULT_FROM_NUMBER", base_config.default_from_number
            ),
            allowed_webhook_ips=base_config.allowed_webhook_ips,
        )


@dataclass
class BTConfig(SIPConfig):
    """Configuration for BT (British Telecom) provider."""

    provider_code: str = "bt"
    """Provider identifier."""

    webhook_token: str | None = None
    """Bearer token for webhook validation."""

    @classmethod
    def from_env(cls) -> BTConfig:
        """Load configuration from environment variables.

        Returns:
            BTConfig instance populated from environment variables.
        """
        base_config = SIPConfig.from_env()
        return cls(
            sip_server=os.getenv("BT_SIP_SERVER", base_config.sip_server),
            sip_port=int(os.getenv("BT_SIP_PORT", str(base_config.sip_port))),
            sip_username=os.getenv("BT_SIP_USERNAME", base_config.sip_username),
            sip_password=os.getenv("BT_SIP_PASSWORD", base_config.sip_password),
            sip_domain=os.getenv("BT_SIP_DOMAIN", base_config.sip_domain),
            sip_transport=os.getenv("BT_SIP_TRANSPORT", base_config.sip_transport),
            webhook_base_url=os.getenv(
                "BT_WEBHOOK_BASE_URL", base_config.webhook_base_url
            ),
            webhook_secret=os.getenv(
                "BT_WEBHOOK_SECRET", base_config.webhook_secret
            ),
            default_from_number=os.getenv(
                "BT_DEFAULT_FROM_NUMBER", base_config.default_from_number
            ),
            allowed_webhook_ips=base_config.allowed_webhook_ips,
            webhook_token=os.getenv("BT_WEBHOOK_TOKEN"),
        )
