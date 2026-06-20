"""Offline unit tests for external target parsers.

These verify each parser handles expected/edge/boundary inputs
without requiring network or browser access.
"""

from __future__ import annotations

from adversarial3.core import Tier, Verdict
from adversarial3.vectors.external import (
    SCANNER_TARGETS,
    VENDOR_TARGETS,
    _parse_browserscan,
    _parse_cloudflare_demo,
    _parse_creepjs,
    _parse_datadome_demo,
    _parse_incolumitas,
    _parse_sannysoft,
    get_external_targets,
)


class TestSannysoftParser:
    def test_clean(self):
        r = _parse_sannysoft("ext_sannysoft", webdriver=False, body_text="Welcome")
        assert r.verdict == Verdict.CLEAN
        assert r.score == 1.0

    def test_flagged_webdriver(self):
        r = _parse_sannysoft("ext_sannysoft", webdriver=True, body_text="Welcome")
        assert r.verdict == Verdict.FLAGGED
        assert r.score == 0.0

    def test_flagged_bot_label(self):
        r = _parse_sannysoft("ext_sannysoft", webdriver=False, body_text="YOU ARE A BOT")
        assert r.verdict == Verdict.FLAGGED


class TestIncolumitasParser:
    def test_clean_low_probability(self):
        r = _parse_incolumitas("ext_incolumitas", bot_probability=0.1, body_text="")
        assert r.verdict == Verdict.CLEAN
        assert r.score == 0.9

    def test_flagged_high_probability(self):
        r = _parse_incolumitas("ext_incolumitas", bot_probability=0.9, body_text="")
        assert r.verdict == Verdict.FLAGGED

    def test_boundary_exactly_half(self):
        r = _parse_incolumitas("ext_incolumitas", bot_probability=0.5, body_text="")
        assert r.verdict == Verdict.CLEAN

    def test_null_probability_human_text(self):
        r = _parse_incolumitas("ext_incolumitas", bot_probability=None, body_text="You are human")
        assert r.verdict == Verdict.CLEAN

    def test_null_probability_no_text(self):
        r = _parse_incolumitas("ext_incolumitas", bot_probability=None, body_text="loading...")
        assert r.verdict == Verdict.INCONCLUSIVE


class TestCreepJSParser:
    def test_clean_high_trust(self):
        r = _parse_creepjs("ext_creepjs", trust_score=85.0)
        assert r.verdict == Verdict.CLEAN
        assert r.score == 0.85

    def test_flagged_low_trust(self):
        r = _parse_creepjs("ext_creepjs", trust_score=30.0)
        assert r.verdict == Verdict.FLAGGED

    def test_boundary_50(self):
        r = _parse_creepjs("ext_creepjs", trust_score=50.0)
        assert r.verdict == Verdict.CLEAN

    def test_none_trust(self):
        r = _parse_creepjs("ext_creepjs", trust_score=None)
        assert r.verdict == Verdict.INCONCLUSIVE


class TestBrowserscanParser:
    def test_clean(self):
        r = _parse_browserscan("ext_browserscan", webdriver=False, body_text="Complete")
        assert r.verdict == Verdict.CLEAN

    def test_flagged_webdriver(self):
        r = _parse_browserscan("ext_browserscan", webdriver=True, body_text="")
        assert r.verdict == Verdict.FLAGGED

    def test_flagged_automation_name(self):
        r = _parse_browserscan("ext_browserscan", webdriver=False, body_text="Detected: Playwright")
        assert r.verdict == Verdict.FLAGGED

    def test_challenged_bot(self):
        r = _parse_browserscan("ext_browserscan", webdriver=False, body_text="You are bot")
        assert r.verdict == Verdict.CHALLENGED


class TestCloudflareParser:
    def test_clean(self):
        r = _parse_cloudflare_demo("ext_cloudflare", challenge_present=False, ray_id="abc")
        assert r.verdict == Verdict.CLEAN

    def test_challenged(self):
        r = _parse_cloudflare_demo("ext_cloudflare", challenge_present=True, ray_id="def")
        assert r.verdict == Verdict.CHALLENGED


class TestDatadomeParser:
    def test_clean(self):
        r = _parse_datadome_demo("ext_datadome", blocked=False, captcha_present=False)
        assert r.verdict == Verdict.CLEAN

    def test_blocked(self):
        r = _parse_datadome_demo("ext_datadome", blocked=True, captcha_present=False)
        assert r.verdict == Verdict.FLAGGED

    def test_captcha(self):
        r = _parse_datadome_demo("ext_datadome", blocked=False, captcha_present=True)
        assert r.verdict == Verdict.CHALLENGED


class TestTargetRegistry:
    def test_scanner_count(self):
        assert len(SCANNER_TARGETS) == 4

    def test_vendor_count(self):
        assert len(VENDOR_TARGETS) == 2

    def test_scanner_tier(self):
        for t in SCANNER_TARGETS:
            assert t.tier == Tier.EXTERNAL_SCANNER

    def test_vendor_tier(self):
        for t in VENDOR_TARGETS:
            assert t.tier == Tier.EXTERNAL_VENDOR

    def test_vendor_interval_30s(self):
        for t in VENDOR_TARGETS:
            assert t.min_interval_s >= 30.0

    def test_all_urls_https(self):
        for t in SCANNER_TARGETS + VENDOR_TARGETS:
            assert t.url.startswith("https://"), f"{t.target_id}: {t.url}"

    def test_get_external_targets_empty(self):
        assert get_external_targets() == []

    def test_get_external_targets_scanners_only(self):
        result = get_external_targets(include_scanners=True)
        assert len(result) == 4

    def test_get_external_targets_all(self):
        result = get_external_targets(include_scanners=True, include_vendors=True)
        assert len(result) == 6
