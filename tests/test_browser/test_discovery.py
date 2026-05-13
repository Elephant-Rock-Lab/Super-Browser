"""Tests for BrowserDiscovery."""

import os
from unittest.mock import patch

from super_browser.browser import BrowserDiscovery


class TestDiscovery:
    def test_no_browser_running(self):
        result = BrowserDiscovery.discover(timeout=0.1, interval=0.05)
        assert result.found is False
        assert result.ws_url is None

    def test_ws_url_override(self):
        result = BrowserDiscovery.discover(
            timeout=0.1,
            ws_url_override="ws://localhost:9222/devtools/browser/abc",
        )
        assert result.found is True
        assert result.ws_url == "ws://localhost:9222/devtools/browser/abc"

    def test_env_var_override(self):
        with patch.dict(os.environ, {"SB_CDP_WS": "ws://localhost:9333/test"}):
            result = BrowserDiscovery.discover(timeout=0.1)
            assert result.found is True
            assert result.ws_url == "ws://localhost:9333/test"

    def test_reads_devtools_active_port(self, tmp_path):
        profile = tmp_path / "Chrome" / "User Data"
        profile.mkdir(parents=True)
        port_file = profile / "DevToolsActivePort"
        port_file.write_text("9222\n/devtools/browser/abc123\n")

        with patch("super_browser.browser.discovery._PROFILE_PATHS", [profile]):
            result = BrowserDiscovery.discover(timeout=1.0, interval=0.1)
            assert result.found is True
            assert "9222" in result.ws_url
            assert result.profile_path == str(profile)

    def test_timeout_exceeded(self):
        result = BrowserDiscovery.discover(timeout=0.05, interval=0.02)
        assert result.found is False
        assert result.discovery_time_ms > 0

    def test_result_serialization(self):
        result = BrowserDiscovery.discover(
            timeout=0.1,
            ws_url_override="ws://test",
        )
        assert isinstance(result.found, bool)
        assert isinstance(result.discovery_time_ms, float)
