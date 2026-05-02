"""CostAnalytics — per-session cost accumulation and queries."""

from __future__ import annotations

from typing import Any

from super_browser.tracing.session_db import SessionDB
from super_browser.tracing.types import CostRecord


class CostAnalytics:

    def __init__(self, session_db: SessionDB) -> None:
        self._db = session_db
        self._records: dict[str, list[CostRecord]] = {}

    def record(self, cost: CostRecord) -> None:
        self._records.setdefault(cost.trace_id, []).append(cost)
        try:
            self._db.insert_cost_record(cost)
        except Exception:
            pass

    def session_total(self, trace_id: str) -> float:
        records = self._records.get(trace_id, [])
        if records:
            return sum(r.cost_usd for r in records)
        return 0.0

    def session_breakdown(self, trace_id: str) -> dict[str, Any]:
        records = self._records.get(trace_id, [])
        by_provider: dict[str, dict[str, Any]] = {}
        by_model: dict[str, dict[str, Any]] = {}
        total = 0.0

        for r in records:
            total += r.cost_usd
            if r.provider not in by_provider:
                by_provider[r.provider] = {"cost": 0.0, "token_input": 0, "token_output": 0}
            by_provider[r.provider]["cost"] += r.cost_usd
            by_provider[r.provider]["token_input"] += r.token_input
            by_provider[r.provider]["token_output"] += r.token_output

            if r.model not in by_model:
                by_model[r.model] = {"cost": 0.0, "tokens": 0}
            by_model[r.model]["cost"] += r.cost_usd
            by_model[r.model]["tokens"] += r.token_input + r.token_output

        return {"total": total, "by_provider": by_provider, "by_model": by_model}
