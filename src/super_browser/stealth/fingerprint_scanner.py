"""FingerprintScanner — scans browser fingerprints against detection sites.

Supports two modes:

- **Offline** (default): returns deterministic mock scores without any
  network access.  Used by unit tests and the ``stealth-check`` CLI.
- **Online**: visits detection sites via a browser page and parses
  results.  Not used in tests (requires live browser + network).
"""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

from super_browser.stealth.scoring import FingerprintCheck, FingerprintScore

logger = logging.getLogger(__name__)

# Default mock checks used in offline mode
_OFFLINE_CHECKS: list[FingerprintCheck] = [
    FingerprintCheck(name="webdriver", passed=True, score=100, detail="navigator.webdriver is undefined"),
    FingerprintCheck(name="fingerprintjs", passed=True, score=95, detail="Fingerprint hash is randomized"),
    FingerprintCheck(name="bot_sannysoft", passed=True, score=90, detail="No bot indicators detected"),
    FingerprintCheck(name="headless_detection", passed=True, score=100, detail="Headless mode not detected"),
    FingerprintCheck(name="canvas_fingerprint", passed=True, score=85, detail="Canvas fingerprint varies"),
    FingerprintCheck(name="webgl_renderer", passed=True, score=90, detail="WebGL renderer appears legitimate"),
]


class FingerprintScanner:
    """Scans browser fingerprint against detection sites.

    Parameters
    ----------
    scanner_config:
        Optional configuration dict.  Recognised keys:

        - ``"offline"`` (bool): Force offline mode (default *True*).
        - ``"backend"`` (str): Stealth backend name for reports.
        - ``"custom_checks"`` (list[FingerprintCheck]): Override offline
          checks in offline mode.
    """

    def __init__(self, scanner_config: Optional[dict] = None) -> None:
        cfg = scanner_config or {}
        self._offline: bool = cfg.get("offline", True)
        self._backend: str = cfg.get("backend", "patchright")
        self._custom_checks: Optional[list[FingerprintCheck]] = cfg.get("custom_checks")

    @property
    def offline(self) -> bool:
        return self._offline

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def scan(self, browser_page: Any = None) -> FingerprintScore:
        """Run a fingerprint scan and return a composite score.

        In offline mode, returns mock scores without touching the network.
        In online mode, visits detection sites and parses results.
        """
        if self._offline:
            return self._offline_scan()

        return await self._online_scan(browser_page)

    async def scan_site(self, browser_page: Any, url: str) -> FingerprintCheck:
        """Visit a single detection site and return a check result.

        Only available in online mode.  In offline mode, returns a
        passed check with a note.
        """
        if self._offline:
            return FingerprintCheck(
                name=url,
                passed=True,
                score=100,
                detail="Offline mode — mock result",
            )

        return await self._online_scan_site(browser_page, url)

    @staticmethod
    def format_report(score: FingerprintScore) -> str:
        """Produce a Markdown report from a FingerprintScore."""
        lines = [
            "## Stealth Report",
            "",
            f"**Backend:** {score.backend}",
            f"**Overall Score:** {score.overall}/100",
            f"**Timestamp:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(score.timestamp))}",
            "",
            "### Checks",
            "",
            "| Check | Passed | Score | Detail |",
            "|:------|:------:|------:|:-------|",
        ]
        for check in score.checks:
            passed_str = "✅" if check.passed else "❌"
            lines.append(f"| {check.name} | {passed_str} | {check.score} | {check.detail} |")

        lines.append("")
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Offline mode
    # ------------------------------------------------------------------

    def _offline_scan(self) -> FingerprintScore:
        """Return deterministic mock scores without network access."""
        checks = list(self._custom_checks) if self._custom_checks else list(_OFFLINE_CHECKS)
        overall = _compute_overall(checks)
        return FingerprintScore(
            overall=overall,
            checks=checks,
            timestamp=time.time(),
            backend=self._backend,
        )

    # ------------------------------------------------------------------
    # Online mode (not used in tests)
    # ------------------------------------------------------------------

    async def _online_scan(self, browser_page: Any) -> FingerprintScore:
        """Visit detection sites and collect results."""
        if browser_page is None:
            raise ValueError("browser_page is required for online scanning")

        checks: list[FingerprintCheck] = []
        urls = [
            ("webdriver", "https://bot.sannysoft.com"),
            ("fingerprintjs", "https://fingerprint.com"),
            ("bot_sannysoft", "https://nowsecure.nl"),
        ]

        for name, url in urls:
            try:
                check = await self._online_scan_site(browser_page, url)
                checks.append(check)
            except Exception as exc:
                checks.append(FingerprintCheck(
                    name=name,
                    passed=False,
                    score=0,
                    detail=f"Scan failed: {exc}",
                ))

        overall = _compute_overall(checks)
        return FingerprintScore(
            overall=overall,
            checks=checks,
            timestamp=time.time(),
            backend=self._backend,
        )

    async def _online_scan_site(self, browser_page: Any, url: str) -> FingerprintCheck:
        """Visit a single detection site and evaluate the result."""
        await browser_page.goto(url, wait_until="networkidle", timeout=15000)
        await browser_page.wait_for_timeout(2000)

        # Evaluate webdriver detection
        result = await browser_page.evaluate("navigator.webdriver")
        if result is True:
            return FingerprintCheck(
                name="webdriver",
                passed=False,
                score=0,
                detail=f"Site {url}: webdriver detected",
            )
        return FingerprintCheck(
            name="webdriver",
            passed=True,
            score=100,
            detail=f"Site {url}: webdriver not detected",
        )


def _compute_overall(checks: list[FingerprintCheck]) -> int:
    """Compute the overall score as the mean of check scores."""
    if not checks:
        return 0
    total = sum(c.score for c in checks)
    return int(round(total / len(checks)))
