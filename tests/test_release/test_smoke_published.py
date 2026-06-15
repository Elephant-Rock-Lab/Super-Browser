"""Unit tests for the post-release smoke test script.

Tests report building, check result construction, Markdown rendering,
and CLI arg parsing — without requiring actual PyPI installation.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "smoke_published.py"

sys.path.insert(0, str(SCRIPT.parent))
import smoke_published as sp  # noqa: E402  type: ignore[import-not-found]


class TestCheckResult:
    """Test _check_result()."""

    def test_passing_check(self) -> None:
        result = sp._check_result("test_check", 0, "success output", "")
        assert result["name"] == "test_check"
        assert result["passed"] is True
        assert result["exit_code"] == 0
        assert result["stdout"] == "success output"

    def test_failing_check(self) -> None:
        result = sp._check_result("test_check", 1, "", "error message")
        assert result["passed"] is False
        assert result["exit_code"] == 1
        assert result["stderr"] == "error message"

    def test_long_output_truncated(self) -> None:
        """Output longer than 2000 chars should be truncated."""
        long_output = "x" * 3000
        result = sp._check_result("test", 0, long_output, "")
        assert len(result["stdout"]) <= 2000

    def test_timeout_exit_code(self) -> None:
        result = sp._check_result("test", 124, "", "timed out")
        assert result["passed"] is False
        assert result["exit_code"] == 124


class TestBuildReport:
    """Test _build_report()."""

    def _make_checks(self) -> list[dict[str, Any]]:
        return [
            sp._check_result("check1", 0, "ok", ""),
            sp._check_result("check2", 0, "ok", ""),
            sp._check_result("check3", 1, "", "fail"),
        ]

    def test_report_structure(self) -> None:
        report = sp._build_report("2026-01-01T00:00:00Z", "superbrowser-sdk", self._make_checks())
        assert report["schema_version"] == 1
        assert "timestamp_utc" in report
        assert report["install_spec"] == "superbrowser-sdk"
        assert "environment" in report
        assert "summary" in report
        assert "checks" in report

    def test_summary_counts(self) -> None:
        report = sp._build_report("ts", "spec", self._make_checks())
        assert report["summary"]["total_checks"] == 3
        assert report["summary"]["passed"] == 2
        assert report["summary"]["failed"] == 1

    def test_overall_fail(self) -> None:
        report = sp._build_report("ts", "spec", self._make_checks())
        assert report["summary"]["overall"] == "FAIL"

    def test_overall_pass(self) -> None:
        checks = [sp._check_result("c", 0, "ok", "")]
        report = sp._build_report("ts", "spec", checks)
        assert report["summary"]["overall"] == "PASS"

    def test_empty_checks(self) -> None:
        report = sp._build_report("ts", "spec", [])
        assert report["summary"]["total_checks"] == 0
        assert report["summary"]["passed"] == 0
        assert report["summary"]["overall"] == "PASS"  # vacuously true

    def test_json_serializable(self) -> None:
        report = sp._build_report("ts", "spec", self._make_checks())
        serialized = json.dumps(report)
        assert json.loads(serialized)["schema_version"] == 1


class TestFormatMarkdown:
    """Test format_markdown()."""

    def _make_report(self) -> dict[str, Any]:
        return sp._build_report("2026-06-16T00:00:00Z", "superbrowser-sdk", [
            sp._check_result("import_super_browser", 0, "2.0.2", ""),
            sp._check_result("cli_version", 0, "superbrowser 2.0.2", ""),
            sp._check_result("install_patchright", 1, "", "conflict"),
        ])

    def test_renders_header(self) -> None:
        md = sp.format_markdown(self._make_report())
        assert "# Post-Release Smoke Report" in md
        assert "superbrowser-sdk" in md

    def test_renders_table(self) -> None:
        md = sp.format_markdown(self._make_report())
        assert "| Check | Result |" in md
        assert "import_super_browser" in md
        assert "cli_version" in md
        assert "install_patchright" in md

    def test_renders_pass_fail(self) -> None:
        md = sp.format_markdown(self._make_report())
        assert "✅" in md
        assert "❌" in md

    def test_renders_summary(self) -> None:
        md = sp.format_markdown(self._make_report())
        assert "FAIL" in md
        assert "2/3" in md

    def test_all_pass_renders_pass(self) -> None:
        report = sp._build_report("ts", "spec", [sp._check_result("c", 0, "ok", "")])
        md = sp.format_markdown(report)
        assert "**PASS**" in md


class TestSchemaValidation:
    """Validate smoke report schema shape."""

    def test_top_level_keys(self) -> None:
        report = sp._build_report("ts", "spec", [])
        for key in ("schema_version", "timestamp_utc", "install_spec", "environment", "summary", "checks"):
            assert key in report, f"Missing key: {key}"

    def test_check_keys(self) -> None:
        check = sp._check_result("test", 0, "out", "err")
        for key in ("name", "passed", "exit_code", "stdout", "stderr"):
            assert key in check, f"Missing check key: {key}"

    def test_summary_keys(self) -> None:
        report = sp._build_report("ts", "spec", [])
        summary = report["summary"]
        for key in ("total_checks", "passed", "failed", "overall"):
            assert key in summary, f"Missing summary key: {key}"


class TestConstants:
    """Test default constants."""

    def test_default_dist(self) -> None:
        assert sp.DEFAULT_DIST == "superbrowser-sdk"

    def test_default_out(self) -> None:
        assert sp.DEFAULT_OUT == "smoke-report.json"


class TestRunCommand:
    """Test _run() helper."""

    def test_successful_command(self) -> None:
        rc, out, err = sp._run([sys.executable, "-c", "print('hello')"])
        assert rc == 0
        assert "hello" in out

    def test_failing_command(self) -> None:
        rc, out, err = sp._run([sys.executable, "-c", "import sys; sys.exit(1)"])
        assert rc == 1

    def test_timeout(self) -> None:
        rc, out, err = sp._run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=1)
        assert rc == 124
        assert "timed out" in err.lower()


class TestVenvCreation:
    """Test _create_venv()."""

    def test_creates_python_exe(self, tmp_path: Path) -> None:
        venv_python = sp._create_venv(tmp_path / "venv")
        assert venv_python.exists()

    def test_python_works(self, tmp_path: Path) -> None:
        venv_python = sp._create_venv(tmp_path / "venv")
        rc, out, err = sp._run([str(venv_python), "--version"])
        assert rc == 0
        assert "Python" in out
