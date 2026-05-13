"""BATCH-36/TASK-01 — Canvas Noise Injector + Ejector Framework tests.

TEST-36-01-01 … TEST-36-01-08: pure string/data checks, no browser.
"""

from __future__ import annotations

from super_browser.stealth.ejecta import (
    EjectorConfig,
    EjectorResult,
    build_ejector_payloads,
)
from super_browser.stealth.ejecta.canvas import CanvasEjector

# ── TEST-36-01-01: EjectorConfig is frozen ────────────────────────────


class TestEjectorConfigFrozen:
    """TEST-36-01-01 — EjectorConfig is frozen (immutable)."""

    def test_frozen_rejects_attribute_assignment(self) -> None:
        cfg = EjectorConfig()
        try:
            cfg.canvas_enabled = False  # type: ignore[misc]
        except AttributeError:
            pass
        else:
            raise AssertionError("EjectorConfig should be frozen")


# ── TEST-36-01-02: EjectorConfig defaults ─────────────────────────────


class TestEjectorConfigDefaults:
    """TEST-36-01-02 — EjectorConfig has correct default values."""

    def test_canvas_enabled_default(self) -> None:
        assert EjectorConfig().canvas_enabled is True

    def test_canvas_noise_magnitude_default(self) -> None:
        assert EjectorConfig().canvas_noise_magnitude == 2

    def test_audio_enabled_default(self) -> None:
        assert EjectorConfig().audio_enabled is True

    def test_audio_noise_magnitude_default(self) -> None:
        assert EjectorConfig().audio_noise_magnitude == 0.0001

    def test_profile_id_default(self) -> None:
        assert EjectorConfig().profile_id == ""

    def test_seed_default(self) -> None:
        assert EjectorConfig().seed == "default"


# ── TEST-36-01-03: EjectorResult fields ───────────────────────────────


class TestEjectorResultFields:
    """TEST-36-01-03 — EjectorResult stores all expected fields."""

    def _make(self) -> EjectorResult:
        return EjectorResult(
            ejector_id="canvas",
            js_payload="var x = 1;",
            inject_order=10,
            size_bytes=10,
        )

    def test_ejector_id(self) -> None:
        assert self._make().ejector_id == "canvas"

    def test_js_payload(self) -> None:
        assert self._make().js_payload == "var x = 1;"

    def test_inject_order(self) -> None:
        assert self._make().inject_order == 10

    def test_size_bytes(self) -> None:
        assert self._make().size_bytes == 10


# ── TEST-36-01-04: EjectorResult is frozen ────────────────────────────


class TestEjectorResultFrozen:
    """TEST-36-01-04 — EjectorResult is frozen (immutable)."""

    def test_frozen_rejects_attribute_assignment(self) -> None:
        r = EjectorResult(
            ejector_id="canvas",
            js_payload="",
            inject_order=0,
            size_bytes=0,
        )
        try:
            r.js_payload = "new"  # type: ignore[misc]
        except AttributeError:
            pass
        else:
            raise AssertionError("EjectorResult should be frozen")


# ── TEST-36-01-05: CanvasEjector.generate returns valid EjectorResult ─


class TestCanvasEjectorGenerate:
    """TEST-36-01-05 — CanvasEjector.generate returns a valid EjectorResult."""

    def test_returns_ejector_result(self) -> None:
        cfg = EjectorConfig()
        result = CanvasEjector().generate(cfg)
        assert isinstance(result, EjectorResult)

    def test_ejector_id_is_canvas(self) -> None:
        result = CanvasEjector().generate(EjectorConfig())
        assert result.ejector_id == "canvas"

    def test_js_payload_is_nonempty_string(self) -> None:
        result = CanvasEjector().generate(EjectorConfig())
        assert isinstance(result.js_payload, str)
        assert len(result.js_payload) > 0

    def test_size_bytes_matches_utf8_length(self) -> None:
        result = CanvasEjector().generate(EjectorConfig())
        assert result.size_bytes == len(result.js_payload.encode("utf-8"))

    def test_inject_order_is_int(self) -> None:
        result = CanvasEjector().generate(EjectorConfig())
        assert isinstance(result.inject_order, int)


# ── TEST-36-01-06: JS payload contains all canvas API overrides ───────


class TestPayloadOverrides:
    """TEST-36-01-06 — JS payload contains all required canvas API overrides."""

    REQUIRED_SUBSTRINGS = (
        "HTMLCanvasElement.prototype.toDataURL",
        "HTMLCanvasElement.prototype.toBlob",
        "CanvasRenderingContext2D.prototype.putImageData",
        "CanvasRenderingContext2D.prototype.getImageData",
        "OffscreenCanvas.prototype.convertToBlob",
        "WebGL2RenderingContext.prototype.readPixels",
        "WebGLRenderingContext.prototype.readPixels",
    )

    def test_payload_contains_all_overrides(self) -> None:
        js = CanvasEjector().generate(EjectorConfig()).js_payload
        for substr in self.REQUIRED_SUBSTRINGS:
            assert substr in js, f"Missing override: {substr}"


# ── TEST-36-01-07: Deterministic output for same config ───────────────


class TestDeterminism:
    """TEST-36-01-07 — Same config produces identical payloads."""

    def test_identical_config_identical_payload(self) -> None:
        cfg = EjectorConfig(seed="alpha", profile_id="p1")
        r1 = CanvasEjector().generate(cfg)
        r2 = CanvasEjector().generate(cfg)
        assert r1.js_payload == r2.js_payload

    def test_different_seed_different_payload(self) -> None:
        r1 = CanvasEjector().generate(EjectorConfig(seed="alpha"))
        r2 = CanvasEjector().generate(EjectorConfig(seed="beta"))
        assert r1.js_payload != r2.js_payload

    def test_different_profile_id_different_payload(self) -> None:
        r1 = CanvasEjector().generate(EjectorConfig(profile_id="p1"))
        r2 = CanvasEjector().generate(EjectorConfig(profile_id="p2"))
        assert r1.js_payload != r2.js_payload


# ── TEST-36-01-08: build_ejector_payloads returns ordered results ─────


class TestBuildEjectorPayloads:
    """TEST-36-01-08 — build_ejector_payloads returns ordered results."""

    def test_returns_list(self) -> None:
        results = build_ejector_payloads(EjectorConfig())
        assert isinstance(results, list)

    def test_canvas_enabled_returns_canvas_result(self) -> None:
        results = build_ejector_payloads(EjectorConfig(canvas_enabled=True))
        assert any(r.ejector_id == "canvas" for r in results)

    def test_canvas_disabled_returns_empty(self) -> None:
        results = build_ejector_payloads(EjectorConfig(canvas_enabled=False))
        canvas = [r for r in results if r.ejector_id == "canvas"]
        assert len(canvas) == 0

    def test_results_ordered_by_inject_order(self) -> None:
        results = build_ejector_payloads(EjectorConfig())
        orders = [r.inject_order for r in results]
        assert orders == sorted(orders)

    def test_payload_size_positive(self) -> None:
        results = build_ejector_payloads(EjectorConfig())
        for r in results:
            assert r.size_bytes > 0
