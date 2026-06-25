"""Tests for P2.3 inspect-output redaction at the MCP boundary.

Verifies that _redact_inspect_output() masks secrets in text and URL fields
across the 9 inspect-tier tools, and that the no-SM / disabled paths are
no-ops that preserve raw output.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

# A fake JWT that the SecretRedactor reliably detects.
FAKE_KEY = "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.SflKxwRJSMeKKF2QT4fwpMZJ"


def _sm_with_redaction() -> Any:
    """A real SecurityManager with redaction enabled (the default)."""
    from super_browser.security import SecurityManager
    from super_browser.security.types import SecurityConfig

    return SecurityManager(SecurityConfig(
        redaction_enabled=True,
        domain_filter_enabled=False,
        injection_detection_enabled=False,
    ))


def _sm_without_redaction() -> Any:
    """A real SecurityManager with redaction explicitly disabled."""
    from super_browser.security import SecurityManager
    from super_browser.security.types import SecurityConfig

    return SecurityManager(SecurityConfig(
        redaction_enabled=False,
        domain_filter_enabled=False,
        injection_detection_enabled=False,
    ))


def _make_dispatcher(sm: Any | None = None) -> Any:
    """Build a dispatcher with a mocked facade and the given SecurityManager."""
    from super_browser.mcp_server import (
        MCPAuthorizer,
        MCPBrowserRuntime,
        MCPSessionPolicy,
        ToolDispatcher,
    )

    fake_sb = MagicMock()
    fake_sb.diagnostics = MagicMock()
    runtime = MCPBrowserRuntime()
    runtime._sb = fake_sb  # type: ignore[assignment]
    authorizer = MCPAuthorizer(MCPSessionPolicy(), security_manager=sm)
    return ToolDispatcher(runtime, authorizer=authorizer)


# ============================================================================
# Shared helper unit tests
# ============================================================================


class TestRedactInspectOutputHelper:
    def test_redacts_secret_in_text_field(self):
        d = _make_dispatcher(_sm_with_redaction())
        payload = {"ok": True, "text": f"Error: key={FAKE_KEY}"}
        result = d._redact_inspect_output(payload)
        assert FAKE_KEY not in result["text"]
        assert "REDACTED" in result["text"]

    def test_redacts_secret_in_url_query_param(self):
        d = _make_dispatcher(_sm_with_redaction())
        payload = {"ok": True, "url": f"https://api.local?token={FAKE_KEY}"}
        result = d._redact_inspect_output(payload, url_fields=("url",))
        assert FAKE_KEY not in result["url"]

    def test_redacts_secret_in_list_entries(self):
        d = _make_dispatcher(_sm_with_redaction())
        payload = {
            "ok": True,
            "messages": [
                {"text": f"token is {FAKE_KEY}"},
                {"text": "clean message"},
            ],
        }
        result = d._redact_inspect_output(payload, list_keys={"messages": ("text",)})
        assert FAKE_KEY not in result["messages"][0]["text"]
        assert result["messages"][1]["text"] == "clean message"

    def test_noop_when_no_security_manager(self):
        d = _make_dispatcher(sm=None)
        original = {"ok": True, "text": f"key={FAKE_KEY}"}
        result = d._redact_inspect_output(original)
        assert result is original  # unchanged, same object

    def test_noop_when_redaction_disabled(self):
        d = _make_dispatcher(_sm_without_redaction())
        payload = {"ok": True, "text": f"key={FAKE_KEY}"}
        result = d._redact_inspect_output(payload)
        assert result["text"] == f"key={FAKE_KEY}"  # raw, not redacted

    def test_preserves_output_shape(self):
        d = _make_dispatcher(_sm_with_redaction())
        payload = {"ok": True, "count": 5, "url": f"https://x.local?t={FAKE_KEY}"}
        result = d._redact_inspect_output(payload, url_fields=("url",))
        assert set(result.keys()) == set(payload.keys())  # same keys
        assert result["count"] == 5  # non-string fields untouched

    def test_non_secret_text_passes_through(self):
        d = _make_dispatcher(_sm_with_redaction())
        text = "The page loaded successfully. Click here for more info."
        payload = {"ok": True, "text": text}
        result = d._redact_inspect_output(payload)
        assert result["text"] == text  # no false positive

    def test_redacts_url_with_secret_in_innocuous_param(self):
        """Secrets in non-sensitive param names (e.g. ?code=sk-...) must be
        caught by the SecretRedactor pattern scan, not just redact_context."""
        d = _make_dispatcher(_sm_with_redaction())
        payload = {"ok": True, "url": f"https://api.local?code={FAKE_KEY}"}
        result = d._redact_inspect_output(payload, url_fields=("url",))
        assert FAKE_KEY not in result["url"]


# ============================================================================
# Per-tool fixture tests (9 tools)
# ============================================================================


class TestExtractTextRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_extracted_text(self):
        from super_browser.mcp_server import (
            MCPAuthorizer,
            MCPBrowserRuntime,
            MCPSessionPolicy,
            ToolDispatcher,
        )
        from super_browser.security import SecurityConfig, SecurityManager

        fake_sb = MagicMock()
        ar = MagicMock()
        ar.ok = True
        ar.data = {"text": f"The API key is {FAKE_KEY} here."}
        ar.error = None
        ar.meta = None
        fake_sb.extract = AsyncMock(return_value=ar)
        runtime = MCPBrowserRuntime()
        runtime._sb = fake_sb  # type: ignore[assignment]
        sm = SecurityManager(SecurityConfig(redaction_enabled=True, domain_filter_enabled=False, injection_detection_enabled=False))
        dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy(), security_manager=sm))

        result = await dispatcher.dispatch("extract_text", {"query": "key"})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestObserveRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_observe_url(self):
        from super_browser.mcp_server import (
            MCPAuthorizer,
            MCPBrowserRuntime,
            MCPSessionPolicy,
            ToolDispatcher,
        )
        from super_browser.security import SecurityConfig, SecurityManager

        fake_sb = MagicMock()
        ar = MagicMock()
        ar.ok = True
        ar.data = {"url": f"https://page.local?token={FAKE_KEY}", "title": "Page"}
        ar.error = None
        ar.meta = None
        fake_sb.observe = AsyncMock(return_value=ar)
        runtime = MCPBrowserRuntime()
        runtime._sb = fake_sb  # type: ignore[assignment]
        sm = SecurityManager(SecurityConfig(redaction_enabled=True, domain_filter_enabled=False, injection_detection_enabled=False))
        dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy(), security_manager=sm))

        result = await dispatcher.dispatch("observe", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestCurrentUrlRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_current_url(self):
        from super_browser.mcp_server import (
            MCPAuthorizer,
            MCPBrowserRuntime,
            MCPSessionPolicy,
            ToolDispatcher,
        )
        from super_browser.security import SecurityConfig, SecurityManager

        runtime = MCPBrowserRuntime()
        runtime._current_url_cache = f"https://app.local?access_token={FAKE_KEY}"  # type: ignore[attr-defined]
        runtime._sb = MagicMock()  # type: ignore[assignment]
        sm = SecurityManager(SecurityConfig(redaction_enabled=True, domain_filter_enabled=False, injection_detection_enabled=False))
        dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy(), security_manager=sm))

        # current_url calls runtime.current_url() which returns a dict
        async def fake_current_url():
            return {"url": f"https://app.local?access_token={FAKE_KEY}"}
        runtime.current_url = fake_current_url

        result = await dispatcher.dispatch("current_url", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestListTabsRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_tab_url(self):
        from super_browser.mcp_server import (
            MCPAuthorizer,
            MCPBrowserRuntime,
            MCPSessionPolicy,
            ToolDispatcher,
        )
        from super_browser.security import SecurityConfig, SecurityManager

        fake_sb = MagicMock()
        ar = MagicMock()
        ar.ok = True
        ar.data = [{"url": f"https://x.local?token={FAKE_KEY}", "title": "Secret Tab"}]
        ar.error = None
        ar.meta = None
        fake_sb.list_tabs = AsyncMock(return_value=ar)
        runtime = MCPBrowserRuntime()
        runtime._sb = fake_sb  # type: ignore[assignment]
        sm = SecurityManager(SecurityConfig(redaction_enabled=True, domain_filter_enabled=False, injection_detection_enabled=False))
        dispatcher = ToolDispatcher(runtime, authorizer=MCPAuthorizer(MCPSessionPolicy(), security_manager=sm))

        result = await dispatcher.dispatch("list_tabs", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestConsoleMessagesRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_console_text(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._console.append({"seq": 1, "timestamp_ms": 1.0, "type": "log",
                             "text": f"Initialized with key={FAKE_KEY}", "page_url": "https://x.local"})

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_console_messages", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestPageErrorsRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_error_message(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._errors.append({"seq": 1, "timestamp_ms": 1.0, "message": f"Auth failed for {FAKE_KEY}",
                            "name": "Error", "stack": None, "page_url": "https://x.local"})

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_page_errors", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestNetworkErrorsRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_request_url_and_failure_text(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._request_counter = 1
        rec = {"seq": 1, "request_id": "r-1", "timestamp_ms": 1.0, "method": "GET",
               "url": f"https://api.local?token={FAKE_KEY}", "resource_type": "fetch",
               "is_navigation": False, "redirected_from": None, "status": 500,
               "status_text": "ISE", "ok": False, "failed": True,
               "failure_text": f"conn refused: {FAKE_KEY}", "header_names": [], "page_url": "p",
               "_request_obj_id": 9999}
        buf._requests.append(rec)
        buf._req_index["r-1"] = rec
        buf._req_obj_index[9999] = "r-1"

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_network_errors", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestListRequestsRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_request_url(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._request_counter = 1
        rec = {"seq": 1, "request_id": "r-1", "timestamp_ms": 1.0, "method": "GET",
               "url": f"https://api.local?key={FAKE_KEY}", "resource_type": "fetch",
               "is_navigation": False, "redirected_from": None, "status": 200,
               "status_text": "OK", "ok": True, "failed": False,
               "failure_text": None, "header_names": [], "page_url": "p",
               "_request_obj_id": 9999}
        buf._requests.append(rec)
        buf._req_index["r-1"] = rec
        buf._req_obj_index[9999] = "r-1"

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("list_requests", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


class TestGetRequestRedaction:
    @pytest.mark.asyncio
    async def test_redacts_secret_in_request_failure_text(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._request_counter = 1
        rec = {"seq": 1, "request_id": "r-1", "timestamp_ms": 1.0, "method": "POST",
               "url": f"https://api.local?token={FAKE_KEY}", "resource_type": "fetch",
               "is_navigation": False, "redirected_from": None, "status": None,
               "status_text": None, "ok": None, "failed": True,
               "failure_text": f"net::ERR with {FAKE_KEY}", "header_names": [], "page_url": "p",
               "_request_obj_id": 9999}
        buf._requests.append(rec)
        buf._req_index["r-1"] = rec
        buf._req_obj_index[9999] = "r-1"

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_request", {"request_id": "r-1"})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in json.dumps(payload)


# ============================================================================
# Negative test: disabled redaction preserves raw output
# ============================================================================


class TestRedactionDisabled:
    @pytest.mark.asyncio
    async def test_raw_output_when_redaction_disabled(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._console.append({"seq": 1, "timestamp_ms": 1.0, "type": "log",
                             "text": f"key={FAKE_KEY}", "page_url": "https://x.local"})

        dispatcher = _make_dispatcher(_sm_without_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_console_messages", {})
        payload = json.loads(result[0].text)
        # Raw — the key is visible because redaction is disabled.
        assert FAKE_KEY in payload["messages"][0]["text"]


# ============================================================================
# Regression: diagnostics buffers stay raw after MCP redaction (deepcopy)
# ============================================================================


class TestBufferNotMutated:
    """The MCP-boundary-only guarantee: redacting MCP output must NOT mutate
    the underlying diagnostics buffer dicts."""

    @pytest.mark.asyncio
    async def test_console_buffer_stays_raw_after_redaction(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._console.append({"seq": 1, "timestamp_ms": 1.0, "type": "log",
                             "text": f"token={FAKE_KEY}", "page_url": "https://x.local"})

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        # Redact via MCP
        result = await dispatcher.dispatch("get_console_messages", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in payload["messages"][0]["text"]

        # Buffer must still have the raw key
        assert FAKE_KEY in buf._console[0]["text"]

    @pytest.mark.asyncio
    async def test_errors_buffer_stays_raw_after_redaction(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._errors.append({"seq": 1, "timestamp_ms": 1.0, "message": f"err={FAKE_KEY}",
                            "name": "Error", "stack": None, "page_url": "https://x.local"})

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_page_errors", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in payload["errors"][0]["message"]

        # Buffer must still have the raw key
        assert FAKE_KEY in buf._errors[0]["message"]


# ============================================================================
# Nested page_url redaction
# ============================================================================


class TestPageUrlRedaction:
    """page_url fields in diagnostics records must be redacted (two-pass URL)."""

    @pytest.mark.asyncio
    async def test_console_page_url_redacted(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._console.append({"seq": 1, "timestamp_ms": 1.0, "type": "log",
                             "text": "clean", "page_url": f"https://x.local?token={FAKE_KEY}"})

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_console_messages", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in payload["messages"][0]["page_url"]

    @pytest.mark.asyncio
    async def test_page_errors_page_url_redacted(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._errors.append({"seq": 1, "timestamp_ms": 1.0, "message": "err",
                            "name": "E", "stack": None,
                            "page_url": f"https://x.local?token={FAKE_KEY}"})

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_page_errors", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in payload["errors"][0]["page_url"]

    @pytest.mark.asyncio
    async def test_list_requests_page_url_redacted(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._request_counter = 1
        rec = {"seq": 1, "request_id": "r-1", "timestamp_ms": 1.0, "method": "GET",
               "url": "https://clean.local", "resource_type": "fetch",
               "is_navigation": False, "redirected_from": None, "status": 200,
               "status_text": "OK", "ok": True, "failed": False,
               "failure_text": None, "header_names": [],
               "page_url": f"https://x.local?token={FAKE_KEY}",
               "_request_obj_id": 9999}
        buf._requests.append(rec)
        buf._req_index["r-1"] = rec
        buf._req_obj_index[9999] = "r-1"

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("list_requests", {})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in payload["requests"][0]["page_url"]

    @pytest.mark.asyncio
    async def test_get_request_page_url_redacted(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        buf._request_counter = 1
        rec = {"seq": 1, "request_id": "r-1", "timestamp_ms": 1.0, "method": "GET",
               "url": "https://clean.local", "resource_type": "fetch",
               "is_navigation": False, "redirected_from": None, "status": 200,
               "status_text": "OK", "ok": True, "failed": False,
               "failure_text": None, "header_names": [],
               "page_url": f"https://x.local?token={FAKE_KEY}",
               "_request_obj_id": 9999}
        buf._requests.append(rec)
        buf._req_index["r-1"] = rec
        buf._req_obj_index[9999] = "r-1"

        dispatcher = _make_dispatcher(_sm_with_redaction())
        dispatcher.runtime._sb.diagnostics = buf  # type: ignore[attr-defined]

        result = await dispatcher.dispatch("get_request", {"request_id": "r-1"})
        payload = json.loads(result[0].text)
        assert FAKE_KEY not in payload["request"]["page_url"]
