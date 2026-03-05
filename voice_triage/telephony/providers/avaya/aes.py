"""Avaya AES (Application Enablement Services) provider implementation.

This module provides the Avaya AES provider, which is the middleware platform
that provides TSAPI, JTAPI, and DMCC interfaces for advanced telephony integration.
"""

from __future__ import annotations

import logging

from voice_triage.telephony.providers.avaya.provider import AvayaProvider
from voice_triage.telephony.registry import register_provider

logger = logging.getLogger(__name__)


@register_provider("avaya_aes")
class AvayaAESProvider(AvayaProvider):
    """Avaya Application Enablement Services (AES) provider.

    AES is the middleware platform that provides TSAPI, JTAPI, and DMCC
    interfaces for advanced telephony integration.

    This provider inherits from AvayaProvider and uses the same underlying
    client, but is registered under a different name for explicit AES
    configurations.
    """

    @property
    def name(self) -> str:
        """Return the provider name."""
        return "avaya_aes"
