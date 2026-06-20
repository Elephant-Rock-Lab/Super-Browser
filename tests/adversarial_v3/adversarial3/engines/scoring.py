"""Scoring engine with tier multipliers and critical failure caps.

Scoring contract:
  - Each VectorResult carries an authoritative score (0.0-1.0) that
    already encodes verdict severity (CLEAN=1.0, CHALLENGED=0.4,
    FLAGGED=0.0). The engine trusts this value directly.
  - Per-tier score = simple average of conclusive vector scores.
    FLAGGED vectors (score=0.0) count in the denominator so they pull
    the average down. INCONCLUSIVE and SKIPPED are excluded from both
    numerator and denominator.
  - Overall score = weighted average of tier scores using tier
    multipliers.
  - Critical failure cap: any CRITICAL-severity vector with a FLAGGED
    verdict caps the overall score at critical_cap_threshold. Only
    FLAGGED triggers the cap -- CHALLENGED is partial credit, not a
    failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from adversarial3.core import (
    AssessmentReport,
    BaseEngine,
    Severity,
    Tier,
    TierSummary,
    VectorResult,
    Verdict,
    now_utc,
)


@dataclass(frozen=True, slots=True)
class ScoringConfig:
    """Configuration for the scoring engine."""

    # Tier importance multipliers (higher = more weight in overall score)
    tier_multipliers: dict[Tier, float] = field(default_factory=lambda: {
        Tier.FINGERPRINT: 0.9,
        Tier.AUTOMATION: 1.2,
        Tier.EJECTOR: 1.1,
        Tier.BEHAVIORAL: 0.8,
        Tier.NETWORK: 0.7,
        Tier.EXTERNAL_SCANNER: 0.8,
        Tier.EXTERNAL_VENDOR: 1.3,
        Tier.CONTROLLED: 1.0,
    })

    # If True, any CRITICAL+FLAGGED vector caps the overall score
    critical_failure_cap: bool = True
    critical_cap_threshold: float = 0.5

    # Minimum vectors per tier to include in overall scoring
    min_vectors_per_tier: int = 1


class WeightedScoringEngine(BaseEngine):
    """Weighted scoring with tier multipliers and critical failure handling."""

    def __init__(self, config: ScoringConfig | None = None) -> None:
        self.config = config or ScoringConfig()

    def compute(self, results: list[VectorResult]) -> AssessmentReport:
        if not results:
            return AssessmentReport(
                run_id="empty",
                timestamp=now_utc(),
                overall_score=0.0,
                tier_summaries=[],
                results=[],
            )

        # Group by tier
        by_tier: dict[Tier, list[VectorResult]] = {}
        for r in results:
            by_tier.setdefault(r.tier, []).append(r)

        tier_summaries: list[TierSummary] = []
        total_weight = 0.0
        weighted_sum = 0.0
        critical_failures: list[str] = []

        for tier, tier_results in sorted(by_tier.items(), key=lambda x: x[0].value):
            if len(tier_results) < self.config.min_vectors_per_tier:
                continue

            summary = self._compute_tier(tier, tier_results)
            tier_summaries.append(summary)

            mult = self.config.tier_multipliers.get(tier, 1.0)
            weighted_sum += summary.score * mult
            total_weight += mult

            critical_failures.extend(summary.critical_failures)

        overall = weighted_sum / total_weight if total_weight > 0 else 0.0

        # Critical failure cap: only FLAGGED triggers (not CHALLENGED)
        if self.config.critical_failure_cap and critical_failures:
            overall = min(overall, self.config.critical_cap_threshold)

        return AssessmentReport(
            run_id="",  # filled by caller
            timestamp=now_utc(),
            overall_score=round(overall, 4),
            tier_summaries=tier_summaries,
            results=results,
            metadata={
                "critical_failures": critical_failures,
                "total_vectors": len(results),
                "config": {
                    "critical_failure_cap": self.config.critical_failure_cap,
                    "critical_cap_threshold": self.config.critical_cap_threshold,
                },
            },
        )

    def _compute_tier(self, tier: Tier, results: list[VectorResult]) -> TierSummary:
        conclusive = [
            r for r in results
            if r.verdict not in (Verdict.INCONCLUSIVE, Verdict.SKIPPED)
        ]

        if not conclusive:
            return TierSummary(
                tier=tier,
                score=0.0,
                vector_count=len(results),
                passed=0,
                failed=0,
                skipped=sum(1 for r in results if r.verdict == Verdict.SKIPPED),
                inconclusive=sum(1 for r in results if r.verdict == Verdict.INCONCLUSIVE),
                avg_duration_ms=sum(r.duration_ms for r in results) / len(results) if results else 0.0,
                critical_failures=[],
            )

        avg_score = sum(r.score for r in conclusive) / len(conclusive)

        passed = sum(1 for r in conclusive if r.verdict == Verdict.CLEAN)
        failed = len(conclusive) - passed
        criticals = [
            r.vector_id for r in results
            if r.severity == Severity.CRITICAL and r.verdict == Verdict.FLAGGED
        ]

        return TierSummary(
            tier=tier,
            score=round(avg_score, 4),
            vector_count=len(results),
            passed=passed,
            failed=failed,
            skipped=sum(1 for r in results if r.verdict == Verdict.SKIPPED),
            inconclusive=sum(1 for r in results if r.verdict == Verdict.INCONCLUSIVE),
            avg_duration_ms=sum(r.duration_ms for r in results) / len(results),
            critical_failures=criticals,
        )
