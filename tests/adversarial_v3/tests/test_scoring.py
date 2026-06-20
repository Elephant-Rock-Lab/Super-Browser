"""Tests for the scoring engine.

Covers: empty results, all pass, all fail, partial credit, tier weighting,
critical failure caps (FLAGGED only), boundary conditions, inconclusive
handling, and the FLAGGED-in-denominator regression guard.
"""

from __future__ import annotations

from adversarial3.core import (
    Severity,
    Tier,
    VectorResult,
    Verdict,
)
from adversarial3.engines.scoring import ScoringConfig, WeightedScoringEngine


class TestScoringConfig:
    """Test scoring configuration."""

    def test_default_multipliers(self):
        config = ScoringConfig()
        assert config.tier_multipliers[Tier.EXTERNAL_VENDOR] == 1.3
        assert config.tier_multipliers[Tier.AUTOMATION] == 1.2
        assert config.tier_multipliers[Tier.CONTROLLED] == 1.0

    def test_custom_config(self):
        config = ScoringConfig(
            critical_failure_cap=False,
            critical_cap_threshold=0.3,
        )
        assert config.critical_failure_cap is False
        assert config.critical_cap_threshold == 0.3

    def test_no_verdict_weights(self):
        """verdict_weights removed -- score is authoritative from VectorResult."""
        config = ScoringConfig()
        assert not hasattr(config, "verdict_weights")


class TestEmptyResults:
    def test_empty(self):
        engine = WeightedScoringEngine()
        report = engine.compute([])
        assert report.overall_score == 0.0
        assert len(report.tier_summaries) == 0


class TestAllPass:
    def test_single_vector(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0),
        ]
        report = engine.compute(results)
        assert report.overall_score == 1.0
        assert report.tier_summaries[0].passed == 1

    def test_multiple_tiers(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0),
            VectorResult("T2-001", Tier.AUTOMATION, "B", Verdict.CLEAN, 1.0),
        ]
        report = engine.compute(results)
        assert report.overall_score == 1.0


class TestAllFail:
    def test_all_flagged(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.FLAGGED, 0.0),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.FLAGGED, 0.0),
        ]
        report = engine.compute(results)
        assert report.overall_score == 0.0
        assert report.tier_summaries[0].failed == 2

    def test_all_inconclusive(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.INCONCLUSIVE, 0.0),
        ]
        report = engine.compute(results)
        assert report.tier_summaries[0].score == 0.0
        assert report.tier_summaries[0].inconclusive == 1
        assert report.tier_summaries[0].passed == 0


class TestPartialCredit:
    def test_challenged_gives_partial(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CHALLENGED, 0.4),
        ]
        report = engine.compute(results)
        assert report.tier_summaries[0].score == 0.4

    def test_mixed_verdicts(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.CHALLENGED, 0.4),
            VectorResult("T1-003", Tier.FINGERPRINT, "C", Verdict.FLAGGED, 0.0),
        ]
        report = engine.compute(results)
        # Simple average: (1.0 + 0.4 + 0.0) / 3 = 0.4666...
        assert 0.46 < report.tier_summaries[0].score < 0.47


class TestTierWeighting:
    def test_vendor_tier_weighted_higher(self):
        config = ScoringConfig()
        engine = WeightedScoringEngine(config)
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0),
            VectorResult("T7-001", Tier.EXTERNAL_VENDOR, "B", Verdict.CLEAN, 1.0),
        ]
        report = engine.compute(results)
        assert report.overall_score == 1.0

    def test_vendor_failure_hurts_more(self):
        config = ScoringConfig()
        engine = WeightedScoringEngine(config)
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0),
            VectorResult("T7-001", Tier.EXTERNAL_VENDOR, "B", Verdict.FLAGGED, 0.0),
        ]
        report = engine.compute(results)
        # (1.0*0.9 + 0.0*1.3) / (0.9 + 1.3) = 0.9 / 2.2 = 0.409...
        assert 0.40 < report.overall_score < 0.41


class TestCriticalFailureCap:
    """Critical cap triggers on CRITICAL severity + FLAGGED verdict only."""

    def test_critical_flagged_caps_high_score(self):
        """Cap triggers when CRITICAL+FLAGGED would otherwise leave score high."""
        config = ScoringConfig(critical_failure_cap=True, critical_cap_threshold=0.5)
        engine = WeightedScoringEngine(config)
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T3-001", Tier.EJECTOR, "C", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T3-002", Tier.EJECTOR, "D", Verdict.FLAGGED, 0.0, severity=Severity.CRITICAL),
        ]
        report = engine.compute(results)
        # Without cap: fingerprint=1.0(0.9), ejector=0.5(1.1)
        # = (0.9 + 0.55) / 2.0 = 0.725
        # With cap: min(0.725, 0.5) = 0.5
        assert report.overall_score == 0.5

    def test_critical_challenged_no_cap(self):
        """CRITICAL + CHALLENGED is partial credit, cap does NOT trigger."""
        config = ScoringConfig(critical_failure_cap=True, critical_cap_threshold=0.5)
        engine = WeightedScoringEngine(config)
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T3-001", Tier.EJECTOR, "C", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T2-001", Tier.AUTOMATION, "D", Verdict.CHALLENGED, 0.4, severity=Severity.CRITICAL),
        ]
        report = engine.compute(results)
        # Without cap: fp=1.0(0.9), auto=0.4(1.2), ejector=1.0(1.1)
        # = (0.9 + 0.48 + 1.1) / 3.2 = 0.775
        # CHALLENGED is NOT FLAGGED, so cap should NOT trigger
        assert report.overall_score > 0.5

    def test_warning_flagged_no_cap(self):
        """WARNING severity + FLAGGED does NOT trigger critical cap."""
        config = ScoringConfig(critical_failure_cap=True, critical_cap_threshold=0.5)
        engine = WeightedScoringEngine(config)
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T3-001", Tier.EJECTOR, "C", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T3-002", Tier.EJECTOR, "D", Verdict.FLAGGED, 0.0, severity=Severity.WARNING),
        ]
        report = engine.compute(results)
        # Same as test_critical_flagged_caps_high_score but WARNING not CRITICAL
        # Cap should NOT trigger
        assert report.overall_score > 0.5

    def test_no_cap_when_disabled(self):
        config = ScoringConfig(critical_failure_cap=False)
        engine = WeightedScoringEngine(config)
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T3-001", Tier.EJECTOR, "C", Verdict.CLEAN, 1.0, severity=Severity.INFO),
            VectorResult("T3-002", Tier.EJECTOR, "D", Verdict.FLAGGED, 0.0, severity=Severity.CRITICAL),
        ]
        report = engine.compute(results)
        assert report.overall_score > 0.5

    def test_no_cap_without_critical_failures(self):
        config = ScoringConfig(critical_failure_cap=True, critical_cap_threshold=0.5)
        engine = WeightedScoringEngine(config)
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0, severity=Severity.WARNING),
        ]
        report = engine.compute(results)
        assert report.overall_score == 1.0


class TestInconclusiveHandling:
    def test_inconclusive_excluded(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.INCONCLUSIVE, 0.0),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.CLEAN, 1.0),
        ]
        report = engine.compute(results)
        assert report.tier_summaries[0].score == 1.0
        assert report.tier_summaries[0].passed == 1
        assert report.tier_summaries[0].inconclusive == 1

    def test_all_inconclusive(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.INCONCLUSIVE, 0.0),
        ]
        report = engine.compute(results)
        assert report.tier_summaries[0].score == 0.0
        assert report.tier_summaries[0].passed == 0


class TestSkippedHandling:
    def test_skipped_excluded_from_score(self):
        """SKIPPED vectors excluded from both numerator and denominator."""
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.SKIPPED, 0.0),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.CLEAN, 1.0),
        ]
        report = engine.compute(results)
        # Only T1-002 counts: score = 1.0
        assert report.tier_summaries[0].score == 1.0
        assert report.tier_summaries[0].skipped == 1
        assert report.tier_summaries[0].passed == 1


class TestMetadata:
    def test_critical_failures_in_metadata(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T2-001", Tier.AUTOMATION, "A", Verdict.FLAGGED, 0.0, severity=Severity.CRITICAL),
        ]
        report = engine.compute(results)
        assert "critical_failures" in report.metadata
        assert len(report.metadata["critical_failures"]) == 1
        assert "T2-001" in report.metadata["critical_failures"]

    def test_critical_challenged_not_in_failures(self):
        """CRITICAL + CHALLENGED should NOT appear in critical_failures."""
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T2-001", Tier.AUTOMATION, "A", Verdict.CHALLENGED, 0.4, severity=Severity.CRITICAL),
        ]
        report = engine.compute(results)
        assert len(report.metadata["critical_failures"]) == 0


class TestFlaggedDenominator:
    """FLAGGED vectors must count in the denominator (regression guard)."""

    def test_flagged_drags_average_down(self):
        """1 clean + 1 flagged = 0.5, not 1.0."""
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.FLAGGED, 0.0),
        ]
        report = engine.compute(results)
        ts = report.tier_summaries[0]
        assert ts.score == 0.5, f"Expected 0.5, got {ts.score}"

    def test_inconclusive_excluded_from_denominator(self):
        """1 clean + 1 inconclusive = 1.0, not 0.5."""
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.CLEAN, 1.0),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.INCONCLUSIVE, 0.0),
        ]
        report = engine.compute(results)
        ts = report.tier_summaries[0]
        assert ts.score == 1.0
        assert ts.inconclusive == 1

    def test_all_flagged_zero(self):
        engine = WeightedScoringEngine()
        results = [
            VectorResult("T1-001", Tier.FINGERPRINT, "A", Verdict.FLAGGED, 0.0),
            VectorResult("T1-002", Tier.FINGERPRINT, "B", Verdict.FLAGGED, 0.0),
        ]
        report = engine.compute(results)
        ts = report.tier_summaries[0]
        assert ts.score == 0.0
