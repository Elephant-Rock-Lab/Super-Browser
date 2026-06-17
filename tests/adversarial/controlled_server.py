#!/usr/bin/env python3
"""Controlled bot-detection target for Tier 3 adversarial tests.

Self-contained HTTP server implementing real-world bot-detection
heuristics. Enhanced version with WebGL, canvas noise, permissions
cross-check, and behavioral timing vectors.

Run standalone for debugging::

    python tests/adversarial/controlled_server.py --port 8901
"""

from __future__ import annotations

import argparse
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------------------
# Detection page — client-side checks post results to /api/verdict
# ---------------------------------------------------------------------------

DETECTION_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Controlled Detection Target</title>
</head>
<body>
  <h1 id="title">Controlled Detection Target</h1>
  <div id="status">running checks...</div>
  <script>
  (function () {
    function detect() {
      var signals = {};

      // --- Tier 1: Basic automation artifacts ---

      // 1. navigator.webdriver
      signals.webdriver = !!navigator.webdriver;

      // 2. Headless indicator surface — plugin/mimetype length
      signals.plugins_length = navigator.plugins ? navigator.plugins.length : -1;
      signals.mimetypes_length = navigator.mimeTypes ? navigator.mimeTypes.length : -1;

      // 3. CDP Runtime.enable artifact — cdc_ properties
      signals.has_cdc_props = Object.keys(window).some(function (k) {
        return k.indexOf('cdc_') === 0 || k.indexOf('$cdc_') === 0;
      });

      // 4. Chrome object structure
      signals.has_chrome_object = typeof window.chrome === 'object' && window.chrome !== null;

      // --- Tier 2: WebGL fingerprint analysis ---

      // 5. WebGL renderer — SwiftShader = headless indicator
      signals.webgl_vendor = 'unknown';
      signals.webgl_renderer = 'unknown';
      signals.is_swiftshader = false;
      try {
        var canvas = document.createElement('canvas');
        var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
        if (gl) {
          var dbgInfo = gl.getExtension('WEBGL_debug_renderer_info');
          if (dbgInfo) {
            signals.webgl_vendor = gl.getParameter(dbgInfo.UNMASKED_VENDOR_WEBGL) || 'unknown';
            signals.webgl_renderer = gl.getParameter(dbgInfo.UNMASKED_RENDERER_WEBGL) || 'unknown';
            var rendererLower = signals.webgl_renderer.toLowerCase();
            signals.is_swiftshader = rendererLower.indexOf('swiftshader') >= 0;
          }
        }
      } catch (e) {}

      // --- Tier 3: Canvas noise verification ---
      // Draw a known pattern and hash it. If canvas noise injection is
      // active, the hash should differ from the headless baseline.
      signals.canvas_hash = 'none';
      signals.canvas_data_length = 0;
      try {
        var c = document.createElement('canvas');
        c.width = 200;
        c.height = 50;
        var ctx = c.getContext('2d');
        ctx.textBaseline = 'top';
        ctx.font = '14px Arial';
        ctx.fillStyle = '#f60';
        ctx.fillRect(0, 0, 200, 50);
        ctx.fillStyle = '#069';
        ctx.fillText('SuperBrowser Detection Test', 2, 15);
        ctx.fillStyle = 'rgba(102, 204, 0, 0.7)';
        ctx.fillText('SuperBrowser Detection Test', 4, 17);
        var dataUrl = c.toDataURL();
        signals.canvas_data_length = dataUrl.length;
        // Simple hash for comparison
        var hash = 0;
        for (var i = 0; i < dataUrl.length; i++) {
          hash = ((hash << 5) - hash + dataUrl.charCodeAt(i)) | 0;
        }
        signals.canvas_hash = hash;
      } catch (e) {}

      // --- Tier 4: Permissions API cross-check ---

      // 6. Notification.permission vs permissions.query mismatch
      signals.notification_permission = Notification.permission;
      signals.permissions_api_state = null;

      if (navigator.permissions && navigator.permissions.query) {
        navigator.permissions.query({name: 'notifications'}).then(function (p) {
          signals.permissions_api_state = p.state;
          signals.permissions_checked = true;
          finish(signals);
        }).catch(function () {
          signals.permissions_checked = false;
          finish(signals);
        });
      } else {
        signals.permissions_checked = false;
        finish(signals);
      }
    }

    var finished = false;
    function finish(signals) {
      if (finished) return;
      finished = true;
      signals.user_agent = navigator.userAgent;
      signals.languages = navigator.languages ? navigator.languages.join(',') : '';
      signals.first_interaction_ts = window.__sb_first_interaction_ts || null;
      signals.page_load_ts = window.__sb_page_load_ts;
      signals.hardware_concurrency = navigator.hardwareConcurrency || -1;
      signals.device_memory = navigator.deviceMemory || -1;

      fetch('/api/verdict', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(signals)
      }).then(function (r) { return r.json(); }).then(function (verdict) {
        document.getElementById('status').textContent = JSON.stringify(verdict);
        window.__sb_verdict = verdict;
      });
    }

    window.__sb_page_load_ts = Date.now();
    window.addEventListener('mousemove', function once() {
      if (!window.__sb_first_interaction_ts) {
        window.__sb_first_interaction_ts = Date.now();
      }
    }, {once: true});
    window.addEventListener('mousedown', function once() {
      if (!window.__sb_first_interaction_ts) {
        window.__sb_first_interaction_ts = Date.now();
      }
    }, {once: true});

    detect();
  })();
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Behavioral analysis page — records mouse/keyboard timing
# ---------------------------------------------------------------------------

BEHAVIORAL_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Behavioral Analysis Target</title>
</head>
<body>
  <h1 id="title">Behavioral Analysis Target</h1>
  <input id="input-field" type="text" placeholder="Type here" style="width:300px;height:40px;font-size:16px;">
  <div id="status">Collecting behavioral data...</div>
  <script>
  (function () {
    var mouseEvents = [];
    var keyEvents = [];
    var collecting = true;

    document.addEventListener('mousemove', function (e) {
      if (!collecting) return;
      mouseEvents.push({
        x: e.clientX,
        y: e.clientY,
        ts: performance.now()
      });
      // Keep only last 100 events
      if (mouseEvents.length > 100) mouseEvents.shift();
    });

    var input = document.getElementById('input-field');
    input.addEventListener('keydown', function (e) {
      if (!collecting) return;
      keyEvents.push({
        key: e.key,
        ts: performance.now()
      });
    });

    // Stop after 3 seconds and analyze
    setTimeout(function () {
      collecting = false;

      var analysis = analyzeBehavior(mouseEvents, keyEvents);
      window.__sb_behavioral = analysis;

      document.getElementById('status').textContent = JSON.stringify(analysis);

      fetch('/api/behavior', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(analysis)
      }).catch(function () {});
    }, 3000);

    function analyzeBehavior(mouse, keys) {
      var result = {};

      // Mouse trajectory analysis
      result.mouse_events = mouse.length;
      result.mouse_straight_line = false;
      result.mouse_constant_speed = false;

      if (mouse.length >= 3) {
        // Check if all points are colinear (straight line)
        var allLinear = true;
        for (var i = 2; i < mouse.length; i++) {
          var dx1 = mouse[i-1].x - mouse[i-2].x;
          var dy1 = mouse[i-1].y - mouse[i-2].y;
          var dx2 = mouse[i].x - mouse[i-1].x;
          var dy2 = mouse[i].y - mouse[i-1].y;
          var cross = dx1 * dy2 - dy1 * dx2;
          if (Math.abs(cross) > 0.5) {
            allLinear = false;
            break;
          }
        }
        result.mouse_straight_line = allLinear;

        // Check constant speed (all intervals within 2ms of each other)
        if (mouse.length >= 4) {
          var intervals = [];
          for (var i = 1; i < mouse.length; i++) {
            intervals.push(mouse[i].ts - mouse[i-1].ts);
          }
          var mean = intervals.reduce(function (a, b) { return a + b; }, 0) / intervals.length;
          var variance = intervals.reduce(function (s, v) { return s + (v - mean) * (v - mean); }, 0) / intervals.length;
          result.mouse_interval_variance = Math.round(variance * 100) / 100;
          result.mouse_constant_speed = variance < 0.5;
        }
      }

      // Keystroke timing analysis
      result.key_events = keys.length;
      result.keystroke_constant_interval = false;

      if (keys.length >= 3) {
        var kIntervals = [];
        for (var i = 1; i < keys.length; i++) {
          kIntervals.push(keys[i].ts - keys[i-1].ts);
        }
        var kMean = kIntervals.reduce(function (a, b) { return a + b; }, 0) / kIntervals.length;
        var kVariance = kIntervals.reduce(function (s, v) { return s + (v - kMean) * (v - kMean); }, 0) / kIntervals.length;
        result.keystroke_interval_variance = Math.round(kVariance * 100) / 100;
        result.keystroke_constant_interval = kVariance < 1.0;
      }

      // Overall verdict
      var botSignals = 0;
      if (result.mouse_straight_line) botSignals++;
      if (result.mouse_constant_speed) botSignals++;
      if (result.keystroke_constant_interval) botSignals++;
      if (mouse.length === 0) botSignals++;
      if (keys.length === 0 && result.mouse_events === 0) botSignals++;

      result.bot_signals = botSignals;
      result.verdict = botSignals >= 2 ? 'flagged' : (botSignals >= 1 ? 'challenged' : 'clean');
      result.score = Math.max(0, 100 - botSignals * 30);

      return result;
    }
  })();
  </script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Server handler
# ---------------------------------------------------------------------------

class _Handler(BaseHTTPRequestHandler):
    server_version = "ControlledDetectionTarget/2.0"

    def log_message(self, fmt: str, *args) -> None:
        pass

    def _capture_request_signals(self) -> dict:
        header_names = list(self.headers.keys())
        return {
            "header_order": header_names,
            "has_sec_ch_ua": any(h.lower().startswith("sec-ch-ua") for h in header_names),
            "has_accept_language": "Accept-Language" in self.headers,
            "user_agent_header": self.headers.get("User-Agent", ""),
            "connection_header": self.headers.get("Connection", ""),
        }

    def do_GET(self) -> None:
        if self.path in ("/", "/index.html"):
            request_signals = self._capture_request_signals()
            self.server.request_log.append(request_signals)  # type: ignore[attr-defined]
            body = DETECTION_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/behavioral":
            body = BEHAVIORAL_HTML.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self) -> None:
        if self.path == "/api/verdict":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                signals = json.loads(raw)
            except json.JSONDecodeError:
                signals = {}

            verdict = _score_signals(
                signals,
                self.server.request_log[-1] if self.server.request_log else {}  # type: ignore[attr-defined]
            )
            self.server.last_verdict = verdict  # type: ignore[attr-defined]

            body = json.dumps(verdict).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path == "/api/behavior":
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                data = {}
            self.server.last_behavior = data  # type: ignore[attr-defined]
            body = json.dumps({"ok": True}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


# ---------------------------------------------------------------------------
# Signal scoring engine
# ---------------------------------------------------------------------------

def _score_signals(client_signals: dict, request_signals: dict) -> dict:
    """Apply documented, public-domain bot heuristics."""
    flags: list[str] = []

    # --- Automation artifacts (hard) ---

    if client_signals.get("webdriver"):
        flags.append("navigator.webdriver=true")

    if client_signals.get("has_cdc_props"):
        flags.append("CDP automation artifact (cdc_ property) present")

    plugins_len = client_signals.get("plugins_length", -1)
    mimetypes_len = client_signals.get("mimetypes_length", -1)
    if plugins_len == 0 and mimetypes_len == 0:
        flags.append("zero plugins and zero mimetypes (classic headless signature)")

    ua = client_signals.get("user_agent", "")
    if "HeadlessChrome" in ua:
        flags.append("User-Agent contains HeadlessChrome token")

    if not request_signals.get("has_accept_language"):
        flags.append("missing Accept-Language header")

    # --- WebGL fingerprint (hard) ---

    if client_signals.get("is_swiftshader"):
        flags.append("WebGL renderer is SwiftShader (headless indicator)")

    webgl_renderer = client_signals.get("webgl_renderer", "").lower()
    if "mesa" in webgl_renderer and "llvmpipe" in webgl_renderer:
        flags.append("WebGL renderer is llvmpipe (software rendering)")

    # --- Permissions API cross-check (soft) ---

    notif_perm = client_signals.get("notification_permission")
    perm_state = client_signals.get("permissions_api_state")
    # Normalize: Chromium uses "default" for Notification.permission
    # but "prompt" for permissions.query — these are semantically equivalent.
    _PERM_MAP = {"default": "prompt", "granted": "granted", "denied": "denied"}
    notif_norm = _PERM_MAP.get(notif_perm or "", notif_perm)
    if notif_perm and perm_state and notif_norm != perm_state:
        flags.append(
            f"Notification.permission={notif_perm} but permissions.query={perm_state} (mismatch)"
        )

    if notif_perm == "denied":
        flags.append("notifications permission denied without prompt (soft signal)")

    # --- Interaction timing (soft) ---

    first_interaction = client_signals.get("first_interaction_ts")
    load_ts = client_signals.get("page_load_ts")
    if first_interaction and load_ts:
        delta_ms = first_interaction - load_ts
        if delta_ms < 50:
            flags.append(f"first interaction within {delta_ms}ms of load (implausibly fast)")

    # --- Hardware plausibility ---

    cores = client_signals.get("hardware_concurrency", -1)
    if cores == 0 or cores > 128:
        flags.append(f"hardware_concurrency={cores} (implausible)")

    memory = client_signals.get("device_memory", -1)
    if memory > 8:
        flags.append(f"device_memory={memory} (exceeds 8GB browser privacy cap)")

    # --- Classify ---

    hard_flags = [f for f in flags if "soft signal" not in f]
    if hard_flags:
        verdict = "flagged"
        score = 0
    elif flags:
        verdict = "challenged"
        score = 40
    else:
        verdict = "clean"
        score = 100

    return {"verdict": verdict, "score": score, "flags": flags}


class ControlledDetectionServer:
    """Context-manager wrapper around the threaded HTTP server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def __enter__(self) -> "ControlledDetectionServer":
        self._server = ThreadingHTTPServer((self._host, self._port), _Handler)
        self._server.request_log = []  # type: ignore[attr-defined]
        self._server.last_verdict = None  # type: ignore[attr-defined]
        self._server.last_behavior = None  # type: ignore[attr-defined]
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
        if self._thread is not None:
            self._thread.join(timeout=5)

    @property
    def base_url(self) -> str:
        assert self._server is not None
        port = self._server.server_address[1]
        return f"http://{self._host}:{port}"

    @property
    def last_verdict(self) -> dict | None:
        assert self._server is not None
        return self._server.last_verdict  # type: ignore[attr-defined]

    @property
    def last_behavior(self) -> dict | None:
        assert self._server is not None
        return self._server.last_behavior  # type: ignore[attr-defined]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8901)
    args = parser.parse_args()

    with ControlledDetectionServer(port=args.port) as srv:
        print(f"Controlled detection target running at {srv.base_url}")
        print(f"  Detection page: {srv.base_url}/")
        print(f"  Behavioral page: {srv.base_url}/behavioral")
        print("Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopped.")
