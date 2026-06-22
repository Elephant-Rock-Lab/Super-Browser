"""Test that the MCP console-script entry point bootstraps without crashing.

This test was prompted by the v2.3.0 bug where ``logging.Stderr`` (which
doesn't exist) crashed ``main()`` before ``asyncio.run()`` was reached.
The artifact verifier checked that the entry point existed in metadata but
never exercised the bootstrap code path.
"""

from __future__ import annotations

import asyncio

from super_browser import mcp_server


class TestMCPCallEntrypointBootstrap:
    def test_main_does_not_crash_before_asyncio_run(self, monkeypatch):
        """Calling main() must reach asyncio.run() without raising.

        The v2.3.0 bug (logging.Stderr) raised AttributeError before
        asyncio.run was called. This test monkeypatches run_server so no
        real server starts, but the bootstrap path (logging setup, etc.)
        must execute cleanly.
        """
        calls: list[str] = []

        async def fake_run_server():
            calls.append("run_server")

        def fake_asyncio_run(coro):
            calls.append("asyncio.run")
            # Drive the coroutine to completion.
            try:
                coro.send(None)
            except StopIteration:
                pass

        monkeypatch.setattr(mcp_server, "run_server", fake_run_server)
        monkeypatch.setattr(asyncio, "run", fake_asyncio_run)

        # Must not raise.
        mcp_server.main()

        assert "asyncio.run" in calls
        assert "run_server" in calls
