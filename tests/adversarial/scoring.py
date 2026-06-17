"""Composite scoring model for adversarial test results.

Mirrors the weighting style of the existing ``FingerprintScorer`` but
operates on per-target Verdicts rather than fingerprint signals.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from .targets import TargetResult, Tier, Verdict  # type: ignore[import-not-found]

# ---------------------------------------------------------------------------
# Per-tier scoring weights
# ---------------------------------------------------------------------------

# Verdict → base score contribution (0-100 scale)
VERDICT_WEIGHTS: dict[Verdict, float] = {
    Verdict.CLEAN: 1.0,
    Verdict.CHALLENGED: 0.4,
    Verdict.FLAGGED: 0.0,
    Verdict.INCONCLUSIVE: 0.0,  # excluded from averages
}

# Tier → importance multiplier (arbitrary scale, Tier 2 matters most)
TIER_MULTIPLIERS: dict[Tier, float] = {
    Tier.SCANNER: 0.8,
    Tier.VENDOR: 1.2,
    Tier.CONTROLLED: 1.0,
}


# ---------------------------------------------------------------------------
# Score dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TierScore:
    """Aggregated score for a single tier."""

    tier: Tier
    composite_score: int  # 0-100, rounded
    target_count: int
    conclusive_count: int  # excludes INCONCLUSIVE
    clean_count: int
    challenged_count: int
    flagged_count: int
    inconclusive_count: int
    avg_score: float  # raw average before rounding
    details: list[TargetResult]


@dataclass(frozen=True)
class AdversarialReport:
    """Full report from one adversarial harness run."""

    run_id: str
    timestamp: str
    total_targets: int
    tier_scores: list[TierScore]
    overall_score: int  # 0-100, weighted across tiers
    inconclusive_rate: float  # 0.0-1.0
    summary: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "total_targets": self.total_targets,
            "overall_score": self.overall_score,
            "inconclusive_rate": self.inconclusive_rate,
            "summary": self.summary,
            "tiers": [
                {
                    "tier": ts.tier.value,
                    "composite_score": ts.composite_score,
                    "target_count": ts.target_count,
                    "conclusive_count": ts.conclusive_count,
                    "clean": ts.clean_count,
                    "challenged": ts.challenged_count,
                    "flagged": ts.flagged_count,
                    "inconclusive": ts.inconclusive_count,
                    "avg_score": round(ts.avg_score, 2),
                    "details": [
                        {
                            "target_id": d.target_id,
                            "verdict": d.verdict.value,
                            "score": d.score,
                            "detail": d.detail,
                            "raw": d.raw,
                        }
                        for d in ts.details
                    ],
                }
                for ts in self.tier_scores
            ],
        }


# ---------------------------------------------------------------------------
# Scoring engine
# ---------------------------------------------------------------------------

def compute_tier_score(tier: Tier, results: list[TargetResult]) -> TierScore:
    """Aggregate a list of TargetResults into a TierScore."""
    conclusive = [r for r in results if r.verdict != Verdict.INCONCLUSIVE]

    if not conclusive:
        return TierScore(
            tier=tier,
            composite_score=0,
            target_count=len(results),
            conclusive_count=0,
            clean_count=0,
            challenged_count=0,
            flagged_count=0,
            inconclusive_count=len(results),
            avg_score=0.0,
            details=results,
        )

    # Weighted average: each target contributes its score * verdict_weight
    total_weight = 0.0
    weighted_sum = 0.0
    for r in conclusive:
        w = VERDICT_WEIGHTS.get(r.verdict, 0.0)
        weighted_sum += r.score * w
        total_weight += w

    avg_score = weighted_sum / total_weight if total_weight > 0 else 0.0
    composite = int(round(avg_score))

    return TierScore(
        tier=tier,
        composite_score=max(0, min(100, composite)),
        target_count=len(results),
        conclusive_count=len(conclusive),
        clean_count=sum(1 for r in results if r.verdict == Verdict.CLEAN),
        challenged_count=sum(1 for r in results if r.verdict == Verdict.CHALLENGED),
        flagged_count=sum(1 for r in results if r.verdict == Verdict.FLAGGED),
        inconclusive_count=sum(1 for r in results if r.verdict == Verdict.INCONCLUSIVE),
        avg_score=avg_score,
        details=results,
    )


def compute_overall_score(tier_scores: list[TierScore]) -> int:
    """Weighted overall score across all tiers."""
    total_weight = 0.0
    weighted_sum = 0.0
    for ts in tier_scores:
        mult = TIER_MULTIPLIERS.get(ts.tier, 1.0)
        if ts.conclusive_count > 0:
            weighted_sum += ts.composite_score * mult
            total_weight += mult

    if total_weight == 0:
        return 0
    return max(0, min(100, int(round(weighted_sum / total_weight))))


def build_report(
    run_id: str,
    results_by_tier: dict[Tier, list[TargetResult]],
) -> AdversarialReport:
    """Build a full AdversarialReport from per-tier results."""
    tier_scores = [
        compute_tier_score(tier, results)
        for tier, results in results_by_tier.items()
    ]

    total = sum(len(r) for r in results_by_tier.values())
    inconclusive_total = sum(
        ts.inconclusive_count for ts in tier_scores
    )
    inconclusive_rate = inconclusive_total / total if total > 0 else 0.0

    overall = compute_overall_score(tier_scores)

    # Generate human-readable summary
    parts = []
    for ts in tier_scores:
        parts.append(
            f"{ts.tier.value}: {ts.composite_score}/100 "
            f"({ts.clean_count} clean, {ts.challenged_count} challenged, "
            f"{ts.flagged_count} flagged, {ts.inconclusive_count} inconclusive)"
        )
    summary = f"Overall {overall}/100. " + " | ".join(parts)

    return AdversarialReport(
        run_id=run_id,
        timestamp=datetime.utcnow().isoformat() + "Z",
        total_targets=total,
        tier_scores=tier_scores,
        overall_score=overall,
        inconclusive_rate=inconclusive_rate,
        summary=summary,
    )


# ---------------------------------------------------------------------------
# Trend tracking
# ---------------------------------------------------------------------------

HISTORY_FILE = Path("adversarial-history.json")


def append_to_history(report: AdversarialReport, history_path: Path | None = None) -> None:
    """Append a lightweight snapshot of this run to the trend file."""
    path = history_path or HISTORY_FILE
    snapshot = {
        "run_id": report.run_id,
        "timestamp": report.timestamp,
        "overall_score": report.overall_score,
        "inconclusive_rate": report.inconclusive_rate,
        "tier_scores": {
            ts.tier.value: ts.composite_score for ts in report.tier_scores
        },
    }

    history: list[dict[str, Any]] = []
    if path.exists():
        try:
            with path.open("r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, OSError):
            history = []

    history.append(snapshot)

    with path.open("w", encoding="utf-8") as f:
        json.dump(history, f, indent=2)
