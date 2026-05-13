"""BATCH-38/TASK-01 — Browser APIs ejector tests.

TEST-38-01-01 … TEST-38-01-10: pure string/data checks, no browser.
"""

from __future__ import annotations

from super_browser.stealth.ejecta import (
    EjectorConfig,
    build_ejector_payloads,
)
from super_browser.stealth.ejecta.browser_apis import BrowserAPIsEjector


def _default_config() -> EjectorConfig:
    return EjectorConfig(seed="test-seed", profile_id="profile-1")


# ── TEST-38-01-01: Payload non-empty, > 100 bytes ─────────────────────


class TestPayloadNonEmpty:
    """TEST-38-01-01 — BrowserAPIsEjector.generate returns a substantial payload."""

    def test_js_payload_is_nonempty_string(self) -> None:
        result = BrowserAPIsEjector().generate(_default_config())
        assert isinstance(result.js_payload, str)
        assert len(result.js_payload) > 0

    def test_js_payload_exceeds_100_bytes(self) -> None:
        result = BrowserAPIsEjector().generate(_default_config())
        assert result.size_bytes > 100

    def test_ejector_id_is_browser_apis(self) -> None:
        result = BrowserAPIsEjector().generate(_default_config())
        assert result.ejector_id == "browser_apis"

    def test_inject_order_is_50(self) -> None:
        result = BrowserAPIsEjector().generate(_default_config())
        assert result.inject_order == 50


# ── TEST-38-01-02: Contains getBattery override ───────────────────────


class TestGetBattery:
    """TEST-38-01-02 — Payload overrides navigator.getBattery."""

    def test_contains_get_battery(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "navigator.getBattery" in js

    def test_contains_promise_reject(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "Promise.reject" in js


# ── TEST-38-01-03: Contains permissions override ──────────────────────


class TestPermissions:
    """TEST-38-01-03 — Payload overrides navigator.permissions.query."""

    def test_contains_permissions_query(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "navigator.permissions" in js
        assert ".query" in js

    def test_returns_denied_state(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "denied" in js


# ── TEST-38-01-04: Contains speechSynthesis / getVoices override ──────


class TestSpeechSynthesis:
    """TEST-38-01-04 — Payload overrides speechSynthesis.getVoices."""

    def test_contains_speech_synthesis(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "speechSynthesis" in js

    def test_contains_get_voices(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "getVoices" in js


# ── TEST-38-01-05: Contains getComputedStyle / visited override ───────


class TestComputedStyle:
    """TEST-38-01-05 — Payload overrides getComputedStyle for :visited links."""

    def test_contains_get_computed_style(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "getComputedStyle" in js

    def test_contains_visited_normalisation(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert ":link" in js


# ── TEST-38-01-06: Contains getBoundingClientRect jitter ──────────────


class TestBoundingClientRect:
    """TEST-38-01-06 — Payload adds jitter to getBoundingClientRect."""

    def test_contains_get_bounding_client_rect(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "getBoundingClientRect" in js

    def test_contains_get_client_rects(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "getClientRects" in js

    def test_contains_jitter_function(self) -> None:
        js = BrowserAPIsEjector().generate(_default_config()).js_payload
        assert "jitter" in js


# ── TEST-38-01-07: Deterministic (same seed → same payload) ───────────


class TestDeterministic:
    """TEST-38-01-07 — Same config always produces the same payload."""

    def test_same_config_same_payload(self) -> None:
        cfg = _default_config()
        r1 = BrowserAPIsEjector().generate(cfg)
        r2 = BrowserAPIsEjector().generate(cfg)
        assert r1.js_payload == r2.js_payload

    def test_same_config_same_size(self) -> None:
        cfg = _default_config()
        r1 = BrowserAPIsEjector().generate(cfg)
        r2 = BrowserAPIsEjector().generate(cfg)
        assert r1.size_bytes == r2.size_bytes


# ── TEST-38-01-08: Different seeds → different payloads ──────────────


class TestDifferentSeeds:
    """TEST-38-01-08 — Different seeds produce different payloads."""

    def test_different_seeds_differ(self) -> None:
        r1 = BrowserAPIsEjector().generate(
            EjectorConfig(seed="alpha", profile_id="p1"),
        )
        r2 = BrowserAPIsEjector().generate(
            EjectorConfig(seed="beta", profile_id="p1"),
        )
        assert r1.js_payload != r2.js_payload


# ── TEST-38-01-09: Registry includes "browser_apis" when enabled ─────


class TestRegistryEnabled:
    """TEST-38-01-09 — Registry includes browser_apis when enabled."""

    def test_browser_apis_in_registry(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(browser_apis_enabled=True),
        )
        ids = [r.ejector_id for r in results]
        assert "browser_apis" in ids

    def test_browser_apis_order_is_50(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(browser_apis_enabled=True),
        )
        ba = [r for r in results if r.ejector_id == "browser_apis"]
        assert len(ba) == 1
        assert ba[0].inject_order == 50


# ── TEST-38-01-10: Not in registry when disabled ──────────────────────


class TestRegistryDisabled:
    """TEST-38-01-10 — Registry excludes browser_apis when disabled."""

    def test_browser_apis_absent_when_disabled(self) -> None:
        results = build_ejector_payloads(
            EjectorConfig(browser_apis_enabled=False),
        )
        ids = [r.ejector_id for r in results]
        assert "browser_apis" not in ids
