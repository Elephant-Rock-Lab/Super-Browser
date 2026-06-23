"""Session-wide diagnostics capture for page events.

Wires Playwright/Patchright page-event listeners (console, pageerror, request,
response) into bounded ring buffers that survive tab switches. Read semantics
are snapshots (non-destructive): callers get list-copies; the bounded deques
naturally drop the oldest entries.

Designed for the MCP diagnostics tool pack — an inspect-tier explainability
layer for failed reads/rendering. No action gate, no side effects, no response
bodies, no raw header values (header keys only).
"""

from __future__ import annotations

import time
from collections import deque
from typing import Any

_DEFAULT_MAX_SIZE = 500


def _safe_call(obj: Any, attr: str, *, default: Any = None) -> Any:
    """Call a sync attr/method on a Playwright object, swallowing errors.

    Many Playwright surfaces expose properties that are sometimes methods,
    sometimes attributes, and can raise if the underlying handle is gone.
    Used only in the sync event handlers.
    """
    fn = getattr(obj, attr, None)
    if fn is None:
        return default
    try:
        return fn() if callable(fn) else fn
    except Exception:  # noqa: BLE001
        return default


class DiagnosticsBuffer:
    """Session-wide ring buffers for page diagnostic events.

    Three bounded deques (console / errors / requests) plus a monotonic seq
    counter. Reads are snapshots (non-destructive). ``attach()`` is idempotent
    by raw-page identity (tracked via a ``WeakSet``), so it is safe to call
    across repeated tab switches on the same underlying page.

    Event handlers are intentionally sync-safe — they never ``await`` inside
    ``page.on(...)`` callbacks. All Playwright/Patchright properties read in
    the handlers (``ConsoleMessage.type/.text``, ``Request.method/.url/...``,
    ``Request.failure``, ``Request.timing``) are sync.
    """

    def __init__(self, max_size: int = _DEFAULT_MAX_SIZE) -> None:
        self.max_size = max_size
        self._console: deque[dict] = deque(maxlen=max_size)
        self._errors: deque[dict] = deque(maxlen=max_size)
        self._requests: deque[dict] = deque(maxlen=max_size)
        self._seq = 0
        self._request_counter = 0
        # request_id -> record, for O(1) request_detail lookup.
        self._req_index: dict[str, dict] = {}
        # id(Playwright Request obj) -> request_id, for response correlation
        # via response.request back-reference. (Request objects are hashable by
        # identity; we key by id() to avoid holding strong refs in the dict.)
        self._req_obj_index: dict[int, str] = {}
        # Idempotent-attach tracking by raw page identity.
        self._attached: set[int] = set()

    # --- internal helpers ---

    def _next_seq(self) -> int:
        self._seq += 1
        return self._seq

    @staticmethod
    def _now_ms() -> float:
        return time.time() * 1000.0

    def _on_console(self, raw_page: Any, message: Any) -> None:
        self._console.append({
            "seq": self._next_seq(),
            "timestamp_ms": self._now_ms(),
            "type": getattr(message, "type", None),
            "text": getattr(message, "text", None),
            "page_url": getattr(raw_page, "url", None),
        })

    # --- attach / detach ---

    def attach(self, raw_page: Any) -> None:
        """Wire console/pageerror/request/response listeners onto ``raw_page``.

        Idempotent by raw-page identity: a second call with the same page
        object is a no-op. Safe across repeated tab switches.
        """
        page_id = id(raw_page)
        if page_id in self._attached:
            return
        self._attached.add(page_id)

        raw_page.on("console", lambda msg: self._on_console(raw_page, msg))
        # pageerror/request/response wired in later tasks.
        raw_page.on("pageerror", lambda err: self._on_pageerror(raw_page, err))
        raw_page.on("request", lambda req: self._on_request(raw_page, req))
        raw_page.on("response", lambda resp: self._on_response(raw_page, resp))

    def detach(self, raw_page: Any) -> None:
        """Remove a page from the attached set so it can be re-attached.

        Note: Playwright/Patchright does not expose listener removal on the
        Page object, so this only clears the idempotency guard. Listeners on
        a page that is being closed are harmless (the page is GC'd).
        """
        self._attached.discard(id(raw_page))

    # --- placeholders for later tasks ---

    def _on_pageerror(self, raw_page: Any, error: Any) -> None:
        # Real page errors may carry only .message; .name/.stack are optional.
        # getattr-with-default keeps the handler robust without swallowing the
        # event on a missing attribute.
        self._errors.append({
            "seq": self._next_seq(),
            "timestamp_ms": self._now_ms(),
            "message": getattr(error, "message", str(error)),
            "name": getattr(error, "name", None),
            "stack": getattr(error, "stack", None),
            "page_url": getattr(raw_page, "url", None),
        })

    def _on_request(self, raw_page: Any, request: Any) -> None:
        # Assign a stable request_id and capture the request-side fields.
        # Response-side fields (status/status_text/ok) are filled in by
        # _on_response via the correlation index. Failure/header enrichment is
        # captured here (sync) since the Request object is available.
        self._request_counter += 1
        request_id = f"r-{self._request_counter}"
        seq = self._next_seq()

        # redirected_from: a Playwright Request or None. Correlate to our
        # request_id if we've seen it; else record None.
        redirected_from_obj = _safe_call(request, "redirected_from", default=None)
        redirected_from_id = (
            self._req_obj_index.get(id(redirected_from_obj))
            if redirected_from_obj is not None else None
        )

        # Failure text: Request.failure() returns a string or None for net errors.
        failure_text = _safe_call(request, "failure", default=None)

        # Header NAMES only (keys), never values — sensitivity control.
        headers = _safe_call(request, "headers", default={}) or {}
        try:
            header_names = list(headers.keys())
        except Exception:  # noqa: BLE001
            header_names = []

        record = {
            "seq": seq,
            "request_id": request_id,
            "timestamp_ms": self._now_ms(),
            "method": getattr(request, "method", None),
            "url": getattr(request, "url", None),
            "resource_type": getattr(request, "resource_type", None),
            "is_navigation": bool(_safe_call(request, "is_navigation_request", default=False)),
            "redirected_from": redirected_from_id,
            "status": None,
            "status_text": None,
            "ok": None,
            "failed": failure_text is not None,
            "failure_text": failure_text,
            "header_names": header_names,
            "page_url": getattr(raw_page, "url", None),
        }
        self._requests.append(record)
        self._req_index[request_id] = record
        self._req_obj_index[id(request)] = request_id

    def _on_response(self, raw_page: Any, response: Any) -> None:
        # Correlate back to the originating request via response.request, then
        # enrich the record with status/status_text/ok. If we never buffered
        # the request (e.g. started mid-session), silently drop.
        origin = getattr(response, "request", None)
        if origin is None:
            return
        request_id = self._req_obj_index.get(id(origin))
        if request_id is None:
            return
        record = self._req_index.get(request_id)
        if record is None:
            return
        status = _safe_call(response, "status", default=None)
        record["status"] = status
        record["status_text"] = _safe_call(response, "status_text", default=None)
        record["ok"] = _safe_call(response, "ok", default=None)
        # A response with status>=400 is a failure even if the request had no
        # net-level failure_text.
        if status is not None and status >= 400:
            record["failed"] = True

    # --- snapshot accessors ---

    def last_seq(self) -> int:
        """The highest seq assigned so far (0 before any event)."""
        return self._seq

    def console_messages(
        self, *, level: str | None = None, limit: int = 100,
    ) -> list[dict]:
        """Snapshot of console entries (newest-last), optionally filtered by level."""
        items = list(self._console)
        if level is not None:
            items = [e for e in items if e.get("type") == level]
        return items[-limit:] if limit is not None else items

    def page_errors(self, *, limit: int = 100) -> list[dict]:
        """Snapshot of uncaught page errors (newest-last)."""
        items = list(self._errors)
        return items[-limit:] if limit is not None else items

    def requests(
        self,
        *,
        url_filter: str | None = None,
        resource_type: str | None = None,
        failed_only: bool = False,
        limit: int = 100,
    ) -> list[dict]:
        """Snapshot of request records (newest-last).

        - ``url_filter``: substring match against the request URL.
        - ``resource_type``: exact match (e.g. "fetch", "xhr", "image").
        - ``failed_only``: requests where failed OR status>=400 OR status is None.
        - ``limit``: return the last N (None = all).
        """
        items = list(self._requests)
        if url_filter is not None:
            items = [r for r in items if r.get("url") and url_filter in r["url"]]
        if resource_type is not None:
            items = [r for r in items if r.get("resource_type") == resource_type]
        if failed_only:
            items = [
                r for r in items
                if r.get("failed") or (r.get("status") is not None and r["status"] >= 400)
                or r.get("status") is None
            ]
        return items[-limit:] if limit is not None else items

    def request_detail(self, request_id: str) -> dict | None:
        """One record by request_id, or None if not buffered/evicted.

        Returns the live record (reflects response enrichment that arrived
        after the request event). The MCP tool layer turns None into a
        structured ``{ok: false, reason: "not_found"}`` response.
        """
        rec = self._req_index.get(request_id)
        return dict(rec) if rec is not None else None
