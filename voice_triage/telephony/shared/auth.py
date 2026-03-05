"""Authentication helpers for telephony providers.

This module provides common authentication utilities used across
multiple telephony providers.
"""

from __future__ import annotations

import hashlib
import hmac


def compute_hmac(
    key: str | bytes,
    message: bytes,
    algorithm: str = "sha256",
) -> bytes:
    """Compute HMAC hash of a message.

    Args:
        key: The secret key for HMAC computation.
        message: The message to hash.
        algorithm: Hashing algorithm (default: sha256).

    Returns:
        Computed HMAC digest as bytes.
    """
    if algorithm == "sha256":
        hasher = hashlib.sha256
    elif algorithm == "sha1":
        hasher = hashlib.sha1
    elif algorithm == "sha512":
        hasher = hashlib.sha512
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}")

    return hmac.new(
        key.encode() if isinstance(key, str) else key,
        message,
        hasher,
    ).digest()


def validate_basic_auth(
    username: str,
    password: str,
    auth_header: str,
) -> bool:
    """Validate HTTP Basic Auth credentials.

    Args:
        username: Expected username.
        password: Expected password.
        auth_header: The Authorization header value.

    Returns:
        True if credentials are valid, False otherwise.
    """
    import base64

    if not auth_header or not auth_header.startswith("Basic "):
        return False

    try:
        # Decode the Base64 credentials
        encoded_credentials = auth_header[6:]  # Remove "Basic "
        decoded = base64.b64decode(encoded_credentials).decode("utf-8")
        provided_username, provided_password = decoded.split(":", 1)

        return provided_username == username and provided_password == password
    except (ValueError, UnicodeDecodeError):
        return False
