"""Unit tests for DiagnosticsBuffer — the session-wide page-event capture layer.

These tests target the buffer data model directly (no MCP, no real browser).
Event capture tests use lightweight fake objects that mimic the Playwright
ConsoleMessage/Error/Request/Response surface the buffer reads from.

Key invariants under test:
  - Bounded ring deques (max_size), evicting oldest on overflow.
  - Monotonic buffer-wide seq counter.
  - Reads are snapshots (non-destructive).
  - attach() is idempotent by raw-page identity (no double-recording).
  - Event handlers are sync-safe (no awaits inside page.on callbacks).
"""

from __future__ import annotations

from unittest.mock import MagicMock

# ============================================================================
# Helpers: fakes that mimic the Playwright/Patchright event surface
# ============================================================================


def _fake_page(*, url: str = "https://example.com") -> MagicMock:
    """A fake raw page with an on() registration surface and a stable url."""
    p = MagicMock()
    p.url = url
    # Collect registered handlers so tests can fire them.
    p._handlers: dict[str, list] = {}
    p.on = MagicMock(side_effect=lambda event, fn: p._handlers.setdefault(event, []).append(fn))
    return p


def _fire(page: MagicMock, event: str, *args) -> None:
    for fn in page._handlers.get(event, []):
        fn(*args)


# ============================================================================
# Task 1: Data model — empty snapshots, ring bound, seq, idempotent attach
# ============================================================================


class TestBufferDataModel:
    def test_empty_snapshots_return_empty_lists(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer(max_size=500)
        assert buf.console_messages() == []
        assert buf.page_errors() == []
        assert buf.requests() == []

    def test_max_size_defaults_to_500(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        assert buf.max_size == 500

    def test_seq_starts_at_zero_before_any_event(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        assert buf.last_seq() == 0

    def test_attach_is_idempotent_by_raw_page_identity(self):
        """attach() twice on the SAME raw page must register listeners once."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        buf.attach(page)  # second attach — same page object
        # page.on called once per event type on first attach; not again.
        assert page.on.call_count == 4  # console, pageerror, request, response

    def test_attach_different_pages_registers_each(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        p1 = _fake_page()
        p2 = _fake_page()
        buf.attach(p1)
        buf.attach(p2)
        assert p1.on.call_count == 4
        assert p2.on.call_count == 4

    def test_attach_then_detach_allows_reattach(self):
        """detach() removes the page from the attached set so re-attach re-registers."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        buf.detach(page)
        buf.attach(page)
        # Two attaches with a detach between → 8 on() calls total (4 + 4).
        assert page.on.call_count == 8

    def test_attach_tracks_pages_weakly_not_by_raw_id(self):
        """The attached-set holds weak references to page objects, not raw
        id() integers. A page that is GC'd drops out automatically, so a
        later page that reuses a freed page's memory address is NOT wrongly
        treated as already-attached.

        This is the documented fix for the id()-reuse window. We prove weak
        tracking by deleting the only strong reference and forcing GC; the
        WeakSet must then be empty (or not contain a new page at the same id).
        """
        import gc
        import weakref

        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        assert page in buf._attached  # type: ignore[attr-defined]
        assert isinstance(buf._attached, weakref.WeakSet)  # type: ignore[attr-defined]

        # Drop the strong ref + force GC → the WeakSet entry must vanish.
        del page
        gc.collect()
        assert len(buf._attached) == 0  # type: ignore[attr-defined]

        # A NEW page object (even if CPython reused the address) is not treated
        # as already-attached, so it gets its listeners registered.
        new_page = _fake_page()
        buf.attach(new_page)
        assert new_page.on.call_count == 4  # registered, not skipped
        del new_page

    def test_console_ring_evicts_oldest_on_overflow(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer(max_size=3)
        page = _fake_page()
        buf.attach(page)
        # Fire 5 console events into a size-3 buffer.
        for i in range(5):
            msg = MagicMock()
            msg.type = "log"
            msg.text = f"msg-{i}"
            _fire(page, "console", msg)
        msgs = buf.console_messages()
        assert len(msgs) == 3  # bounded
        # Oldest evicted; newest three kept.
        assert [m["text"] for m in msgs] == ["msg-2", "msg-3", "msg-4"]

    def test_seq_is_monotonic_across_event_types(self):
        """seq increments buffer-wide regardless of event type.

        (Console-only here; cross-type seq with pageerror is covered in Task 3
        once page-error capture lands.)"""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)

        cmsg = MagicMock()
        cmsg.type = "log"
        cmsg.text = "c"
        _fire(page, "console", cmsg)
        cmsg2 = MagicMock()
        cmsg2.type = "error"
        cmsg2.text = "c2"
        _fire(page, "console", cmsg2)

        assert buf.console_messages()[0]["seq"] == 1
        assert buf.console_messages()[1]["seq"] == 2
        assert buf.last_seq() == 2


# ============================================================================
# Task 2: console_messages() — level filter, limit, snapshot non-destructive
# ============================================================================


def _fire_console(page, msg_type, text):
    msg = MagicMock()
    msg.type = msg_type
    msg.text = text
    _fire(page, "console", msg)


class TestConsoleMessages:
    def test_level_filter_returns_only_matching_type(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_console(page, "log", "a")
        _fire_console(page, "error", "boom")
        _fire_console(page, "warning", "careful")
        _fire_console(page, "error", "boom2")

        errors = buf.console_messages(level="error")
        assert [m["text"] for m in errors] == ["boom", "boom2"]
        assert all(m["type"] == "error" for m in errors)

    def test_limit_returns_last_n(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        for i in range(10):
            _fire_console(page, "log", f"m{i}")

        last3 = buf.console_messages(limit=3)
        assert [m["text"] for m in last3] == ["m7", "m8", "m9"]

    def test_limit_none_returns_all(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        for i in range(5):
            _fire_console(page, "log", f"m{i}")
        assert len(buf.console_messages(limit=None)) == 5

    def test_snapshot_is_non_destructive(self):
        """Repeated reads return the same data; no clearing."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_console(page, "log", "once")

        first = buf.console_messages()
        second = buf.console_messages()
        assert first == second
        assert len(first) == 1

    def test_entry_shape_has_required_fields(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page(url="https://test.local")
        buf.attach(page)
        _fire_console(page, "error", "oops")

        e = buf.console_messages()[0]
        for k in ("seq", "timestamp_ms", "type", "text", "page_url"):
            assert k in e, f"missing {k}"
        assert e["page_url"] == "https://test.local"
        assert isinstance(e["timestamp_ms"], float)
        assert e["seq"] == 1


# ============================================================================
# Task 3: page_errors() — uncaught error capture + snapshot + limit
# ============================================================================


def _fire_pageerror(page, *, message, name=None, stack=None):
    err = MagicMock()
    err.message = message
    err.name = name
    err.stack = stack
    _fire(page, "pageerror", err)


class TestPageErrors:
    def test_captures_uncaught_errors(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_pageerror(page, message="Uncaught TypeError: x is not a function",
                        name="TypeError", stack="at foo (a.js:1:2)")

        errs = buf.page_errors()
        assert len(errs) == 1
        e = errs[0]
        assert e["message"] == "Uncaught TypeError: x is not a function"
        assert e["name"] == "TypeError"
        assert e["stack"] == "at foo (a.js:1:2)"

    def test_entry_shape_has_required_fields(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page(url="https://err.local")
        buf.attach(page)
        _fire_pageerror(page, message="boom")

        e = buf.page_errors()[0]
        for k in ("seq", "timestamp_ms", "message", "page_url"):
            assert k in e, f"missing {k}"
        assert e["page_url"] == "https://err.local"

    def test_limit_returns_last_n(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        for i in range(6):
            _fire_pageerror(page, message=f"e{i}")
        assert [e["message"] for e in buf.page_errors(limit=2)] == ["e4", "e5"]

    def test_handles_missing_stack_and_name_gracefully(self):
        """Real errors may not carry .stack or .name — capture must not crash."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        # A bare error with only .message (no .name, no .stack attrs).
        bare = MagicMock()
        bare.message = "no details"
        del bare.name
        del bare.stack
        _fire(page, "pageerror", bare)

        e = buf.page_errors()[0]
        assert e["message"] == "no details"
        assert e.get("name") is None
        assert e.get("stack") is None

    def test_seq_continues_from_console(self):
        """seq is buffer-wide; page errors continue the counter."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_console(page, "log", "first")          # seq 1
        _fire_pageerror(page, message="second")       # seq 2

        assert buf.console_messages()[0]["seq"] == 1
        assert buf.page_errors()[0]["seq"] == 2
        assert buf.last_seq() == 2


# ============================================================================
# Task 4: request capture — request_id assignment, requests() snapshot + filters
# ============================================================================


def _make_request(*, url, method="GET", resource_type="fetch",
                  headers=None, failure=None, is_navigation=False,
                  redirected_from=None):
    """Build a fake Playwright Request with a STABLE identity.

    Identity matters: the buffer correlates the later 'response' event back to
    this request via response.request (object identity), so each fake must be
    a distinct object."""
    req = MagicMock()
    req.url = url
    req.method = method
    req.resource_type = resource_type
    req.headers = headers or {}
    req.failure = (lambda: failure) if failure is not None else (lambda: None)
    req.is_navigation_request = (lambda: is_navigation)
    req.redirected_from = (lambda: redirected_from) if redirected_from else (lambda: None)
    return req


def _fire_request(page, request):
    _fire(page, "request", request)


class TestRequestCapture:
    def test_assigns_stable_request_id(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_request(page, _make_request(url="https://a.local"))

        rec = buf.requests()[0]
        assert rec["request_id"] == "r-1"
        assert rec["url"] == "https://a.local"
        assert rec["method"] == "GET"
        assert rec["resource_type"] == "fetch"

    def test_request_ids_increment_uniquely(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        for i in range(3):
            _fire_request(page, _make_request(url=f"https://{i}.local"))

        ids = [r["request_id"] for r in buf.requests()]
        assert ids == ["r-1", "r-2", "r-3"]

    def test_status_none_until_response(self):
        """A request with no response yet has status=None (not 0, not missing)."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_request(page, _make_request(url="https://pending.local"))

        rec = buf.requests()[0]
        assert rec["status"] is None
        assert rec["ok"] is None
        assert rec["failed"] is False

    def test_url_filter_substring_match(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_request(page, _make_request(url="https://api.local/users"))
        _fire_request(page, _make_request(url="https://cdn.local/style.css"))
        _fire_request(page, _make_request(url="https://api.local/posts"))

        api = buf.requests(url_filter="api.local")
        assert len(api) == 2
        assert all("api.local" in r["url"] for r in api)

    def test_resource_type_filter(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_request(page, _make_request(url="https://x.local", resource_type="fetch"))
        _fire_request(page, _make_request(url="https://x.local", resource_type="image"))

        imgs = buf.requests(resource_type="image")
        assert len(imgs) == 1
        assert imgs[0]["resource_type"] == "image"

    def test_limit_returns_last_n(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        for i in range(5):
            _fire_request(page, _make_request(url=f"https://{i}.local"))

        last2 = buf.requests(limit=2)
        assert [r["url"] for r in last2] == ["https://3.local", "https://4.local"]

    def test_entry_shape_has_required_fields(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page(url="https://page.local")
        buf.attach(page)
        _fire_request(page, _make_request(url="https://req.local", method="POST"))

        rec = buf.requests()[0]
        for k in ("seq", "request_id", "timestamp_ms", "method", "url",
                  "resource_type", "status", "page_url"):
            assert k in rec, f"missing {k}"
        assert rec["method"] == "POST"
        assert rec["page_url"] == "https://page.local"

    def test_snapshot_is_non_destructive(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_request(page, _make_request(url="https://once.local"))

        first = buf.requests()
        second = buf.requests()
        assert first == second
        assert len(first) == 1


# ============================================================================
# Tasks 5 + 6: response correlation, failure/header enrichment, request_detail
# ============================================================================


def _fire_response(page, *, request, status, status_text="OK", ok=True,
                   from_service_worker=False):
    """Build + fire a fake Playwright Response. response.request is the
    back-reference that lets the buffer correlate to the originating request."""
    resp = MagicMock()
    resp.request = request
    resp.status = status
    resp.status_text = status_text
    resp.ok = ok
    resp.from_service_worker = from_service_worker
    _fire(page, "response", resp)


class TestResponseCorrelation:
    def test_response_enriches_originating_request(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        req = _make_request(url="https://api.local/data")
        _fire_request(page, req)
        # Response arrives later, references the same request object.
        _fire_response(page, request=req, status=200, status_text="OK", ok=True)

        rec = buf.requests()[0]
        assert rec["status"] == 200
        assert rec["status_text"] == "OK"
        assert rec["ok"] is True
        assert rec["failed"] is False

    def test_4xx_marks_failed(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        req = _make_request(url="https://api.local/missing")
        _fire_request(page, req)
        _fire_response(page, request=req, status=404, status_text="Not Found", ok=False)

        rec = buf.requests()[0]
        assert rec["status"] == 404
        assert rec["ok"] is False

    def test_failed_only_filter_includes_errors_and_pending(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        ok_req = _make_request(url="https://ok.local")
        _fire_request(page, ok_req)
        _fire_response(page, request=ok_req, status=200, ok=True)
        bad_req = _make_request(url="https://bad.local")
        _fire_request(page, bad_req)
        _fire_response(page, request=bad_req, status=500, ok=False)
        pending_req = _make_request(url="https://pending.local")
        _fire_request(page, pending_req)  # no response

        failed = buf.requests(failed_only=True)
        urls = {r["url"] for r in failed}
        assert urls == {"https://bad.local", "https://pending.local"}

    def test_response_to_unknown_request_is_silently_dropped(self):
        """A response whose request we never buffered must not crash."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        orphan_req = _make_request(url="https://orphan.local")
        # Fire response without firing request first.
        _fire_response(page, request=orphan_req, status=200)
        assert buf.requests() == []  # nothing recorded, no crash


class TestFailureEnrichment:
    def test_failure_text_captured_from_request(self):
        """Request.failure() returns the failure text for net errors."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        req = _make_request(url="https://dead.local", failure="net::ERR_CONNECTION_REFUSED")
        _fire_request(page, req)

        rec = buf.requests()[0]
        assert rec["failed"] is True
        assert rec["failure_text"] == "net::ERR_CONNECTION_REFUSED"

    def test_no_failure_when_request_succeeds(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        req = _make_request(url="https://ok.local")  # failure=None default
        _fire_request(page, req)
        _fire_response(page, request=req, status=200, ok=True)

        rec = buf.requests()[0]
        assert rec["failed"] is False
        assert rec["failure_text"] is None


class TestHeaderNames:
    def test_header_names_are_keys_only(self):
        """Only header KEYS are captured, never values (sensitivity control)."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        req = _make_request(
            url="https://api.local",
            headers={"content-type": "application/json", "authorization": "Bearer SECRET"},
        )
        _fire_request(page, req)

        rec = buf.requests()[0]
        names = set(rec["header_names"])
        assert "content-type" in names
        assert "authorization" in names
        # No header VALUES appear anywhere in the record.
        serialized = str(rec)
        assert "SECRET" not in serialized
        assert "Bearer" not in serialized

    def test_empty_headers_yields_empty_header_names(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        _fire_request(page, _make_request(url="https://bare.local", headers={}))

        assert buf.requests()[0]["header_names"] == []


class TestRequestDetail:
    def test_returns_record_by_request_id(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        req = _make_request(url="https://detail.local")
        _fire_request(page, req)

        detail = buf.request_detail("r-1")
        assert detail is not None
        assert detail["request_id"] == "r-1"
        assert detail["url"] == "https://detail.local"

    def test_unknown_request_id_returns_none(self):
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        assert buf.request_detail("r-999") is None

    def test_detail_reflects_response_enrichment(self):
        """request_detail returns the live record (enriched after response)."""
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        buf = DiagnosticsBuffer()
        page = _fake_page()
        buf.attach(page)
        req = _make_request(url="https://live.local")
        _fire_request(page, req)
        assert buf.request_detail("r-1")["status"] is None
        _fire_response(page, request=req, status=201, status_text="Created", ok=True)
        assert buf.request_detail("r-1")["status"] == 201


# ============================================================================
# Tasks 7+8: Facade wiring — buffer constructed, attached on start + tab switch
# ============================================================================


class TestFacadeWiring:
    def test_superbrowser_exposes_diagnostics_property(self):
        """A constructed SuperBrowser (pre-start) exposes a DiagnosticsBuffer."""
        from super_browser import SuperBrowser
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        sb = SuperBrowser()
        assert isinstance(sb.diagnostics, DiagnosticsBuffer)

    def test_attach_diagnostics_helper_calls_buffer_attach(self):
        """_attach_diagnostics(raw_page) delegates to the buffer."""
        from super_browser import SuperBrowser

        sb = SuperBrowser()
        sb._diagnostics = MagicMock()  # type: ignore[assignment]
        fake_page = _fake_page()
        sb._attach_diagnostics(fake_page)
        sb._diagnostics.attach.assert_called_once_with(fake_page)

    def test_diagnostics_survives_across_attach_calls(self):
        """Repeated _attach_diagnostics calls on different pages hit the same
        buffer (session-wide, not per-page)."""
        from super_browser import SuperBrowser
        from super_browser.agent.diagnostics import DiagnosticsBuffer

        sb = SuperBrowser()
        original = sb.diagnostics
        p1 = _fake_page()
        p2 = _fake_page()
        sb._attach_diagnostics(p1)
        sb._attach_diagnostics(p2)
        # Same buffer instance the whole time.
        assert sb.diagnostics is original
        assert isinstance(sb.diagnostics, DiagnosticsBuffer)
