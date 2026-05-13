"""Tests for BrowserFetch — CDP-routed HTTP client (all offline, mocked)."""

import asyncio
import base64
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.browser.cdp import CDPBridge, CDPResult
from super_browser.browser.fetch import (
    BrowserFetch,
    BrowserFetchResponse,
    CdpFetchError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bridge(send_side_effects: list[CDPResult] | None = None) -> CDPBridge:
    """Build a CDPBridge backed by an AsyncMock for ``send()``."""
    mock_session = AsyncMock()
    bridge = CDPBridge.__new__(CDPBridge)
    bridge._session = mock_session
    bridge._config = MagicMock()
    bridge._config.stale_recovery = False
    bridge._config.event_buffer_size = 500
    bridge._events = []
    bridge._handlers = {}
    bridge._reattach_fn = None
    if send_side_effects is not None:
        bridge.send = AsyncMock(side_effect=send_side_effects)
    else:
        bridge.send = AsyncMock(return_value=CDPResult(ok=True, data={}))
    return bridge


def _ok(data: dict, method: str = "") -> CDPResult:
    return CDPResult(ok=True, data=data, method=method)


def _err(error: str, method: str = "") -> CDPResult:
    return CDPResult(ok=False, error=error, method=method)


def _scratch_frame_setup(
    target_id: str = "t-1",
    session_id: str = "s-1",
    frame_id: str = "f-1",
) -> list[CDPResult]:
    """Return the CDPResult sequence for scratch-frame creation."""
    return [
        _ok({"targetId": target_id}, "Target.createTarget"),
        _ok({"sessionId": session_id}, "Target.attachToTarget"),
        _ok(
            {"frameTree": {"frame": {"id": frame_id}}},
            "Page.getFrameTree",
        ),
    ]


# ===================================================================
# TEST-31-01-01: Mechanism A — simple GET with IO stream
# ===================================================================

class TestMechanismASimpleGet:
    """TEST-31-01-01: Network.loadNetworkResource + IO.read drain."""

    def test_simple_get_with_stream(self):
        body_text = "hello world"
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            _ok(
                {
                    "resource": {
                        "success": True,
                        "httpStatusCode": 200,
                        "stream": "io-42",
                        "headers": {"content-type": "text/plain"},
                    },
                },
                "Network.loadNetworkResource",
            ),
            _ok(
                {
                    "data": body_text,
                    "eof": True,
                    "base64Encoded": False,
                },
                "IO.read",
            ),
            _ok({}, "IO.close"),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            resp = await fetch.fetch("https://example.com")
            assert resp.status == 200
            assert resp.ok is True
            assert resp.body == body_text.encode("utf-8")
            assert resp.headers["content-type"] == "text/plain"
            assert resp.text() == body_text
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-02: Mechanism A — empty body (no stream)
# ===================================================================

class TestMechanismAEmptyBody:
    """TEST-31-01-02: loadNetworkResource with no stream → empty body."""

    def test_empty_body_no_stream(self):
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            _ok(
                {
                    "resource": {
                        "success": True,
                        "httpStatusCode": 204,
                        "headers": {},
                    },
                },
                "Network.loadNetworkResource",
            ),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            resp = await fetch.fetch("https://example.com/empty")
            assert resp.status == 204
            assert resp.body == b""
            assert resp.ok is True
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-03: Mechanism A — multi-chunk IO stream drain
# ===================================================================

class TestMechanismAMultiChunk:
    """TEST-31-01-03: IO stream drained in multiple chunks."""

    def test_multi_chunk_drain(self):
        chunk1 = "AAAA"  # base64-decoded → b'\x00\x00\x00'
        chunk2 = "Qg=="  # base64-decoded → b'B'
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            _ok(
                {
                    "resource": {
                        "success": True,
                        "httpStatusCode": 200,
                        "stream": "io-99",
                        "headers": {},
                    },
                },
                "Network.loadNetworkResource",
            ),
            _ok(
                {"data": chunk1, "eof": False, "base64Encoded": True},
                "IO.read",
            ),
            _ok(
                {"data": chunk2, "eof": True, "base64Encoded": True},
                "IO.read",
            ),
            _ok({}, "IO.close"),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            resp = await fetch.fetch("https://example.com/binary")
            assert resp.status == 200
            assert resp.body == base64.b64decode(chunk1) + base64.b64decode(chunk2)
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-04: Mechanism A — failure raises CdpFetchError
# ===================================================================

class TestMechanismAFailure:
    """TEST-31-01-04: loadNetworkResource failure raises CdpFetchError."""

    def test_resource_failure(self):
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            _ok(
                {
                    "resource": {
                        "success": False,
                        "netErrorName": "net::ERR_CONNECTION_REFUSED",
                        "httpStatusCode": 502,
                    },
                },
                "Network.loadNetworkResource",
            ),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            with pytest.raises(CdpFetchError, match="net::ERR_CONNECTION_REFUSED"):
                await fetch.fetch("https://down.example.com")
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-05: Mechanism B — POST with body via page evaluate
# ===================================================================

class TestMechanismBPost:
    """TEST-31-01-05: POST via Runtime.callFunctionOn with fetch()."""

    def test_post_with_body(self):
        body_b64 = base64.b64encode(b'{"ok":true}').decode()
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            # DOM.getDocument for documentObjectId
            _ok({"root": {"nodeId": 1}}, "DOM.getDocument"),
            _ok({"object": {"objectId": "obj-doc-1"}}, "DOM.resolveNode"),
            # Runtime.callFunctionOn
            _ok(
                {
                    "result": {
                        "type": "object",
                        "value": {
                            "status": 201,
                            "headers": {"content-type": "application/json"},
                            "bodyB64": body_b64,
                        },
                    },
                },
                "Runtime.callFunctionOn",
            ),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            resp = await fetch.fetch(
                "https://api.example.com/data",
                init={"method": "POST", "body": '{"name":"test"}'},
            )
            assert resp.status == 201
            assert resp.ok is True
            assert resp.json() == {"ok": True}
            assert resp.headers["content-type"] == "application/json"
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-06: Mechanism B — exceptionDetails raises CdpFetchError
# ===================================================================

class TestMechanismBException:
    """TEST-31-01-06: page-evaluate fetch exception → CdpFetchError."""

    def test_exception_details(self):
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            _ok({"root": {"nodeId": 1}}, "DOM.getDocument"),
            _ok({"object": {"objectId": "obj-doc-1"}}, "DOM.resolveNode"),
            _ok(
                {
                    "exceptionDetails": {
                        "text": "fetch failed",
                        "exception": {
                            "description": "TypeError: Failed to fetch"
                        },
                    },
                    "result": {},
                },
                "Runtime.callFunctionOn",
            ),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            with pytest.raises(CdpFetchError, match="TypeError: Failed to fetch"):
                await fetch.fetch(
                    "https://api.example.com",
                    init={"method": "POST"},
                )
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-07: Path selection — init with method=GET routes to Mechanism A
# ===================================================================

class TestPathSelectionSimpleGet:
    """TEST-31-01-07: init with method=GET (no headers/body) → Mechanism A."""

    def test_explicit_get_method_routes_a(self):
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            _ok(
                {
                    "resource": {
                        "success": True,
                        "httpStatusCode": 200,
                        "stream": "io-7",
                        "headers": {},
                    },
                },
                "Network.loadNetworkResource",
            ),
            _ok({"data": "", "eof": True}, "IO.read"),
            _ok({}, "IO.close"),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            resp = await fetch.fetch(
                "https://example.com",
                init={"method": "GET"},
            )
            assert resp.status == 200
            # Verify Network.loadNetworkResource was used (call index after
            # scratch setup = 3)
            calls = bridge.send.call_args_list
            assert calls[3][0][0] == "Network.loadNetworkResource"
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-08: Path selection — init with headers routes to Mechanism B
# ===================================================================

class TestPathSelectionWithHeaders:
    """TEST-31-01-08: init with headers → Mechanism B."""

    def test_get_with_headers_routes_b(self):
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            _ok({"root": {"nodeId": 1}}, "DOM.getDocument"),
            _ok({"object": {"objectId": "obj-doc-1"}}, "DOM.resolveNode"),
            _ok(
                {
                    "result": {
                        "type": "object",
                        "value": {
                            "status": 200,
                            "headers": {"x-custom": "yes"},
                            "bodyB64": base64.b64encode(b"ok").decode(),
                        },
                    },
                },
                "Runtime.callFunctionOn",
            ),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            resp = await fetch.fetch(
                "https://example.com",
                init={"headers": {"X-Test": "1"}},
            )
            assert resp.status == 200
            calls = bridge.send.call_args_list
            assert calls[3][0][0] == "DOM.getDocument"
            assert calls[5][0][0] == "Runtime.callFunctionOn"
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-09: Scratch frame reuse across multiple fetches
# ===================================================================

class TestScratchFrameReuse:
    """TEST-31-01-09: scratch frame is created once and reused."""

    def test_scratch_reuse(self):
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            # First fetch
            _ok(
                {
                    "resource": {
                        "success": True,
                        "httpStatusCode": 200,
                        "headers": {},
                    },
                },
                "Network.loadNetworkResource",
            ),
            # Second fetch (reuses same scratch)
            _ok(
                {
                    "resource": {
                        "success": True,
                        "httpStatusCode": 200,
                        "headers": {},
                    },
                },
                "Network.loadNetworkResource",
            ),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            r1 = await fetch.fetch("https://a.com")
            r2 = await fetch.fetch("https://b.com")
            assert r1.status == 200
            assert r2.status == 200
            # Target.createTarget should be called exactly once
            method_calls = [c[0][0] for c in bridge.send.call_args_list]
            assert method_calls.count("Target.createTarget") == 1
            await fetch.close()

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-10: close() tears down scratch frame
# ===================================================================

class TestClose:
    """TEST-31-01-10: close() calls Target.closeTarget on the scratch."""

    def test_close_calls_target_close(self):
        bridge = _make_bridge([
            *_scratch_frame_setup(),
            # Target.closeTarget
            _ok({"success": True}, "Target.closeTarget"),
        ])

        async def _run():
            fetch = BrowserFetch(bridge)
            # Force scratch frame creation
            await fetch._ensure_scratch_frame()
            assert fetch._scratch is not None
            await fetch.close()
            assert fetch._scratch is None
            last_call = bridge.send.call_args_list[-1]
            assert last_call[0][0] == "Target.closeTarget"

        asyncio.run(_run())


# ===================================================================
# TEST-31-01-11: BrowserFetchResponse properties and helpers
# ===================================================================

class TestBrowserFetchResponse:
    """TEST-31-01-11: BrowserFetchResponse frozen dataclass behaviour."""

    def test_ok_property(self):
        r = BrowserFetchResponse(status=200, headers={}, body=b"")
        assert r.ok is True
        r2 = BrowserFetchResponse(status=404, headers={}, body=b"")
        assert r2.ok is False
        r3 = BrowserFetchResponse(status=301, headers={}, body=b"")
        assert r3.ok is True
        r4 = BrowserFetchResponse(status=500, headers={}, body=b"")
        assert r4.ok is False

    def test_text_and_json(self):
        payload = json.dumps({"msg": "hi"}).encode()
        r = BrowserFetchResponse(
            status=200,
            headers={"content-type": "application/json"},
            body=payload,
        )
        assert r.json() == {"msg": "hi"}
        assert json.loads(r.text()) == {"msg": "hi"}

    def test_frozen(self):
        r = BrowserFetchResponse(status=200, headers={}, body=b"x")
        with pytest.raises(AttributeError):
            r.status = 404  # type: ignore[misc]

    def test_text_encoding_override(self):
        body = "héllo".encode("latin-1")
        r = BrowserFetchResponse(status=200, headers={}, body=body)
        assert r.text("latin-1") == "héllo"
