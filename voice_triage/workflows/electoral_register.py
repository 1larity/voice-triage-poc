"""workflows.electoral_register module."""

from __future__ import annotations

from typing import Any


class ElectoralRegisterHandler:
    """Electoralregisterhandler."""

    def run(self, _: dict[str, str]) -> tuple[str, dict[str, Any]]:
        """Run."""
        return (
            "Electoral register workflow is stubbed in this POC.",
            {"status": "stub"},
        )
