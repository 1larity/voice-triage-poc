"""workflows.move_home module."""

from __future__ import annotations

from datetime import datetime
from typing import Any


class MoveHomeHandler:
    """Movehomehandler."""

    def run(self, fields: dict[str, str]) -> tuple[str, dict[str, Any]]:
        """Run."""
        required = ("current_address", "new_address", "move_date")
        missing = [field for field in required if not fields.get(field)]
        if missing:
            return (
                f"I still need the following details: {', '.join(missing)}.",
                {"status": "incomplete", "missing_fields": missing, "fields": fields},
            )

        case_reference = f"MOVE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        return (
            "Move-of-home request captured. A case has been created for follow-up.",
            {"status": "submitted", "case_reference": case_reference, "fields": fields},
        )
