"""nlu.extractor module."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import ClassVar, Protocol

from voice_triage.nlu.schemas import ExtractionResult, Intent


class Extractor(Protocol):
    """Extractor."""

    def extract(self, text: str) -> ExtractionResult:
        """Extract structured intent and fields from free text."""


@dataclass(slots=True)
class HeuristicExtractor:
    """Deterministic extractor for an initial local POC."""

    postcode_pattern: re.Pattern[str] = re.compile(
        r"\b([A-Z]{1,2}\d[A-Z\d]?\s?\d[A-Z]{2})\b", re.IGNORECASE
    )
    numeric_date_pattern: re.Pattern[str] = re.compile(
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|\d{4}-\d{2}-\d{2})\b"
    )
    natural_date_pattern: re.Pattern[str] = re.compile(
        r"\b(\d{1,2})(?:st|nd|rd|th)?(?:\s+of)?\s+"
        r"(january|february|march|april|may|june|july|august|september|october|november|december)"
        r"\s+(\d{4})\b",
        re.IGNORECASE,
    )
    natural_date_pattern_alt: re.Pattern[str] = re.compile(
        r"\b(january|february|march|april|may|june|july|august|september|october|november|december)"
        r"\s+(\d{1,2})(?:st|nd|rd|th)?(?:,)?\s+(\d{4})\b",
        re.IGNORECASE,
    )
    voting_terms: tuple[str, ...] = ("vote", "voting", "ballot", "election")
    month_names: ClassVar[dict[str, int]] = {
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

    def extract(self, text: str) -> ExtractionResult:
        """Extract."""
        normalized = text.strip()
        lowered = normalized.lower()

        intent = self._detect_intent(lowered)
        postcode = self._extract_postcode(normalized)
        move_date = self._extract_move_date(normalized)
        address_line = self._extract_address(normalized, postcode, move_date)

        return ExtractionResult(
            intent=intent,
            raw_text=normalized,
            postcode=postcode,
            address_line=address_line,
            move_date=move_date,
        )

    def _detect_intent(self, lowered: str) -> Intent:
        """detect intent."""
        if any(keyword in lowered for keyword in ("move", "moving", "new address")):
            return Intent.MOVE_HOME
        # Keep electoral routing strict; many council services also use "register".
        if "electoral register" in lowered:
            return Intent.ELECTORAL_REGISTER
        if "register to vote" in lowered:
            return Intent.ELECTORAL_REGISTER
        if "register" in lowered and any(term in lowered for term in self.voting_terms):
            return Intent.ELECTORAL_REGISTER
        if any(term in lowered for term in self.voting_terms) and "electoral" in lowered:
            return Intent.ELECTORAL_REGISTER
        if "council tax" in lowered:
            return Intent.COUNCIL_TAX
        return Intent.RAG_QA

    def _extract_postcode(self, text: str) -> str | None:
        """extract postcode."""
        match = self.postcode_pattern.search(text)
        if match is None:
            return None
        return match.group(1).upper()

    def _extract_move_date(self, text: str) -> str | None:
        """extract move date."""
        numeric_match = self.numeric_date_pattern.search(text)
        if numeric_match is not None:
            normalized = self._parse_numeric_date(numeric_match.group(1))
            if normalized is not None:
                return normalized

        natural_match = self.natural_date_pattern.search(text)
        if natural_match is not None:
            day = int(natural_match.group(1))
            month_name = natural_match.group(2).lower()
            year = int(natural_match.group(3))
            month = self.month_names.get(month_name)
            if month is not None:
                parsed = self._safe_date(year=year, month=month, day=day)
                if parsed is not None:
                    return parsed

        natural_alt_match = self.natural_date_pattern_alt.search(text)
        if natural_alt_match is not None:
            month_name = natural_alt_match.group(1).lower()
            day = int(natural_alt_match.group(2))
            year = int(natural_alt_match.group(3))
            month = self.month_names.get(month_name)
            if month is not None:
                parsed = self._safe_date(year=year, month=month, day=day)
                if parsed is not None:
                    return parsed

        return None

    def _parse_numeric_date(self, raw: str) -> str | None:
        """parse numeric date."""
        value = raw.strip()
        if "-" in value:
            parts = value.split("-")
            if len(parts) == 3 and len(parts[0]) == 4:
                year, month, day = parts
                return self._safe_date(year=int(year), month=int(month), day=int(day))
            if len(parts) == 3:
                day, month, year = parts
                return self._safe_date(
                    year=self._normalize_year(int(year)),
                    month=int(month),
                    day=int(day),
                )
            return None

        if "/" in value:
            parts = value.split("/")
            if len(parts) != 3:
                return None
            day, month, year = parts
            return self._safe_date(
                year=self._normalize_year(int(year)),
                month=int(month),
                day=int(day),
            )
        return None

    @staticmethod
    def _normalize_year(year: int) -> int:
        """normalize year."""
        if year < 100:
            return 2000 + year
        return year

    @staticmethod
    def _safe_date(year: int, month: int, day: int) -> str | None:
        """safe date."""
        try:
            parsed = datetime(year=year, month=month, day=day)
        except ValueError:
            return None
        return parsed.strftime("%Y-%m-%d")

    def _extract_address(
        self, text: str, postcode: str | None, move_date: str | None
    ) -> str | None:
        """extract address."""
        cleaned = text
        if postcode:
            cleaned = re.sub(re.escape(postcode), "", cleaned, flags=re.IGNORECASE)
        if move_date:
            cleaned = cleaned.replace(move_date, "")

        for keyword in ("moving", "move", "new address", "to", "from"):
            cleaned = re.sub(rf"\b{re.escape(keyword)}\b", "", cleaned, flags=re.IGNORECASE)

        cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,.-")
        if len(cleaned) < 6:
            return None
        return cleaned
