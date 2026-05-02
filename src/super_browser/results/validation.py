"""PreExecutionValidator — selector/xpath validation before browser dispatch."""

from __future__ import annotations

import time
import uuid
from typing import Any

from super_browser.results.types import (
    ActionError,
    ActionMethod,
    ActionResult,
    ErrorCategory,
    ResultMeta,
)


class PreExecutionValidator:
    """Validates selectors/xpaths against the current DOM before dispatching.

    Prevents hallucinated selectors from reaching the browser.
    Ported from LaVague _verify_llm_response pattern.
    """

    def __init__(self, page: Any) -> None:
        self._page = page

    def validate_selector(self, selector: str) -> ActionResult:
        """Check that a CSS selector matches at least one element."""
        import json as _json
        start = time.monotonic()
        try:
            # HB-09-01: No f-string interpolation — selector passed as JSON arg
            selector_json = _json.dumps(selector)
            count = self._page.evaluate(
                '(function() { var sel = JSON.parse(' + selector_json + ');'
                ' return document.querySelectorAll(sel).length; })()'
            )
            elapsed = (time.monotonic() - start) * 1000
            if count == 0:
                return ActionResult(
                    ok=False,
                    error=ActionError(
                        category=ErrorCategory.VALIDATION,
                        message=f"Selector matches 0 elements: {selector}",
                        selector=selector,
                        recoverable=True,
                        retry_hint="try alternative selector or coordinate tier",
                    ),
                    meta=ResultMeta(
                        trace_id=str(uuid.uuid4()), duration_ms=elapsed,
                        method=ActionMethod.SELECTOR,
                    ),
                )
            return ActionResult(
                ok=True,
                data={"match_count": count},
                meta=ResultMeta(
                    trace_id=str(uuid.uuid4()), duration_ms=elapsed,
                    method=ActionMethod.SELECTOR,
                ),
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return ActionResult(
                ok=False,
                error=ActionError(
                    category=ErrorCategory.VALIDATION,
                    message=f"Selector validation raised: {exc}",
                    selector=selector,
                    recoverable=False,
                ),
                meta=ResultMeta(
                    trace_id=str(uuid.uuid4()), duration_ms=elapsed,
                ),
            )

    def validate_xpath(self, xpath: str) -> ActionResult:
        """Check that an XPath expression matches at least one element."""
        import json as _json
        start = time.monotonic()
        try:
            # HB-09-01: No f-string interpolation — xpath passed as JSON arg
            xpath_json = _json.dumps(xpath)
            result = self._page.evaluate(
                '(function() { var xp = JSON.parse(' + xpath_json + ');'
                ' return document.evaluate(xp, document, null, '
                '   XPathResult.ORDERED_NODE_SNAPSHOT_TYPE, null).snapshotLength;'
                ' })()'
            )
            elapsed = (time.monotonic() - start) * 1000
            if result == 0:
                return ActionResult(
                    ok=False,
                    error=ActionError(
                        category=ErrorCategory.VALIDATION,
                        message=f"XPath matches 0 elements: {xpath}",
                        selector=xpath,
                        recoverable=True,
                        retry_hint="try alternative xpath or coordinate tier",
                    ),
                    meta=ResultMeta(
                        trace_id=str(uuid.uuid4()), duration_ms=elapsed,
                    ),
                )
            return ActionResult(
                ok=True,
                data={"match_count": result},
                meta=ResultMeta(
                    trace_id=str(uuid.uuid4()), duration_ms=elapsed,
                ),
            )
        except Exception as exc:
            elapsed = (time.monotonic() - start) * 1000
            return ActionResult(
                ok=False,
                error=ActionError(
                    category=ErrorCategory.VALIDATION,
                    message=f"XPath validation raised: {exc}",
                    selector=xpath,
                    recoverable=False,
                ),
                meta=ResultMeta(
                    trace_id=str(uuid.uuid4()), duration_ms=elapsed,
                ),
            )
