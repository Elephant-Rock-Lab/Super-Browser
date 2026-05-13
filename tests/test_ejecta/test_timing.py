"""BATCH-37/TASK-02 — Timing & Math Precision Ejector tests.

TEST-37-02-01 … TEST-37-02-08: pure string/data checks, no browser.
"""

from __future__ import annotations

from super_browser.stealth.ejecta import (
    EjectorConfig,
    EjectorResult,
    build_ejector_payloads,
)
from super_browser.stealth.ejecta.timing import TimingEjector

# ── TEST-37-02-01: Payload is non-empty ──────────────────────────────


class TestPayloadNonEmpty:
    """TEST-37-02-01 — TimingEjector.generate returns a non-empty payload."""

    def test_js_payload_is_nonempty_string(self) -> None:
        result = TimingEjector().generate(EjectorConfig())
        assert isinstance(result.js_payload, str)
        assert len(result.js_payload) > 0

    def test_returns_ejector_result(self) -> None:
        cfg = EjectorConfig()
        result = TimingEjector().generate(cfg)
        assert isinstance(result, EjectorResult)

    def test_ejector_id_is_timing(self) -> None:
        result = TimingEjector().generate(EjectorConfig())
        assert result.ejector_id == "timing"

    def test_inject_order_is_40(self) -> None:
        result = TimingEjector().generate(EjectorConfig())
        assert result.inject_order == 40

    def test_size_bytes_matches_utf8_length(self) -> None:
        result = TimingEjector().generate(EjectorConfig())
        assert result.size_bytes == len(result.js_payload.encode("utf-8"))


# ── TEST-37-02-02: Overrides performance.now ─────────────────────────


class TestOverridesPerformanceNow:
    """TEST-37-02-02 — JS payload overrides performance.now()."""

    def test_contains_performance_now_override(self) -> None:
        js = TimingEjector().generate(EjectorConfig()).js_payload
        assert "performance.now" in js
        assert "performance.now = function()" in js

    def test_contains_precision_floor(self) -> None:
        js = TimingEjector().generate(EjectorConfig()).js_payload
        assert "PRECISION" in js
        assert "Math.floor" in js

    def test_contains_micro_jitter(self) -> None:
        js = TimingEjector().generate(EjectorConfig()).js_payload
        assert "jitter" in js
        assert "0.1" in js


# ── TEST-37-02-03: Overrides performance.timeOrigin ──────────────────


class TestOverridesTimeOrigin:
    """TEST-37-02-03 — JS payload overrides performance.timeOrigin."""

    def test_contains_timeorigin_override(self) -> None:
        js = TimingEjector().generate(EjectorConfig()).js_payload
        assert "timeOrigin" in js

    def test_contains_origin_offset(self) -> None:
        js = TimingEjector().generate(EjectorConfig()).js_payload
        assert "_originOffset" in js
        assert "200" in js
        assert "100" in js


# ── TEST-37-02-04: Perturbs Math constants ───────────────────────────


class TestPerturbsMathConstants:
    """TEST-37-02-04 — JS payload perturbs Math.PI, E, SQRT2, LOG2E, LN10."""

    MATH_CONSTANTS = ("Math.PI", "Math.E", "Math.SQRT2", "Math.LOG2E", "Math.LN10")

    def test_all_constants_overridden(self) -> None:
        js = TimingEjector().generate(EjectorConfig()).js_payload
        # Uses Object.create(Math) + shadow properties
        assert "Object.create(Math)" in js, "Must use prototype shadow"
        for const in ("PI", "E", "SQRT2", "LOG2E", "LN10"):
            assert f"Math.{const} + _noise" in js, f"Missing perturbation for Math.{const}"

    def test_noise_magnitude_is_1e15(self) -> None:
        js = TimingEjector().generate(EjectorConfig()).js_payload
        assert "1e-15" in js


# ── TEST-37-02-05: Deterministic for same seed ──────────────────────


class TestDeterministic:
    """TEST-37-02-05 — Same config produces identical payloads."""

    def test_identical_config_identical_payload(self) -> None:
        cfg = EjectorConfig(seed="alpha", profile_id="p1")
        r1 = TimingEjector().generate(cfg)
        r2 = TimingEjector().generate(cfg)
        assert r1.js_payload == r2.js_payload


# ── TEST-37-02-06: Different seeds differ ───────────────────────────


class TestDifferentSeeds:
    """TEST-37-02-06 — Different seeds produce different payloads."""

    def test_different_seed_different_payload(self) -> None:
        r1 = TimingEjector().generate(EjectorConfig(seed="alpha"))
        r2 = TimingEjector().generate(EjectorConfig(seed="beta"))
        assert r1.js_payload != r2.js_payload


# ── TEST-37-02-07: Configurable precision ───────────────────────────


class TestConfigurablePrecision:
    """TEST-37-02-07 — timing_precision_ms is embedded in payload."""

    def test_default_precision_embedded(self) -> None:
        js = TimingEjector().generate(EjectorConfig()).js_payload
        assert "var PRECISION = 1;" in js

    def test_custom_precision_embedded(self) -> None:
        cfg = EjectorConfig(timing_precision_ms=5)
        js = TimingEjector().generate(cfg).js_payload
        assert "var PRECISION = 5;" in js


# ── TEST-37-02-08: Registry includes timing ─────────────────────────


class TestRegistryIntegration:
    """TEST-37-02-08 — build_ejector_payloads includes timing when enabled."""

    def test_timing_enabled_returns_timing_result(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(
                timing_enabled=True,
                canvas_enabled=False,
                audio_enabled=False,
                webrtc_enabled=False,
            )
        )
        assert any(r.ejector_id == "timing" for r in results)

    def test_timing_disabled_no_timing_result(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(
                timing_enabled=False,
                canvas_enabled=False,
                audio_enabled=False,
                webrtc_enabled=False,
            )
        )
        timing = [r for r in results if r.ejector_id == "timing"]
        assert len(timing) == 0

    def test_all_enabled_returns_timing_in_order(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(
                canvas_enabled=True,
                audio_enabled=True,
                webrtc_enabled=True,
                timing_enabled=True,
            )
        )
        ids = [r.ejector_id for r in results]
        assert "timing" in ids
        orders = {r.ejector_id: r.inject_order for r in results}
        # timing (40) comes after canvas (10) and audio (20)
        assert orders["timing"] > orders["canvas"]
        assert orders["timing"] > orders["audio"]
