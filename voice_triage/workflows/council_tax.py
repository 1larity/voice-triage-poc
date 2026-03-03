"""workflows.council_tax module."""

from __future__ import annotations

from typing import Any


class CouncilTaxHandler:
    """Counciltaxhandler."""

    def run(self, _: dict[str, str]) -> tuple[str, dict[str, Any]]:
        """Run."""
        return (
            "Council tax management workflow is stubbed in this POC.",
            {"status": "stub"},
        )
