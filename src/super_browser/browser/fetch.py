"""BrowserFetch — HTTP client that routes through Chromium via CDP.

Dual-mechanism routing:

* **Mechanism A** — ``Network.loadNetworkResource`` for simple GETs.
  Bypasses same-origin policy at the network layer.  Body is returned
  as an ``IO.StreamHandle`` which is drained via ``IO.read`` in 64 KiB
  chunks.

* **Mechanism B** — ``Runtime.callFunctionOn`` with an in-page ``fetch()``
  call for POSTs, custom headers, and request bodies.  Full ``RequestInit``
  semantics pass through; CORS applies the same as a real browser.

Both mechanisms inherit the browser's cookie jar, proxy, and TLS stack.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
from dataclasses import dataclass
from typing import Any, Optional

from super_browser.browser.cdp import CDPBridge

logger = logging.getLogger(__name__)

_CHUNK_SIZE = 64 * 1024  # 64 KiB — same window DevTools frontend uses


@dataclass(frozen=True)
class BrowserFetchResponse:
    """Immutable response from a CDP-routed fetch."""

    status: int
    headers: dict[str, str]
    body: bytes

    @property
    def ok(self) -> bool:
        """``True`` when the HTTP status is in the 2xx–3xx range."""
        return 200 <= self.status < 400

    def text(self, encoding: str = "utf-8") -> str:
        """Decode the body as text."""
        return self.body.decode(encoding)

    def json(self) -> Any:
        """Parse the body as JSON."""
        return json.loads(self.body)


class BrowserFetch:
    """HTTP client that routes every request through Chromium via CDP.

    Parameters
    ----------
    bridge:
        The :class:`CDPBridge` used for all CDP protocol calls.

    The first fetch lazily allocates an ``about:blank`` scratch frame and
    reuses it for all subsequent calls.  Call :meth:`close` to tear it
    down.
    """

    def __init__(self, bridge: CDPBridge) -> None:
        self._bridge = bridge
        self._scratch: Optional[_ScratchFrame] = None
        self._scratch_lock = asyncio.Lock()
        self._document_object_id: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def fetch(
        self,
        url: str,
        init: Optional[dict[str, Any]] = None,
    ) -> BrowserFetchResponse:
        """Fetch *url* through Chromium.

        ``init`` mirrors the ``RequestInit`` dictionary — accepted keys
        are ``method``, ``headers``, ``body``, etc.  When ``init`` is
        ``None`` or contains only a GET method with no headers/body,
        Mechanism A (``Network.loadNetworkResource``) is used; otherwise
        Mechanism B (in-page ``fetch``) is used.
        """
        if self._is_simple_get(init):
            return await self._fetch_via_load_network_resource(url)
        return await self._fetch_via_page_evaluate(url, init or {})

    async def close(self) -> None:
        """Close the scratch frame (best-effort)."""
        if self._scratch is None:
            return
        scratch = self._scratch
        self._scratch = None
        self._document_object_id = None
        try:
            await self._bridge.send(
                "Target.closeTarget",
                {"targetId": scratch.target_id},
            )
        except Exception:
            pass  # best-effort

    # ------------------------------------------------------------------
    # Mechanism A — Network.loadNetworkResource
    # ------------------------------------------------------------------

    async def _fetch_via_load_network_resource(
        self,
        url: str,
    ) -> BrowserFetchResponse:
        """Simple GET via ``Network.loadNetworkResource`` + IO stream drain."""
        scratch = await self._ensure_scratch_frame()
        result = await self._bridge.send(
            "Network.loadNetworkResource",
            {
                "frameId": scratch.frame_id,
                "url": url,
                "options": {
                    "disableCache": False,
                    "includeCredentials": True,
                },
            },
        )
        if not result.ok:
            raise CdpFetchError(
                f"Network.loadNetworkResource failed: {result.error}"
            )

        resource = result.data.get("resource", {}) if result.data else {}
        if not resource.get("success", False):
            status = resource.get("httpStatusCode")
            err_name = resource.get("netErrorName", "fetch failed")
            suffix = f" (httpStatus={status})" if status else ""
            raise CdpFetchError(f"{err_name}{suffix}")

        status = resource.get("httpStatusCode", 200)
        if not isinstance(status, int) or status <= 0:
            status = 200

        headers = _flatten_headers(resource.get("headers", {}))

        stream_handle = resource.get("stream")
        if not stream_handle:
            return BrowserFetchResponse(
                status=status,
                headers=headers,
                body=b"",
            )

        body = await self._drain_io_stream(stream_handle)
        return BrowserFetchResponse(status=status, headers=headers, body=body)

    async def _drain_io_stream(self, handle: str) -> bytes:
        """Drain an ``IO.StreamHandle`` in 64 KiB chunks."""
        chunks: list[bytes] = []
        for _ in range(10_000):  # safety bound
            r = await self._bridge.send(
                "IO.read",
                {"handle": handle, "size": _CHUNK_SIZE},
            )
            if not r.ok:
                break
            data_str = r.data.get("data", "") if r.data else ""
            if data_str:
                is_b64 = r.data.get("base64Encoded", False) if r.data else False
                chunks.append(
                    base64.b64decode(data_str) if is_b64
                    else data_str.encode("utf-8")
                )
            if r.data.get("eof", False) if r.data else True:
                break
        try:
            await self._bridge.send("IO.close", {"handle": handle})
        except Exception:
            pass  # best-effort
        return b"".join(chunks)

    # ------------------------------------------------------------------
    # Mechanism B — Runtime.callFunctionOn with fetch()
    # ------------------------------------------------------------------

    async def _fetch_via_page_evaluate(
        self,
        url: str,
        init: dict[str, Any],
    ) -> BrowserFetchResponse:
        """Non-GET or complex init via in-page ``fetch``."""
        scratch = await self._ensure_scratch_frame()
        doc_id = await self._get_document_object_id(scratch.session_id)

        init_json = json.dumps(init)
        fn_decl = (
            "async function(urlArg, initJson) {"
            "  const init = JSON.parse(initJson);"
            "  const r = await fetch(urlArg, init);"
            "  const buf = await r.arrayBuffer();"
            "  let b64 = '';"
            "  const view = new Uint8Array(buf);"
            "  const CHUNK = 0x8000;"
            "  for (let i = 0; i < view.length; i += CHUNK) {"
            "    let s = '';"
            "    const end = Math.min(i + CHUNK, view.length);"
            "    for (let j = i; j < end; j++) s += String.fromCharCode(view[j]);"
            "    b64 += btoa(s);"
            "  }"
            "  const headers = {};"
            "  r.headers.forEach((v, k) => { headers[k] = v; });"
            "  return { status: r.status, headers, bodyB64: b64 };"
            "}"
        )

        call_result = await self._bridge.send(
            "Runtime.callFunctionOn",
            {
                "functionDeclaration": fn_decl,
                "objectId": doc_id,
                "arguments": [{"value": url}, {"value": init_json}],
                "returnByValue": True,
                "awaitPromise": True,
            },
        )
        if not call_result.ok:
            raise CdpFetchError(
                f"Runtime.callFunctionOn failed: {call_result.error}"
            )

        data = call_result.data or {}
        exception = data.get("exceptionDetails")
        if exception:
            desc = (
                exception.get("exception", {}).get("description")
                or exception.get("text")
                or "page-evaluate fetch threw"
            )
            raise CdpFetchError(desc)

        result_value = data.get("result", {}).get("value")
        if result_value is None:
            raise CdpFetchError("page-evaluate fetch returned undefined")

        headers = result_value.get("headers", {})
        body_b64 = result_value.get("bodyB64", "")
        status = result_value.get("status", 200)

        body = base64.b64decode(body_b64) if body_b64 else b""
        return BrowserFetchResponse(
            status=status,
            headers=headers,
            body=body,
        )

    # ------------------------------------------------------------------
    # Scratch Frame Lifecycle
    # ------------------------------------------------------------------

    async def _ensure_scratch_frame(self) -> _ScratchFrame:
        """Lazily create and cache the ``about:blank`` scratch frame."""
        if self._scratch is not None:
            return self._scratch
        async with self._scratch_lock:
            # Double-check after acquiring the lock
            if self._scratch is not None:
                return self._scratch
            self._scratch = await self._create_scratch_frame()
            return self._scratch

    async def _create_scratch_frame(self) -> _ScratchFrame:
        """Allocate a new scratch target via ``Target.createTarget``."""
        created = await self._bridge.send(
            "Target.createTarget",
            {"url": "about:blank"},
        )
        if not created.ok:
            raise CdpFetchError(
                f"Target.createTarget failed: {created.error}"
            )
        target_id = created.data["targetId"]

        attached = await self._bridge.send(
            "Target.attachToTarget",
            {"targetId": target_id, "flatten": True},
        )
        if not attached.ok:
            raise CdpFetchError(
                f"Target.attachToTarget failed: {attached.error}"
            )
        session_id = attached.data["sessionId"]

        # Get the frame tree to extract the main frame id
        tree = await self._bridge.send(
            "Page.getFrameTree",
            {},
        )
        if not tree.ok:
            raise CdpFetchError(
                f"Page.getFrameTree failed: {tree.error}"
            )
        frame_id = tree.data["frameTree"]["frame"]["id"]

        return _ScratchFrame(
            target_id=target_id,
            session_id=session_id,
            frame_id=frame_id,
        )

    async def _get_document_object_id(self, session_id: str) -> str:
        """Resolve the scratch page's ``document`` objectId."""
        if self._document_object_id is not None:
            return self._document_object_id

        doc = await self._bridge.send(
            "DOM.getDocument",
            {"depth": 0},
        )
        if not doc.ok:
            raise CdpFetchError(
                f"DOM.getDocument failed: {doc.error}"
            )
        node_id = doc.data["root"]["nodeId"]

        resolved = await self._bridge.send(
            "DOM.resolveNode",
            {"nodeId": node_id},
        )
        if not resolved.ok:
            raise CdpFetchError(
                f"DOM.resolveNode failed: {resolved.error}"
            )
        object_id = resolved.data.get("object", {}).get("objectId")
        if not object_id:
            raise CdpFetchError(
                "scratch document objectId unresolved"
            )
        self._document_object_id = object_id
        return object_id

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_simple_get(init: Optional[dict[str, Any]]) -> bool:
        """Return ``True`` when *init* qualifies for Mechanism A."""
        return (
            init is None
            or (
                init.get("method", "GET").upper() == "GET"
                and "headers" not in init
                and "body" not in init
            )
        )


@dataclass(frozen=True)
class _ScratchFrame:
    """Cached metadata for the scratch ``about:blank`` frame."""

    target_id: str
    session_id: str
    frame_id: str


class CdpFetchError(Exception):
    """Error raised when a CDP-routed fetch fails."""


def _flatten_headers(raw: Any) -> dict[str, str]:
    """Normalise CDP header maps to ``dict[str, str]``."""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, str] = {}
    for k, v in raw.items():
        if isinstance(v, list):
            out[k] = ", ".join(str(x) for x in v)
        else:
            out[k] = str(v)
    return out
