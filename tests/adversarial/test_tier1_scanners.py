"""Tier 1 adversarial tests: open fingerprint scanners.

Evaluates SuperBrowser against publicly-available bot-detection
diagnostic pages. These tell us *which* signals are leaking, not
whether a commercial vendor would block us.

Requires: SB_ADV=1
"""

from __future__ import annotations

import os

import pytest

from .targets import TIER1_TARGETS, TargetResult, Verdict  # type: ignore[import-not-found]


@pytest.mark.adversarial
@pytest.mark.tier1
@pytest.mark.skipif(
    os.environ.get("SB_ADV", "0") != "1",
    reason="Tier 1 requires SB_ADV=1",
)
class TestTier1Scanners:
    """Evaluate SuperBrowser against open fingerprint scanners."""

    @pytest.mark.parametrize("target", TIER1_TARGETS, ids=lambda t: t.target_id)
    async def test_scanner(self, target, evaluate_target, tier1_enabled):
        if not tier1_enabled:
            pytest.skip("Tier 1 not enabled (set SB_ADV=1)")

        result: TargetResult = await evaluate_target(target)

        # Tier 1 is diagnostic — we record the verdict but do not hard-fail
        # on FLAGGED. The report captures the signal.
        assert result.verdict != Verdict.INCONCLUSIVE, (
            f"{target.target_id}: inconclusive — {result.detail}"
        )

        # Soft assertion: log the outcome without failing the build
        if result.verdict == Verdict.FLAGGED:
            pytest.xfail(f"{target.target_id}: flagged — {result.detail}")
        elif result.verdict == Verdict.CHALLENGED:
            pytest.xfail(f"{target.target_id}: challenged — {result.detail}")
