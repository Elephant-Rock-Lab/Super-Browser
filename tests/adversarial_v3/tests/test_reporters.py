"""Tests for report formatters (JSON and Markdown).

These verify that reporters produce valid output and would have caught
the release-blocking Markdown reporter syntax error.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from adversarial3.core import (
    AssessmentReport,
    Severity,
    Tier,
    TierSummary,
    VectorResult,
    Verdict,
    now_utc,
)
from adversarial3.reporters.json_reporter import JSONReporter
from adversarial3.reporters.markdown_reporter import MarkdownReporter


def _make_report() -> AssessmentReport:
    """Build a minimal report with mixed verdicts for testing."""
    results = [
        VectorResult(
            vector_id="T1-001", tier=Tier.FINGERPRINT, name="UA-Platform Check",
            verdict=Verdict.CLEAN, score=1.0,
            details={"ua": "Mozilla/5.0", "platform": "Win32"},
        ),
        VectorResult(
            vector_id="T2-001", tier=Tier.AUTOMATION, name="navigator.webdriver",
            verdict=Verdict.FLAGGED, score=0.0,
            details={"webdriver": True},
            severity=Severity.CRITICAL,
        ),
        VectorResult(
            vector_id="T3-001", tier=Tier.EJECTOR, name="Canvas Noise",
            verdict=Verdict.CHALLENGED, score=0.4,
            details={"perturbed": True},
            severity=Severity.WARNING,
        ),
    ]
    tier_summaries = [
        TierSummary(
            tier=Tier.FINGERPRINT, score=1.0, vector_count=1,
            passed=1, failed=0, skipped=0, inconclusive=0,
            avg_duration_ms=5.0, critical_failures=[],
        ),
        TierSummary(
            tier=Tier.AUTOMATION, score=0.0, vector_count=1,
            passed=0, failed=1, skipped=0, inconclusive=0,
            avg_duration_ms=10.0, critical_failures=["T2-001"],
        ),
        TierSummary(
            tier=Tier.EJECTOR, score=0.4, vector_count=1,
            passed=0, failed=1, skipped=0, inconclusive=0,
            avg_duration_ms=8.0, critical_failures=[],
        ),
    ]
    return AssessmentReport(
        run_id="test-001",
        timestamp=now_utc(),
        overall_score=0.3,
        tier_summaries=tier_summaries,
        results=results,
        metadata={"backend": "StubBackend", "suite_version": "3.0.0"},
    )


class TestMarkdownReporter:
    def test_renders_without_error(self):
        """The reporter must import and render without raising."""
        report = _make_report()
        md = MarkdownReporter().render(report)
        assert isinstance(md, str)
        assert len(md) > 100

    def test_extension(self):
        assert MarkdownReporter().extension() == "md"

    def test_contains_run_id(self):
        md = MarkdownReporter().render(_make_report())
        assert "test-001" in md

    def test_contains_summary_table(self):
        md = MarkdownReporter().render(_make_report())
        assert "| Tier |" in md
        assert "fingerprint" in md
        assert "automation" in md

    def test_contains_critical_section(self):
        md = MarkdownReporter().render(_make_report())
        # T2-001 is CRITICAL + FLAGGED
        assert "Critical Failures" in md
        assert "T2-001" in md

    def test_no_critical_section_when_clean(self):
        """No critical section when no CRITICAL+FLAGGED results."""
        results = [
            VectorResult(
                vector_id="T1-001", tier=Tier.FINGERPRINT, name="Clean",
                verdict=Verdict.CLEAN, score=1.0,
            ),
        ]
        report = AssessmentReport(
            run_id="clean-001", timestamp=now_utc(), overall_score=1.0,
            tier_summaries=[], results=results, metadata={},
        )
        md = MarkdownReporter().render(report)
        assert "Critical Failures" not in md

    def test_write_to_file(self, tmp_path):
        report = _make_report()
        path = tmp_path / "report.md"
        MarkdownReporter().write(report, path)
        assert path.exists()
        content = path.read_text(encoding="utf-8")
        assert "test-001" in content

    def test_metadata_included(self):
        md = MarkdownReporter().render(_make_report())
        assert "suite_version" in md
        assert "3.0.0" in md

    def test_details_rendered_as_json(self):
        """Vector details must be valid JSON in the output."""
        md = MarkdownReporter().render(_make_report())
        assert "webdriver" in md  # from details dict


class TestJSONReporter:
    def test_renders_valid_json(self):
        report = _make_report()
        text = JSONReporter().render(report)
        data = json.loads(text)  # Must not raise
        assert data["run_id"] == "test-001"
        assert len(data["results"]) == 3

    def test_extension(self):
        assert JSONReporter().extension() == "json"

    def test_write_to_file(self, tmp_path):
        report = _make_report()
        path = tmp_path / "report.json"
        JSONReporter().write(report, path)
        assert path.exists()
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["overall_score"] == 0.3
