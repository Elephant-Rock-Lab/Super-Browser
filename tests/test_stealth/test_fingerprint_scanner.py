"""Tests for BATCH-28/TASK-02 — Fingerprint Scoring Utility.

Test IDs: TEST-28-02-01 through TEST-28-02-04
"""

import time

import pytest

from super_browser.stealth.fingerprint_scanner import FingerprintScanner, _compute_overall
from super_browser.stealth.scoring import FingerprintCheck, FingerprintScore


# -- TEST-28-02-01: FingerprintScore aggregates checks ----------------------


class TestScoreAggregation:
    """TEST-28-02-01: FingerprintScore correctly aggregates check scores."""

    def test_overall_is_mean_of_check_scores(self):
        checks = [
            FingerprintCheck(name="a", passed=True, score=80, detail="ok"),
            FingerprintCheck(name="b", passed=True, score=100, detail="ok"),
        ]
        overall = _compute_overall(checks)
        assert overall == 90

    def test_overall_zero_for_empty_checks(self):
        overall = _compute_overall([])
        assert overall == 0

    def test_overall_100_for_all_perfect(self):
        checks = [
            FingerprintCheck(name="a", passed=True, score=100, detail="ok"),
            FingerprintCheck(name="b", passed=True, score=100, detail="ok"),
            FingerprintCheck(name="c", passed=True, score=100, detail="ok"),
        ]
        overall = _compute_overall(checks)
        assert overall == 100

    def test_overall_rounds_correctly(self):
        checks = [
            FingerprintCheck(name="a", passed=True, score=33, detail="ok"),
            FingerprintCheck(name="b", passed=True, score=66, detail="ok"),
        ]
        overall = _compute_overall(checks)
        # (33 + 66) / 2 = 49.5 → rounds to 50
        assert overall == 50


# -- TEST-28-02-02: Offline scan returns mock scores -----------------------


class TestOfflineScan:
    """TEST-28-02-02: Offline scan returns mock scores without network."""

    @pytest.mark.asyncio
    async def test_offline_scan_returns_fingerprint_score(self):
        scanner = FingerprintScanner(scanner_config={"offline": True})
        result = await scanner.scan()
        assert isinstance(result, FingerprintScore)
        assert result.overall > 0
        assert len(result.checks) > 0
        assert result.backend == "patchright"

    @pytest.mark.asyncio
    async def test_offline_scan_no_network(self):
        """Verify no page/browser is needed for offline scan."""
        scanner = FingerprintScanner(scanner_config={"offline": True})
        result = await scanner.scan(browser_page=None)
        assert result.overall > 0

    @pytest.mark.asyncio
    async def test_custom_checks_override(self):
        custom = [
            FingerprintCheck(name="custom", passed=False, score=50, detail="mock"),
        ]
        scanner = FingerprintScanner(scanner_config={
            "offline": True,
            "custom_checks": custom,
        })
        result = await scanner.scan()
        assert len(result.checks) == 1
        assert result.overall == 50

    def test_scanner_default_offline(self):
        scanner = FingerprintScanner()
        assert scanner.offline is True


# -- TEST-28-02-03: format_report produces markdown -------------------------


class TestFormatReport:
    """TEST-28-02-03: format_report produces markdown."""

    def test_report_has_stealth_report_header(self):
        score = FingerprintScore(
            overall=85,
            checks=[
                FingerprintCheck(name="webdriver", passed=True, score=100, detail="ok"),
            ],
            timestamp=time.time(),
            backend="patchright",
        )
        report = FingerprintScanner.format_report(score)
        assert "## Stealth Report" in report

    def test_report_has_check_table(self):
        score = FingerprintScore(
            overall=85,
            checks=[
                FingerprintCheck(name="webdriver", passed=True, score=100, detail="undetected"),
                FingerprintCheck(name="canvas", passed=False, score=60, detail="leaked"),
            ],
            timestamp=time.time(),
            backend="cloak",
        )
        report = FingerprintScanner.format_report(score)
        assert "webdriver" in report
        assert "canvas" in report
        assert "✅" in report
        assert "❌" in report

    def test_report_has_overall_score(self):
        score = FingerprintScore(
            overall=92,
            checks=[],
            timestamp=time.time(),
            backend="patchright",
        )
        report = FingerprintScanner.format_report(score)
        assert "92/100" in report


# -- TEST-28-02-04: FingerprintCheck has required fields --------------------


class TestFingerprintCheckFields:
    """TEST-28-02-04: FingerprintCheck has all required fields."""

    def test_name_field(self):
        c = FingerprintCheck(name="test", passed=True, score=100, detail="ok")
        assert c.name == "test"

    def test_passed_field(self):
        c = FingerprintCheck(name="test", passed=True, score=100, detail="ok")
        assert c.passed is True

    def test_score_field(self):
        c = FingerprintCheck(name="test", passed=True, score=75, detail="ok")
        assert c.score == 75

    def test_detail_field(self):
        c = FingerprintCheck(name="test", passed=False, score=0, detail="failed")
        assert c.detail == "failed"

    def test_fingerprint_score_has_backend(self):
        s = FingerprintScore(
            overall=80,
            checks=[],
            timestamp=0.0,
            backend="cloak",
        )
        assert s.backend == "cloak"

    def test_fingerprint_score_has_timestamp(self):
        s = FingerprintScore(
            overall=80,
            checks=[],
            timestamp=1234.5,
            backend="patchright",
        )
        assert s.timestamp == 1234.5
