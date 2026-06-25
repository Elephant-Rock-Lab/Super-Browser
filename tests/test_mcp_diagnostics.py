"""MCP diagnostics tool tests — the 5 inspect-tier handlers.

These exercise the ToolDispatcher → handler → sb.diagnostics path with a
mocked facade whose DiagnosticsBuffer is pre-seeded. The tools are inspect-tier
(no action gate, no audit, no budget), routed via INSPECT_TOOL_NAMES.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import MagicMock

import pytest


def _seeded_buffer() -> Any:
    """A real DiagnosticsBuffer pre-populated with deterministic entries."""
    from super_browser.agent.diagnostics import DiagnosticsBuffer

    buf = DiagnosticsBuffer(max_size=500)
    # Console
    page = MagicMock()
    page.url = "https://page.local"
    buf.attach(page)
    # We can't easily fire real events without a fake page; populate deques directly.
    buf._console.append({"seq": 1, "timestamp_ms": 1.0, "type": "log",
                         "text": "hello", "page_url": "https://page.local"})
    buf._console.append({"seq": 2, "timestamp_ms": 2.0, "type": "error",
                         "text": "bad", "page_url": "https://page.local"})
    buf._errors.append({"seq": 3, "timestamp_ms": 3.0, "message": "Uncaught",
                        "name": "TypeError", "stack": "at x", "page_url": "https://page.local"})
    # Requests
    buf._request_counter = 2
    rec1 = {"seq": 4, "request_id": "r-1", "timestamp_ms": 4.0, "method": "GET",
            "url": "https://api.local/users", "resource_type": "fetch",
            "is_navigation": False, "redirected_from": None, "status": 200,
            "status_text": "OK", "ok": True, "failed": False, "failure_text": None,
            "header_names": ["content-type"], "page_url": "https://page.local"}
    rec2 = {"seq": 5, "request_id": "r-2", "timestamp_ms": 5.0, "method": "POST",
            "url": "https://api.local/missing", "resource_type": "fetch",
            "is_navigation": False, "redirected_from": None, "status": 404,
            "status_text": "Not Found", "ok": False, "failed": True,
            "failure_text": None, "header_names": ["authorization"], "page_url": "https://page.local"}
    buf._requests.append(rec1)
    buf._requests.append(rec2)
    buf._req_index["r-1"] = rec1
    buf._req_index["r-2"] = rec2
    return buf


def _make_dispatcher(buffer: Any) -> tuple[Any, Any]:
    from super_browser.mcp_server import (
        MCPAuthorizer,
        MCPBrowserRuntime,
        MCPSessionPolicy,
        ToolDispatcher,
    )

    fake_sb = MagicMock()
    fake_sb.diagnostics = buffer
    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb  # type: ignore[assignment]
    dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy()))
    return dispatcher, fake_sb


# ============================================================================
# Tool advertisement
# ============================================================================


class TestDiagnosticsAdvertisement:
    def test_default_advertises_13_tools(self):
        from super_browser.mcp_server import MCPSessionPolicy, _tools_for_policy

        names = {t.name for t in _tools_for_policy(MCPSessionPolicy())}
        assert len(names) == 13
        for diag in ("get_console_messages", "get_page_errors", "get_network_errors",
                     "list_requests", "get_request"):
            assert diag in names

    def test_action_mode_advertises_19_tools(self):
        from super_browser.mcp_server import MCPSessionPolicy, _tools_for_policy

        names = {t.name for t in _tools_for_policy(MCPSessionPolicy(allow_actions=True))}
        assert len(names) == 19

    def test_diagnostics_are_inspect_tier(self):
        """Diagnostics tools are in INSPECT_TOOL_NAMES (no action gate)."""
        from super_browser.mcp_server import INSPECT_TOOL_NAMES

        for diag in ("get_console_messages", "get_page_errors", "get_network_errors",
                     "list_requests", "get_request"):
            assert diag in INSPECT_TOOL_NAMES


# ============================================================================
# Handlers
# ============================================================================


class TestGetConsoleMessages:
    @pytest.mark.asyncio
    async def test_returns_all_console_messages(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_console_messages", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        assert len(payload["messages"]) == 2
        assert payload["messages"][0]["text"] == "hello"

    @pytest.mark.asyncio
    async def test_level_filter(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_console_messages", {"level": "error"})
        payload = json.loads(result[0].text)
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["type"] == "error"

    @pytest.mark.asyncio
    async def test_limit(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_console_messages", {"limit": 1})
        payload = json.loads(result[0].text)
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["text"] == "bad"  # last one


class TestGetPageErrors:
    @pytest.mark.asyncio
    async def test_returns_page_errors(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_page_errors", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        assert len(payload["errors"]) == 1
        assert payload["errors"][0]["name"] == "TypeError"


class TestGetNetworkErrors:
    @pytest.mark.asyncio
    async def test_returns_only_failed_requests(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_network_errors", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        urls = [r["url"] for r in payload["requests"]]
        assert urls == ["https://api.local/missing"]  # only the 404


class TestListRequests:
    @pytest.mark.asyncio
    async def test_returns_all_requests(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("list_requests", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        assert len(payload["requests"]) == 2

    @pytest.mark.asyncio
    async def test_url_filter(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("list_requests", {"url_filter": "missing"})
        payload = json.loads(result[0].text)
        assert len(payload["requests"]) == 1

    @pytest.mark.asyncio
    async def test_resource_type_filter(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("list_requests", {"resource_type": "image"})
        payload = json.loads(result[0].text)
        assert payload["requests"] == []  # none are images

    @pytest.mark.asyncio
    async def test_response_includes_request_ids(self):
        """list_requests must return request_ids for get_request follow-up."""
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("list_requests", {})
        payload = json.loads(result[0].text)
        ids = {r["request_id"] for r in payload["requests"]}
        assert ids == {"r-1", "r-2"}


class TestGetRequest:
    @pytest.mark.asyncio
    async def test_returns_detail_by_request_id(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_request", {"request_id": "r-1"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is True
        assert payload["request"]["request_id"] == "r-1"
        assert payload["request"]["status"] == 200

    @pytest.mark.asyncio
    async def test_unknown_request_id_returns_not_found(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_request", {"request_id": "r-999"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["reason"] == "not_found"

    @pytest.mark.asyncio
    async def test_no_response_body_in_detail(self):
        """get_request must NOT include response bodies."""
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_request", {"request_id": "r-1"})
        payload = json.loads(result[0].text)
        rec_str = json.dumps(payload["request"])
        assert "body" not in payload["request"]
        # And no raw header VALUES leak (only header_names keys).
        assert "Bearer" not in rec_str
        assert "SECRET" not in rec_str

    @pytest.mark.asyncio
    async def test_missing_request_id_arg_returns_invalid_arguments(self):
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        result = await dispatcher.dispatch("get_request", {})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert "invalid_arguments" in payload

    @pytest.mark.asyncio
    async def test_evicted_request_returns_not_found(self):
        """When a request is evicted from the bounded deque, get_request must
        return {ok: false, reason: "not_found"}, not stale data."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer(max_size=1)
        # Seed: one request that will be evicted.
        buf._request_counter = 1
        rec = {"seq": 1, "request_id": "r-1", "timestamp_ms": 1.0, "method": "GET",
               "url": "https://gone.local", "resource_type": "fetch", "is_navigation": False,
               "redirected_from": None, "status": None, "status_text": None, "ok": None,
               "failed": False, "failure_text": None, "header_names": [], "page_url": "p",
               "_request_obj_id": 9999}
        buf._requests.append(rec)
        buf._req_index["r-1"] = rec
        buf._req_obj_index[9999] = "r-1"
        # Now evict r-1 by appending a second request to the size-1 deque.
        buf._request_counter = 2
        rec2 = {"seq": 2, "request_id": "r-2", "timestamp_ms": 2.0, "method": "GET",
                "url": "https://new.local", "resource_type": "fetch", "is_navigation": False,
                "redirected_from": None, "status": 200, "status_text": "OK", "ok": True,
                "failed": False, "failure_text": None, "header_names": [], "page_url": "p",
                "_request_obj_id": 10000}
        # Simulate the eviction path (prune-then-append).
        evicted = buf._requests[0]
        buf._req_index.pop(evicted.get("request_id"), None)
        buf._req_obj_index.pop(evicted.get("_request_obj_id"), None)
        buf._requests.append(rec2)
        buf._req_index["r-2"] = rec2
        buf._req_obj_index[10000] = "r-2"

        dispatcher, _ = _make_dispatcher(buf)
        result = await dispatcher.dispatch("get_request", {"request_id": "r-1"})
        payload = json.loads(result[0].text)
        assert payload["ok"] is False
        assert payload["reason"] == "not_found"


class TestDiagnosticsAreInspectTier:
    @pytest.mark.asyncio
    async def test_works_in_default_mode_without_allow_actions(self):
        """Diagnostics are inspect-tier: no action gate, no budget."""
        dispatcher, _ = _make_dispatcher(_seeded_buffer())
        # Should work even though allow_actions=False (default).
        result = await dispatcher.dispatch("get_console_messages", {})
        assert json.loads(result[0].text)["ok"] is True
        # And did NOT consume any action budget.
        assert dispatcher.authorizer.policy.actions_used == 0
