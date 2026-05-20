"""Inject delivery — install stealth scripts via CDP Fetch interception.

Two delivery mechanisms:

1. **Primary: Fetch.fulfillRequest body-splice** — intercept Document
   responses via ``Fetch.enable`` + ``Fetch.requestPaused``, inject a
   ``<script>`` tag into the HTML ``<head>``, respond with modified body
   via ``Fetch.fulfillRequest``.
2. **Fallback: Page.addScriptToEvaluateOnNewDocument** — for
   ``about:blank``, ``data:``, and other non-HTTP targets.

A CSP rewriter strips/relaxes Content-Security-Policy headers on
intercepted responses so the injected script is not blocked.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["InjectDelivery"]


class InjectDelivery:
    """Manages delivery of stealth inject scripts via CDP interception.

    Parameters
    ----------
    js_payload:
        The initial JavaScript payload to inject.
    """

    def __init__(self, js_payload: str = "") -> None:
        self._js_payload = js_payload
        self._stealth_bridge: Any = None
        self._cdp_bridge: Any = None
        self._page: Any = None
        self._installed = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def install(
        self,
        cdp_bridge: Any = None,
        page: Any = None,
        *,
        stealth_bridge: Any = None,
    ) -> None:
        """Set up Fetch interception and addInitScript fallback.

        Parameters
        ----------
        stealth_bridge:
            A :class:`StealthBridge` instance (preferred over *cdp_bridge*).
            Keyword-only to preserve backward compatibility with positional calls.
        cdp_bridge:
            A :class:`CDPBridge` instance for raw CDP access (fallback).
        page:
            The Patchright ``Page`` object (used for addInitScript).

        Precedence: stealth_bridge > cdp_bridge.
        """
        self._stealth_bridge = stealth_bridge
        self._cdp_bridge = stealth_bridge if stealth_bridge is not None else cdp_bridge
        self._page = page
        self._installed = True

        if not self._js_payload:
            logger.warning("InjectDelivery installed with empty payload")
            return

        # ── Primary: CDP Fetch interception ───────────────────────
        await self._install_fetch_interception()

        # ── Fallback: addInitScript for about:blank, data:, etc. ──
        await self._install_add_init_script()

        logger.info("InjectDelivery installed (Fetch + addInitScript)")

    async def update_payload(self, js_payload: str) -> None:
        """Update the active inject script.

        Takes effect on the next page load.  For immediate effect on the
        current page, call ``install()`` again.
        """
        self._js_payload = js_payload
        if self._installed and self._page:
            # Re-register the init script with updated payload.
            await self._install_add_init_script()
            logger.info("InjectDelivery payload updated (%d bytes)", len(js_payload))

    # ------------------------------------------------------------------
    # Internal: Fetch interception (primary)
    # ------------------------------------------------------------------

    async def _install_fetch_interception(self) -> None:
        """Register CDP Fetch.enable and handle requestPaused events."""
        if not self._cdp_bridge:
            return

        try:
            await self._send("Fetch.enable", {
                "patterns": [
                    {
                        "resourceType": "Document",
                        "requestStage": "Response",
                    },
                ],
            })
        except Exception as exc:
            logger.warning("Fetch.enable failed: %s", exc)
            return

        # Register the paused handler on the underlying CDP session.
        # StealthBridge wraps CDPBridge — access via ._cdp._session.
        raw_session = self._get_raw_session()
        if raw_session is None:
            logger.warning("No raw CDP session available for Fetch interception")
            return

        delivery_ref = self

        async def _on_fetch_paused(params: dict) -> None:
            """Handle Fetch.requestPaused — inject script into HTML body."""
            request_id = params.get("requestId", "")
            response_status_code = params.get("responseStatusCode", 200)
            response_headers = params.get("responseHeaders", [])

            try:
                # Get the response body.
                body_result = await self._send(
                    "Fetch.getResponseBody", {"requestId": request_id},
                )
                if not body_result.ok or not body_result.data:
                    await self._fulfill_passthrough(request_id, response_status_code, response_headers)
                    return

                body_data = body_result.data
                body_text = body_data.get("body", "")
                is_base64 = body_data.get("base64Encoded", False)

                if is_base64:
                    # Binary response — skip injection.
                    await self._fulfill_passthrough(request_id, response_status_code, response_headers)
                    return

                # Only inject into HTML responses.
                content_type = ""
                for h in response_headers:
                    if h.get("name", "").lower() == "content-type":
                        content_type = h.get("value", "")
                        break

                if "text/html" not in content_type:
                    await self._fulfill_passthrough(request_id, response_status_code, response_headers)
                    return

                # CSP rewriting — strip/relax CSP headers.
                cleaned_headers = delivery_ref._strip_csp_headers(response_headers)

                # Body-splice: inject <script> into <head>.
                modified_body = delivery_ref._splice_script(body_text)

                await self._send("Fetch.fulfillRequest", {
                    "requestId": request_id,
                    "responseCode": response_status_code,
                    "responseHeaders": cleaned_headers,
                    "body": modified_body,
                })

            except Exception as exc:
                logger.warning("Fetch.requestPaused handler failed: %s", exc)
                try:
                    await self._send("Fetch.continueResponse", {
                        "requestId": request_id,
                    })
                except Exception:
                    pass

        try:
            raw_session.on("Fetch.requestPaused", _on_fetch_paused)
        except Exception as exc:
            logger.warning("Failed to register Fetch.requestPaused handler: %s", exc)

    async def _fulfill_passthrough(
        self,
        request_id: str,
        status_code: int,
        headers: list[dict],
    ) -> None:
        """Fulfill a request without modification."""
        try:
            await self._send("Fetch.continueResponse", {
                "requestId": request_id,
            })
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Internal: addInitScript fallback
    # ------------------------------------------------------------------

    async def _install_add_init_script(self) -> None:
        """Register Page.addScriptToEvaluateOnNewDocument as fallback.

        This handles about:blank, data: URLs, and other non-HTTP targets
        that bypass Fetch interception.
        """
        if not self._page or not self._js_payload:
            return

        try:
            # Use Patchright's addInitScript which wraps
            # Page.addScriptToEvaluateOnNewDocument internally.
            if hasattr(self._page, "add_init_script"):
                await self._page.add_init_script(self._js_payload)
            elif hasattr(self._page, "addInitScript"):
                await self._page.addInitScript(self._js_payload)
        except Exception as exc:
            logger.warning("addInitScript fallback failed: %s", exc)

    # ------------------------------------------------------------------
    # Internal: body-splice helpers
    # ------------------------------------------------------------------

    def _splice_script(self, body: str) -> str:
        """Inject the stealth ``<script>`` tag into HTML ``<head>``.

        Returns the modified HTML string.
        """
        if not self._js_payload:
            return body

        script_tag = f"<script>\n{self._js_payload}\n</script>"

        if "<head" in body:
            head_open = body.find("<head")
            head_close = body.find(">", head_open)
            if head_close != -1:
                return body[: head_close + 1] + script_tag + body[head_close + 1 :]

        if "<html" in body:
            return body.replace("</html>", f"{script_tag}</html>", 1)

        return f"<html><head>{script_tag}</head><body>{body}</body></html>"

    # ------------------------------------------------------------------
    # Internal: bridge helpers
    # ------------------------------------------------------------------

    async def _send(self, method: str, params: dict) -> Any:
        """Dispatch a CDP command via stealth_bridge.cdp_send or cdp_bridge.send."""
        if self._stealth_bridge is not None and hasattr(self._stealth_bridge, "cdp_send"):
            return await self._stealth_bridge.cdp_send(method, params)
        return await self._cdp_bridge.send(method, params)

    def _get_raw_session(self) -> Any:
        """Get the raw CDP session for event subscription.

        StealthBridge wraps CDPBridge: access via ._cdp._session.
        Fallback: cdp_bridge._session (backward compat).
        """
        if self._stealth_bridge is not None:
            inner = getattr(self._stealth_bridge, "_cdp", None)
            if inner is not None:
                return getattr(inner, "_session", None)
        return getattr(self._cdp_bridge, "_session", None)

    @staticmethod
    def _strip_csp_headers(headers: list[dict]) -> list[dict]:
        """Remove Content-Security-Policy headers from the response.

        Returns a new list with CSP headers stripped.
        """
        csp_names = {"content-security-policy", "content-security-policy-report-only"}
        return [
            h for h in headers
            if h.get("name", "").lower() not in csp_names
        ]
