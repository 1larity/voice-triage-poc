"""Common parsing utilities for telephony providers.

This module provides common parsing utilities used across multiple
telephony providers, including phone number normalization and date parsing.
"""

from __future__ import annotations

import re
from datetime import datetime


def normalize_phone_number(phone: str) -> str:
    """Normalize a phone number to E.164 format.

    Converts various UK phone number formats to E.164:
    - "07700900000" -> "+447700900000"
    - "7700900000" -> "+447700900000"
    - "+447700900000" -> "+447700900000"

    Args:
        phone: Phone number in various formats.

    Returns:
        Normalized E.164 phone number.
    """
    if not phone:
        return ""

    # Remove whitespace and dashes
    cleaned = re.sub(r"[\s\-()]", "", phone)

    # Remove leading zero if present (UK format)
    if cleaned.startswith("0"):
        cleaned = "44" + cleaned[1:]

    # Add + prefix if not present
    if not cleaned.startswith("+"):
        cleaned = "+" + cleaned

    return cleaned


def parse_uk_date(date_str: str) -> datetime | None:
    """Parse a UK date string into a datetime object.

    Supports various UK date formats:
    - "4th of April 2026"
    - "4 April 2026"
    - "04/04/2026"
    - "2026-04-04"

    Args:
        date_str: Date string in various UK formats.

    Returns:
        Parsed datetime object or None if parsing fails.
    """
    if not date_str:
        return None

    date_str = date_str.strip().lower()

    # Try ISO format first (YYYY-MM-DD)
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        pass

    # Try UK spoken format (4th of april 2026)
    uk_spoken_pattern = r"(\d{1,2})(?:st|nd|rd|th)\s+(?:of\s+)?(\w+)\s+(\d{4})"
    match = re.match(uk_spoken_pattern, date_str)
    if match:
        day = match.group(1)
        month_name = match.group(3)
        year = match.group(4)

        month_map = {
            "january": 1,
            "february": 2,
            "march": 3,
            "april": 4,
            "may": 5,
            "june": 6,
            "july": 7,
            "august": 8,
            "september": 9,
            "october": 10,
            "november": 11,
            "december": 12,
        }

        month = month_map.get(month_name)
        if month:
            return datetime(int(year), month, int(day))

    # Try UK short format (4 april 2026)
    uk_short_pattern = r"(\d{1,2})\s+(\w+)\s+(\d{4})"
    match = re.match(uk_short_pattern, date_str)
    if match:
        day = match.group(1)
        month_name = match.group(2)
        year = match.group(3)

        month_map = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }

        month = month_map.get(month_name[:3])
        if month:
            return datetime(int(year), month, int(day))

    # Try numeric format (04/04/2026)
    try:
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        pass

    return None
