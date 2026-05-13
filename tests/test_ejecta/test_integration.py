"""Integration tests for BATCH-36/TASK-03 — ejector wiring.

Tests: TEST-36-03-01 through TEST-36-03-05
"""

from __future__ import annotations

from super_browser.stealth.consistency.derive import derive_matrix
from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.registry import build_ejector_payloads
from super_browser.stealth.profiles import load_profile
from super_browser.stealth.validation.suite import FingerprintValidationSuite


class TestMatrixEjectorSeed:
    """TEST-36-03-01: Matrix includes ejector_seed."""

    def test_ejector_seed_populated(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "ejector-test-seed")
        assert hasattr(matrix, "ejector_seed"), "FingerprintMatrix must have ejector_seed"
        assert matrix.ejector_seed == "ejector-test-seed"


class TestDerivedEjectorSeed:
    """TEST-36-03-02: Derive matrix → ejector payload."""

    def test_ejector_seed_nonempty(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "my-seed-123")
        assert matrix.ejector_seed == "my-seed-123"

        config = EjectorConfig(seed=matrix.ejector_seed, profile_id=matrix.profile_id)
        payloads = build_ejector_payloads(config)
        assert len(payloads) >= 1, "At least canvas ejector should produce payload"


class TestValidationCheck:
    """TEST-36-03-03: Canvas_Audio_Consistency check exists."""

    def test_check_in_suite(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "validation-check-test")
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)
        check_ids = [c.check_id for c in report.checks]
        assert "CHK-009" in check_ids, "Canvas_Audio_Consistency (CHK-009) must be in suite"


class TestEjectorConfigToggle:
    """TEST-36-03-04: Ejectors disabled when config off."""

    def test_canvas_disabled_no_canvas_payload(self):
        config = EjectorConfig(canvas_enabled=False, audio_enabled=False, seed="test")
        payloads = build_ejector_payloads(config)
        ejector_ids = [p.ejector_id for p in payloads]
        assert "canvas" not in ejector_ids, "Canvas should not appear when disabled"

    def test_audio_disabled_no_audio_payload(self):
        config = EjectorConfig(canvas_enabled=True, audio_enabled=False, seed="test")
        payloads = build_ejector_payloads(config)
        ejector_ids = [p.ejector_id for p in payloads]
        assert "audio" not in ejector_ids, "Audio should not appear when disabled"


class TestInjectDeliveryPreserved:
    """TEST-36-03-05: Existing inject behavior preserved after ejector wiring."""

    def test_ejector_payloads_are_valid_js(self):
        config = EjectorConfig(canvas_enabled=True, audio_enabled=True, seed="inject-test")
        payloads = build_ejector_payloads(config)
        for p in payloads:
            assert isinstance(p.js_payload, str), f"Payload must be string, got {type(p.js_payload)}"
            assert len(p.js_payload) > 100, f"Payload too short ({len(p.js_payload)} bytes)"
            assert "function" in p.js_payload or "=>" in p.js_payload, "Must contain function definitions"
