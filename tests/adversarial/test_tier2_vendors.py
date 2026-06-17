"""Tier 2 adversarial tests: commercial bot-management vendors.

Evaluates SuperBrowser against vendor-published demo/test endpoints.
These are the actual systems that gate real e-commerce, ticketing,
and social sites. This tier requires explicit opt-in acknowledgment.

Requires: SB_ADV=1 SB_ADV_VENDORS=1 SB_ADV_VENDORS_ACK=1
"""

from __future__ import annotations

import os

import pytest

from .targets import TIER2_TARGETS, TargetResult, Verdict  # type: ignore[import-not-found]


@pytest.mark.adversarial
@pytest.mark.tier2
@pytest.mark.skipif(
    not (
        os.environ.get("SB_ADV", "0") == "1"
        and os.environ.get("SB_ADV_VENDORS", "0") == "1"
        and os.environ.get("SB_ADV_VENDORS_ACK", "0") == "1"
    ),
    reason="Tier 2 requires SB_ADV=1 + SB_ADV_VENDORS=1 + SB_ADV_VENDORS_ACK=1",
)
class TestTier2Vendors:
    """Evaluate SuperBrowser against commercial bot-management demos."""

    @pytest.mark.parametrize("target", TIER2_TARGETS, ids=lambda t: t.target_id)
    async def test_vendor(self, target, evaluate_target, tier2_enabled):
        if not tier2_enabled:
            pytest.skip(
                "Tier 2 not enabled (set SB_ADV=1 SB_ADV_VENDORS=1 SB_ADV_VENDORS_ACK=1)"
            )

        result: TargetResult = await evaluate_target(target)

        # Tier 2 is the signal that matters most, but vendor-side changes
        # (new challenge versions, rate limits, page redesigns) are NOT
        # SuperBrowser regressions. We xfail rather than hard-fail.
        assert result.verdict != Verdict.INCONCLUSIVE, (
            f"{target.target_id}: inconclusive — {result.detail}"
        )

        if result.verdict == Verdict.FLAGGED:
            pytest.xfail(f"{target.target_id}: flagged by vendor — {result.detail}")
        elif result.verdict == Verdict.CHALLENGED:
            pytest.xfail(
                f"{target.target_id}: challenged by vendor — {result.detail}"
            )
