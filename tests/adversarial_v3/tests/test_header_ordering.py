"""Tests for HeaderOrderingConsistency (T5-001) diagnostic semantics.

These tests pin the contract established by issue #174:
HeaderOrderingConsistency cannot return CLEAN or FLAGGED, because the
vector has no expected-header-order contract to validate against. It
captures the observed order (telemetry) but returns INCONCLUSIVE in
every case, so it does not inflate the network-tier score with a
verdict it cannot honestly justify.
"""

from __future__ import annotations

import pytest
from adversarial3.core import EvaluationContext, Verdict
from adversarial3.vectors.network import HeaderOrderingConsistency


def _ctx(headers: dict[str, object]) -> EvaluationContext:
    """Build a minimal context carrying only header data."""
    return EvaluationContext(page=None, browser=None, server_url="", headers=headers)


class TestHeaderOrderingDiagnostic:
    """T5-001 must be diagnostic-only until an ordering contract exists."""

    @pytest.mark.asyncio
    async def test_no_captured_header_order_is_inconclusive(self):
        # No __header_order key at all -> nothing captured.
        vector = HeaderOrderingConsistency()
        result = await vector.evaluate(_ctx({}))

        assert result.verdict == Verdict.INCONCLUSIVE

    @pytest.mark.asyncio
    async def test_captured_order_without_baseline_is_inconclusive(self):
        # Headers were captured, but there is no expected order to compare
        # against. Previously this returned CLEAN (score 1.0), inflating the
        # network-tier average. It must now be INCONCLUSIVE.
        vector = HeaderOrderingConsistency()
        captured = {
            "__header_order": [
                "Host",
                "Connection",
                "sec-ch-ua",
                "sec-ch-ua-mobile",
                "User-Agent",
                "Accept",
            ],
        }

        result = await vector.evaluate(_ctx(captured))

        assert result.verdict == Verdict.INCONCLUSIVE
        # The captured order is still preserved in details as telemetry.
        assert result.details.get("header_order") == captured["__header_order"][:10]

    @pytest.mark.asyncio
    async def test_empty_captured_order_is_inconclusive(self):
        # __header_order present but empty -> treat as not captured.
        vector = HeaderOrderingConsistency()
        result = await vector.evaluate(_ctx({"__header_order": []}))

        assert result.verdict == Verdict.INCONCLUSIVE

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "headers",
        [
            {},  # nothing captured
            {"__header_order": []},  # empty capture
            {"__header_order": ["Host", "User-Agent", "Accept"]},  # captured, no baseline
            {  # clearly automation-like order, but still no contract
                "__header_order": ["X-Custom", "webdriver", "Host"],
            },
        ],
    )
    async def test_never_returns_clean_or_flagged(self, headers):
        # The decisive invariant: no input can make this vector claim CLEAN
        # or FLAGGED. Without an expected-order contract, both would be
        # fabricated evidence.
        vector = HeaderOrderingConsistency()
        result = await vector.evaluate(_ctx(headers))

        assert result.verdict not in (Verdict.CLEAN, Verdict.FLAGGED), (
            f"T5-001 must be diagnostic-only; got {result.verdict} for {headers}"
        )
