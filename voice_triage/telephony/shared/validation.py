"""Webhook signature validation utilities for telephony providers.

This module provides common validation utilities used across multiple
telephony providers for validating webhook signatures and request authenticity.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from typing import Any


def validate_webhook_signature(
    signature: str,
    body: bytes,
    secret: str,
    algorithm: str = "sha256",
) -> bool:
    """Validate a webhook signature using HMAC.

    Args:
        signature: The signature to validate.
        body: The raw request body.
        secret: The shared secret for HMAC computation.
        algorithm: Hashing algorithm (default: sha256).

    Returns:
        True if signature is valid, False otherwise.
    """
    if not signature or not secret:
        return False

    # Compute expected signature
    if algorithm == "sha256":
        hasher = hashlib.sha256
    elif algorithm == "sha1":
        hasher = hashlib.sha1
    elif algorithm == "sha512":
        hasher = hashlib.sha512
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    expected = hmac.new(
        secret.encode(),
        body,
        hasher,
    ).hexdigest()

    # Compare with signature (constant-time comparison)
    return hmac.compare_digest(expected, signature)


def validate_twilio_signature(
    signature: str,
    body: bytes,
    auth_token: str,
    url: str,
    params: dict[str, Any] | None = None,
) -> bool:
    """Validate a Twilio webhook signature.

    Args:
        signature: The X-Twilio-Signature header value.
        body: Raw request body.
        auth_token: Twilio auth token.
        url: The full URL of the webhook.
        params: URL parameters (for GET or form data, or None for post body.
        algorithm: Hashing algorithm (default: sha1)

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not auth_token or not url:
        return False
    if params is None:
        params = {}
    # For POST requests with body, concatenate URL and body
    if body:
        data = url + body.decode("utf-8")
    else:
        # for GET or form data, sort and concatenate params
        sorted_params = sorted(params.items())
        data = url + "".join(f"{k}{v}" for k, v in sorted_params)
    # Compute HMAC-SHA1
    computed = hmac.new(
        auth_token.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    # Compare with signature (base64 encoded)
    expected = base64.b64encode(computed).decode("utf-8")
    return hmac.compare_digest(expected, signature)
