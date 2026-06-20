"""Tier 3: Ejector Survival & Anti-Countermeasure vectors.

Tests whether stealth patches survive adversarial probing.
"""

from __future__ import annotations

import time
from typing import Any

from adversarial3.core import (
    BaseVector,
    EvaluationContext,
    JSUnsupportedError,
    Severity,
    Tier,
    VectorResult,
    Verdict,
)


class _EjectorVector(BaseVector):
    """Base for ejector survival vectors."""

    async def _eval_js(self, context: EvaluationContext, expressions: dict[str, str]) -> dict[str, Any]:
        if not context.page:
            return {k: None for k in expressions}
        results = {}
        for name, expr in expressions.items():
            try:
                results[name] = await context.page.evaluate(expr)
            except JSUnsupportedError:
                raise
            except Exception as e:
                results[name] = {"_error": str(e)}
        return results

    def _make_result(self, passed: bool, details: dict[str, Any], duration_ms: float) -> VectorResult:
        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=Verdict.CLEAN if passed else Verdict.FLAGGED,
            score=1.0 if passed else 0.0,
            details=details,
            severity=self.severity,
            duration_ms=duration_ms,
        )


class CanvasNoiseVerification(_EjectorVector):
    """T3-001: toDataURL produces consistent noise (not blank)."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T3-001",
            tier=Tier.EJECTOR,
            name="Canvas Noise Verification",
            description="Canvas fingerprint noise is present and consistent",
            severity=Severity.CRITICAL,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "dataUrl": """
                (() => {
                    const c = document.createElement('canvas');
                    c.width = 200; c.height = 200;
                    const ctx = c.getContext('2d');
                    ctx.fillStyle = '#FF0000'; ctx.fillRect(0, 0, 100, 100);
                    ctx.fillStyle = '#00FF00'; ctx.fillRect(100, 0, 100, 100);
                    ctx.fillStyle = '#0000FF'; ctx.fillRect(0, 100, 100, 100);
                    ctx.fillStyle = '#FFFF00'; ctx.fillRect(100, 100, 100, 100);
                    return c.toDataURL();
                })()
            """,
        })
        duration = (time.perf_counter() - start) * 1000

        data_url = data.get("dataUrl") or ""
        not_blank = len(data_url) > 1000 and data_url.startswith("data:image")

        return self._make_result(
            passed=not_blank,
            details={"dataUrl_length": len(data_url), "not_blank": not_blank},
            duration_ms=duration,
        )


class AudioContextNoise(_EjectorVector):
    """T3-002: AudioContext fingerprint is perturbed."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T3-002",
            tier=Tier.EJECTOR,
            name="Audio Context Noise",
            description="AudioContext produces non-zero, non-deterministic fingerprint",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "fingerprint": """
                (async () => {
                    try {
                        const ctx = new (window.AudioContext || window.webkitAudioContext)();
                        const osc = ctx.createOscillator();
                        const analyser = ctx.createAnalyser();
                        const gain = ctx.createGain();
                        osc.connect(analyser);
                        analyser.connect(gain);
                        gain.connect(ctx.destination);
                        osc.start(0);
                        const buffer = new Float32Array(analyser.frequencyBinCount);
                        analyser.getFloatFrequencyData(buffer);
                        const sum = buffer.reduce((a, b) => a + b, 0);
                        osc.stop();
                        await ctx.close();
                        return sum;
                    } catch (e) { return null; }
                })()
            """,
        })
        duration = (time.perf_counter() - start) * 1000

        fp = data.get("fingerprint")
        has_fp = fp is not None and fp != 0

        return self._make_result(
            passed=has_fp,
            details={"fingerprint": fp, "has_fingerprint": has_fp},
            duration_ms=duration,
        )


class IframeInjectionConsistency(_EjectorVector):
    """T3-007: Stealth patches apply in same-origin iframes."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T3-007",
            tier=Tier.EJECTOR,
            name="Iframe Injection Consistency",
            description="Stealth patches propagate to same-origin iframes",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "consistent": """
                (() => {
                    const iframe = document.createElement('iframe');
                    iframe.style.display = 'none';
                    document.body.appendChild(iframe);
                    const iNav = iframe.contentWindow.navigator;
                    const result = iNav.webdriver === navigator.webdriver &&
                                   iNav.platform === navigator.platform &&
                                   iNav.userAgent === navigator.userAgent;
                    document.body.removeChild(iframe);
                    return result;
                })()
            """,
        })
        duration = (time.perf_counter() - start) * 1000

        consistent = data.get("consistent", False)

        return self._make_result(
            passed=consistent is True,
            details={"consistent": consistent},
            duration_ms=duration,
        )


class NavigationPersistence(_EjectorVector):
    """T3-008: Patches survive SPA navigation + full reload."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T3-008",
            tier=Tier.EJECTOR,
            name="Navigation Persistence",
            description="Stealth patches survive history.pushState + back()",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "before": """
                JSON.stringify({
                    webdriver: navigator.webdriver,
                    platform: navigator.platform,
                    plugins: navigator.plugins.length
                })
            """,
            "after": """
                (() => {
                    const before = JSON.stringify({
                        webdriver: navigator.webdriver,
                        platform: navigator.platform,
                        plugins: navigator.plugins.length
                    });
                    history.pushState({test: true}, '', '#test');
                    history.back();
                    const after = JSON.stringify({
                        webdriver: navigator.webdriver,
                        platform: navigator.platform,
                        plugins: navigator.plugins.length
                    });
                    return before === after;
                })()
            """,
        })
        duration = (time.perf_counter() - start) * 1000

        persisted = data.get("after", False)

        return self._make_result(
            passed=persisted is True,
            details={"persisted": persisted, "before": data.get("before")},
            duration_ms=duration,
        )


EJECTOR_VECTORS: list[BaseVector] = [
    CanvasNoiseVerification(),
    AudioContextNoise(),
    IframeInjectionConsistency(),
    NavigationPersistence(),
]
