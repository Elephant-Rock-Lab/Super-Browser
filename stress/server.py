#!/usr/bin/env python3
"""Fixture server for the real-world stress harness.

Serves HTML fixtures plus mock API endpoints (data, slow, error, download)
on localhost. Designed to run in a background thread during stress tests.

Run standalone for debugging:

    python stress/server.py --port 8765
"""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

FIXTURE_DIR = Path(__file__).parent

# -- Static fixtures ---------------------------------------------------------

INDEX_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Stress Test — Home</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
  <h1 id="page-title">Stress Test Home</h1>
  <nav id="main-nav">
    <a href="/login.html" id="nav-login">Login</a>
    <a href="/app.html" id="nav-app">Dynamic App</a>
    <a href="/form.html" id="nav-form">File Form</a>
    <a href="/heavy-dom.html" id="nav-heavy">Heavy DOM</a>
  </nav>
  <div id="layout-marker" data-layout="desktop">Layout: Desktop</div>
  <div id="content">
    <p>Welcome to the stress test fixture home page.</p>
  </div>
</body>
</html>
"""

LOGIN_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Stress Test — Login</title>
</head>
<body>
  <h1>Login</h1>
  <form id="login-form" method="POST" action="/api/auth">
    <label>Username: <input type="text" id="username" name="username"></label><br>
    <label>Password: <input type="password" id="password" name="password"></label><br>
    <button type="submit" id="submit-btn">Log In</button>
  </form>
  <div id="auth-status">Not logged in</div>
  <script>
    document.getElementById('login-form').addEventListener('submit', async (e) => {
      e.preventDefault();
      const resp = await fetch('/api/auth', { method: 'POST' });
      const data = await resp.json();
      if (data.authenticated) {
        document.cookie = 'session_token=' + data.token + '; path=/';
        localStorage.setItem('user', JSON.stringify(data.user));
        document.getElementById('auth-status').textContent = 'Logged in as ' + data.user.name;
      }
    });
  </script>
</body>
</html>
"""

APP_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Stress Test — Dynamic App</title>
</head>
<body>
  <h1 id="app-title">Dynamic App</h1>
  <div id="loading">Loading content...</div>
  <div id="content-area" style="display:none;"></div>
  <button id="refresh-btn">Refresh</button>
  <script>
    async function loadContent() {
      document.getElementById('loading').style.display = 'block';
      const resp = await fetch('/api/data');
      const data = await resp.json();
      document.getElementById('loading').style.display = 'none';
      const area = document.getElementById('content-area');
      area.style.display = 'block';
      area.innerHTML = '';
      data.items.forEach((item, i) => {
        const el = document.createElement('div');
        el.className = 'item';
        el.id = 'item-' + i;
        el.textContent = item.label;
        area.appendChild(el);
      });
      window.__HYDRATED__ = true;
    }
    document.getElementById('refresh-btn').addEventListener('click', loadContent);
    // Auto-hydrate after a short delay
    setTimeout(loadContent, 200);
  </script>
</body>
</html>
"""

FORM_HTML = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Stress Test — File Form</title>
</head>
<body>
  <h1>Upload Form</h1>
  <form id="upload-form" enctype="multipart/form-data" method="POST" action="/api/upload">
    <label>File: <input type="file" id="file-input" name="file"></label><br>
    <label>Name: <input type="text" id="name" name="name" value="test-user"></label><br>
    <button type="submit" id="submit-btn">Upload</button>
  </form>
  <div id="upload-result"></div>
</body>
</html>
"""


def _generate_heavy_dom() -> str:
    """Generate heavy DOM fixture with 10k+ nodes."""
    rows = []
    rows.append("<!DOCTYPE html><html><head><meta charset='utf-8'>")
    rows.append("<title>Stress Test — Heavy DOM</title></head><body>")
    rows.append("<h1 id='heavy-title'>Heavy DOM</h1>")
    rows.append("<div id='heavy-container'>")
    for i in range(2500):
        rows.append(
            f"<div class='row' id='row-{i}'>"
            f"<span class='cell' id='cell-{i}-a'>Cell {i}A</span>"
            f"<span class='cell' id='cell-{i}-b'>Cell {i}B</span>"
            f"<span class='cell' id='cell-{i}-c'>Cell {i}C</span>"
            f"<span class='cell' id='cell-{i}-d'>Cell {i}D</span>"
            f"</div>"
        )
    rows.append("</div></body></html>")
    return "\n".join(rows)


HEAVY_DOM_HTML = _generate_heavy_dom()

STATIC_ROUTES: dict[str, str] = {
    "/": INDEX_HTML,
    "/index.html": INDEX_HTML,
    "/login.html": LOGIN_HTML,
    "/app.html": APP_HTML,
    "/form.html": FORM_HTML,
    "/heavy-dom.html": HEAVY_DOM_HTML,
}

# Deterministic download payload (1 KB)
DOWNLOAD_PAYLOAD = bytes(range(256)) * 4
DOWNLOAD_SHA256 = hashlib.sha256(DOWNLOAD_PAYLOAD).hexdigest()


class StressFixtureHandler(BaseHTTPRequestHandler):
    """HTTP handler serving stress test fixtures and mock API endpoints."""

    def log_message(self, format: str, *args: object) -> None:
        """Suppress default logging to keep stdout clean."""
        pass

    # -- GET routes ----------------------------------------------------------

    def do_GET(self) -> None:
        path = self.path.split("?")[0]

        # Static HTML fixtures
        if path in STATIC_ROUTES:
            self._serve_html(STATIC_ROUTES[path])
            return

        # Download endpoint — deterministic 1 KB file
        if path == "/download":
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(DOWNLOAD_PAYLOAD)))
            self.send_header("Content-Disposition", "attachment; filename='stress-test.bin'")
            self.end_headers()
            self.wfile.write(DOWNLOAD_PAYLOAD)
            return

        # API: normal JSON data
        if path == "/api/data":
            data = {
                "items": [
                    {"id": i, "label": f"Item {i}"} for i in range(20)
                ],
                "timestamp": time.time(),
            }
            self._serve_json(data)
            return

        # API: slow endpoint (simulates network degradation)
        if path == "/api/slow":
            time.sleep(2.0)  # 2-second delay
            self._serve_json({"status": "slow-ok", "delay_ms": 2000})
            return

        # API: error endpoint
        if path == "/api/error":
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Internal Server Error"}).encode())
            return

        # 404
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not Found")

    # -- POST routes ---------------------------------------------------------

    def do_POST(self) -> None:
        path = self.path.split("?")[0]

        if path == "/api/auth":
            # Always succeed with a deterministic token
            data = {
                "authenticated": True,
                "token": "stress-session-token-" + str(int(time.time())),
                "user": {"id": 1, "name": "stress-tester"},
            }
            self._serve_json(data)
            return

        if path == "/api/upload":
            # Read body and compute real digest
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length)
            data = {
                "uploaded": True,
                "size_bytes": content_length,
                "sha256": hashlib.sha256(body).hexdigest(),
            }
            self._serve_json(data)
            return

        # 404
        self.send_response(404)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Not Found")

    # -- Helpers -------------------------------------------------------------

    def _serve_html(self, content: str) -> None:
        encoded = content.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _serve_json(self, data: object) -> None:
        encoded = json.dumps(data).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


class StressFixtureServer:
    """Context-managed fixture server for stress tests."""

    def __init__(self, port: int = 0, host: str = "127.0.0.1") -> None:
        self._host = host
        self._port = port
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def base_url(self) -> str:
        if self._server is None:
            raise RuntimeError("Server not started")
        return f"http://{self._host}:{self.actual_port}"

    @property
    def actual_port(self) -> int:
        if self._server is None:
            raise RuntimeError("Server not started")
        return self._server.server_address[1]

    def start(self) -> str:
        """Start the server in a background thread. Returns base URL."""
        self._server = ThreadingHTTPServer(
            (self._host, self._port), StressFixtureHandler
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever, daemon=True
        )
        self._thread.start()
        return self.base_url

    def stop(self) -> None:
        """Stop the server and wait for thread cleanup."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None

    def __enter__(self) -> str:
        return self.start()

    def __exit__(self, *exc: object) -> None:
        self.stop()


def main() -> None:
    """Run the fixture server standalone for debugging."""
    parser = argparse.ArgumentParser(description="Stress test fixture server")
    parser.add_argument("--port", type=int, default=8765, help="Port (default: 8765)")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default: 127.0.0.1)")
    args = parser.parse_args()

    server = StressFixtureServer(port=args.port, host=args.host)
    base_url = server.start()
    print(f"Stress fixture server running at {base_url}")
    print(f"  Static fixtures: {len(STATIC_ROUTES)} routes")
    print("  API endpoints: /api/data, /api/slow, /api/error, /api/auth, /api/upload, /download")
    print(f"  Heavy DOM: {len(HEAVY_DOM_HTML)} bytes, {HEAVY_DOM_HTML.count('<')} nodes")
    print("Press Ctrl+C to stop.")
    try:
        import signal
        signal.pause()
    except (ImportError, AttributeError):
        # Windows has no signal.pause()
        import threading
        threading.Event().wait()
    except KeyboardInterrupt:
        pass
    finally:
        server.stop()
        print("Server stopped.")


if __name__ == "__main__":
    main()
