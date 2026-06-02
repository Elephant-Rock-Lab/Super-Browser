"""Enhanced Turnstile auto-solver — invisible and managed challenge handling.

Gate 4-A of the v2.0 roadmap. Extends the basic Turnstile resolver with:

- Version detection (invisible vs managed) via iframe attributes
- Configurable timeout and max retries
- Success rate logging
- Fallback strategy for managed challenges
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TurnstileVersion(StrEnum):
    """Turnstile challenge versions."""

    INVISIBLE = "invisible"  # Auto-processed, no user interaction
    MANAGED = "managed"      # Shows interactive widget
    UNKNOWN = "unknown"


@dataclass
class TurnstileResult:
    """Outcome of a Turnstile resolution attempt."""

    resolved: bool
    version: TurnstileVersion
    strategy: str
    duration_ms: float
    retries: int = 0
    token_length: int = 0


@dataclass
class TurnstileConfig:
    """Configuration for Turnstile resolution."""

    timeout: float = 30.0
    max_retries: int = 3
    retry_delay: float = 2.0
    poll_interval: float = 0.5


# ---------------------------------------------------------------------------
# Version detection
# ---------------------------------------------------------------------------


def detect_turnstile_version(iframe_src: str) -> TurnstileVersion:
    """Detect Turnstile version from the iframe src URL.

    Turnstile URLs contain query parameters indicating the mode:
    - 'invisible' for invisible challenges
    - 'managed' for interactive challenges
    - Default (no mode param) is typically invisible
    """
    if not iframe_src:
        return TurnstileVersion.UNKNOWN

    src_lower = iframe_src.lower()
    if "invisible" in src_lower or "mode=invisible" in src_lower:
        return TurnstileVersion.INVISIBLE
    if "managed" in src_lower or "mode=managed" in src_lower:
        return TurnstileVersion.MANAGED

    # Check for explicit 'execution' parameter
    if "execution=render" in src_lower:
        return TurnstileVersion.MANAGED
    if "execution=execute" in src_lower:
        return TurnstileVersion.INVISIBLE

    # Default: most Turnstile deployments are invisible
    return TurnstileVersion.INVISIBLE


# ---------------------------------------------------------------------------
# Resolution strategies
# ---------------------------------------------------------------------------


async def solve_turnstile(
    page: Any,
    cdp: Any,
    *,
    config: Optional[TurnstileConfig] = None,
) -> TurnstileResult:
    """Attempt to solve a Cloudflare Turnstile challenge.

    Strategy:
    1. Detect the Turnstile iframe
    2. Determine version (invisible vs managed)
    3. For invisible: wait for cf-turnstile-response token
    4. For managed: click the challenge widget, wait for token
    5. Retry on failure up to max_retries

    Args:
        page: Browser page with query_selector/wait_for_selector support.
        cdp: CDP bridge for Runtime.evaluate.
        config: Resolution configuration.

    Returns:
        TurnstileResult with resolution details.
    """
    config = config or TurnstileConfig()
    start = time.monotonic()
    retries = 0

    # Step 1: Find the Turnstile iframe
    iframe_src = await _find_turnstile_iframe(page)
    if iframe_src is None:
        return TurnstileResult(
            resolved=False,
            version=TurnstileVersion.UNKNOWN,
            strategy="no_iframe_found",
            duration_ms=(time.monotonic() - start) * 1000,
        )

    version = detect_turnstile_version(iframe_src)

    # Step 2: Apply version-specific strategy
    for attempt in range(config.max_retries + 1):
        retries = attempt
        try:
            if version == TurnstileVersion.INVISIBLE:
                success = await _solve_invisible(page, cdp, config)
            else:
                success = await _solve_managed(page, cdp, config)

            if success:
                # Extract token length for logging
                token_len = await _get_token_length(cdp)
                duration_ms = (time.monotonic() - start) * 1000
                logger.info(
                    "Turnstile solved: version=%s, retries=%d, duration=%.0fms",
                    version.value, retries, duration_ms,
                )
                return TurnstileResult(
                    resolved=True,
                    version=version,
                    strategy=f"page_interaction:{version.value}",
                    duration_ms=duration_ms,
                    retries=retries,
                    token_length=token_len,
                )
        except Exception as exc:
            logger.debug("Turnstile attempt %d failed: %s", attempt, exc)

        # Retry delay
        if attempt < config.max_retries:
            await asyncio.sleep(config.retry_delay)

    duration_ms = (time.monotonic() - start) * 1000
    logger.warning(
        "Turnstile NOT solved: version=%s, retries=%d, duration=%.0fms",
        version.value, retries, duration_ms,
    )
    return TurnstileResult(
        resolved=False,
        version=version,
        strategy=f"failed_after_{retries}_retries",
        duration_ms=duration_ms,
        retries=retries,
    )


async def _find_turnstile_iframe(page: Any) -> Optional[str]:
    """Find the Turnstile iframe and return its src."""
    try:
        el = await page.wait_for_selector(
            'iframe[src*="challenges.cloudflare.com"]',
            timeout=5000,
        )
        if el:
            src = await el.get_attribute("src")
            return src
    except Exception:
        pass
    return None


async def _solve_invisible(page: Any, cdp: Any, config: TurnstileConfig) -> bool:
    """Solve an invisible Turnstile challenge by waiting for the response token."""
    js = (
        "(function() {"
        "  var el = document.querySelector('[name=\"cf-turnstile-response\"]');"
        "  return el ? (el.value || '').length > 0 : false;"
        "})()"
    )
    return await _poll_js_true(cdp, js, timeout=config.timeout, interval=config.poll_interval)


async def _solve_managed(page: Any, cdp: Any, config: TurnstileConfig) -> bool:
    """Solve a managed Turnstile challenge by clicking the widget."""
    try:
        # Click the Turnstile iframe/widget
        iframe = await page.wait_for_selector(
            'iframe[src*="challenges.cloudflare.com"]',
            timeout=5000,
        )
        if iframe:
            await iframe.click()
    except Exception:
        pass

    # Wait for the response token
    js = (
        "(function() {"
        "  var el = document.querySelector('[name=\"cf-turnstile-response\"]');"
        "  return el ? (el.value || '').length > 0 : false;"
        "})()"
    )
    return await _poll_js_true(cdp, js, timeout=config.timeout, interval=config.poll_interval)


async def _get_token_length(cdp: Any) -> int:
    """Get the length of the Turnstile response token."""
    js = (
        "(function() {"
        "  var el = document.querySelector('[name=\"cf-turnstile-response\"]');"
        "  return el ? (el.value || '').length : 0;"
        "})()"
    )
    try:
        result = await _cdp_eval(cdp, js)
        return int(result) if result else 0
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


async def _cdp_eval(cdp: Any, expression: str) -> Any:
    """Evaluate a JS expression via CDP."""
    if hasattr(cdp, "cdp_send"):
        result = await cdp.cdp_send("Runtime.evaluate", {"expression": expression, "returnByValue": True})
    else:
        result = await cdp.send("Runtime.evaluate", {"expression": expression, "returnByValue": True})
    if result.ok and result.data:
        return result.data.get("result", {}).get("value")
    return None


async def _poll_js_true(cdp: Any, js: str, timeout: float = 30.0, interval: float = 0.5) -> bool:
    """Poll a JS expression until it returns true or timeout."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            val = await _cdp_eval(cdp, js)
            if val:
                return True
        except Exception:
            pass
        await asyncio.sleep(interval)
    return False
