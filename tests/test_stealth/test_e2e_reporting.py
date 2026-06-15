"""Tests for E2E JSON/Markdown reporting — Track E (Wave 29).

These are unit tests that run without SB_E2E — they test the reporting
functions directly, not the browser harness.
"""

from __future__ import annotations

import json

from super_browser.testing import build_e2e_json_report, render_e2e_markdown_report


class TestJSONReport:
    def test_basic_structure(self) -> None:
        report = build_e2e_json_report(
            suite_name="e2e-test",
            results=[],
            environment={"backend": "patchright"},
            suite_duration_ms=1000.0,
            budget_seconds=120.0,
        )
        assert report["schema_version"] == 2
        assert report["suite_name"] == "e2e-test"
        assert "timestamp" in report
        assert report["environment"]["backend"] == "patchright"
        assert report["results"] == []

    def test_summary_counts(self) -> None:
        results = [
            {"test_name": "test_a", "status": "passed", "duration_ms": 100.0, "budget_exceeded": False},
            {"test_name": "test_b", "status": "passed", "duration_ms": 200.0, "budget_exceeded": False},
            {"test_name": "test_c", "status": "failed", "duration_ms": 300.0, "budget_exceeded": True},
            {"test_name": "test_d", "status": "skipped", "duration_ms": 0.0, "budget_exceeded": False},
        ]
        report = build_e2e_json_report(
            suite_name="e2e-test",
            results=results,
            environment={},
            suite_duration_ms=600.0,
            budget_seconds=60.0,
        )
        summary = report["summary"]
        assert summary["total"] == 4
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["skipped"] == 1
        assert summary["suite_duration_ms"] == 600.0
        assert summary["budget_seconds"] == 60.0

    def test_json_serializable(self) -> None:
        report = build_e2e_json_report(
            suite_name="e2e",
            results=[
                {"test_name": "t", "status": "passed", "duration_ms": 1.0, "budget_exceeded": False},
            ],
            environment={"backend": "patchright", "python_version": "3.11"},
            suite_duration_ms=1.0,
            budget_seconds=30.0,
        )
        json_str = json.dumps(report)
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == 2


class TestMarkdownReport:
    def test_renders_headers(self) -> None:
        report = build_e2e_json_report(
            suite_name="my-suite",
            results=[],
            environment={"backend": "patchright", "headless": True},
            suite_duration_ms=500.0,
            budget_seconds=60.0,
        )
        md = render_e2e_markdown_report(report)
        assert "# E2E Report: my-suite" in md
        assert "## Summary" in md
        assert "## Environment" in md
        assert "## Results" in md

    def test_renders_results_table(self) -> None:
        report = build_e2e_json_report(
            suite_name="t",
            results=[
                {"test_name": "test_one", "status": "passed", "duration_ms": 150.0, "budget_exceeded": False},
                {"test_name": "test_two", "status": "failed", "duration_ms": 5000.0, "budget_exceeded": True},
            ],
            environment={},
            suite_duration_ms=5150.0,
            budget_seconds=120.0,
        )
        md = render_e2e_markdown_report(report)
        assert "test_one" in md
        assert "test_two" in md
        assert "passed" in md
        assert "failed" in md
        assert "✅" in md
        assert "❌" in md

    def test_empty_results(self) -> None:
        report = build_e2e_json_report(
            suite_name="empty",
            results=[],
            environment={},
            suite_duration_ms=0.0,
            budget_seconds=120.0,
        )
        md = render_e2e_markdown_report(report)
        assert "Total:** 0" in md
        assert "| Test | Status" in md
