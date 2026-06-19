"""Tier 6: Controlled Local Target vectors.

Uses the built-in ControlledDetectionServer for CI-safe regression tests.
The harness navigates the browser to the server, which causes the page JS
to collect signals and POST them to /api/verdict. The harness then passes
the server's computed verdict to this vector via context metadata.
"""

from __future__ import annotations

import time
from typing import Any

from adversarial3.core import (
    BaseVector,
    EvaluationContext,
    Severity,
    Tier,
    VectorResult,
    Verdict,
)


class ControlledServerVector(BaseVector):
    """Reads verdict from the local controlled detection server.

    The harness populates ``context.metadata["controlled_verdict"]`` with
    the server's response after the browser navigates to it. If the
    browser did not run JS (e.g., StubBackend), the verdict is absent
    and this vector returns INCONCLUSIVE.
    """

    def __init__(self) -> None:
        super().__init__(
            vector_id="T6-001",
            tier=Tier.CONTROLLED,
            name="Controlled Detection Target",
            description="Local server implementing documented bot-detection heuristics",
            severity=Severity.CRITICAL,
        )

    @property
    def requires_browser(self) -> bool:
        return True

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        verdict_data: dict[str, Any] | None = context.metadata.get("controlled_verdict")
        duration = (time.perf_counter() - start) * 1000

        if not verdict_data:
            return VectorResult(
                vector_id=self.vector_id,
                tier=self.tier,
                name=self.name,
                verdict=Verdict.INCONCLUSIVE,
                score=0.0,
                details={"error": "No verdict from controlled server (browser JS did not execute)"},
                severity=self.severity,
                duration_ms=duration,
            )

        verdict_str = verdict_data.get("verdict", "inconclusive")
        score = verdict_data.get("score", 0)
        hard_flags = verdict_data.get("hard_flags", [])
        soft_flags = verdict_data.get("soft_flags", [])

        verdict_map = {
            "clean": Verdict.CLEAN,
            "challenged": Verdict.CHALLENGED,
            "flagged": Verdict.FLAGGED,
        }
        verdict = verdict_map.get(verdict_str, Verdict.INCONCLUSIVE)

        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=verdict,
            score=score / 100.0,
            details={
                "verdict": verdict_str,
                "score": score,
                "hard_flags": hard_flags,
                "soft_flags": soft_flags,
            },
            severity=self.severity,
            duration_ms=duration,
        )


CONTROLLED_VECTORS: list[BaseVector] = [ControlledServerVector()]
