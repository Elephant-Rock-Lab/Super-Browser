"""Integration tests for v1.6.0 features — Anti-Detection Hardening.

Validates all 5 ejectors work together, validation suite is complete,
and the full pipeline produces valid deterministic output.
"""

from __future__ import annotations

from super_browser.stealth.consistency.derive import derive_matrix
from super_browser.stealth.ejecta.config import EjectorConfig
from super_browser.stealth.ejecta.registry import build_ejector_payloads
from super_browser.stealth.ejecta.types import EjectorResult
from super_browser.stealth.profiles import load_profile
from super_browser.stealth.validation.suite import FingerprintValidationSuite


class TestV160EjectorPipeline:
    """Full 5-ejector pipeline produces deterministic, valid JS."""

    def test_five_ejectors_all_enabled(self):
        config = EjectorConfig(seed="v160-test")
        payloads = build_ejector_payloads(config)
        assert len(payloads) == 5
        ids = {p.ejector_id for p in payloads}
        assert ids == {"canvas", "audio", "webrtc", "timing", "browser_apis"}

    def test_deterministic_across_calls(self):
        config = EjectorConfig(seed="determinism-check")
        p1 = build_ejector_payloads(config)
        p2 = build_ejector_payloads(config)
        for a, b in zip(p1, p2):
            assert a.js_payload == b.js_payload
            assert a.size_bytes == b.size_bytes

    def test_different_seeds_differ(self):
        c1 = EjectorConfig(seed="seed-a")
        c2 = EjectorConfig(seed="seed-b")
        p1 = build_ejector_payloads(c1)
        p2 = build_ejector_payloads(c2)
        for a, b in zip(p1, p2):
            assert a.js_payload != b.js_payload

    def test_payloads_ordered_by_inject_order(self):
        config = EjectorConfig(seed="order-test")
        payloads = build_ejector_payloads(config)
        orders = [p.inject_order for p in payloads]
        assert orders == sorted(orders)
        assert orders == [10, 20, 30, 40, 50]

    def test_all_payloads_are_valid_iife(self):
        config = EjectorConfig(seed="iife-test")
        payloads = build_ejector_payloads(config)
        for p in payloads:
            assert isinstance(p, EjectorResult)
            assert len(p.js_payload) > 100
            assert p.js_payload.startswith("(function()")
            assert "use strict" in p.js_payload


class TestV160ValidationSuite:
    """Validation suite covers all 12 checks."""

    def test_twelve_checks_total(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "v160-validation")
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)
        assert len(report.checks) == 12

    def test_ejector_checks_present(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "v160-checks")
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)
        check_ids = {c.check_id for c in report.checks}
        for expected in ("CHK-009", "CHK-010", "CHK-011", "CHK-012"):
            assert expected in check_ids, f"{expected} missing"

    def test_perfect_matrix_100_score(self):
        profile = load_profile("windows-chrome-stable")
        matrix = derive_matrix(profile, "perfect-v160")
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)
        assert report.score == 100.0
        assert report.passed is True


class TestV160IndividualToggle:
    """Each ejector can be independently disabled."""

    def test_disable_canvas(self):
        config = EjectorConfig(canvas_enabled=False, seed="t")
        ids = {p.ejector_id for p in build_ejector_payloads(config)}
        assert "canvas" not in ids
        assert len(ids) == 4

    def test_disable_audio(self):
        config = EjectorConfig(audio_enabled=False, seed="t")
        ids = {p.ejector_id for p in build_ejector_payloads(config)}
        assert "audio" not in ids

    def test_disable_webrtc(self):
        config = EjectorConfig(webrtc_enabled=False, seed="t")
        ids = {p.ejector_id for p in build_ejector_payloads(config)}
        assert "webrtc" not in ids

    def test_disable_timing(self):
        config = EjectorConfig(timing_enabled=False, seed="t")
        ids = {p.ejector_id for p in build_ejector_payloads(config)}
        assert "timing" not in ids

    def test_disable_browser_apis(self):
        config = EjectorConfig(browser_apis_enabled=False, seed="t")
        ids = {p.ejector_id for p in build_ejector_payloads(config)}
        assert "browser_apis" not in ids

    def test_all_disabled_empty(self):
        config = EjectorConfig(
            canvas_enabled=False, audio_enabled=False,
            webrtc_enabled=False, timing_enabled=False,
            browser_apis_enabled=False, seed="t",
        )
        assert build_ejector_payloads(config) == []


class TestV160MatrixExtension:
    """FingerprintMatrix includes ejector_seed."""

    def test_ejector_seed_from_derive(self):
        profile = load_profile("macos-chrome-stable")
        matrix = derive_matrix(profile, "matrix-ext-test")
        assert matrix.ejector_seed == "matrix-ext-test"

    def test_ejector_seed_independent_of_profile(self):
        p1 = load_profile("windows-chrome-stable")
        p2 = load_profile("macos-chrome-stable")
        m1 = derive_matrix(p1, "shared-seed")
        m2 = derive_matrix(p2, "shared-seed")
        assert m1.ejector_seed == m2.ejector_seed
