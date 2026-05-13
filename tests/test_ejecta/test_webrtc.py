"""BATCH-37/TASK-01 — WebRTC Leak Prevention ejector tests.

TEST-37-01-01 … TEST-37-01-06: pure string/data checks, no browser.
"""

from __future__ import annotations

from super_browser.stealth.ejecta import (
    EjectorConfig,
    build_ejector_payloads,
)
from super_browser.stealth.ejecta.webrtc import WebRTCEjector


def _default_config() -> EjectorConfig:
    return EjectorConfig(seed="test-seed", profile_id="profile-1")


# ── TEST-37-01-01: Payload is non-empty ───────────────────────────────


class TestPayloadNonEmpty:
    """TEST-37-01-01 — WebRTCEjector.generate returns a non-empty payload."""

    def test_js_payload_nonempty(self) -> None:
        result = WebRTCEjector().generate(_default_config())
        assert isinstance(result.js_payload, str)
        assert len(result.js_payload) > 0

    def test_ejector_id_is_webrtc(self) -> None:
        result = WebRTCEjector().generate(_default_config())
        assert result.ejector_id == "webrtc"

    def test_inject_order_is_30(self) -> None:
        result = WebRTCEjector().generate(_default_config())
        assert result.inject_order == 30

    def test_size_bytes_matches_utf8(self) -> None:
        result = WebRTCEjector().generate(_default_config())
        assert result.size_bytes == len(result.js_payload.encode("utf-8"))


# ── TEST-37-01-02: Blocks RTCPeerConnection ───────────────────────────


class TestBlocksRTCPeerConnection:
    """TEST-37-01-02 — Payload blocks window.RTCPeerConnection."""

    def test_blocks_rtc_peer_connection(self) -> None:
        js = WebRTCEjector().generate(_default_config()).js_payload
        assert "window.RTCPeerConnection" in js
        assert "= undefined" in js


# ── TEST-37-01-03: Blocks webkitRTCPeerConnection ─────────────────────


class TestBlocksWebkitRTCPeerConnection:
    """TEST-37-01-03 — Payload blocks window.webkitRTCPeerConnection."""

    def test_blocks_webkit_rtc_peer_connection(self) -> None:
        js = WebRTCEjector().generate(_default_config()).js_payload
        assert "window.webkitRTCPeerConnection" in js


# ── TEST-37-01-04: Blocks mozRTCPeerConnection ────────────────────────


class TestBlocksMozRTCPeerConnection:
    """TEST-37-01-04 — Payload blocks window.mozRTCPeerConnection."""

    def test_blocks_moz_rtc_peer_connection(self) -> None:
        js = WebRTCEjector().generate(_default_config()).js_payload
        assert "window.mozRTCPeerConnection" in js


# ── TEST-37-01-05: Deterministic for same seed, differs for different ─


class TestDeterminism:
    """TEST-37-01-05 — Same seed produces same payload; different seeds differ."""

    def test_deterministic_same_config(self) -> None:
        cfg = _default_config()
        r1 = WebRTCEjector().generate(cfg)
        r2 = WebRTCEjector().generate(cfg)
        assert r1.js_payload == r2.js_payload

    def test_different_seeds_produce_different_payloads(self) -> None:
        r1 = WebRTCEjector().generate(EjectorConfig(seed="alpha", profile_id="p1"))
        r2 = WebRTCEjector().generate(EjectorConfig(seed="beta", profile_id="p1"))
        assert r1.js_payload != r2.js_payload


# ── TEST-37-01-06: Mocks enumerateDevices ─────────────────────────────


class TestMocksEnumerateDevices:
    """TEST-37-01-06 — Payload mocks navigator.mediaDevices.enumerateDevices."""

    def test_overrides_enumerate_devices(self) -> None:
        js = WebRTCEjector().generate(_default_config()).js_payload
        assert "navigator.mediaDevices.enumerateDevices" in js

    def test_returns_mock_device_list(self) -> None:
        js = WebRTCEjector().generate(_default_config()).js_payload
        assert "audioinput" in js
        assert "audiooutput" in js
        assert "videoinput" in js


# ── TEST-37-01-07 (bonus): Registry includes webrtc ───────────────────


class TestRegistryIncludesWebRTC:
    """Registry includes WebRTCEjector when webrtc_enabled is True."""

    def test_webrtc_in_registry_when_enabled(self) -> None:
        results = build_ejector_payloads(EjectorConfig(webrtc_enabled=True))
        assert any(r.ejector_id == "webrtc" for r in results)

    def test_webrtc_absent_when_disabled(self) -> None:
        results = build_ejector_payloads(EjectorConfig(webrtc_enabled=False))
        assert not any(r.ejector_id == "webrtc" for r in results)

    def test_results_ordered_by_inject_order(self) -> None:
        results = build_ejector_payloads(EjectorConfig())
        orders = [r.inject_order for r in results]
        assert orders == sorted(orders)
