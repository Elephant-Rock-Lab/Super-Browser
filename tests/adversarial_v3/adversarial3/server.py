"""Controlled detection server for adversarial testing."""

from __future__ import annotations

import argparse
import json
import threading
import time
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


@dataclass
class RequestSignals:
    """Captured request signals."""
    header_order: list[str] = field(default_factory=list)
    headers: dict[str, str] = field(default_factory=dict)
    user_agent: str = ""
    has_accept_language: bool = False
    has_sec_ch_ua: bool = False


class _DetectionHandler(BaseHTTPRequestHandler):
    """HTTP handler for detection pages."""

    server_version = "ControlledDetectionTarget/2.0"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def _capture_signals(self) -> RequestSignals:
        header_order = list(self.headers.keys())
        headers = {k: v for k, v in self.headers.items()}
        return RequestSignals(
            header_order=header_order,
            headers=headers,
            user_agent=self.headers.get("User-Agent", ""),
            has_accept_language="Accept-Language" in self.headers,
            has_sec_ch_ua=any(k.lower().startswith("sec-ch-ua") for k in header_order),
        )

    def _send_html(self, content: str, status: int = 200) -> None:
        body = content.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, data: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            signals = self._capture_signals()
            self.server.request_log.append(signals)
            self._send_html(_DETECTION_HTML)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/verdict":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                client_signals = json.loads(raw)
            except json.JSONDecodeError:
                client_signals = {}

            request_signals = self.server.request_log[-1] if self.server.request_log else RequestSignals()
            verdict = _compute_verdict(client_signals, request_signals)
            self.server.last_verdict = verdict
            self._send_json(verdict)
            return
        self.send_response(404)
        self.end_headers()


_DETECTION_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Controlled Detection Target v2</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; }
    #status { background: #f5f5f5; padding: 20px; border-radius: 8px; margin-top: 20px; }
    .clean { color: #2e7d32; }
    .challenged { color: #f57c00; }
    .flagged { color: #c62828; }
    pre { overflow-x: auto; }
  </style>
</head>
<body>
  <h1>Controlled Detection Target v2</h1>
  <div id="status">Running detection probes...</div>
  <script>
  (function() {
    'use strict';

    async function collectSignals() {
      const signals = {};
      signals.webdriver = !!navigator.webdriver;
      signals.plugins_length = navigator.plugins ? navigator.plugins.length : -1;
      signals.mimetypes_length = navigator.mimeTypes ? navigator.mimeTypes.length : -1;
      signals.has_cdc_props = Object.keys(window).some(function(k) {
        return k.indexOf('cdc_') === 0 || k.indexOf('$cdc_') === 0;
      });
      signals.chrome_type = typeof window.chrome;
      signals.has_chrome_runtime = !!(window.chrome && window.chrome.runtime);
      try {
        const canvas = document.createElement('canvas');
        const gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (gl) {
          const info = gl.getExtension('WEBGL_debug_renderer_info');
          signals.webgl_renderer = info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : null;
        }
      } catch (e) {
        signals.webgl_renderer = null;
      }
      if (navigator.permissions && navigator.permissions.query) {
        try {
          const perm = await navigator.permissions.query({name: 'notifications'});
          signals.notification_permission = perm.state;
        } catch (e) {
          signals.notification_permission = 'error';
        }
      } else {
        signals.notification_permission = 'unsupported';
      }
      try {
        const c = document.createElement('canvas');
        c.width = 200; c.height = 200;
        const ctx = c.getContext('2d');
        ctx.fillStyle = '#FF0000';
        ctx.fillRect(0, 0, 100, 100);
        signals.canvas_dataurl_length = c.toDataURL().length;
      } catch (e) {
        signals.canvas_dataurl_length = 0;
      }
      signals.user_agent = navigator.userAgent;
      signals.languages = navigator.languages ? navigator.languages.join(',') : '';
      signals.page_load_ts = window.__sb_page_load_ts || Date.now();
      signals.first_interaction_ts = window.__sb_first_interaction_ts || null;
      return signals;
    }

    async function sendVerdict(signals) {
      try {
        const response = await fetch('/api/verdict', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify(signals)
        });
        const verdict = await response.json();
        window.__sb_verdict = verdict;
        const status = document.getElementById('status');
        const cssClass = verdict.verdict;
        status.innerHTML = '<pre class="' + cssClass + '">' + JSON.stringify(verdict, null, 2) + '</pre>';
      } catch (e) {
        document.getElementById('status').textContent = 'Error: ' + e.message;
      }
    }

    window.__sb_page_load_ts = Date.now();
    function markInteraction() {
      if (!window.__sb_first_interaction_ts) {
        window.__sb_first_interaction_ts = Date.now();
      }
    }
    window.addEventListener('mousemove', markInteraction, {once: true});
    window.addEventListener('mousedown', markInteraction, {once: true});
    window.addEventListener('keydown', markInteraction, {once: true});
    window.addEventListener('scroll', markInteraction, {once: true});
    window.addEventListener('touchstart', markInteraction, {once: true});

    collectSignals().then(sendVerdict);
  })();
  </script>
</body>
</html>
"""


def _compute_verdict(client: dict[str, Any], request: RequestSignals) -> dict[str, Any]:
    hard_flags: list[str] = []
    soft_flags: list[str] = []

    if client.get("webdriver"):
        hard_flags.append("navigator.webdriver=true")

    if client.get("has_cdc_props"):
        hard_flags.append("CDP automation artifact (cdc_ property)")

    ua = client.get("user_agent", "")
    if "HeadlessChrome" in ua:
        hard_flags.append("User-Agent contains HeadlessChrome")

    plugins_len = client.get("plugins_length", -1)
    mimetypes_len = client.get("mimetypes_length", -1)
    if plugins_len == 0 and mimetypes_len == 0:
        hard_flags.append("zero plugins and zero mimetypes")

    renderer = client.get("webgl_renderer", "")
    if renderer and "SwiftShader" in renderer:
        hard_flags.append("WebGL renderer is SwiftShader")

    if not request.has_accept_language:
        soft_flags.append("missing Accept-Language header")

    if not request.has_sec_ch_ua:
        soft_flags.append("missing sec-ch-ua headers")

    notif = client.get("notification_permission")
    if notif == "denied":
        soft_flags.append("notifications permission denied without prompt")

    first_interaction = client.get("first_interaction_ts")
    load_ts = client.get("page_load_ts")
    if first_interaction and load_ts:
        delta = first_interaction - load_ts
        if delta < 50:
            soft_flags.append("first interaction within " + str(delta) + "ms of load")

    canvas_len = client.get("canvas_dataurl_length", 0)
    if canvas_len < 500:
        soft_flags.append("canvas toDataURL suspiciously short")

    if hard_flags:
        verdict = "flagged"
        score = 0
    elif soft_flags:
        verdict = "challenged"
        score = max(20, 100 - len(soft_flags) * 15)
    else:
        verdict = "clean"
        score = 100

    return {
        "verdict": verdict,
        "score": score,
        "hard_flags": hard_flags,
        "soft_flags": soft_flags,
        "client_signals": {k: v for k, v in client.items() if k != "page_load_ts"},
    }


class ControlledDetectionServer:
    """Context-manager wrapper for the detection server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "ControlledDetectionServer":
        self._server = ThreadingHTTPServer((self._host, self._port), _DetectionHandler)
        self._server.request_log = []
        self._server.last_verdict = None
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        if self._server:
            self._server.shutdown()
            self._server.server_close()
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def base_url(self) -> str:
        assert self._server is not None
        port = self._server.server_address[1]
        return "http://" + self._host + ":" + str(port)

    @property
    def last_verdict(self) -> dict[str, Any] | None:
        assert self._server is not None
        return self._server.last_verdict

    @property
    def request_log(self) -> list[RequestSignals]:
        assert self._server is not None
        return self._server.request_log


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Controlled detection target server")
    parser.add_argument("--port", type=int, default=8901)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    with ControlledDetectionServer(host=args.host, port=args.port) as srv:
        print("Controlled detection target running at " + srv.base_url)
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("")
            print("Stopped.")
