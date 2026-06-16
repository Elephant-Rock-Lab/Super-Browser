"""Tests for E2E JSON/Markdown reporting — schema v3.

Unit tests that run without SB_E2E — they test the reporting functions
and the schema validator directly, not the browser harness.
"""

from __future__ import annotations

import json

from super_browser.testing import build_e2e_json_report, render_e2e_markdown_report


def _sample_results() -> list[dict]:
    return [
        {
            "test_name": "test_a",
            "status": "passed",
            "duration_ms": 100.0,
            "budget_exceeded": False,
            "nodeid": "tests/e2e/test_foo.py::test_a",
        },
        {
            "test_name": "test_b",
            "status": "passed",
            "duration_ms": 200.0,
            "budget_exceeded": False,
            "nodeid": "tests/e2e/test_foo.py::test_b",
        },
        {
            "test_name": "test_c",
            "status": "failed",
            "duration_ms": 300.0,
            "budget_exceeded": True,
            "nodeid": "tests/e2e/test_bar.py::test_c",
            "error": "AssertionError: expected True",
        },
        {
            "test_name": "test_d",
            "status": "skipped",
            "duration_ms": 0.0,
            "budget_exceeded": False,
            "nodeid": "tests/e2e/test_bar.py::test_d",
        },
    ]


class TestJSONReport:
    def test_basic_structure(self) -> None:
        report = build_e2e_json_report(
            suite_name="e2e-test",
            results=[],
            environment={"backend": "patchright"},
            suite_duration_ms=1000.0,
            budget_seconds=120.0,
        )
        assert report["schema_version"] == 3
        assert report["config"]["suite_name"] == "e2e-test"
        assert "timestamp_utc" in report
        assert report["environment"]["backend"] == "patchright"
        assert report["tests"] == []

    def test_summary_counts(self) -> None:
        report = build_e2e_json_report(
            suite_name="e2e-test",
            results=_sample_results(),
            environment={},
            suite_duration_ms=600.0,
            budget_seconds=60.0,
        )
        summary = report["summary"]
        assert summary["total"] == 4
        assert summary["passed"] == 2
        assert summary["failed"] == 1
        assert summary["skipped"] == 1
        assert summary["duration_s"] == 0.6
        assert summary["budget_exceeded"] is True  # one test exceeded

    def test_budget_exceeded_false(self) -> None:
        results = [
            {"test_name": "t", "status": "passed", "duration_ms": 10.0, "budget_exceeded": False},
        ]
        report = build_e2e_json_report(
            suite_name="e2e",
            results=results,
            environment={},
            suite_duration_ms=10.0,
            budget_seconds=60.0,
        )
        assert report["summary"]["budget_exceeded"] is False

    def test_json_serializable(self) -> None:
        report = build_e2e_json_report(
            suite_name="e2e",
            results=_sample_results(),
            environment={"backend": "patchright", "python_version": "3.11"},
            suite_duration_ms=1.0,
            budget_seconds=30.0,
        )
        json_str = json.dumps(report)
        parsed = json.loads(json_str)
        assert parsed["schema_version"] == 3

    def test_tests_format(self) -> None:
        """Tests array should have v3 field names."""
        report = build_e2e_json_report(
            suite_name="e2e",
            results=_sample_results(),
            environment={},
            suite_duration_ms=100.0,
            budget_seconds=60.0,
        )
        tests = report["tests"]
        assert len(tests) == 4

        t0 = tests[0]
        assert t0["name"] == "test_a"
        assert t0["status"] == "passed"
        assert t0["duration_s"] == 0.1  # ms → s conversion
        assert t0["file"] == "tests/e2e/test_foo.py"
        assert t0["error"] is None

        # Failed test should have error
        t2 = tests[2]
        assert t2["name"] == "test_c"
        assert t2["error"] == "AssertionError: expected True"

    def test_artifacts_included(self) -> None:
        report = build_e2e_json_report(
            suite_name="e2e",
            results=[],
            environment={},
            suite_duration_ms=0.0,
            budget_seconds=60.0,
            artifacts={"json_path": "/tmp/r.json", "markdown_path": "/tmp/r.md"},
        )
        assert report["artifacts"]["json_path"] == "/tmp/r.json"
        assert report["artifacts"]["markdown_path"] == "/tmp/r.md"

    def test_artifacts_default_null(self) -> None:
        report = build_e2e_json_report(
            suite_name="e2e",
            results=[],
            environment={},
            suite_duration_ms=0.0,
            budget_seconds=60.0,
        )
        assert report["artifacts"]["json_path"] is None
        assert report["artifacts"]["markdown_path"] is None


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
        assert "## Tests" in md

    def test_renders_tests_table(self) -> None:
        report = build_e2e_json_report(
            suite_name="t",
            results=_sample_results(),
            environment={},
            suite_duration_ms=5150.0,
            budget_seconds=120.0,
        )
        md = render_e2e_markdown_report(report)
        assert "test_a" in md
        assert "test_c" in md
        assert "passed" in md
        assert "failed" in md
        assert "✅" in md
        assert "❌" in md

    def test_empty_tests(self) -> None:
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
