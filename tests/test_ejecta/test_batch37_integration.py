"""Integration tests for BATCH-37/TASK-03 — WebRTC + Timing ejector wiring.

Tests: TEST-37-03-01 through TEST-37-03-04
"""

from __future__ import annotations

from super_browser.stealth.consistency.derive import derive_matrix
from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.registry import build_ejector_payloads
from super_browser.stealth.profiles import load_profile
from super_browser.stealth.validation.suite import FingerprintValidationSuite


class TestAllEjectorsInRegistry:
    """TEST-37-03-01: All 4 ejectors in registry."""

    def test_four_ejectors_when_all_enabled(self):
        config = EjectorConfig(
            canvas_enabled=True, audio_enabled=True,
            webrtc_enabled=True, timing_enabled=True,
            seed="full-pipeline",
        )
        payloads = build_ejector_payloads(config)
        ejector_ids = [p.ejector_id for p in payloads]
        assert len(payloads) == 4
        assert "canvas" in ejector_ids
        assert "audio" in ejector_ids
        assert "webrtc" in ejector_ids
        assert "timing" in ejector_ids


class TestIndividualDisable:
    """TEST-37-03-02: Each ejector individually disableable."""

    def test_disable_webrtc(self):
        config = EjectorConfig(webrtc_enabled=False, seed="test")
        payloads = build_ejector_payloads(config)
        assert "webrtc" not in [p.ejector_id for p in payloads]

    def test_disable_timing(self):
        config = EjectorConfig(timing_enabled=False, seed="test")
        payloads = build_ejector_payloads(config)
        assert "timing" not in [p.ejector_id for p in payloads]


class TestNewValidationChecks:
    """TEST-37-03-03: New validation checks exist."""

    def test_webrtc_and_timing_checks_in_suite(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "batch37-validation")
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)
        check_ids = [c.check_id for c in report.checks]
        assert "CHK-010" in check_ids, "WebRTC_Blocked (CHK-010) must be present"
        assert "CHK-011" in check_ids, "Timing_Precision (CHK-011) must be present"
        assert len(report.checks) == 11, f"Expected 11 checks, got {len(report.checks)}"


class TestFullPipelineValidJs:
    """TEST-37-03-04: Full pipeline produces valid JS."""

    def test_all_payloads_valid(self):
        config = EjectorConfig(seed="pipeline-test")
        payloads = build_ejector_payloads(config)
        for p in payloads:
            assert isinstance(p.js_payload, str)
            assert len(p.js_payload) > 100, f"{p.ejector_id}: too short ({len(p.js_payload)})"
            assert "(" in p.js_payload and ")" in p.js_payload, f"{p.ejector_id}: no function calls"
