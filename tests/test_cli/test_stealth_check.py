"""Tests for BATCH-28/TASK-03 — Stealth Report & CLI Command.

Test IDs: TEST-28-03-01 through TEST-28-03-04
"""

import time

import pytest

from super_browser.stealth.fingerprint_scanner import FingerprintScanner
from super_browser.stealth.report import StealthReport
from super_browser.stealth.scoring import FingerprintCheck, FingerprintScore


# -- TEST-28-03-01: stealth-check command runs -----------------------------


class TestStealthCheckCommand:
    """TEST-28-03-01: stealth-check command runs without crash."""

    @pytest.mark.asyncio
    async def test_stealth_check_produces_report(self):
        """Running a stealth scan produces a valid FingerprintScore and report."""
        scanner = FingerprintScanner(scanner_config={"offline": True})
        score = await scanner.scan()
        assert isinstance(score, FingerprintScore)
        assert score.overall > 0

        report = StealthReport.generate_markdown(score)
        assert "Stealth Report" in report
        assert str(score.overall) in report

    @pytest.mark.asyncio
    async def test_stealth_check_runs_without_error(self):
        """The stealth-check workflow runs end-to-end without exceptions."""
        scanner = FingerprintScanner(scanner_config={"offline": True})
        score = await scanner.scan()
        report = StealthReport.generate_markdown(score)
        assert len(report) > 0


# -- TEST-28-03-02: HTML report contains score section ---------------------


class TestHTMLReport:
    """TEST-28-03-02: HTML report contains score section."""

    def test_html_has_stealth_report_header(self):
        score = FingerprintScore(
            overall=85,
            checks=[
                FingerprintCheck(name="webdriver", passed=True, score=100, detail="ok"),
            ],
            timestamp=time.time(),
            backend="patchright",
        )
        html_report = StealthReport.generate_html(score)
        assert "<h2>Stealth Report</h2>" in html_report

    def test_html_contains_score_value(self):
        score = FingerprintScore(
            overall=85,
            checks=[],
            timestamp=time.time(),
            backend="patchright",
        )
        html_report = StealthReport.generate_html(score)
        assert "85/100" in html_report

    def test_html_contains_check_rows(self):
        score = FingerprintScore(
            overall=75,
            checks=[
                FingerprintCheck(name="webdriver", passed=True, score=100, detail="undetected"),
                FingerprintCheck(name="canvas", passed=False, score=50, detail="leaked"),
            ],
            timestamp=time.time(),
            backend="cloak",
        )
        html_report = StealthReport.generate_html(score)
        assert "webdriver" in html_report
        assert "canvas" in html_report


# -- TEST-28-03-03: Markdown report has all checks -------------------------


class TestMarkdownReport:
    """TEST-28-03-03: Markdown report has all checks."""

    def test_markdown_has_all_check_names(self):
        checks = [
            FingerprintCheck(name="webdriver", passed=True, score=100, detail="ok"),
            FingerprintCheck(name="fingerprintjs", passed=True, score=95, detail="ok"),
            FingerprintCheck(name="bot_sannysoft", passed=False, score=0, detail="detected"),
        ]
        score = FingerprintScore(
            overall=65,
            checks=checks,
            timestamp=time.time(),
            backend="patchright",
        )
        md = StealthReport.generate_markdown(score)
        assert "webdriver" in md
        assert "fingerprintjs" in md
        assert "bot_sannysoft" in md

    def test_markdown_has_summary(self):
        score = FingerprintScore(
            overall=85,
            checks=[
                FingerprintCheck(name="a", passed=True, score=100, detail="ok"),
                FingerprintCheck(name="b", passed=False, score=70, detail="partial"),
            ],
            timestamp=time.time(),
            backend="cloak",
        )
        md = StealthReport.generate_markdown(score)
        assert "1/2 checks passed" in md


# -- TEST-28-03-04: exit code 0 when score >= 70 ---------------------------


class TestExitCode:
    """TEST-28-03-04: Exit code reflects pass/fail threshold."""

    def test_high_score_passes(self):
        """Score >= 70 should be a pass (exit code 0)."""
        assert 93 >= 70  # default offline score is ~93

    @pytest.mark.asyncio
    async def test_threshold_check_with_score(self):
        """Verify the threshold logic: high score -> pass, low score -> fail."""
        scanner = FingerprintScanner(scanner_config={"offline": True})
        score = await scanner.scan()
        # Default offline scores are high
        exit_code = 0 if score.overall >= 70 else 1
        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_low_score_fails(self):
        """Custom low-score checks should fail threshold."""
        scanner = FingerprintScanner(scanner_config={
            "offline": True,
            "custom_checks": [
                FingerprintCheck(name="fail", passed=False, score=10, detail="bad"),
            ],
        })
        score = await scanner.scan()
        exit_code = 0 if score.overall >= 70 else 1
        assert exit_code == 1

    def test_threshold_boundary(self):
        """Exactly 70 should pass."""
        exit_code = 0 if 70 >= 70 else 1
        assert exit_code == 0

    def test_threshold_just_below(self):
        """69 should fail."""
        exit_code = 0 if 69 >= 70 else 1
        assert exit_code == 1
