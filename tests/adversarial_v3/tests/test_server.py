"""Tests for the controlled detection server.

Verifies: startup, request handling, verdict computation, signal capture.
"""

from __future__ import annotations

import json
import urllib.request

from adversarial3.server import ControlledDetectionServer, RequestSignals, _compute_verdict


class TestComputeVerdict:
    """Test verdict computation logic."""

    def test_clean_no_flags(self):
        client = {"webdriver": False, "plugins_length": 3, "mimetypes_length": 4,
                  "canvas_dataurl_length": 5000, "user_agent": "Chrome/120"}
        request = RequestSignals(has_accept_language=True, has_sec_ch_ua=True)
        verdict = _compute_verdict(client, request)
        assert verdict["verdict"] == "clean"
        assert verdict["score"] == 100
        assert len(verdict["hard_flags"]) == 0
        assert len(verdict["soft_flags"]) == 0

    def test_flagged_webdriver(self):
        client = {"webdriver": True, "plugins_length": 3}
        request = RequestSignals()
        verdict = _compute_verdict(client, request)
        assert verdict["verdict"] == "flagged"
        assert verdict["score"] == 0
        assert "navigator.webdriver=true" in verdict["hard_flags"]

    def test_flagged_headless_ua(self):
        client = {"user_agent": "HeadlessChrome/120.0.0.0", "plugins_length": 3}
        request = RequestSignals()
        verdict = _compute_verdict(client, request)
        assert verdict["verdict"] == "flagged"
        assert "HeadlessChrome" in str(verdict["hard_flags"])

    def test_challenged_soft_flags(self):
        client = {"webdriver": False, "plugins_length": 3, "mimetypes_length": 4}
        request = RequestSignals(has_accept_language=False, has_sec_ch_ua=False)
        verdict = _compute_verdict(client, request)
        assert verdict["verdict"] == "challenged"
        assert verdict["score"] < 100
        assert len(verdict["soft_flags"]) > 0

    def test_zero_plugins_and_mimetypes(self):
        client = {"webdriver": False, "plugins_length": 0, "mimetypes_length": 0}
        request = RequestSignals()
        verdict = _compute_verdict(client, request)
        assert verdict["verdict"] == "flagged"
        assert "zero plugins" in str(verdict["hard_flags"])

    def test_swiftshader_renderer(self):
        client = {"webdriver": False, "webgl_renderer": "SwiftShader", "plugins_length": 3}
        request = RequestSignals()
        verdict = _compute_verdict(client, request)
        assert verdict["verdict"] == "flagged"
        assert "SwiftShader" in str(verdict["hard_flags"])

    def test_fast_interaction(self):
        client = {
            "webdriver": False,
            "plugins_length": 3,
            "page_load_ts": 1000,
            "first_interaction_ts": 1020,
        }
        request = RequestSignals()
        verdict = _compute_verdict(client, request)
        assert verdict["verdict"] == "challenged"
        assert "20ms" in str(verdict["soft_flags"])

    def test_cdc_props(self):
        client = {"webdriver": False, "has_cdc_props": True, "plugins_length": 3}
        request = RequestSignals()
        verdict = _compute_verdict(client, request)
        assert verdict["verdict"] == "flagged"
        assert "cdc_" in str(verdict["hard_flags"])


class TestControlledServer:
    """Test the HTTP server."""

    def test_server_starts(self):
        with ControlledDetectionServer() as server:
            assert server.base_url.startswith("http://127.0.0.1:")
            port = int(server.base_url.split(":")[-1])
            assert 1024 < port < 65535  # auto-assigned ephemeral port

    def test_server_serves_html(self):
        with ControlledDetectionServer() as server:
            req = urllib.request.Request(server.base_url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert resp.status == 200
                body = resp.read().decode()
                assert "Controlled Detection Target" in body
                assert "navigator.webdriver" in body

    def test_request_log_populated(self):
        with ControlledDetectionServer() as server:
            req = urllib.request.Request(
                server.base_url,
                headers={"User-Agent": "TestAgent/1.0"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                _ = resp.read()

            assert len(server.request_log) == 1
            assert server.request_log[0].user_agent == "TestAgent/1.0"

    def test_verdict_endpoint(self):
        with ControlledDetectionServer() as server:
            # First GET to populate request log
            req = urllib.request.Request(server.base_url)
            with urllib.request.urlopen(req, timeout=5):
                pass

            # POST verdict
            data = json.dumps({
                "webdriver": False,
                "plugins_length": 3,
                "mimetypes_length": 4,
                "user_agent": "Mozilla/5.0",
                "canvas_dataurl_length": 5000,
            }).encode()
            req = urllib.request.Request(
                f"{server.base_url}/api/verdict",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                verdict = json.load(resp)
                # urllib doesn't send Accept-Language/sec-ch-ua by default,
                # so those become soft flags. Verify hard flags are empty
                # and verdict is not flagged.
                assert verdict["verdict"] in ("clean", "challenged")
                assert len(verdict["hard_flags"]) == 0
                assert verdict["score"] >= 20

    def test_server_last_verdict(self):
        with ControlledDetectionServer() as server:
            # GET then POST
            req = urllib.request.Request(server.base_url)
            with urllib.request.urlopen(req, timeout=5):
                pass

            data = json.dumps({"webdriver": True, "plugins_length": 0}).encode()
            req = urllib.request.Request(
                f"{server.base_url}/api/verdict",
                data=data,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=5):
                pass

            assert server.last_verdict is not None
            assert server.last_verdict["verdict"] == "flagged"
