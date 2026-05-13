"""Integration tests for BATCH-38/TASK-02 — Browser API ejector wiring.

Tests: TEST-38-02-01 through TEST-38-02-05
"""

from __future__ import annotations

from super_browser.stealth.consistency.derive import derive_matrix
from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.registry import build_ejector_payloads
from super_browser.stealth.profiles import load_profile
from super_browser.stealth.validation.suite import FingerprintValidationSuite


class TestAllEjectorsInRegistry:
    """TEST-38-02-01: All 5 ejectors in registry."""

    def test_five_ejectors_when_all_enabled(self):
        config = EjectorConfig(seed="full-pipeline-v2")
        payloads = build_ejector_payloads(config)
        ejector_ids = [p.ejector_id for p in payloads]
        assert len(payloads) == 5
        for expected in ("canvas", "audio", "webrtc", "timing", "browser_apis"):
            assert expected in ejector_ids, f"{expected} missing from registry"


class TestNewValidationCheck:
    """TEST-38-02-02: CHK-012 Browser_APIs in suite."""

    def test_browser_apis_check_in_suite(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "batch38-validation")
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)
        check_ids = [c.check_id for c in report.checks]
        assert "CHK-012" in check_ids, "Browser_APIs (CHK-012) must be present"


class TestSuiteCheckCount:
    """TEST-38-02-03: Suite now has 12 checks."""

    def test_twelve_checks(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "count-test")
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)
        assert len(report.checks) == 12, f"Expected 12 checks, got {len(report.checks)}"


class TestIndividualToggle:
    """TEST-38-02-04: Each payload independently toggleable."""

    def test_disable_browser_apis(self):
        config = EjectorConfig(browser_apis_enabled=False, seed="test")
        payloads = build_ejector_payloads(config)
        assert "browser_apis" not in [p.ejector_id for p in payloads]

    def test_disable_canvas_still_has_others(self):
        config = EjectorConfig(canvas_enabled=False, seed="test")
        payloads = build_ejector_payloads(config)
        ejector_ids = [p.ejector_id for p in payloads]
        assert "canvas" not in ejector_ids
        assert "audio" in ejector_ids
        assert "browser_apis" in ejector_ids


class TestFullPipelineValidJs:
    """TEST-38-02-05: Full 5-ejector pipeline produces valid JS."""

    def test_all_payloads_valid(self):
        config = EjectorConfig(seed="pipeline-v2-test")
        payloads = build_ejector_payloads(config)
        for p in payloads:
            assert isinstance(p.js_payload, str)
            assert len(p.js_payload) > 100, f"{p.ejector_id}: too short"
            assert "(" in p.js_payload, f"{p.ejector_id}: no function calls"
