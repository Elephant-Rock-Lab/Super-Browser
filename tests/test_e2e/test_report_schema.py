"""Tests for E2E report schema validation (v3).

Exercises the validator with valid reports, missing fields, wrong types,
failed entries, skipped tests, and artifact paths. All tests run without
a real browser.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "validate_e2e_report.py"
sys.path.insert(0, str(SCRIPT.parent))
from validate_e2e_report import validate_report  # noqa: E402  type: ignore[import-not-found]


def _valid_report() -> dict[str, Any]:
    """Return a minimal valid v3 report."""
    return {
        "schema_version": 3,
        "timestamp_utc": "2026-06-16T00:00:00Z",
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
            "total": 3,
            "passed": 2,
            "failed": 1,
            "skipped": 0,
            "duration_s": 5.5,
            "budget_exceeded": False,
        },
        "tests": [
            {
                "name": "test_navigate",
                "status": "passed",
                "duration_s": 0.05,
                "file": "tests/e2e/test_navigation.py",
                "error": None,
                "screenshot": None,
            },
            {
                "name": "test_click",
                "status": "passed",
                "duration_s": 0.08,
                "file": "tests/e2e/test_interaction.py",
                "error": None,
                "screenshot": None,
            },
            {
                "name": "test_fail_example",
                "status": "failed",
                "duration_s": 5.37,
                "file": "tests/e2e/test_example.py",
                "error": "TimeoutError: page.goto timed out",
                "screenshot": "tests/e2e/artifacts/test_fail_example-failure.png",
            },
        ],
        "artifacts": {
            "json_path": "tests/e2e/artifacts/e2e-report.json",
            "markdown_path": "tests/e2e/artifacts/e2e-report.md",
        },
    }


class TestValidReport:
    """Reports that should pass validation."""

    def test_minimal_valid(self) -> None:
        report = _valid_report()
        errors = validate_report(report)
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_empty_tests(self) -> None:
        report = _valid_report()
        report["tests"] = []
        report["summary"]["total"] = 0
        report["summary"]["passed"] = 0
        report["summary"]["failed"] = 0
        errors = validate_report(report)
        assert errors == []

    def test_skipped_tests(self) -> None:
        report = _valid_report()
        report["tests"][0]["status"] = "skipped"
        report["summary"]["skipped"] = 1
        report["summary"]["passed"] = 1
        errors = validate_report(report)
        assert errors == []

    def test_no_artifacts_key_errors(self) -> None:
        """artifacts is now required — missing it must error."""
        report = _valid_report()
        del report["artifacts"]
        errors = validate_report(report)
        assert any("artifacts" in e for e in errors)

    def test_null_artifact_paths(self) -> None:
        report = _valid_report()
        report["artifacts"] = {"json_path": None, "markdown_path": None}
        errors = validate_report(report)
        assert errors == []

    def test_test_without_optional_fields(self) -> None:
        """Tests don't need error/screenshot fields."""
        report = _valid_report()
        for t in report["tests"]:
            del t["error"]
            del t["screenshot"]
        errors = validate_report(report)
        assert errors == []


class TestMissingTopLevelFields:
    """Reports missing required top-level keys."""

    @pytest.mark.parametrize("missing_key", [
        "schema_version",
        "timestamp_utc",
        "environment",
        "config",
        "summary",
        "tests",
        "artifacts",
    ])
    def test_missing_key(self, missing_key: str) -> None:
        report = _valid_report()
        del report[missing_key]
        errors = validate_report(report)
        assert any(f"'{missing_key}'" in e for e in errors), f"Expected error about '{missing_key}'"


class TestWrongTypes:
    """Reports with wrong field types."""

    def test_schema_version_not_int(self) -> None:
        report = _valid_report()
        report["schema_version"] = "3"
        errors = validate_report(report)
        assert any("schema_version" in e and "int" in e for e in errors)

    def test_schema_version_wrong_value(self) -> None:
        report = _valid_report()
        report["schema_version"] = 2
        errors = validate_report(report)
        assert any("schema_version" in e and "3" in e for e in errors)

    def test_tests_is_not_list(self) -> None:
        report = _valid_report()
        report["tests"] = "not a list"
        errors = validate_report(report)
        assert any("tests" in e and "list" in e for e in errors)

    def test_summary_total_not_int(self) -> None:
        report = _valid_report()
        report["summary"]["total"] = "3"
        errors = validate_report(report)
        assert any("total" in e and "int" in e for e in errors)

    def test_budget_exceeded_not_bool(self) -> None:
        report = _valid_report()
        report["summary"]["budget_exceeded"] = "yes"
        errors = validate_report(report)
        assert any("budget_exceeded" in e and "bool" in e for e in errors)

    def test_headless_not_bool(self) -> None:
        report = _valid_report()
        report["environment"]["headless"] = "yes"
        errors = validate_report(report)
        assert any("headless" in e and "bool" in e for e in errors)

    def test_duration_s_not_numeric(self) -> None:
        report = _valid_report()
        report["summary"]["duration_s"] = "5.5"
        errors = validate_report(report)
        assert any("duration_s" in e and "numeric" in e for e in errors)


class TestSummaryCrossCheck:
    """Test summary count cross-validation."""

    def test_counts_dont_add_up(self) -> None:
        report = _valid_report()
        report["summary"]["total"] = 5  # but only 3 tests
        errors = validate_report(report)
        assert any("add up" in e for e in errors)

    def test_counts_match(self) -> None:
        report = _valid_report()
        # Ensure counts are correct
        report["summary"]["total"] = 3
        report["summary"]["passed"] = 2
        report["summary"]["failed"] = 1
        report["summary"]["skipped"] = 0
        errors = validate_report(report)
        assert not any("add up" in e for e in errors)


class TestTestEntryValidation:
    """Test per-test entry validation."""

    def test_invalid_status(self) -> None:
        report = _valid_report()
        report["tests"][0]["status"] = "error"
        errors = validate_report(report)
        assert any("status" in e and "passed" in e for e in errors)

    def test_missing_name(self) -> None:
        report = _valid_report()
        del report["tests"][0]["name"]
        errors = validate_report(report)
        assert any("name" in e for e in errors)

    def test_empty_name(self) -> None:
        report = _valid_report()
        report["tests"][0]["name"] = ""
        errors = validate_report(report)
        assert any("name" in e for e in errors)

    def test_duration_s_wrong_type(self) -> None:
        report = _valid_report()
        report["tests"][0]["duration_s"] = "0.05"
        errors = validate_report(report)
        assert any("duration_s" in e and "numeric" in e for e in errors)

    def test_missing_duration_s(self) -> None:
        """duration_s is required per test entry."""
        report = _valid_report()
        del report["tests"][0]["duration_s"]
        errors = validate_report(report)
        assert any("duration_s" in e and "missing" in e for e in errors)

    def test_file_not_string(self) -> None:
        report = _valid_report()
        report["tests"][0]["file"] = 123
        errors = validate_report(report)
        assert any("file" in e for e in errors)

    def test_error_not_string(self) -> None:
        report = _valid_report()
        report["tests"][0]["error"] = 123
        errors = validate_report(report)
        assert any("error" in e for e in errors)

    def test_screenshot_not_string(self) -> None:
        report = _valid_report()
        report["tests"][0]["screenshot"] = 123
        errors = validate_report(report)
        assert any("screenshot" in e for e in errors)

    def test_failed_test_with_error(self) -> None:
        """A failed test with an error string should be valid."""
        report = _valid_report()
        errors = validate_report(report)
        assert errors == []

    def test_failed_test_without_error(self) -> None:
        """A failed test without error field should still be valid."""
        report = _valid_report()
        del report["tests"][2]["error"]
        errors = validate_report(report)
        assert errors == []

    def test_skipped_test(self) -> None:
        """A skipped test entry should be valid."""
        report = _valid_report()
        report["tests"][0]["status"] = "skipped"
        report["summary"]["passed"] = 1
        report["summary"]["skipped"] = 1
        errors = validate_report(report)
        assert errors == []


class TestFileValidation:
    """Test validate_file() with actual files."""

    def test_valid_file(self, tmp_path: Path) -> None:
        report = _valid_report()
        path = tmp_path / "e2e-report.json"
        path.write_text(json.dumps(report), encoding="utf-8")

        from validate_e2e_report import validate_file
        errors = validate_file(path)
        assert errors == []

    def test_invalid_json(self, tmp_path: Path) -> None:
        path = tmp_path / "bad.json"
        path.write_text("{not valid json", encoding="utf-8")

        from validate_e2e_report import validate_file
        errors = validate_file(path)
        assert len(errors) == 1
        assert "Invalid JSON" in errors[0]

    def test_file_not_found(self) -> None:
        from validate_e2e_report import validate_file
        errors = validate_file(Path("/nonexistent/report.json"))
        assert len(errors) == 1
        assert "not found" in errors[0].lower()

    def test_root_not_dict(self, tmp_path: Path) -> None:
        path = tmp_path / "report.json"
        path.write_text("[1, 2, 3]", encoding="utf-8")

        from validate_e2e_report import validate_file
        errors = validate_file(path)
        assert any("dict" in e for e in errors)


class TestIntegrationWithBuilder:
    """Test that build_e2e_json_report output passes validation."""

    def test_builder_output_valid(self) -> None:
        from super_browser.testing import build_e2e_json_report

        report = build_e2e_json_report(
            suite_name="e2e-real-browser",
            results=[
                {
                    "test_name": "test_one",
                    "status": "passed",
                    "duration_ms": 100.0,
                    "budget_exceeded": False,
                    "nodeid": "tests/e2e/test_foo.py::test_one",
                },
                {
                    "test_name": "test_two",
                    "status": "failed",
                    "duration_ms": 5000.0,
                    "budget_exceeded": True,
                    "nodeid": "tests/e2e/test_bar.py::test_two",
                    "error": "TimeoutError",
                },
            ],
            environment={
                "backend": "patchright",
                "headless": True,
                "python_version": "3.12.0",
                "platform": "linux",
                "live": False,
            },
            suite_duration_ms=5100.0,
            budget_seconds=120.0,
        )
        errors = validate_report(report)
        assert errors == [], f"Builder output failed validation: {errors}"
