"""Unit tests for E2E historical trend tracker.

Tests valid report appending, invalid report rejection, history
truncation, duplicate handling, Markdown rendering, and CLI output.
No real browser, no live E2E, no network.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "e2e_trend.py"
sys.path.insert(0, str(SCRIPT.parent))
import e2e_trend as trend  # noqa: E402  type: ignore[import-not-found]


def _valid_report(
    *,
    timestamp: str = "2026-06-16T00:00:00Z",
    passed: int = 18,
    failed: int = 0,
    skipped: int = 0,
    duration_s: float = 12.345,
    failed_tests: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return a minimal valid v3 report for testing."""
    if failed_tests is None:
        failed_tests = []

    total = passed + failed + skipped
    tests: list[dict[str, Any]] = []
    for i in range(passed):
        tests.append({
            "name": f"test_pass_{i}", "status": "passed",
            "duration_s": 0.05, "file": "tests/e2e/test_foo.py",
            "error": None, "screenshot": None,
        })
    for i, ft in enumerate(failed_tests):
        tests.append({
            "name": ft.get("name", f"test_fail_{i}"), "status": "failed",
            "duration_s": ft.get("duration_s", 5.0), "file": "tests/e2e/test_bar.py",
            "error": ft.get("error", "AssertionError"), "screenshot": None,
        })
    for i in range(skipped):
        tests.append({
            "name": f"test_skip_{i}", "status": "skipped",
            "duration_s": 0.0, "file": "tests/e2e/test_baz.py",
            "error": None, "screenshot": None,
        })

    return {
        "schema_version": 3,
        "timestamp_utc": timestamp,
        "environment": {
            "backend": "patchright",
            "headless": True,
            "python_version": "3.12.0",
            "platform": "linux",
            "live": False,
        },
        "config": {
            "suite_name": "e2e-real-browser",
            "budget_seconds": 120.0,
        },
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "skipped": skipped,
            "duration_s": duration_s,
            "budget_exceeded": failed > 0 and duration_s > 10,
        },
        "tests": tests,
        "artifacts": {"json_path": None, "markdown_path": None},
    }


def _write_report(tmp_path: Path, report: dict[str, Any], name: str = "e2e-report.json") -> Path:
    """Write a report dict to a file and return the path."""
    path = tmp_path / name
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Test classes
# ---------------------------------------------------------------------------


class TestExtractRunSummary:
    """Test extract_run_summary()."""

    def test_basic_extraction(self) -> None:
        report = _valid_report()
        run = trend.extract_run_summary(report)
        assert run["suite_name"] == "e2e-real-browser"
        assert run["backend"] == "patchright"
        assert run["headless"] is True
        assert run["total"] == 18
        assert run["passed"] == 18
        assert run["failed"] == 0
        assert run["duration_s"] == 12.345
        assert run["failed_tests"] == []

    def test_failed_tests_collected(self) -> None:
        report = _valid_report(
            passed=15, failed=3,
            failed_tests=[
                {"name": "test_a"},
                {"name": "test_b"},
                {"name": "test_c"},
            ],
        )
        run = trend.extract_run_summary(report)
        assert len(run["failed_tests"]) == 3
        assert "test_a" in run["failed_tests"]

    def test_budget_exceeded(self) -> None:
        report = _valid_report()
        report["summary"]["budget_exceeded"] = True
        run = trend.extract_run_summary(report)
        assert run["budget_exceeded"] is True


class TestAppendRun:
    """Test append_run()."""

    def test_append_to_empty(self) -> None:
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        run = trend.extract_run_summary(_valid_report())
        result = trend.append_run(history, run, max_runs=30)
        assert len(result["runs"]) == 1
        assert result["runs"][0]["timestamp_utc"] == run["timestamp_utc"]

    def test_truncate_to_max_runs(self) -> None:
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 3, "runs": []}
        for i in range(10):
            run = trend.extract_run_summary(
                _valid_report(timestamp=f"2026-06-1{i}T00:00:00Z"),
            )
            history = trend.append_run(history, run, max_runs=3)
        assert len(history["runs"]) == 3
        # Should keep the 3 most recent
        timestamps = [r["timestamp_utc"] for r in history["runs"]]
        assert "2026-06-19T00:00:00Z" in timestamps
        assert "2026-06-16T00:00:00Z" not in timestamps

    def test_duplicate_timestamp_replaces(self) -> None:
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        run1 = trend.extract_run_summary(
            _valid_report(timestamp="2026-06-16T00:00:00Z", passed=10),
        )
        history = trend.append_run(history, run1, max_runs=30)

        # Same timestamp, different data
        run2 = trend.extract_run_summary(
            _valid_report(timestamp="2026-06-16T00:00:00Z", passed=15),
        )
        history = trend.append_run(history, run2, max_runs=30)

        assert len(history["runs"]) == 1
        assert history["runs"][0]["passed"] == 15  # replaced, not duplicated

    def test_sorted_newest_first(self) -> None:
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        for ts in ["2026-06-14T00:00:00Z", "2026-06-16T00:00:00Z", "2026-06-15T00:00:00Z"]:
            run = trend.extract_run_summary(_valid_report(timestamp=ts))
            history = trend.append_run(history, run, max_runs=30)
        assert history["runs"][0]["timestamp_utc"] == "2026-06-16T00:00:00Z"
        assert history["runs"][1]["timestamp_utc"] == "2026-06-15T00:00:00Z"
        assert history["runs"][2]["timestamp_utc"] == "2026-06-14T00:00:00Z"

    def test_updated_utc_set(self) -> None:
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        run = trend.extract_run_summary(_valid_report())
        result = trend.append_run(history, run, max_runs=30)
        assert result["updated_utc"] != ""


class TestProcessReports:
    """Test process_reports() with file I/O and validation."""

    def test_valid_report_appended(self, tmp_path: Path) -> None:
        report_path = _write_report(tmp_path, _valid_report())
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        history, errors = trend.process_reports([report_path], history, max_runs=30)
        assert len(errors) == 0
        assert len(history["runs"]) == 1

    def test_invalid_report_rejected(self, tmp_path: Path) -> None:
        bad_report = {"not_valid": True}
        report_path = _write_report(tmp_path, bad_report)
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        history, errors = trend.process_reports([report_path], history, max_runs=30)
        assert len(errors) == 1
        assert "schema validation" in errors[0].lower()
        assert len(history["runs"]) == 0  # not appended

    def test_missing_file_rejected(self, tmp_path: Path) -> None:
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        history, errors = trend.process_reports([tmp_path / "nonexistent.json"], history, max_runs=30)
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_invalid_json_rejected(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        history, errors = trend.process_reports([path], history, max_runs=30)
        assert len(errors) == 1
        assert "invalid json" in errors[0].lower()

    def test_multiple_reports(self, tmp_path: Path) -> None:
        paths = []
        for i in range(3):
            report = _valid_report(timestamp=f"2026-06-1{i}T00:00:00Z")
            paths.append(_write_report(tmp_path, report, name=f"report-{i}.json"))
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        history, errors = trend.process_reports(paths, history, max_runs=30)
        assert len(errors) == 0
        assert len(history["runs"]) == 3

    def test_mixed_valid_invalid(self, tmp_path: Path) -> None:
        good = _write_report(tmp_path, _valid_report(), name="good.json")
        bad = _write_report(tmp_path, {"bad": True}, name="bad.json")
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        history, errors = trend.process_reports([good, bad], history, max_runs=30)
        assert len(errors) == 1
        assert len(history["runs"]) == 1  # only valid one appended


class TestLoadHistory:
    """Test load_history()."""

    def test_existing_history(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        data = {"schema_version": 1, "runs": [{"timestamp_utc": "ts"}], "max_runs": 10}
        path.write_text(json.dumps(data), encoding="utf-8")
        history = trend.load_history(path)
        assert len(history["runs"]) == 1

    def test_empty_history_shell(self, tmp_path: Path) -> None:
        history = trend.load_history(tmp_path / "nonexistent.json")
        assert history["runs"] == []
        assert history["schema_version"] == 1
        assert history["max_runs"] == 30

    def test_corrupt_history_treated_as_empty(self, tmp_path: Path) -> None:
        path = tmp_path / "history.json"
        path.write_text("{corrupt", encoding="utf-8")
        history = trend.load_history(path)
        assert history["runs"] == []


class TestRenderTrendMarkdown:
    """Test render_trend_markdown()."""

    def test_empty_history(self) -> None:
        history = {"schema_version": 1, "updated_utc": "", "max_runs": 30, "runs": []}
        md = trend.render_trend_markdown(history)
        assert "# E2E Trend Summary" in md
        assert "No runs recorded" in md

    def test_single_run(self) -> None:
        history = {"schema_version": 1, "updated_utc": "ts", "max_runs": 30, "runs": [
            trend.extract_run_summary(_valid_report()),
        ]}
        md = trend.render_trend_markdown(history)
        assert "# E2E Trend Summary" in md
        assert "18/18 passed" in md
        assert "first run" in md

    def test_pass_fail_trend(self) -> None:
        history = {"schema_version": 1, "updated_utc": "ts", "max_runs": 30, "runs": [
            trend.extract_run_summary(_valid_report(timestamp="2026-06-16T00:00:00Z", passed=15, failed=3, failed_tests=[{"name": "test_a"}])),
            trend.extract_run_summary(_valid_report(timestamp="2026-06-15T00:00:00Z", passed=18, failed=0)),
        ]}
        md = trend.render_trend_markdown(history)
        assert "Pass rate trend" in md
        assert "Duration trend" in md

    def test_duration_trend(self) -> None:
        history = {"schema_version": 1, "updated_utc": "ts", "max_runs": 30, "runs": [
            trend.extract_run_summary(_valid_report(timestamp="2026-06-16T00:00:00Z", duration_s=20.0)),
            trend.extract_run_summary(_valid_report(timestamp="2026-06-15T00:00:00Z", duration_s=10.0)),
        ]}
        md = trend.render_trend_markdown(history)
        assert "Duration trend" in md
        assert "20.0s" in md

    def test_budget_exceeded_count(self) -> None:
        history = {"schema_version": 1, "updated_utc": "ts", "max_runs": 30, "runs": [
            trend.extract_run_summary(_valid_report(timestamp="t1", passed=18)),
            trend.extract_run_summary(_valid_report(timestamp="t2", passed=18)),
            trend.extract_run_summary(_valid_report(timestamp="t3", passed=10, failed=8, duration_s=50.0)),
        ]}
        md = trend.render_trend_markdown(history)
        assert "Budget exceeded" in md

    def test_recent_failures_listed(self) -> None:
        history = {"schema_version": 1, "updated_utc": "ts", "max_runs": 30, "runs": [
            trend.extract_run_summary(_valid_report(
                timestamp="2026-06-16T00:00:00Z",
                passed=15, failed=3,
                failed_tests=[{"name": "test_fail_one"}, {"name": "test_fail_two"}],
            )),
        ]}
        md = trend.render_trend_markdown(history)
        assert "Recent Failures" in md
        assert "test_fail_one" in md
        assert "test_fail_two" in md

    def test_no_failures_message(self) -> None:
        history = {"schema_version": 1, "updated_utc": "ts", "max_runs": 30, "runs": [
            trend.extract_run_summary(_valid_report()),
        ]}
        md = trend.render_trend_markdown(history)
        assert "No failures" in md

    def test_no_thresholds_or_gates(self) -> None:
        """Markdown should not contain threshold or gate language."""
        history = {"schema_version": 1, "updated_utc": "ts", "max_runs": 30, "runs": [
            trend.extract_run_summary(_valid_report()),
        ]}
        md = trend.render_trend_markdown(history)
        assert "threshold" not in md.lower()
        assert "gate" not in md.lower()
        assert "regression" not in md.lower()


class TestFileWriting:
    """Test write_history() and write_markdown()."""

    def test_write_history_creates_dirs(self, tmp_path: Path) -> None:
        history = {"schema_version": 1, "runs": [], "max_runs": 30}
        path = tmp_path / "a" / "b" / "history.json"
        trend.write_history(history, path)
        assert path.exists()
        loaded = json.loads(path.read_text())
        assert loaded["schema_version"] == 1

    def test_write_markdown_creates_dirs(self, tmp_path: Path) -> None:
        path = tmp_path / "a" / "b" / "trend.md"
        trend.write_markdown("# Test", path)
        assert path.exists()
        assert "# Test" in path.read_text()

    def test_existing_history_extended(self, tmp_path: Path) -> None:
        """Re-processing should extend, not replace, history."""
        history_path = tmp_path / "history.json"

        # First run
        report1 = _write_report(tmp_path, _valid_report(timestamp="2026-06-14T00:00:00Z"), "r1.json")
        history = trend.load_history(history_path)
        history, _ = trend.process_reports([report1], history, max_runs=30)
        trend.write_history(history, history_path)
        assert len(json.loads(history_path.read_text())["runs"]) == 1

        # Second run
        report2 = _write_report(tmp_path, _valid_report(timestamp="2026-06-15T00:00:00Z"), "r2.json")
        history = trend.load_history(history_path)
        history, _ = trend.process_reports([report2], history, max_runs=30)
        trend.write_history(history, history_path)
        assert len(json.loads(history_path.read_text())["runs"]) == 2


class TestCLI:
    """Test the CLI arg parsing and output."""

    def test_cli_writes_both_files(self, tmp_path: Path) -> None:
        """The main() function should write both JSON and Markdown."""
        from unittest.mock import patch

        report_path = _write_report(tmp_path, _valid_report())
        history_path = tmp_path / "history.json"
        md_path = tmp_path / "trend.md"

        with patch.object(sys, "argv", [
            "e2e_trend",
            "--reports", str(report_path),
            "--history", str(history_path),
            "--markdown", str(md_path),
            "--max-runs", "30",
        ]):
            trend.main()

        assert history_path.exists()
        assert md_path.exists()
        assert "# E2E Trend Summary" in md_path.read_text()

        data = json.loads(history_path.read_text())
        assert len(data["runs"]) == 1
