"""Tier 1: Fingerprint Consistency vectors.

These vectors probe for logical contradictions in spoofed browser
fingerprints. Each is self-contained and can run against any page.
"""

from __future__ import annotations

import json
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


class _FingerprintVector(BaseVector):
    """Base for fingerprint vectors with common evaluation pattern."""

    async def _eval_js(self, context: EvaluationContext, expressions: dict[str, str]) -> dict[str, Any]:
        """Evaluate multiple JS expressions and return results."""
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

    def _make_result(
        self,
        passed: bool,
        details: dict[str, Any],
        duration_ms: float,
        error: str | None = None,
    ) -> VectorResult:
        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=Verdict.CLEAN if passed else Verdict.FLAGGED,
            score=1.0 if passed else 0.0,
            details=details,
            severity=self.severity,
            duration_ms=duration_ms,
            error=error,
        )


class UAPlatformMismatch(_FingerprintVector):
    """T1-001: UA claims Windows but platform says Linux (or vice versa)."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T1-001",
            tier=Tier.FINGERPRINT,
            name="UA ↔ Platform Mismatch",
            description="User-Agent and navigator.platform disagree on OS",
            severity=Severity.CRITICAL,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "ua": "navigator.userAgent",
            "platform": "navigator.platform",
        })
        duration = (time.perf_counter() - start) * 1000

        ua = data.get("ua") or ""
        platform = data.get("platform") or ""

        ua_win = "Windows" in ua
        ua_mac = "Mac" in ua and "iPhone" not in ua and "iPad" not in ua
        ua_linux = "Linux" in ua and "Android" not in ua

        plat_win = platform.startswith("Win")
        plat_mac = platform.startswith("Mac")
        plat_linux = "Linux" in platform

        mismatch = (
            (ua_win and (plat_mac or plat_linux)) or
            (ua_mac and (plat_win or plat_linux)) or
            (ua_linux and (plat_win or plat_mac))
        )

        return self._make_result(
            passed=not mismatch,
            details={"ua": ua, "platform": platform, "mismatch": mismatch},
            duration_ms=duration,
        )


class HardwareConcurrencyPlausibility(_FingerprintVector):
    """T1-003: hardwareConcurrency is 0, 1, or >128."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T1-003",
            tier=Tier.FINGERPRINT,
            name="hardwareConcurrency Plausibility",
            description="navigator.hardwareConcurrency outside plausible range",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {"hc": "navigator.hardwareConcurrency"})
        duration = (time.perf_counter() - start) * 1000

        hc = data.get("hc")
        plausible = isinstance(hc, int) and 1 < hc <= 128

        return self._make_result(
            passed=plausible,
            details={"hardwareConcurrency": hc, "plausible": plausible},
            duration_ms=duration,
        )


class DeviceMemoryCap(_FingerprintVector):
    """T1-004: deviceMemory >8 or 0."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T1-004",
            tier=Tier.FINGERPRINT,
            name="deviceMemory Cap",
            description="navigator.deviceMemory outside browser privacy limits",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {"dm": "navigator.deviceMemory"})
        duration = (time.perf_counter() - start) * 1000

        dm = data.get("dm")
        valid = isinstance(dm, (int, float)) and 0 < dm <= 8

        return self._make_result(
            passed=valid,
            details={"deviceMemory": dm, "valid": valid},
            duration_ms=duration,
        )


class ScreenDPRMath(_FingerprintVector):
    """T1-005: Screen dimensions inconsistent with devicePixelRatio."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T1-005",
            tier=Tier.FINGERPRINT,
            name="Screen ↔ DPR Math",
            description="window.screen dimensions vs devicePixelRatio inconsistency",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "dpr": "window.devicePixelRatio",
            "sw": "screen.width",
            "sh": "screen.height",
            "iw": "window.innerWidth",
            "ih": "window.innerHeight",
        })
        duration = (time.perf_counter() - start) * 1000

        dpr = data.get("dpr", 1)
        sw = data.get("sw") or 0
        sh = data.get("sh") or 0
        iw = data.get("iw") or 0
        ih = data.get("ih") or 0

        dpr_valid = isinstance(dpr, (int, float)) and 0.5 <= dpr <= 4
        dims_valid = (sw or 0) > 0 and (sh or 0) > 0
        viewport_valid = (iw or 0) <= (sw or 0) * 1.5 and (ih or 0) <= (sh or 0) * 1.5

        return self._make_result(
            passed=dpr_valid and dims_valid and viewport_valid,
            details={"dpr": dpr, "screen": {"w": sw, "h": sh}, "inner": {"w": iw, "h": ih}},
            duration_ms=duration,
        )


class WebGLVendorGPUPlausibility(_FingerprintVector):
    """T1-007: SwiftShader on NVIDIA-claiming profile."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T1-007",
            tier=Tier.FINGERPRINT,
            name="WebGL Vendor ↔ GPU Plausibility",
            description="WebGL renderer string contradicts User-Agent GPU claims",
            severity=Severity.CRITICAL,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "ua": "navigator.userAgent",
            "renderer": """
                (() => {
                    const c = document.createElement('canvas');
                    const gl = c.getContext('webgl') || c.getContext('experimental-webgl');
                    if (!gl) return null;
                    const d = gl.getExtension('WEBGL_debug_renderer_info');
                    return d ? gl.getParameter(d.UNMASKED_RENDERER_WEBGL) : null;
                })()
            """,
        })
        duration = (time.perf_counter() - start) * 1000

        ua = data.get("ua") or ""
        renderer = data.get("renderer") or ""

        has_nvidia = "NVIDIA" in ua
        is_swiftshader = renderer and "SwiftShader" in renderer
        mismatch = has_nvidia and is_swiftshader

        return self._make_result(
            passed=not mismatch,
            details={"ua_has_nvidia": has_nvidia, "renderer": renderer, "is_swiftshader": is_swiftshader},
            duration_ms=duration,
        )


class LanguagesArrayConsistency(_FingerprintVector):
    """T1-009: navigator.languages[0] must match navigator.language."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T1-009",
            tier=Tier.FINGERPRINT,
            name="Languages Array Consistency",
            description="navigator.languages[0] doesn't match navigator.language",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "lang": "navigator.language",
            "langs": "navigator.languages",
        })
        duration = (time.perf_counter() - start) * 1000

        lang = data.get("lang")
        langs = data.get("langs", [])
        primary = langs[0] if isinstance(langs, list) and langs else None
        consistent = primary == lang

        return self._make_result(
            passed=consistent,
            details={"language": lang, "languages": langs, "consistent": consistent},
            duration_ms=duration,
        )


class ViewportScreenRelationship(_FingerprintVector):
    """T1-011: innerWidth/innerHeight > screen dimensions."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T1-011",
            tier=Tier.FINGERPRINT,
            name="Viewport ↔ Screen Relationship",
            description="Viewport larger than screen (impossible without zoom)",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "iw": "window.innerWidth",
            "ih": "window.innerHeight",
            "sw": "screen.width",
            "sh": "screen.height",
        })
        duration = (time.perf_counter() - start) * 1000

        iw = data.get("iw") or 0
        ih = data.get("ih") or 0
        sw = data.get("sw") or 0
        sh = data.get("sh") or 0

        valid = (iw or 0) <= (sw or 0) * 1.2 and (ih or 0) <= (sh or 0) * 1.2

        return self._make_result(
            passed=valid,
            details={"inner": {"w": iw, "h": ih}, "screen": {"w": sw, "h": sh}},
            duration_ms=duration,
        )


# Registry of all Tier 1 vectors
FINGERPRINT_VECTORS: list[BaseVector] = [
    UAPlatformMismatch(),
    HardwareConcurrencyPlausibility(),
    DeviceMemoryCap(),
    ScreenDPRMath(),
    WebGLVendorGPUPlausibility(),
    LanguagesArrayConsistency(),
    ViewportScreenRelationship(),
]
