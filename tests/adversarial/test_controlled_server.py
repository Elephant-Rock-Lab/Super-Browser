"""Structural and scoring tests for the enhanced controlled server.

Verifies:
- Server starts/stops correctly
- Detection HTML contains all probe vectors
- Scoring engine classifies signals correctly
- Behavioral analysis page exists
- New vectors (WebGL, canvas, permissions) are present in scoring
"""

from __future__ import annotations

import pytest

from tests.adversarial.controlled_server import (
    BEHAVIORAL_HTML,
    DETECTION_HTML,
    ControlledDetectionServer,
    _score_signals,
)

# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


class TestServerLifecycle:
    """Verify server starts and stops cleanly."""

    def test_server_starts_and_serves(self) -> None:
        """Server serves the detection page."""
        import urllib.request

        with ControlledDetectionServer() as server:
            url = server.base_url
            with urllib.request.urlopen(url, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                assert "Controlled Detection Target" in body

    def test_server_serves_behavioral_page(self) -> None:
        """Server serves the behavioral analysis page."""
        import urllib.request

        with ControlledDetectionServer() as server:
            with urllib.request.urlopen(f"{server.base_url}/behavioral", timeout=5) as resp:
                body = resp.read().decode("utf-8")
                assert "Behavioral Analysis Target" in body

    def test_server_returns_404_for_unknown(self) -> None:
        """Unknown paths return 404."""
        import urllib.error
        import urllib.request

        with ControlledDetectionServer() as server:
            with pytest.raises(urllib.error.HTTPError):
                urllib.request.urlopen(f"{server.base_url}/nonexistent", timeout=5)

    def test_last_verdict_initially_none(self) -> None:
        """last_verdict is None before any detection."""
        with ControlledDetectionServer() as server:
            assert server.last_verdict is None

    def test_last_behavior_initially_none(self) -> None:
        """last_behavior is None before any behavioral analysis."""
        with ControlledDetectionServer() as server:
            assert server.last_behavior is None


# ---------------------------------------------------------------------------
# Detection HTML content
# ---------------------------------------------------------------------------


class TestDetectionHTML:
    """Verify the detection page contains all probe vectors."""

    def test_contains_webdriver_check(self) -> None:
        assert "navigator.webdriver" in DETECTION_HTML

    def test_contains_cdc_check(self) -> None:
        assert "cdc_" in DETECTION_HTML

    def test_contains_plugins_check(self) -> None:
        assert "navigator.plugins" in DETECTION_HTML

    def test_contains_webgl_check(self) -> None:
        assert "WEBGL_debug_renderer_info" in DETECTION_HTML
        assert "swiftshader" in DETECTION_HTML.lower()

    def test_contains_canvas_check(self) -> None:
        assert "toDataURL" in DETECTION_HTML
        assert "canvas_hash" in DETECTION_HTML

    def test_contains_permissions_check(self) -> None:
        assert "permissions.query" in DETECTION_HTML
        assert "Notification.permission" in DETECTION_HTML

    def test_contains_hardware_checks(self) -> None:
        assert "hardwareConcurrency" in DETECTION_HTML
        assert "deviceMemory" in DETECTION_HTML

    def test_contains_interaction_timing(self) -> None:
        assert "__sb_first_interaction_ts" in DETECTION_HTML
        assert "__sb_page_load_ts" in DETECTION_HTML

    def test_posts_to_api_verdict(self) -> None:
        assert "/api/verdict" in DETECTION_HTML

    def test_sets_window_verdict(self) -> None:
        assert "window.__sb_verdict" in DETECTION_HTML


class TestBehavioralHTML:
    """Verify the behavioral analysis page."""

    def test_has_input_field(self) -> None:
        assert "input-field" in BEHAVIORAL_HTML

    def test_tracks_mouse_events(self) -> None:
        assert "mousemove" in BEHAVIORAL_HTML
        assert "mouseEvents" in BEHAVIORAL_HTML

    def test_tracks_key_events(self) -> None:
        assert "keydown" in BEHAVIORAL_HTML
        assert "keyEvents" in BEHAVIORAL_HTML

    def test_analyzes_linearity(self) -> None:
        assert "mouse_straight_line" in BEHAVIORAL_HTML

    def test_analyzes_speed_variance(self) -> None:
        assert "mouse_constant_speed" in BEHAVIORAL_HTML

    def test_analyzes_keystroke_variance(self) -> None:
        assert "keystroke_constant_interval" in BEHAVIORAL_HTML

    def test_posts_to_api_behavior(self) -> None:
        assert "/api/behavior" in BEHAVIORAL_HTML


# ---------------------------------------------------------------------------
# Scoring engine — enhanced vectors
# ---------------------------------------------------------------------------


class TestScoringAutomation:
    """Classic automation artifact scoring."""

    def test_clean_no_signals(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "has_cdc_props": False, "user_agent": "Mozilla/5.0 Chrome/120",
             "is_swiftshader": False},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "clean"
        assert result["score"] == 100
        assert len(result["flags"]) == 0

    def test_flagged_webdriver(self) -> None:
        result = _score_signals(
            {"webdriver": True, "plugins_length": 3, "user_agent": "Chrome",
             "is_swiftshader": False},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"
        assert result["score"] == 0

    def test_flagged_cdc_props(self) -> None:
        result = _score_signals(
            {"webdriver": False, "has_cdc_props": True, "user_agent": "Chrome",
             "is_swiftshader": False, "plugins_length": 3, "mimetypes_length": 2},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"

    def test_flagged_headless_plugins(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 0, "mimetypes_length": 0,
             "user_agent": "Chrome", "is_swiftshader": False},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"

    def test_flagged_headless_ua(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Mozilla/5.0 HeadlessChrome/120", "is_swiftshader": False},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"


class TestScoringWebGL:
    """WebGL fingerprint vector scoring."""

    def test_flagged_swiftshader(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": True},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"
        assert "SwiftShader" in " ".join(result["flags"])

    def test_flagged_llvmpipe(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "webgl_renderer": "Mesa llvmpipe"},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"
        assert any("llvmpipe" in f for f in result["flags"])


class TestScoringPermissions:
    """Permissions API cross-check scoring."""

    def test_flagged_permission_mismatch(self) -> None:
        """Real mismatch: granted vs denied is a genuine inconsistency."""
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "notification_permission": "granted",
             "permissions_api_state": "denied"},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"
        assert any("mismatch" in f for f in result["flags"])

    def test_clean_permission_semantic_match(self) -> None:
        """Chromium returns 'default' for Notification but 'prompt' for
        permissions.query — these are semantically equivalent."""
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "notification_permission": "default",
             "permissions_api_state": "prompt"},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "clean"


class TestScoringHardware:
    """Hardware plausibility scoring."""

    def test_flagged_zero_cores(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "hardware_concurrency": 0},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"

    def test_flagged_too_many_cores(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "hardware_concurrency": 256},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"

    def test_flagged_excess_memory(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "device_memory": 16},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"

    def test_clean_normal_hardware(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "hardware_concurrency": 8, "device_memory": 8},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "clean"


class TestScoringTiming:
    """Interaction timing scoring."""

    def test_flagged_instant_interaction(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "first_interaction_ts": 10030, "page_load_ts": 10000},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "flagged"

    def test_clean_normal_interaction(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "first_interaction_ts": 15000, "page_load_ts": 10000},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "clean"


class TestScoringHeaders:
    """Request header scoring."""

    def test_flagged_missing_accept_language(self) -> None:
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False},
            {"has_accept_language": False},
        )
        assert result["verdict"] == "flagged"

    def test_flagged_soft_notification_denied(self) -> None:
        """Notification denied without prompt is a soft signal."""
        result = _score_signals(
            {"webdriver": False, "plugins_length": 3, "mimetypes_length": 2,
             "user_agent": "Chrome", "is_swiftshader": False,
             "notification_permission": "denied",
             "permissions_api_state": "denied"},
            {"has_accept_language": True},
        )
        assert result["verdict"] == "challenged"
        assert result["score"] == 40


class TestScoringMultipleFlags:
    """Multiple flags accumulate."""

    def test_multiple_hard_flags_still_flagged(self) -> None:
        result = _score_signals(
            {"webdriver": True, "plugins_length": 0, "mimetypes_length": 0,
             "user_agent": "HeadlessChrome", "is_swiftshader": True,
             "has_cdc_props": True},
            {"has_accept_language": False},
        )
        assert result["verdict"] == "flagged"
        assert result["score"] == 0
        assert len(result["flags"]) >= 5
