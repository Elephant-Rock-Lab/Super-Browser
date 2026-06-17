"""Tier 3 adversarial tests: controlled local target.

Fully offline, CI-safe regression tests using the built-in
``ControlledDetectionServer``. This is the only tier that can
run in scheduled CI without any opt-in gates.

Usage::

    pytest tests/adversarial/test_tier3_controlled.py
"""

from __future__ import annotations

import pytest

from .controlled_server import ControlledDetectionServer  # type: ignore[import-not-found]
from .targets import Target, TargetResult, Tier, Verdict  # type: ignore[import-not-found]


def _browser_available() -> bool:
    """Check if a browser engine can actually launch."""
    for mod_name in ("playwright", "patchright"):
        try:
            mod = __import__(f"{mod_name}.sync_api", fromlist=["sync_playwright"])
        except ImportError:
            continue
        try:
            pw = mod.sync_playwright().start()
            browser = pw.chromium.launch(headless=True)
            browser.close()
            pw.stop()
            return True
        except Exception:
            try:
                pw.stop()
            except Exception:
                pass
            continue
    return False

# Build a Target descriptor for the controlled server so it fits the
# same evaluation pipeline as Tier 1 and Tier 2.


def _parse_controlled(target_id: str, *, verdict_data: dict | None, **_) -> TargetResult:
    if verdict_data is None:
        return TargetResult(
            target_id=target_id,
            verdict=Verdict.INCONCLUSIVE,
            score=0,
            detail="no verdict data received from controlled server",
        )
    verdict_str = verdict_data.get("verdict", "inconclusive")
    score = verdict_data.get("score", 0)
    flags = verdict_data.get("flags", [])

    verdict_map = {
        "clean": Verdict.CLEAN,
        "challenged": Verdict.CHALLENGED,
        "flagged": Verdict.FLAGGED,
    }
    verdict = verdict_map.get(verdict_str, Verdict.INCONCLUSIVE)

    return TargetResult(
        target_id=target_id,
        verdict=verdict,
        score=score,
        detail=f"verdict={verdict_str}, flags={flags}",
        raw=verdict_data,
    )


CONTROLLED_TARGET = Target(
    target_id="controlled_local",
    tier=Tier.CONTROLLED,
    url="",  # filled in at runtime from server.base_url
    description="Local controlled detection target with documented heuristics",
    probes={
        # Read verdict from the #status element's text content.
        # Patchright uses isolated JS worlds, so window.__sb_verdict
        # is invisible to page.evaluate(). The DOM is shared.
        "verdict_data": (
            "() => { try { "
            "  var s = document.getElementById('status'); "
            "  if (!s || s.textContent.indexOf('{') < 0) return null; "
            "  return JSON.parse(s.textContent); "
            "} catch (e) { return null; } }"
        ),
    },
    settle_ms=2000,
    parser=_parse_controlled,
)


@pytest.mark.adversarial
@pytest.mark.tier3
@pytest.mark.skipif(
    not _browser_available(),
    reason="Tier 3 live evaluation requires Playwright or Patchright installed",
)
class TestTier3Controlled:
    """Evaluate SuperBrowser against the controlled detection target."""

    async def test_controlled_target_clean(self, evaluate_target):
        """SuperBrowser should pass the controlled target with a clean verdict."""
        with ControlledDetectionServer() as server:
            # Override the target URL at runtime
            target = Target(
                target_id=CONTROLLED_TARGET.target_id,
                tier=CONTROLLED_TARGET.tier,
                url=server.base_url,
                description=CONTROLLED_TARGET.description,
                probes=CONTROLLED_TARGET.probes,
                settle_ms=CONTROLLED_TARGET.settle_ms,
                parser=CONTROLLED_TARGET.parser,
            )

            result: TargetResult = await evaluate_target(target)

            assert result.verdict != Verdict.INCONCLUSIVE, (
                f"Controlled target returned inconclusive: {result.detail}"
            )

            # Tier 3 is a regression gate: FLAGGED is a real failure
            assert result.verdict != Verdict.FLAGGED, (
                f"SuperBrowser flagged by controlled target: {result.detail}"
            )

            # CHALLENGED is acceptable but logged as a warning signal
            if result.verdict == Verdict.CHALLENGED:
                pytest.xfail(f"Controlled target challenged: {result.detail}")

            assert result.verdict == Verdict.CLEAN, (
                f"Expected CLEAN, got {result.verdict.value}: {result.detail}"
            )
            assert result.score == 100, (
                f"Expected score 100, got {result.score}: {result.detail}"
            )
