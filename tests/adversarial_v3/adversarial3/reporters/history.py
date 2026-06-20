"""Trend tracking across assessment runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from adversarial3.core import AssessmentReport


class HistoryTracker:
    """Append lightweight snapshots to a trend file."""

    def __init__(self, path: Path | str = "adversarial-history.json") -> None:
        self.path = Path(path)

    def append(self, report: AssessmentReport) -> None:
        """Append a snapshot of this run to the history file."""
        snapshot = {
            "run_id": report.run_id,
            "timestamp": report.timestamp,
            "overall_score": report.overall_score,
            "tier_scores": {
                str(ts.tier): ts.score for ts in report.tier_summaries
            },
            "total_vectors": len(report.results),
            # Must match the failure predicate used by scoring/reporting:
            # CRITICAL severity AND FLAGGED verdict. The previous form
            # (verdict != CLEAN) counted INCONCLUSIVE and CHALLENGED as
            # failures, which inflated the trend and made an honest
            # stub run record spurious critical_failures.
            "critical_failures": len([
                r for r in report.results
                if r.severity.name == "CRITICAL" and r.verdict.name == "FLAGGED"
            ]),
        }

        history: list[dict[str, Any]] = []
        if self.path.exists():
            try:
                with self.path.open("r", encoding="utf-8") as f:
                    history = json.load(f)
            except (json.JSONDecodeError, OSError):
                history = []

        history.append(snapshot)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(history, f, indent=2)

    def load(self) -> list[dict[str, Any]]:
        """Load full history."""
        if not self.path.exists():
            return []
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)
