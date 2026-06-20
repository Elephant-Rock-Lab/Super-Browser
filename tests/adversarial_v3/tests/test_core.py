"""Tests for core types, protocols, and utilities."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

from adversarial3.core import (
    AssessmentReport,
    BaseVector,
    Severity,
    Tier,
    TierSummary,
    VectorResult,
    Verdict,
    now_utc,
    severity_emoji,
    verdict_emoji,
)


class TestVerdictEnum:
    """Test Verdict enum behavior."""

    def test_values(self):
        assert str(Verdict.CLEAN) == "clean"
        assert str(Verdict.FLAGGED) == "flagged"
        assert str(Verdict.CHALLENGED) == "challenged"
        assert str(Verdict.INCONCLUSIVE) == "inconclusive"
        assert str(Verdict.SKIPPED) == "skipped"

    def test_equality(self):
        assert Verdict.CLEAN != Verdict.FLAGGED
        assert Verdict.CLEAN == Verdict.CLEAN

    def test_from_string(self):
        assert Verdict("clean") == Verdict.CLEAN
        assert Verdict("flagged") == Verdict.FLAGGED


class TestSeverityEnum:
    """Test Severity enum behavior."""

    def test_values(self):
        assert str(Severity.CRITICAL) == "critical"
        assert str(Severity.WARNING) == "warning"
        assert str(Severity.INFO) == "info"


class TestTierEnum:
    """Test Tier enum behavior."""

    def test_values(self):
        assert str(Tier.FINGERPRINT) == "fingerprint"
        assert str(Tier.AUTOMATION) == "automation"
        assert str(Tier.EXTERNAL_VENDOR) == "external_vendor"
        assert str(Tier.CONTROLLED) == "controlled"

    def test_from_string(self):
        assert Tier("fingerprint") == Tier.FINGERPRINT
        assert Tier("external_vendor") == Tier.EXTERNAL_VENDOR


class TestVectorResult:
    """Test VectorResult dataclass."""

    def test_valid_creation(self):
        r = VectorResult(
            vector_id="T1-001",
            tier=Tier.FINGERPRINT,
            name="Test",
            verdict=Verdict.CLEAN,
            score=1.0,
            details={"foo": "bar"},
            severity=Severity.INFO,
            duration_ms=42.0,
        )
        assert r.vector_id == "T1-001"
        assert r.score == 1.0
        assert r.duration_ms == 42.0

    def test_score_clamping_above(self):
        r = VectorResult(
            vector_id="T1-001", tier=Tier.FINGERPRINT, name="Test",
            verdict=Verdict.CLEAN, score=1.5,
        )
        assert r.score == 1.0

    def test_score_clamping_below(self):
        r = VectorResult(
            vector_id="T1-001", tier=Tier.FINGERPRINT, name="Test",
            verdict=Verdict.CLEAN, score=-0.5,
        )
        assert r.score == 0.0

    def test_frozen(self):
        r = VectorResult(
            vector_id="T1-001", tier=Tier.FINGERPRINT, name="Test",
            verdict=Verdict.CLEAN, score=1.0,
        )
        # Frozen dataclass — direct assignment raises AttributeError
        # (FrozenInstanceError on <3.11, AttributeError on 3.11+)
        import pytest as _pytest
        with _pytest.raises((FrozenInstanceError, AttributeError)):
            r.score = 0.5  # type: ignore[misc]

    def test_to_dict(self):
        r = VectorResult(
            vector_id="T1-001", tier=Tier.FINGERPRINT, name="Test",
            verdict=Verdict.CLEAN, score=1.0, details={"x": 1},
        )
        d = r.to_dict()
        assert d["vector_id"] == "T1-001"
        assert d["tier"] == "fingerprint"
        assert d["verdict"] == "clean"
        assert d["score"] == 1.0


class TestTierSummary:
    """Test TierSummary dataclass."""

    def test_creation(self):
        ts = TierSummary(
            tier=Tier.FINGERPRINT,
            score=0.85,
            vector_count=10,
            passed=8,
            failed=2,
            skipped=0,
            inconclusive=0,
            avg_duration_ms=45.0,
        )
        assert ts.score == 0.85
        assert ts.passed == 8

    def test_to_dict(self):
        ts = TierSummary(
            tier=Tier.FINGERPRINT,
            score=0.85,
            vector_count=10,
            passed=8,
            failed=2,
            skipped=0,
            inconclusive=0,
            avg_duration_ms=45.0,
        )
        d = ts.to_dict()
        assert d["tier"] == "fingerprint"
        assert d["score"] == 0.85


class TestAssessmentReport:
    """Test AssessmentReport."""

    def test_empty_report(self):
        r = AssessmentReport(
            run_id="test",
            timestamp=now_utc(),
            overall_score=0.0,
            tier_summaries=[],
            results=[],
        )
        assert r.overall_score == 0.0
        assert r.total_targets == 0  # computed from results

    def test_to_json(self):
        r = AssessmentReport(
            run_id="test",
            timestamp=now_utc(),
            overall_score=0.85,
            tier_summaries=[],
            results=[],
        )
        json_str = r.to_json()
        assert "test" in json_str
        assert "0.85" in json_str


class TestUtilities:
    """Test utility functions."""

    def test_now_utc_format(self):
        ts = now_utc()
        assert "T" in ts
        assert "+00:00" in ts or "Z" in ts

    def test_verdict_emoji(self):
        assert verdict_emoji(Verdict.CLEAN) == "✅"
        assert verdict_emoji(Verdict.FLAGGED) == "🚫"
        assert verdict_emoji(Verdict.CHALLENGED) == "⚠️"
        assert verdict_emoji(Verdict.INCONCLUSIVE) == "❓"

    def test_severity_emoji(self):
        assert severity_emoji(Severity.CRITICAL) == "🔴"
        assert severity_emoji(Severity.WARNING) == "🟡"
        assert severity_emoji(Severity.INFO) == "🔵"


class TestBaseVector:
    """Test BaseVector abstract class."""

    def test_properties(self):
        class DummyVector(BaseVector):
            async def evaluate(self, ctx):
                return VectorResult(
                    vector_id="T0-001", tier=Tier.FINGERPRINT, name="Dummy",
                    verdict=Verdict.CLEAN, score=1.0,
                )

        v = DummyVector("T0-001", Tier.FINGERPRINT, "Dummy", "A test vector", Severity.INFO)
        assert v.vector_id == "T0-001"
        assert v.tier == Tier.FINGERPRINT
        assert v.name == "Dummy"
        assert v.severity == Severity.INFO
        assert v.requires_browser is True
        assert v.requires_interaction is False
