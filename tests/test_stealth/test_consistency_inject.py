"""Tests for BATCH-30/TASK-03 — Inject Pipeline & StealthManager Integration.

TEST-30-03-01: Inject JS generation — non-empty string output from valid matrix
TEST-30-03-02: JS syntax validity — no SyntaxError when parsing
TEST-30-03-03: Matrix→inject round-trip — inject contains exact user agent string
TEST-30-03-04: Fetch.fulfillRequest delivery — body-splice adds script tag to HTML head
TEST-30-03-05: CSP header stripping — script-src directive removed/relaxed
TEST-30-03-06: addInitScript fallback — about:blank handled without error
TEST-30-03-07: Backward compat — consistency.enabled=False uses old path
TEST-30-03-08: Runtime.enable ban — CDPBridge.send("Runtime.enable") raises ForbiddenCdpMethodError
TEST-30-03-09: Malformed matrix — inject generation handles gracefully
"""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.stealth.consistency import (
    FingerprintMatrix,
    derive_matrix,
    generate_inject,
)
from super_browser.stealth.consistency.inject_delivery import InjectDelivery
from super_browser.stealth.profiles import list_profiles, load_profile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_matrix(**overrides) -> FingerprintMatrix:
    """Create a minimal valid FingerprintMatrix for tests."""
    defaults = dict(
        profile_id="test-profile",
        seed="test-seed",
        derived_at="2026-01-01T00:00:00Z",
        consistency_engine_version="0.1.0",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        platform="Win32",
        hardware_concurrency=8,
        device_memory=8,
        languages=("en-US", "en"),
        locale="en-US",
        timezone="America/New_York",
        webdriver=False,
        sec_ch_ua='"Chromium";v="131", "Google Chrome";v="131"',
        sec_ch_ua_platform="Windows",
        sec_ch_ua_platform_version="15.0.0",
        sec_ch_ua_arch="x86",
        sec_ch_ua_bitness="64",
        sec_ch_ua_mobile="?0",
        sec_ch_ua_model="",
        screen_width=1920,
        screen_height=1080,
        screen_avail_width=1920,
        screen_avail_height=1040,
        color_depth=24,
        pixel_depth=24,
        device_pixel_ratio=1,
        viewport_inner_width=1920,
        viewport_inner_height=1040,
        viewport_outer_width=1920,
        viewport_outer_height=1040,
        screen_orientation_type="landscape-primary",
        screen_orientation_angle=0,
        webgl_unmasked_vendor="Google Inc. (NVIDIA)",
        webgl_unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3070, D3D11)",
        webgl_max_texture_size=16384,
        webgl_max_color_attachments=8,
        webgl_extensions=("EXT_color_buffer_float",),
        audio_context_sample_rate=48000,
        audio_worklet_latency=0.04,
        audio_destination_max_channel_count=2,
        fonts=("Arial", "Consolas", "Courier New"),
        behavior_hand="right",
        behavior_tremor=0.18,
        behavior_wpm=60,
        behavior_scroll_style="smooth",
        connection_effective_type="4g",
        connection_downlink=10.0,
        connection_rtt=50,
        connection_save_data=False,
        storage_quota=0,
        storage_usage=0,
        navigator_vendor="Google Inc.",
        navigator_app_version="5.0 (Windows NT 10.0; Win64; x64)",
        navigator_app_codename="Mozilla",
        navigator_product="Gecko",
        navigator_cookie_enabled=True,
        navigator_max_touch_points=0,
    )
    defaults.update(overrides)
    return FingerprintMatrix(**defaults)


# ===================================================================
# TEST-30-03-01: Inject JS generation — non-empty output
# ===================================================================


class TestInjectGeneration:
    """generate_inject produces non-empty JS from a valid matrix."""

    def test_non_empty_output(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        assert isinstance(js, str)
        assert len(js) > 100

    def test_iife_wrapper(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        assert js.startswith("(function()")
        assert js.endswith("})();")

    def test_idempotency_guard(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        assert "window.__sb_inject_marker" in js
        assert "if (window.__sb_inject_marker) return;" in js

    def test_marker_set_at_end(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        assert "window.__sb_inject_marker = true;" in js


# ===================================================================
# TEST-30-03-02: JS syntax validity — no SyntaxError when parsing
# ===================================================================


class TestJsSyntaxValidity:
    """The generated JS parses without SyntaxError."""

    def test_no_syntax_error(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        # Use Python's subprocess to check with node if available,
        # otherwise parse manually.
        import subprocess

        try:
            result = subprocess.run(
                ["node", "-e", js],
                capture_output=True,
                text=True,
                timeout=5,
            )
            # Node should not report a syntax error.
            assert "SyntaxError" not in result.stderr, (
                f"JS SyntaxError: {result.stderr}"
            )
        except FileNotFoundError:
            # Node.js not available — do a heuristic check instead.
            # Verify balanced braces and parentheses.
            assert js.count("{") == js.count("}"), "Unbalanced braces"
            assert js.count("(") == js.count(")"), "Unbalanced parentheses"

    def test_valid_json_embeds(self) -> None:
        """All embedded values are valid JSON strings."""
        matrix = _make_matrix()
        js = generate_inject(matrix)
        # The UA string must appear as a valid JSON-quoted string.
        assert json.dumps(matrix.user_agent) in js


# ===================================================================
# TEST-30-03-03: Matrix→inject round-trip — inject contains exact UA
# ===================================================================


class TestMatrixInjectRoundTrip:
    """The inject contains the exact user-agent string from the matrix."""

    def test_inject_contains_user_agent(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        assert matrix.user_agent in js

    def test_inject_contains_platform(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        assert matrix.platform in js

    def test_inject_contains_webgl_vendor(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        assert matrix.webgl_unmasked_vendor in js

    def test_inject_contains_timezone(self) -> None:
        matrix = _make_matrix()
        js = generate_inject(matrix)
        assert matrix.timezone in js

    def test_inject_contains_all_fonts(self) -> None:
        matrix = _make_matrix(fonts=("Arial", "Consolas", "Helvetica"))
        js = generate_inject(matrix)
        for font in matrix.fonts:
            assert font in js

    def test_inject_contains_hardware_concurrency(self) -> None:
        matrix = _make_matrix(hardware_concurrency=16)
        js = generate_inject(matrix)
        assert "16" in js

    def test_inject_contains_device_memory(self) -> None:
        matrix = _make_matrix(device_memory=4)
        js = generate_inject(matrix)
        assert "4" in js

    def test_inject_contains_screen_dimensions(self) -> None:
        matrix = _make_matrix(screen_width=2560, screen_height=1440)
        js = generate_inject(matrix)
        assert "2560" in js
        assert "1440" in js

    def test_round_trip_all_profiles(self) -> None:
        """Every profile produces inject containing its user-agent."""
        for pid in list_profiles():
            profile = load_profile(pid)
            matrix = derive_matrix(profile, "round-trip-test")
            js = generate_inject(matrix)
            assert matrix.user_agent in js, f"Profile {pid}: UA not in inject"


# ===================================================================
# TEST-30-03-04: Fetch.fulfillRequest delivery — body-splice
# ===================================================================


class TestFetchFulfillDelivery:
    """Body-splice adds <script> tag to HTML <head>."""

    def test_splice_adds_script_to_head(self) -> None:
        delivery = InjectDelivery("window.__test = 42;")
        html = "<html><head></head><body>Hello</body></html>"
        result = delivery._splice_script(html)
        assert "<script>" in result
        assert "window.__test = 42;" in result
        # Script must be inside <head>
        head_end = result.find("</head>")
        script_pos = result.find("<script>")
        assert script_pos < head_end

    def test_splice_preserves_existing_head_content(self) -> None:
        delivery = InjectDelivery("window.__x = 1;")
        html = '<html><head><title>Test</title></head><body></body></html>'
        result = delivery._splice_script(html)
        assert "<title>Test</title>" in result
        assert "window.__x = 1;" in result

    def test_splice_no_head_uses_html_fallback(self) -> None:
        delivery = InjectDelivery("window.__y = 2;")
        html = "<html><body>No head</body></html>"
        result = delivery._splice_script(html)
        assert "<script>" in result
        assert "window.__y = 2;" in result

    def test_splice_no_html_wraps_entirely(self) -> None:
        delivery = InjectDelivery("window.__z = 3;")
        html = "Just some text"
        result = delivery._splice_script(html)
        assert "<html>" in result
        assert "<script>" in result

    def test_splice_empty_payload_returns_original(self) -> None:
        delivery = InjectDelivery("")
        html = "<html><head></head><body>Hello</body></html>"
        result = delivery._splice_script(html)
        assert result == html


# ===================================================================
# TEST-30-03-05: CSP header stripping
# ===================================================================


class TestCspHeaderStripping:
    """CSP headers are stripped from intercepted responses."""

    def test_csp_headers_removed(self) -> None:
        headers = [
            {"name": "content-type", "value": "text/html"},
            {"name": "content-security-policy", "value": "default-src 'self'"},
            {"name": "content-security-policy-report-only", "value": "script-src 'none'"},
        ]
        result = InjectDelivery._strip_csp_headers(headers)
        assert len(result) == 1
        assert result[0]["name"] == "content-type"

    def test_no_csp_headers_unchanged(self) -> None:
        headers = [
            {"name": "content-type", "value": "text/html"},
            {"name": "cache-control", "value": "no-cache"},
        ]
        result = InjectDelivery._strip_csp_headers(headers)
        assert len(result) == 2

    def test_case_insensitive_matching(self) -> None:
        headers = [
            {"name": "Content-Security-Policy", "value": "default-src 'self'"},
            {"name": "Content-Type", "value": "text/html"},
        ]
        result = InjectDelivery._strip_csp_headers(headers)
        assert len(result) == 1
        assert result[0]["name"] == "Content-Type"

    def test_empty_headers(self) -> None:
        result = InjectDelivery._strip_csp_headers([])
        assert result == []


# ===================================================================
# TEST-30-03-06: addInitScript fallback — about:blank handled
# ===================================================================


class TestAddInitScriptFallback:
    """addInitScript fallback handles about:blank without error."""

    def test_install_with_mock_page(self) -> None:
        delivery = InjectDelivery("window.__blank = true;")

        mock_cdp = MagicMock()
        mock_cdp.send = AsyncMock(return_value=MagicMock(ok=True, data={}))

        mock_page = MagicMock()
        mock_page.add_init_script = AsyncMock()

        async def _test():
            await delivery.install(mock_cdp, mock_page)
            # addInitScript should have been called.
            mock_page.add_init_script.assert_called_once_with("window.__blank = true;")

        asyncio.run(_test())

    def test_install_without_page_no_error(self) -> None:
        delivery = InjectDelivery("window.__test = 1;")

        mock_cdp = MagicMock()
        mock_cdp.send = AsyncMock(return_value=MagicMock(ok=True, data={}))

        async def _test():
            await delivery.install(mock_cdp, None)
            # Should not raise.

        asyncio.run(_test())

    def test_update_payload(self) -> None:
        delivery = InjectDelivery("old")
        delivery._installed = True

        mock_page = MagicMock()
        mock_page.add_init_script = AsyncMock()
        delivery._page = mock_page

        async def _test():
            await delivery.update_payload("new payload")
            assert delivery._js_payload == "new payload"

        asyncio.run(_test())


# ===================================================================
# TEST-30-03-07: Backward compat — consistency.enabled=False uses old path
# ===================================================================


class TestBackwardCompat:
    """With consistency disabled, legacy UA pool + init scripts are used."""

    def test_legacy_path_used_when_disabled(self) -> None:
        from super_browser.stealth.manager import StealthManager
        from super_browser.stealth.types import StealthConfig

        cfg = StealthConfig(custom_init_scripts=("console.log('legacy');",))
        fake_page = MagicMock()
        fake_page.route = AsyncMock()

        mgr = StealthManager(config=cfg, page=fake_page)

        async def _test():
            # Patch _detect_consistency_config to return disabled config
            with patch(
                "super_browser.stealth.manager._detect_consistency_config",
                return_value=None,
            ):
                await mgr.initialize()
                # Should have used legacy path — route registered.
                fake_page.route.assert_called_once()

        asyncio.run(_test())

    def test_no_consistency_config_uses_legacy(self) -> None:
        from super_browser.stealth.manager import StealthManager
        from super_browser.stealth.types import StealthConfig

        fake_page = MagicMock()
        fake_page.route = AsyncMock()

        cfg = StealthConfig(custom_init_scripts=("console.log('x');",))
        mgr = StealthManager(config=cfg, page=fake_page)

        async def _test():
            with patch(
                "super_browser.stealth.manager._detect_consistency_config",
                return_value=None,
            ):
                await mgr.initialize()
                assert mgr._inject_delivery is None

        asyncio.run(_test())


# ===================================================================
# TEST-30-03-08: Runtime.enable ban — CDPBridge.send raises
# ===================================================================


class TestRuntimeEnableBan:
    """CDPBridge.send('Runtime.enable') raises ForbiddenCdpMethodError."""

    def test_runtime_enable_banned(self) -> None:
        from super_browser.browser.cdp import CDPBridge, ForbiddenCdpMethodError
        from super_browser.browser.config import SessionConfig

        mock_session = MagicMock()
        config = SessionConfig()
        bridge = CDPBridge(mock_session, config)

        async def _test():
            with pytest.raises(ForbiddenCdpMethodError) as exc_info:
                await bridge.send("Runtime.enable")
            assert exc_info.value.method == "Runtime.enable"

        asyncio.run(_test())

    def test_page_create_isolated_world_banned(self) -> None:
        from super_browser.browser.cdp import CDPBridge, ForbiddenCdpMethodError
        from super_browser.browser.config import SessionConfig

        mock_session = MagicMock()
        config = SessionConfig()
        bridge = CDPBridge(mock_session, config)

        async def _test():
            with pytest.raises(ForbiddenCdpMethodError) as exc_info:
                await bridge.send("Page.createIsolatedWorld")
            assert exc_info.value.method == "Page.createIsolatedWorld"

        asyncio.run(_test())

    def test_runtime_evaluate_allowed(self) -> None:
        """Runtime.evaluate is NOT banned — only Runtime.enable is."""
        from super_browser.browser.cdp import CDPBridge
        from super_browser.browser.config import SessionConfig

        mock_session = MagicMock()
        mock_session.send = AsyncMock(return_value={"result": {"value": 42}})
        config = SessionConfig()
        bridge = CDPBridge(mock_session, config)

        async def _test():
            result = await bridge.send("Runtime.evaluate", {
                "expression": "1+1",
                "returnByValue": True,
            })
            # Should not raise — Runtime.evaluate is allowed.
            assert result.ok

        asyncio.run(_test())

    def test_forbidden_error_message(self) -> None:
        from super_browser.browser.cdp import ForbiddenCdpMethodError

        err = ForbiddenCdpMethodError("Runtime.enable")
        assert "Runtime.enable" in str(err)
        assert "forbidden" in str(err).lower()


# ===================================================================
# TEST-30-03-09: Malformed matrix — inject generation handles gracefully
# ===================================================================


class TestMalformedMatrix:
    """Inject generation handles bad inputs gracefully."""

    def test_non_matrix_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="FingerprintMatrix"):
            generate_inject("not a matrix")  # type: ignore

    def test_dict_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="FingerprintMatrix"):
            generate_inject({"user_agent": "test"})  # type: ignore

    def test_none_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="FingerprintMatrix"):
            generate_inject(None)  # type: ignore

    def test_matrix_with_empty_strings(self) -> None:
        """Matrix with empty strings still generates valid JS."""
        matrix = _make_matrix(
            user_agent="",
            platform="",
            webgl_unmasked_vendor="",
            webgl_unmasked_renderer="",
            timezone="",
            fonts=(),
        )
        js = generate_inject(matrix)
        assert isinstance(js, str)
        assert len(js) > 50

    def test_matrix_with_unicode_values(self) -> None:
        """Matrix with Unicode values generates valid JS."""
        matrix = _make_matrix(
            webgl_unmasked_vendor="NVIDIA\u00ae Corporation\u2122",
        )
        js = generate_inject(matrix)
        # json.dumps escapes Unicode characters; verify the escaped form.
        assert json.dumps(matrix.webgl_unmasked_vendor) in js
