"""Tests for FingerprintScorer — composite stealth scoring (M40).

Test IDs: TEST-13-02-01 through TEST-13-02-03
"""

import asyncio

from super_browser.stealth.diagnostics import run_full_diagnostics
from super_browser.stealth.fingerprint_score import (
    FingerprintGrade,
    FingerprintScorer,
    FingerprintScoreResult,
)
from super_browser.stealth.types import StealthConfig

# -- Helpers ----------------------------------------------------------------


def _perfect_checks() -> dict:
    """All checks passing — should score 100."""
    return {
        "webdriver": {"passed": True, "detail": "navigator.webdriver = None"},
        "plugins_mimetypes": {"passed": True, "detail": "OK"},
        "user_agent": {"passed": True, "detail": "Headed mode"},
        "headers": {"passed": True, "detail": "Automation flags clean"},
        "tls": {"passed": True, "detail": "httpmorph available"},
        "misc": {"passed": True, "detail": "Runtime.enable absent"},
    }


def _all_failing_checks() -> dict:
    """All checks failing — should score 0."""
    return {
        "webdriver": {"passed": False, "detail": "navigator.webdriver = True"},
        "plugins_mimetypes": {"passed": False, "detail": "Missing plugins"},
        "user_agent": {"passed": False, "detail": "Headless detected"},
        "headers": {"passed": False, "detail": "--enable-automation present"},
        "tls": {"passed": False, "detail": "JA4 mismatch"},
        "misc": {"passed": False, "detail": "Runtime.enable present"},
    }


# -- TEST-13-02-01: Score 0-100 returned -------------------------------------


class TestScoreRange:
    """TEST-13-02-01: Score 0-100 returned for stealth checks."""

    def test_perfect_score_is_100(self):
        scorer = FingerprintScorer()
        result = scorer.score_from_checks(_perfect_checks())
        assert isinstance(result, FingerprintScoreResult)
        assert 0 <= result.score <= 100
        assert result.score == 100
        assert result.grade == FingerprintGrade.A

    def test_all_fail_score_is_0(self):
        scorer = FingerprintScorer()
        result = scorer.score_from_checks(_all_failing_checks())
        assert result.score == 0
        assert result.grade == FingerprintGrade.D

    def test_partial_checks_score_in_range(self):
        """Mix of passing and failing checks yields mid-range score."""
        checks = _perfect_checks()
        checks["webdriver"] = {"passed": False, "detail": "webdriver detected"}
        checks["headers"] = {"passed": False, "detail": "bad headers"}
        scorer = FingerprintScorer()
        result = scorer.score_from_checks(checks)
        assert 0 <= result.score <= 100
        assert result.score < 100
        assert result.score > 0

    def test_missing_categories_score_zero_for_them(self):
        """Categories not provided default to failed."""
        scorer = FingerprintScorer()
        result = scorer.score_from_checks({
            "webdriver": {"passed": True, "detail": "OK"},
        })
        assert result.score < 100
        assert result.score > 0

    def test_empty_checks_scores_zero(self):
        scorer = FingerprintScorer()
        result = scorer.score_from_checks({})
        assert result.score == 0
        assert result.grade == FingerprintGrade.D

    def test_deductions_populated_on_failure(self):
        scorer = FingerprintScorer()
        result = scorer.score_from_checks(_all_failing_checks())
        assert len(result.deductions) == 6

    def test_no_deductions_when_all_pass(self):
        scorer = FingerprintScorer()
        result = scorer.score_from_checks(_perfect_checks())
        assert len(result.deductions) == 0


# -- TEST-13-02-02: Perfect Patchright config scores ≥90 ---------------------


class _FakeCDPResult:
    def __init__(self, value=None):
        self.ok = True
        self.data = {"result": {"value": value}}


class _FakeCDP:
    """Patchright CDP — navigator.webdriver returns None (not detectable)."""

    def __init__(self):
        pass

    async def send(self, method, params=None):
        if "webdriver" in params.get("expression", ""):
            return _FakeCDPResult(None)
        return _FakeCDPResult(None)


class TestPerfectPatchright:
    """TEST-13-02-02: Perfect Patchright config scores ≥ 90."""

    def test_default_config_scores_90_plus(self):
        """Default StealthConfig with proper CDP scores at least 90."""

        async def _test():
            cdp = _FakeCDP()
            config = StealthConfig()  # defaults are Patchright-friendly
            result = await run_full_diagnostics(cdp, config)
            score_result = result["score_result"]
            assert score_result.score >= 90
            assert score_result.grade in (FingerprintGrade.A, FingerprintGrade.B)

        asyncio.run(_test())

    def test_grade_is_A_for_perfect_config(self):
        """With webdriver=None and default args, grade should be A."""

        async def _test():
            cdp = _FakeCDP()
            config = StealthConfig()
            result = await run_full_diagnostics(cdp, config)
            score_result = result["score_result"]
            assert score_result.grade == FingerprintGrade.A

        asyncio.run(_test())


# -- TEST-13-02-03: Missing headers reduces score ----------------------------


class TestMissingHeadersReduceScore:
    """TEST-13-02-03: Missing headers reduces score."""

    def test_bad_cli_switches_reduces_score(self):
        """--enable-automation flag should reduce the score."""

        async def _test():
            cdp = _FakeCDP()
            # Bad config: has --enable-automation and no good flag
            config = StealthConfig(
                patchright_args=("--enable-automation",),
            )
            result = await run_full_diagnostics(cdp, config)
            score_result = result["score_result"]

            # Compare against a good config
            good_result = await run_full_diagnostics(cdp, StealthConfig())
            good_score = good_result["score_result"].score

            assert score_result.score < good_score
            assert "headers" in str(score_result.deductions).lower() or len(score_result.deductions) > 0

        asyncio.run(_test())

    def test_webdriver_detected_reduces_score(self):
        """If webdriver=True is detected, score should drop significantly."""

        class _BadCDP:
            async def send(self, method, params=None):
                if "webdriver" in params.get("expression", ""):
                    return _FakeCDPResult(True)
                return _FakeCDPResult(None)

        async def _test():
            cdp = _BadCDP()
            config = StealthConfig()
            result = await run_full_diagnostics(cdp, config)
            score_result = result["score_result"]

            good_result = await run_full_diagnostics(_FakeCDP(), config)
            good_score = good_result["score_result"].score

            assert score_result.score < good_score

        asyncio.run(_test())


# -- Grade mapping tests (extras) -------------------------------------------


class TestGradeMapping:
    """Verify grade boundaries."""

    def test_grade_A(self):
        scorer = FingerprintScorer()
        assert scorer._grade(95) == FingerprintGrade.A
        assert scorer._grade(90) == FingerprintGrade.A

    def test_grade_B(self):
        scorer = FingerprintScorer()
        assert scorer._grade(89) == FingerprintGrade.B
        assert scorer._grade(75) == FingerprintGrade.B

    def test_grade_C(self):
        scorer = FingerprintScorer()
        assert scorer._grade(74) == FingerprintGrade.C
        assert scorer._grade(60) == FingerprintGrade.C

    def test_grade_D(self):
        scorer = FingerprintScorer()
        assert scorer._grade(59) == FingerprintGrade.D
        assert scorer._grade(0) == FingerprintGrade.D
