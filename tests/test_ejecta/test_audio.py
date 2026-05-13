"""BATCH-36/TASK-02 — Audio Noise Injector tests.

TEST-36-02-01 … TEST-36-02-07: pure string/data checks, no browser.
"""

from __future__ import annotations

from super_browser.stealth.ejecta import (
    EjectorConfig,
    EjectorResult,
    build_ejector_payloads,
)
from super_browser.stealth.ejecta.audio import AudioEjector

# ── TEST-36-02-01: AudioEjector.generate returns valid EjectorResult ──


class TestAudioEjectorGenerate:
    """TEST-36-02-01 — AudioEjector.generate returns a valid EjectorResult."""

    def test_returns_ejector_result(self) -> None:
        cfg = EjectorConfig()
        result = AudioEjector().generate(cfg)
        assert isinstance(result, EjectorResult)

    def test_ejector_id_is_audio(self) -> None:
        result = AudioEjector().generate(EjectorConfig())
        assert result.ejector_id == "audio"

    def test_js_payload_is_nonempty_string(self) -> None:
        result = AudioEjector().generate(EjectorConfig())
        assert isinstance(result.js_payload, str)
        assert len(result.js_payload) > 0

    def test_size_bytes_matches_utf8_length(self) -> None:
        result = AudioEjector().generate(EjectorConfig())
        assert result.size_bytes == len(result.js_payload.encode("utf-8"))

    def test_inject_order_is_20(self) -> None:
        result = AudioEjector().generate(EjectorConfig())
        assert result.inject_order == 20


# ── TEST-36-02-02: JS payload contains all audio API overrides ────────


class TestPayloadOverrides:
    """TEST-36-02-02 — JS payload contains all required audio API overrides."""

    REQUIRED_SUBSTRINGS = (
        "AudioContext.prototype.createBuffer",
        "AnalyserNode.prototype.getFloatFrequencyData",
        "AudioBuffer.prototype.getChannelData",
        "OfflineAudioContext.prototype.createBuffer",
        "AudioBufferSourceNode.prototype",
    )

    def test_payload_contains_all_overrides(self) -> None:
        js = AudioEjector().generate(EjectorConfig()).js_payload
        for substr in self.REQUIRED_SUBSTRINGS:
            assert substr in js, f"Missing override: {substr}"


# ── TEST-36-02-03: Deterministic output for same config ───────────────


class TestDeterminism:
    """TEST-36-02-03 — Same config produces identical payloads."""

    def test_identical_config_identical_payload(self) -> None:
        cfg = EjectorConfig(seed="alpha", profile_id="p1")
        r1 = AudioEjector().generate(cfg)
        r2 = AudioEjector().generate(cfg)
        assert r1.js_payload == r2.js_payload

    def test_different_seed_different_payload(self) -> None:
        r1 = AudioEjector().generate(EjectorConfig(seed="alpha"))
        r2 = AudioEjector().generate(EjectorConfig(seed="beta"))
        assert r1.js_payload != r2.js_payload

    def test_different_profile_id_different_payload(self) -> None:
        r1 = AudioEjector().generate(EjectorConfig(profile_id="p1"))
        r2 = AudioEjector().generate(EjectorConfig(profile_id="p2"))
        assert r1.js_payload != r2.js_payload


# ── TEST-36-02-04: Custom inject_order ───────────────────────────────


class TestCustomInjectOrder:
    """TEST-36-02-04 — Custom inject_order is respected."""

    def test_custom_order(self) -> None:
        result = AudioEjector(inject_order=99).generate(EjectorConfig())
        assert result.inject_order == 99

    def test_default_order(self) -> None:
        result = AudioEjector().generate(EjectorConfig())
        assert result.inject_order == 20


# ── TEST-36-02-05: JS payload contains PRNG and noise magnitude ──────


class TestPayloadContent:
    """TEST-36-02-05 — JS payload embeds PRNG seed and noise magnitude."""

    def test_payload_contains_mulberry32(self) -> None:
        js = AudioEjector().generate(EjectorConfig()).js_payload
        assert "mulberry32" in js
        assert "0x6D2B79F5" in js

    def test_payload_contains_noise_function(self) -> None:
        js = AudioEjector().generate(EjectorConfig()).js_payload
        assert "addNoiseFloat32" in js

    def test_default_magnitude_embedded(self) -> None:
        js = AudioEjector().generate(EjectorConfig()).js_payload
        assert "0.0001" in js

    def test_custom_magnitude_embedded(self) -> None:
        cfg = EjectorConfig(audio_noise_magnitude=0.005)
        js = AudioEjector().generate(cfg).js_payload
        assert "0.005" in js


# ── TEST-36-02-06: build_ejector_payloads includes audio ─────────────


class TestRegistryIntegration:
    """TEST-36-02-06 — build_ejector_payloads includes audio when enabled."""

    def test_audio_enabled_returns_audio_result(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(audio_enabled=True, canvas_enabled=False)
        )
        assert any(r.ejector_id == "audio" for r in results)

    def test_audio_disabled_no_audio_result(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(audio_enabled=False, canvas_enabled=False)
        )
        audio = [r for r in results if r.ejector_id == "audio"]
        assert len(audio) == 0

    def test_both_enabled_returns_at_least_two_results(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(canvas_enabled=True, audio_enabled=True)
        )
        ids = [r.ejector_id for r in results]
        assert "canvas" in ids
        assert "audio" in ids
        assert len(results) >= 2

    def test_canvas_before_audio_in_order(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(canvas_enabled=True, audio_enabled=True)
        )
        orders = {r.ejector_id: r.inject_order for r in results}
        assert orders["canvas"] < orders["audio"]


# ── TEST-36-02-07: Payload is a valid IIFE (syntactic markers) ───────


class TestPayloadIIFE:
    """TEST-36-02-07 — JS payload is a valid IIFE with strict mode."""

    def test_starts_with_iife(self) -> None:
        js = AudioEjector().generate(EjectorConfig()).js_payload
        assert js.startswith("(function() {")

    def test_ends_with_iife(self) -> None:
        js = AudioEjector().generate(EjectorConfig()).js_payload
        assert js.rstrip().endswith("})();")

    def test_contains_use_strict(self) -> None:
        js = AudioEjector().generate(EjectorConfig()).js_payload
        assert "'use strict'" in js

    def test_no_template_literals(self) -> None:
        """Payload must use classic string concatenation (ES5 compat)."""
        js = AudioEjector().generate(EjectorConfig()).js_payload
        assert "`" not in js
