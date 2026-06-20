"""Tier 2: Automation Artifact Detection vectors.

Probes for classic automation tells: navigator.webdriver, CDP artifacts,
missing headful APIs, plugin/mimetype enumeration, etc.
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


class _AutomationVector(BaseVector):
    """Base for automation artifact vectors."""

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


class NavigatorWebdriver(_AutomationVector):
    """T2-001: navigator.webdriver must be false or undefined."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T2-001",
            tier=Tier.AUTOMATION,
            name="navigator.webdriver",
            description="Classic automation flag detection",
            severity=Severity.CRITICAL,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {"wd": "navigator.webdriver"})
        duration = (time.perf_counter() - start) * 1000

        wd = data.get("wd")
        passed = wd is False or wd is None or wd is undefined_sentinel(wd)

        return self._make_result(
            passed=passed,
            details={"webdriver": wd, "type": type(wd).__name__},
            duration_ms=duration,
        )


class CDPRuntimeEnableDetection(_AutomationVector):
    """T2-002: Detect Chrome DevTools Protocol artifacts."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T2-002",
            tier=Tier.AUTOMATION,
            name="CDP Runtime.enable Detection",
            description="Detect CDP automation artifacts (cdc_ properties)",
            severity=Severity.CRITICAL,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "cdc_keys": """
                Object.keys(window).filter(k => k.startsWith('cdc_') || k.startsWith('$cdc_'))
            """,
            "chrome_obj": "typeof window.chrome",
        })
        duration = (time.perf_counter() - start) * 1000

        cdc_keys = data.get("cdc_keys") or []
        has_cdc = len(cdc_keys) > 0

        return self._make_result(
            passed=not has_cdc,
            details={"cdc_keys": cdc_keys, "has_cdc": has_cdc},
            duration_ms=duration,
        )


class HeadlessIndicatorSweep(_AutomationVector):
    """T2-003: Missing APIs (notification, plugins, permissions)."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T2-003",
            tier=Tier.AUTOMATION,
            name="Headless Indicator Sweep",
            description="Check for missing headful browser APIs",
            severity=Severity.CRITICAL,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "plugins": "navigator.plugins ? navigator.plugins.length : -1",
            "mimeTypes": "navigator.mimeTypes ? navigator.mimeTypes.length : -1",
            "notification": "'Notification' in window",
            "permissions": "'permissions' in navigator",
        })
        duration = (time.perf_counter() - start) * 1000

        plugins = data.get("plugins", -1)
        mime_types = data.get("mimeTypes", -1)
        notification = data.get("notification", False)
        permissions = data.get("permissions", False)

        headless = plugins == 0 and mime_types == 0

        return self._make_result(
            passed=not headless,
            details={
                "plugins": plugins,
                "mimeTypes": mime_types,
                "notification": notification,
                "permissions": permissions,
                "headless_signature": headless,
            },
            duration_ms=duration,
        )


class PluginEnumeration(_AutomationVector):
    """T2-005: navigator.plugins length and entries."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T2-005",
            tier=Tier.AUTOMATION,
            name="Plugin Enumeration",
            description="navigator.plugins should have entries",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "plugins": "navigator.plugins ? navigator.plugins.length : -1",
            "plugin_names": """
                Array.from(navigator.plugins || []).map(p => p.name).join(',')
            """,
        })
        duration = (time.perf_counter() - start) * 1000

        plugins = data.get("plugins", -1)
        names = data.get("plugin_names", "")
        valid = isinstance(plugins, int) and plugins >= 2

        return self._make_result(
            passed=valid,
            details={"plugin_count": plugins, "plugin_names": names},
            duration_ms=duration,
        )


class WebGLRendererAnalysis(_AutomationVector):
    """T2-009: SwiftShader or Headless in WebGL renderer string."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T2-009",
            tier=Tier.AUTOMATION,
            name="WebGL Renderer String Analysis",
            description="Detect SwiftShader/Headless in WebGL renderer",
            severity=Severity.CRITICAL,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
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

        renderer = data.get("renderer", "")
        is_swiftshader = "SwiftShader" in str(renderer) if renderer else False
        is_headless = "Headless" in str(renderer) if renderer else False

        return self._make_result(
            passed=not (is_swiftshader or is_headless),
            details={"renderer": renderer, "is_swiftshader": is_swiftshader, "is_headless": is_headless},
            duration_ms=duration,
        )


class ChromeRuntimeInjection(_AutomationVector):
    """T2-007: window.chrome object structure validation."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T2-007",
            tier=Tier.AUTOMATION,
            name="Chrome Runtime Injection",
            description="window.chrome.runtime structure should look native",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        data = await self._eval_js(context, {
            "chrome_type": "typeof window.chrome",
            "runtime_type": "typeof (window.chrome || {}).runtime",
            "runtime_tostring": "(window.chrome || {}).runtime ? window.chrome.runtime.toString() : null",
        })
        duration = (time.perf_counter() - start) * 1000

        chrome_type = data.get("chrome_type")
        runtime_tostring = data.get("runtime_tostring", "")
        has_chrome = chrome_type == "object"
        structure_valid = runtime_tostring is None or "native code" in str(runtime_tostring)

        return self._make_result(
            passed=has_chrome and structure_valid,
            details={
                "has_chrome": has_chrome,
                "runtime_tostring": runtime_tostring,
                "structure_valid": structure_valid,
            },
            duration_ms=duration,
        )


# Sentinel for undefined values in JS
def undefined_sentinel(x: object) -> bool:
    return str(x) == "<undefined>" if x is not None else False


AUTOMATION_VECTORS: list[BaseVector] = [
    NavigatorWebdriver(),
    CDPRuntimeEnableDetection(),
    HeadlessIndicatorSweep(),
    PluginEnumeration(),
    WebGLRendererAnalysis(),
    ChromeRuntimeInjection(),
]
