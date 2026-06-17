"""Offline unit tests for every target parser.

Verifies that each parser correctly handles:
- Expected "happy path" inputs (clean, flagged, challenged)
- Edge cases (missing DOM elements, null/undefined probe results)
- Malformed or partial data (empty strings, wrong types)
- Boundary conditions (threshold values, score rounding)

These tests run without network access, browser launches, or any
third-party dependencies. They catch parser bugs (regex changes,
DOM selector drift, threshold logic errors) in CI before any
live target is hit.

Usage::

    pytest tests/adversarial/test_targets_unit.py
"""

from __future__ import annotations

from .targets import (
    ALL_TARGETS,
    TIER1_TARGETS,
    TIER2_TARGETS,
    Tier,
    Verdict,
    _parse_browserscan,
    _parse_cloudflare_demo,
    _parse_creepjs,
    _parse_datadome_demo,
    _parse_incolumitas,
    _parse_sannysoft,
)

# =========================================================================
# Tier 1: sannysoft
# =========================================================================

class TestParseSannysoft:
    """Unit tests for the sannysoft parser."""

    def test_clean_no_webdriver_no_bot_label(self):
        result = _parse_sannysoft(
            "sannysoft",
            webdriver=False,
            body_text="All tests passed. You look like a human.",
        )
        assert result.verdict == Verdict.CLEAN
        assert result.score == 100
        assert "no webdriver flag" in result.detail

    def test_flagged_webdriver_true(self):
        result = _parse_sannysoft(
            "sannysoft",
            webdriver=True,
            body_text="All tests passed. You look like a human.",
        )
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 0
        assert "navigator.webdriver is true" in result.detail

    def test_flagged_bot_label_in_body(self):
        result = _parse_sannysoft(
            "sannysoft",
            webdriver=False,
            body_text="Warning: you are a bot. Automation detected.",
        )
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 0
        assert "bot" in result.detail.lower()

    def test_flagged_webdriver_trumps_bot_label(self):
        # webdriver=True should be caught first (order in parser)
        result = _parse_sannysoft(
            "sannysoft",
            webdriver=True,
            body_text="you are a bot",
        )
        assert result.verdict == Verdict.FLAGGED
        assert "navigator.webdriver is true" in result.detail

    def test_case_insensitive_bot_label(self):
        result = _parse_sannysoft(
            "sannysoft",
            webdriver=False,
            body_text="YOU ARE A BOT",
        )
        assert result.verdict == Verdict.FLAGGED

    def test_empty_body_text(self):
        result = _parse_sannysoft("sannysoft", webdriver=False, body_text="")
        assert result.verdict == Verdict.CLEAN


# =========================================================================
# Tier 1: incolumitas
# =========================================================================

class TestParseIncolumitas:
    """Unit tests for the incolumitas parser."""

    def test_clean_low_probability(self):
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=0.1,
            body_text="Some page content",
        )
        assert result.verdict == Verdict.CLEAN
        assert result.score == 90  # (1 - 0.1) * 100 = 90
        assert "bot_probability=0.10" in result.detail

    def test_exact_threshold_clean(self):
        # At exactly 0.5, should be CLEAN (<= check)
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=0.5,
            body_text="Some page content",
        )
        assert result.verdict == Verdict.CLEAN
        assert result.score == 50

    def test_flagged_above_threshold(self):
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=0.51,
            body_text="Some page content",
        )
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 49  # (1 - 0.51) * 100 = 49

    def test_flagged_high_probability(self):
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=0.95,
            body_text="Some page content",
        )
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 5

    def test_none_probability_human_text(self):
        # When bot_probability is None but page text says "human"
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=None,
            body_text="Congratulations, you appear to be human!",
        )
        assert result.verdict == Verdict.CLEAN
        assert result.score == 80
        assert "human" in result.detail.lower()

    def test_none_probability_no_human_text(self):
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=None,
            body_text="Bot detection in progress...",
        )
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.score == 0
        assert "could not extract" in result.detail.lower()

    def test_none_probability_empty_body(self):
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=None,
            body_text="",
        )
        assert result.verdict == Verdict.INCONCLUSIVE

    def test_rounding_behavior(self):
        # 0.333... should round to 33
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=0.333,
            body_text="x",
        )
        assert result.score == 67  # round(66.7) = 67

    def test_zero_probability(self):
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=0.0,
            body_text="x",
        )
        assert result.verdict == Verdict.CLEAN
        assert result.score == 100

    def test_one_probability(self):
        result = _parse_incolumitas(
            "incolumitas",
            bot_probability=1.0,
            body_text="x",
        )
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 0


# =========================================================================
# Tier 1: creepjs
# =========================================================================

class TestParseCreepjs:
    """Unit tests for the creepjs parser."""

    def test_clean_high_trust(self):
        result = _parse_creepjs("creepjs", trust_score=75.0)
        assert result.verdict == Verdict.CLEAN
        assert result.score == 75
        assert "trust_score=75.0" in result.detail

    def test_exact_threshold_clean(self):
        # At exactly 50.0, should be CLEAN (>= check)
        result = _parse_creepjs("creepjs", trust_score=50.0)
        assert result.verdict == Verdict.CLEAN
        assert result.score == 50

    def test_flagged_below_threshold(self):
        result = _parse_creepjs("creepjs", trust_score=49.9)
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 49  # int(49.9) truncates
        assert result.verdict == Verdict.FLAGGED

    def test_flagged_zero_trust(self):
        result = _parse_creepjs("creepjs", trust_score=0.0)
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 0

    def test_none_trust_score(self):
        result = _parse_creepjs("creepjs", trust_score=None)
        assert result.verdict == Verdict.INCONCLUSIVE
        assert result.score == 0
        assert "could not extract" in result.detail.lower()

    def test_boundary_50(self):
        result = _parse_creepjs("creepjs", trust_score=50)
        assert result.verdict == Verdict.CLEAN
        result2 = _parse_creepjs("creepjs", trust_score=49.999)
        assert result2.verdict == Verdict.FLAGGED

    def test_max_trust(self):
        result = _parse_creepjs("creepjs", trust_score=100.0)
        assert result.verdict == Verdict.CLEAN
        assert result.score == 100


# =========================================================================
# Tier 1: browserscan
# =========================================================================

class TestParseBrowserscan:
    """Unit tests for the browserscan parser."""

    def test_clean_no_markers(self):
        result = _parse_browserscan(
            "browserscan",
            webdriver=False,
            body_text="Your browser fingerprint looks normal.",
        )
        assert result.verdict == Verdict.CLEAN
        assert result.score == 100

    def test_flagged_selenium_in_text(self):
        result = _parse_browserscan(
            "browserscan",
            webdriver=False,
            body_text="Selenium WebDriver detected in your browser.",
        )
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 0
        assert "automation library" in result.detail.lower()

    def test_flagged_playwright_in_text(self):
        result = _parse_browserscan(
            "browserscan",
            webdriver=False,
            body_text="Playwright automation detected.",
        )
        assert result.verdict == Verdict.FLAGGED

    def test_challenged_explicit_bot_verdict(self):
        result = _parse_browserscan(
            "browserscan",
            webdriver=False,
            body_text="You are detected as bot. Please complete the challenge.",
        )
        assert result.verdict == Verdict.CHALLENGED
        assert result.score == 20
        assert "explicit bot verdict" in result.detail.lower()

    def test_challenged_you_are_bot(self):
        result = _parse_browserscan(
            "browserscan",
            webdriver=False,
            body_text="you are bot",
        )
        assert result.verdict == Verdict.CHALLENGED

    def test_challenged_you_are_a_bot(self):
        result = _parse_browserscan(
            "browserscan",
            webdriver=False,
            body_text="You are a bot!",
        )
        assert result.verdict == Verdict.CHALLENGED

    def test_flagged_webdriver_true(self):
        result = _parse_browserscan(
            "browserscan",
            webdriver=True,
            body_text="Normal page content",
        )
        assert result.verdict == Verdict.FLAGGED
        assert "navigator.webdriver is true" in result.detail

    def test_selenium_trumps_webdriver(self):
        # selenium in text is checked before webdriver
        result = _parse_browserscan(
            "browserscan",
            webdriver=True,
            body_text="Selenium detected",
        )
        assert result.verdict == Verdict.FLAGGED
        assert "automation library" in result.detail.lower()

    def test_case_insensitive(self):
        result = _parse_browserscan(
            "browserscan",
            webdriver=False,
            body_text="PLAYWRIGHT AUTOMATION",
        )
        assert result.verdict == Verdict.FLAGGED

    def test_empty_body(self):
        result = _parse_browserscan("browserscan", webdriver=False, body_text="")
        assert result.verdict == Verdict.CLEAN


# =========================================================================
# Tier 2: cloudflare_demo
# =========================================================================

class TestParseCloudflareDemo:
    """Unit tests for the Cloudflare demo parser."""

    def test_clean_no_challenge(self):
        result = _parse_cloudflare_demo(
            "cloudflare_demo",
            challenge_present=False,
            ray_id="abc123def456",
        )
        assert result.verdict == Verdict.CLEAN
        assert result.score == 100
        assert "abc123def456" in result.detail

    def test_challenged_with_challenge(self):
        result = _parse_cloudflare_demo(
            "cloudflare_demo",
            challenge_present=True,
            ray_id="xyz789",
        )
        assert result.verdict == Verdict.CHALLENGED
        assert result.score == 30
        assert "managed challenge" in result.detail.lower()
        assert "xyz789" in result.detail

    def test_challenged_no_ray_id(self):
        result = _parse_cloudflare_demo(
            "cloudflare_demo",
            challenge_present=True,
            ray_id=None,
        )
        assert result.verdict == Verdict.CHALLENGED
        assert "ray=None" in result.detail

    def test_clean_no_ray_id(self):
        result = _parse_cloudflare_demo(
            "cloudflare_demo",
            challenge_present=False,
            ray_id=None,
        )
        assert result.verdict == Verdict.CLEAN
        assert "ray=None" in result.detail


# =========================================================================
# Tier 2: datadome_demo
# =========================================================================

class TestParseDatadomeDemo:
    """Unit tests for the DataDome demo parser."""

    def test_clean_normal_access(self):
        result = _parse_datadome_demo(
            "datadome_demo",
            blocked=False,
            captcha_present=False,
        )
        assert result.verdict == Verdict.CLEAN
        assert result.score == 100
        assert "allowed normal access" in result.detail.lower()

    def test_flagged_blocked(self):
        result = _parse_datadome_demo(
            "datadome_demo",
            blocked=True,
            captcha_present=False,
        )
        assert result.verdict == Verdict.FLAGGED
        assert result.score == 0
        assert "block page" in result.detail.lower()

    def test_challenged_captcha(self):
        result = _parse_datadome_demo(
            "datadome_demo",
            blocked=False,
            captcha_present=True,
        )
        assert result.verdict == Verdict.CHALLENGED
        assert result.score == 30
        assert "captcha" in result.detail.lower()

    def test_blocked_trumps_captcha(self):
        # blocked is checked first in the parser
        result = _parse_datadome_demo(
            "datadome_demo",
            blocked=True,
            captcha_present=True,
        )
        assert result.verdict == Verdict.FLAGGED
        assert "block page" in result.detail.lower()


# =========================================================================
# Registry integrity tests
# =========================================================================

class TestTargetRegistry:
    """Verify the target registry itself is internally consistent."""

    def test_all_targets_have_parser(self):
        for target in ALL_TARGETS:
            assert target.parser is not None, f"{target.target_id} has no parser"
            # Verify parser is callable (parsers take keyword-only args,
            # so we just verify the attribute exists and is callable)
            assert callable(target.parser)

    def test_all_targets_have_url(self):
        for target in ALL_TARGETS:
            assert target.url, f"{target.target_id} has no URL"
            assert target.url.startswith(("http://", "https://"))

    def test_all_targets_have_probes(self):
        for target in ALL_TARGETS:
            assert target.probes, f"{target.target_id} has no probes"
            for probe_name, probe_expr in target.probes.items():
                assert probe_name
                assert probe_expr
                assert isinstance(probe_expr, str)

    def test_unique_target_ids(self):
        ids = [t.target_id for t in ALL_TARGETS]
        assert len(ids) == len(set(ids)), f"Duplicate target IDs: {ids}"

    def test_tier1_count(self):
        assert len(TIER1_TARGETS) == 4

    def test_tier2_count(self):
        assert len(TIER2_TARGETS) == 2

    def test_targets_for_tier_function(self):
        from .targets import targets_for_tier
        assert len(targets_for_tier(Tier.SCANNER)) == 4
        assert len(targets_for_tier(Tier.VENDOR)) == 2
        assert len(targets_for_tier(Tier.CONTROLLED)) == 0  # none registered statically

    def test_target_by_id(self):
        from .targets import target_by_id
        assert target_by_id("sannysoft") is not None
        assert target_by_id("cloudflare_demo") is not None
        assert target_by_id("nonexistent") is None

    def test_settle_ms_non_negative(self):
        for target in ALL_TARGETS:
            assert target.settle_ms >= 0, f"{target.target_id} has negative settle_ms"

    def test_min_interval_s_positive(self):
        for target in ALL_TARGETS:
            assert target.min_interval_s > 0, f"{target.target_id} has non-positive min_interval_s"


# =========================================================================
# Verdict enum tests
# =========================================================================

class TestVerdictEnum:
    """Verify Verdict enum behavior."""

    def test_verdict_values(self):
        assert Verdict.CLEAN.value == "clean"
        assert Verdict.FLAGGED.value == "flagged"
        assert Verdict.CHALLENGED.value == "challenged"
        assert Verdict.INCONCLUSIVE.value == "inconclusive"

    def test_verdict_comparison(self):
        assert Verdict.CLEAN != Verdict.FLAGGED
        assert Verdict.CLEAN == Verdict.CLEAN

    def test_verdict_from_string(self):
        assert Verdict("clean") == Verdict.CLEAN
        assert Verdict("flagged") == Verdict.FLAGGED


# =========================================================================
# Tier enum tests
# =========================================================================

class TestTierEnum:
    """Verify Tier enum behavior."""

    def test_tier_values(self):
        assert Tier.SCANNER.value == "tier1_scanner"
        assert Tier.VENDOR.value == "tier2_vendor"
        assert Tier.CONTROLLED.value == "tier3_controlled"

    def test_tier_from_string(self):
        assert Tier("tier1_scanner") == Tier.SCANNER
        assert Tier("tier2_vendor") == Tier.VENDOR
        assert Tier("tier3_controlled") == Tier.CONTROLLED
