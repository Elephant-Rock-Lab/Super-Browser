"""Built-in testing utilities for Super Browser.

Provides:
- MockLLMClient for testing without a real LLM provider
- E2EContext + FixtureServer for opt-in real-browser E2E tests

Usage (mock LLM)::

    from super_browser.testing import MockLLMClient
    from super_browser import SuperBrowser

    sb = SuperBrowser(llm_client=MockLLMClient())
    await sb.start()
    result = await sb.act("do something")

Usage (E2E context)::

    from super_browser.testing import E2EContext

    ctx = E2EContext.from_env()
    if not ctx.enabled:
        print("SB_E2E not set — skipping real-browser tests")
"""

from __future__ import annotations

import os
import platform
import threading
from collections.abc import AsyncIterator
from dataclasses import dataclass
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from socketserver import ThreadingMixIn
from typing import Any, Optional

# ---------------------------------------------------------------------------
# MockLLMClient (unchanged)
# ---------------------------------------------------------------------------


class MockLLMClient:
    """A mock LLM client that returns deterministic responses.

    Satisfies ``isinstance(mock, LLMClient) == True`` via the
    ``@runtime_checkable`` protocol check.

    Parameters
    ----------
    action_response:
        Dict to return from ``propose_action``. Defaults to done=True.
    plan_response:
        List of step dicts to return from ``create_plan``.
    """

    def __init__(
        self,
        *,
        action_response: dict[str, Any] | None = None,
        plan_response: list[dict[str, Any]] | None = None,
    ) -> None:
        self._action_response = action_response or {
            "done": True,
            "summary": "Mock task completed",
        }
        self._plan_response = plan_response or [
            {"description": "Complete task", "tool": "done"},
        ]
        self.call_count: int = 0
        self.last_prompt: str | None = None

    async def propose_action(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> dict:
        """Return the configured action response."""
        self.call_count += 1
        self.last_prompt = prompt
        return dict(self._action_response)

    async def propose_action_stream(
        self,
        prompt: str,
        *,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[dict]:
        """Return a single done event (no token streaming in mock)."""
        self.call_count += 1
        self.last_prompt = prompt
        yield {"type": "done", "result": dict(self._action_response)}

    async def create_plan(
        self,
        instruction: str,
        *,
        tools: list[dict],
    ) -> list[dict]:
        """Return the configured plan response."""
        self.call_count += 1
        return [dict(s) for s in self._plan_response]

    async def replan(
        self,
        *,
        instruction: str,
        original_plan: list[dict],
        failed_step: int,
        error: str,
    ) -> list[dict]:
        """Return the original plan unchanged."""
        self.call_count += 1
        return original_plan


# ---------------------------------------------------------------------------
# Track E: E2E Harness Infrastructure
# ---------------------------------------------------------------------------

# Path to benchmark fixtures (project root / benchmarks / fixtures)
_FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "benchmarks" / "fixtures"


class _ThreadingHTTPServer(ThreadingMixIn, HTTPServer):
    """Threaded HTTP server for concurrent fixture requests."""
    daemon_threads = True


class FixtureServer:
    """Serves local HTML fixtures for E2E tests.

    Starts a lightweight HTTP server on a random port (OS-assigned)
    serving files from the benchmarks/fixtures directory. Used by the
    E2E harness to provide deterministic local pages without any
    external network dependency.

    Usage::

        server = FixtureServer()
        url = server.start()
        # url = "http://localhost:12345/simple.html"
        server.stop()
    """

    def __init__(
        self,
        fixtures_dir: Optional[Path] = None,
        port: int = 0,
    ) -> None:
        self._fixtures_dir = fixtures_dir or _FIXTURES_DIR
        self._port = port
        self._server: Optional[_ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None

    def start(self) -> str:
        """Start the server. Returns the base URL (without trailing slash)."""
        if self._server is not None:
            raise RuntimeError("FixtureServer already started")

        if not self._fixtures_dir.exists():
            raise FileNotFoundError(
                f"Fixtures directory not found: {self._fixtures_dir}"
            )

        handler = _make_handler(self._fixtures_dir)
        self._server = _ThreadingHTTPServer(
            ("127.0.0.1", self._port), handler,
        )
        self._thread = threading.Thread(
            target=self._server.serve_forever,
            daemon=True,
        )
        self._thread.start()

        actual_port = self._server.server_address[1]
        return f"http://127.0.0.1:{actual_port}"

    def stop(self) -> None:
        """Stop the server and release the port."""
        if self._server is not None:
            self._server.shutdown()
            self._server.server_close()
            self._server = None
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None

    @property
    def base_url(self) -> str:
        """Base URL of the running server. Raises if not started."""
        if self._server is None:
            raise RuntimeError("FixtureServer not started")
        port = self._server.server_address[1]
        return f"http://127.0.0.1:{port}"

    @property
    def is_running(self) -> bool:
        return self._server is not None


def _make_handler(fixtures_dir: Path) -> type[SimpleHTTPRequestHandler]:
    """Create a request handler rooted at fixtures_dir."""

    class _Handler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(fixtures_dir), **kwargs)

        def log_message(self, *args: Any) -> None:
            pass  # Suppress stderr logging during tests

    return _Handler


@dataclass
class E2EContext:
    """Configuration and lifecycle for E2E test sessions.

    Parsed from environment variables. The master gate is ``SB_E2E=1``;
    when unset, ``enabled`` is ``False`` and all E2E tests should skip.

    Environment variables:

    ================ ============= =======================================
    Env var          Default       Purpose
    ================ ============= =======================================
    SB_E2E           unset         Master gate. ``1`` enables E2E tests.
    SB_E2E_LIVE      unset         Network gate. ``1`` enables live tests.
    SB_BACKEND       ``patchright`` Browser backend.
    SB_HEADLESS      ``1``         ``0`` for headed mode.
    SB_E2E_BUDGET_S  ``120``       Suite-level time budget (seconds).
    ================ ============= =======================================
    """

    enabled: bool = False
    live: bool = False
    backend: str = "patchright"
    headless: bool = True
    budget_seconds: float = 120.0
    fixture_server: Optional[FixtureServer] = None
    _expected_test_count: int = 20

    @classmethod
    def from_env(cls) -> E2EContext:
        """Build an E2EContext from environment variables."""
        enabled = os.environ.get("SB_E2E", "").strip() == "1"
        live = os.environ.get("SB_E2E_LIVE", "").strip() == "1"
        backend = os.environ.get("SB_BACKEND", "patchright").strip() or "patchright"
        headless = os.environ.get("SB_HEADLESS", "1").strip() != "0"
        budget_str = os.environ.get("SB_E2E_BUDGET_S", "120").strip()
        try:
            budget = float(budget_str)
        except ValueError:
            budget = 120.0

        return cls(
            enabled=enabled,
            live=live,
            backend=backend,
            headless=headless,
            budget_seconds=budget,
        )

    def start_fixture_server(self) -> str:
        """Start the fixture HTTP server. Returns base URL."""
        if self.fixture_server is None:
            self.fixture_server = FixtureServer()
        return self.fixture_server.start()

    def fixture_url(self, name: str) -> str:
        """Get the full URL for a fixture file.

        Parameters
        ----------
        name:
            Fixture filename (e.g., ``"simple.html"``).

        Returns
        -------
        str
            Full URL like ``http://127.0.0.1:12345/simple.html``.
        """
        if self.fixture_server is None or not self.fixture_server.is_running:
            self.start_fixture_server()
        assert self.fixture_server is not None  # for type checker
        return f"{self.fixture_server.base_url}/{name}"

    @property
    def test_budget(self) -> float:
        """Per-test budget in seconds (suite budget / expected test count)."""
        if self._expected_test_count <= 0:
            return self.budget_seconds
        return self.budget_seconds / self._expected_test_count

    @property
    def environment_info(self) -> dict[str, Any]:
        """Environment metadata for JSON output."""
        return {
            "backend": self.backend,
            "headless": self.headless,
            "python_version": platform.python_version(),
            "platform": platform.platform(),
            "live": self.live,
        }

    def cleanup(self) -> None:
        """Stop fixture server and release resources."""
        if self.fixture_server is not None:
            self.fixture_server.stop()
            self.fixture_server = None
