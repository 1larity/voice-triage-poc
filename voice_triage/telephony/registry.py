"""Registry for telephony providers."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar

if TYPE_CHECKING:
    from voice_triage.telephony.base import TelephonyConfig, TelephonyProvider

# Global registry of provider factories
_PROVIDER_REGISTRY: dict[str, type[TelephonyProvider]] = {}
"""Registry mapping provider names to their implementation classes."""

T = TypeVar("T", bound="TelephonyProvider")
"""Generic type variable for telephony provider classes."""


def register_provider(name: str) -> Callable[[type[T]], type[T]]:
    """Decorator to register a telephony provider.

    Usage:
        @register_provider("twilio")
        class TwilioProvider(TelephonyProvider):
            ...
    """
    def decorator(cls: type[T]) -> type[T]:
        """Register the provider class in the global registry.

        Args:
            cls: The provider class to register.

        Returns:
            The same class, registered.
        """
        _PROVIDER_REGISTRY[name.lower()] = cls
        return cls

    return decorator


def get_provider(config: TelephonyConfig) -> TelephonyProvider:
    """Get a telephony provider instance by name.

    Args:
        config: Configuration for the provider.

    Returns:
        An instance of the requested provider.

    Raises:
        ValueError: If the provider is not registered.
    """
    provider_name = config.provider_name.lower()

    if provider_name not in _PROVIDER_REGISTRY:
        available = ", ".join(sorted(_PROVIDER_REGISTRY.keys()))
        raise ValueError(
            f"Unknown telephony provider: {config.provider_name}. "
            f"Available providers: {available}"
        )

    provider_cls = _PROVIDER_REGISTRY[provider_name]
    return provider_cls(config)


def list_providers() -> list[str]:
    """List all registered telephony providers.

    Returns:
        List of provider names.
    """
    return sorted(_PROVIDER_REGISTRY.keys())


class TelephonyRegistry:
    """Registry for managing telephony providers."""

    def __init__(self) -> None:
        """Initialize the registry."""
        self._providers: dict[str, TelephonyProvider] = {}

    def register(self, provider: TelephonyProvider) -> None:
        """Register a provider instance.

        Args:
            provider: The provider instance to register.
        """
        self._providers[provider.name.lower()] = provider

    def get(self, name: str) -> TelephonyProvider | None:
        """Get a registered provider by name.

        Args:
            name: Provider name.

        Returns:
            The provider instance or None if not found.
        """
        return self._providers.get(name.lower())

    def list_registered(self) -> list[str]:
        """List all registered provider names.

        Returns:
            List of registered provider names.
        """
        return list(self._providers.keys())

    def clear(self) -> None:
        """Clear all registered providers."""
        self._providers.clear()
