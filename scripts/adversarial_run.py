#!/usr/bin/env python3
"""CLI entrypoint for the adversarial stealth validation harness.

Mirrors the shape of ``scripts/stress_real_world.py`` for consistency.

Usage::

    python scripts/adversarial_run.py --tier all --output report.json --markdown report.md
    python scripts/adversarial_run.py --tier tier3 --output report.json
    python scripts/adversarial_run.py --tier tier1 --tier tier2 --output report.json
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Any

# Ensure the project root is on the path
_SCRIPT_DIR = Path(__file__).resolve().parent
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT))

from tests.adversarial.report import (  # noqa: E402
    write_json_report,
    write_markdown_report,
)
from tests.adversarial.scoring import (  # noqa: E402
    append_to_history,
    build_report,
)
from tests.adversarial.targets import (  # noqa: E402
    TIER1_TARGETS,
    TIER2_TARGETS,
    Target,
    TargetResult,
    Tier,
    Verdict,
)

# ---------------------------------------------------------------------------
# Async evaluation (mirrors conftest evaluate_target logic)
# ---------------------------------------------------------------------------

async def _evaluate_target(
    target: Target,
    super_browser_factory,
    rate_limiter: "_RateLimiter",
) -> TargetResult:
    """Evaluate a single target against a fresh SuperBrowser page."""
    rate_limiter.wait_if_needed(target.target_id, target.min_interval_s)

    browser = super_browser_factory()
    try:
        page = await browser.new_page()
        try:
            await page.goto(target.url, wait_until="networkidle", timeout=30000)
            if target.settle_ms:
                await asyncio.sleep(target.settle_ms / 1000.0)

            probe_results: dict[str, Any] = {}
            for name, js_expr in target.probes.items():
                try:
                    probe_results[name] = await page.evaluate(js_expr)
                except Exception:
                    probe_results[name] = None

            return target.parser(target.target_id, **probe_results)
        finally:
            await page.close()
    except Exception as exc:
        return TargetResult(
            target_id=target.target_id,
            verdict=Verdict.INCONCLUSIVE,
            score=0,
            detail=f"Evaluation error: {exc}",
            raw={"error": str(exc)},
        )
    finally:
        await browser.close()


class _RateLimiter:
    """Simple in-memory rate limiter."""

    def __init__(self) -> None:
        self._last_hit: dict[str, float] = {}

    def wait_if_needed(self, target_id: str, min_interval_s: float) -> None:
        now = time.time()
        last = self._last_hit.get(target_id, 0.0)
        elapsed = now - last
        if elapsed < min_interval_s:
            time.sleep(min_interval_s - elapsed)
        self._last_hit[target_id] = time.time()


# ---------------------------------------------------------------------------
# SuperBrowser factory (stub or real)
# ---------------------------------------------------------------------------

class _SuperBrowserPageAdapter:
    """Adapter wrapping SuperBrowser to match the page-based API.

    The adversarial harness expects ``browser.new_page()`` → page with
    ``goto()`` / ``evaluate()`` / ``close()``, and ``browser.close()``.
    SuperBrowser's facade uses ``start()`` / ``navigate()`` / ``stop()``.
    This adapter bridges the gap.
    """

    def __init__(self) -> None:
        from super_browser import SuperBrowser
        self._sb = SuperBrowser()
        self._started = False

    async def _ensure_started(self) -> None:
        if not self._started:
            await self._sb.start()
            self._started = True

    async def new_page(self) -> "_SBPage":
        await self._ensure_started()
        return _SBPage(self._sb)

    async def close(self) -> None:
        if self._started:
            await self._sb.stop()
            self._started = False


class _SBPage:
    """Page adapter for SuperBrowser."""

    def __init__(self, sb: Any) -> None:
        self._sb = sb

    async def goto(self, url: str, **kwargs: Any) -> None:
        await self._sb.navigate(url)

    async def evaluate(self, expression: str) -> Any:
        if self._sb._page and self._sb._page.backend_page:
            return await self._sb._page.backend_page.evaluate(expression)
        return None

    async def close(self) -> None:
        pass  # SuperBrowser manages page lifecycle


def _make_super_browser() -> Any:
    """Return a SuperBrowser instance (real or stub)."""
    try:
        return _SuperBrowserPageAdapter()
    except ImportError:
        class _StubBrowser:
            async def new_page(self):
                return _StubPage()
            async def close(self):
                pass
        class _StubPage:
            async def goto(self, url, **kwargs):
                pass
            async def evaluate(self, expr):
                return None
            async def close(self):
                pass
        return _StubBrowser()


# ---------------------------------------------------------------------------
# Tier 3: Controlled server (synchronous, local)
# ---------------------------------------------------------------------------

def _run_tier3() -> list[TargetResult]:
    """Run the controlled detection target synchronously."""
    from tests.adversarial.controlled_server import (
        ControlledDetectionServer,  # type: ignore[import-not-found]
    )

    results: list[TargetResult] = []
    with ControlledDetectionServer() as server:
        # We can't easily run the full async probe pipeline here without
        # a real browser, so we hit the server with a simple HTTP request
        # and read the verdict it stores.
        import urllib.error
        import urllib.request

        try:
            req = urllib.request.Request(
                server.base_url,
                headers={"User-Agent": "SuperBrowser/AdversarialHarness"},
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                _ = resp.read()
        except urllib.error.URLError:
            pass

        # Give the server time to receive the POST from its own JS
        time.sleep(0.5)
        verdict = server.last_verdict

        if verdict:
            verdict_str = verdict.get("verdict", "inconclusive")
            score = verdict.get("score", 0)
            flags = verdict.get("flags", [])
            from tests.adversarial.targets import Verdict as V
            vmap = {"clean": V.CLEAN, "challenged": V.CHALLENGED, "flagged": V.FLAGGED}
            results.append(
                TargetResult(
                    target_id="controlled_local",
                    verdict=vmap.get(verdict_str, V.INCONCLUSIVE),
                    score=score,
                    detail=f"verdict={verdict_str}, flags={flags}",
                    raw=verdict,
                )
            )
        else:
            results.append(
                TargetResult(
                    target_id="controlled_local",
                    verdict=Verdict.INCONCLUSIVE,
                    score=0,
                    detail="no verdict received from controlled server",
                )
            )
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Adversarial Stealth Validation Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--tier",
        action="append",
        choices=["tier1", "tier2", "tier3", "all"],
        help="Which tier(s) to run. Repeatable. Default: tier3",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("adversarial-results/report.json"),
        help="Path for the JSON report",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("adversarial-results/report.md"),
        help="Path for the Markdown report",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("adversarial-results/adversarial-history.json"),
        help="Path for the trend history file",
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default=None,
        help="Custom run ID (default: UUID)",
    )
    return parser.parse_args()


async def main() -> int:
    args = _parse_args()

    tiers_requested = args.tier or ["tier3"]
    if "all" in tiers_requested:
        tiers_requested = ["tier1", "tier2", "tier3"]

    run_id = args.run_id or str(uuid.uuid4())[:8]
    rate_limiter = _RateLimiter()
    results_by_tier: dict[Tier, list[TargetResult]] = {}

    # --- Tier 3 (controlled, always runnable) ---
    if "tier3" in tiers_requested:
        print("[Tier 3] Running controlled detection target...")
        results_by_tier[Tier.CONTROLLED] = _run_tier3()
        for r in results_by_tier[Tier.CONTROLLED]:
            print(f"  {r.target_id}: {r.verdict.value} (score={r.score}) — {r.detail}")

    # --- Tier 1 (open scanners, requires SB_ADV=1) ---
    if "tier1" in tiers_requested:
        if os.environ.get("SB_ADV", "0") != "1":
            print("[Tier 1] SKIPPED — set SB_ADV=1 to enable", file=sys.stderr)
        else:
            print("[Tier 1] Running open fingerprint scanners...")
            tier1_results: list[TargetResult] = []
            for target in TIER1_TARGETS:
                result = await _evaluate_target(target, _make_super_browser, rate_limiter)
                tier1_results.append(result)
                print(f"  {target.target_id}: {result.verdict.value} (score={result.score}) — {result.detail}")
            results_by_tier[Tier.SCANNER] = tier1_results

    # --- Tier 2 (vendors, requires all three env vars) ---
    if "tier2" in tiers_requested:
        if (
            os.environ.get("SB_ADV", "0") != "1"
            or os.environ.get("SB_ADV_VENDORS", "0") != "1"
            or os.environ.get("SB_ADV_VENDORS_ACK", "0") != "1"
        ):
            print(
                "[Tier 2] SKIPPED — set SB_ADV=1 SB_ADV_VENDORS=1 SB_ADV_VENDORS_ACK=1",
                file=sys.stderr,
            )
        else:
            print("[Tier 2] Running commercial vendor demos...")
            tier2_results: list[TargetResult] = []
            for target in TIER2_TARGETS:
                result = await _evaluate_target(target, _make_super_browser, rate_limiter)
                tier2_results.append(result)
                print(f"  {target.target_id}: {result.verdict.value} (score={result.score}) — {result.detail}")
            results_by_tier[Tier.VENDOR] = tier2_results

    # --- Build and write reports ---
    report = build_report(run_id, results_by_tier)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    write_json_report(report, args.output)
    print(f"JSON report written to {args.output}")

    write_markdown_report(report, args.markdown)
    print(f"Markdown report written to {args.markdown}")

    append_to_history(report, args.history)
    print(f"History appended to {args.history}")

    print(f"{'='*50}")
    print(f"Overall Score: {report.overall_score}/100")
    print(f"Summary: {report.summary}")
    print(f"{'='*50}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
