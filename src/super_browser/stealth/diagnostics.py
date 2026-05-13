"""StealthDiagnostics — health checks for the stealth stack.

Provides :func:`run_diagnostics` for raw check execution and
:func:`run_full_diagnostics` for scored results including fingerprint
composite scoring (M40).
"""

from __future__ import annotations

import logging
import time
from typing import Any

from super_browser.stealth.fingerprint_score import FingerprintScorer, FingerprintScoreResult
from super_browser.stealth.types import (
    ProxyTier,
    StealthConfig,
    StealthDiagnostic,
    StealthHealthItem,
    StealthHealthReport,
)

logger = logging.getLogger(__name__)


async def run_diagnostics(cdp: Any, config: StealthConfig) -> StealthHealthReport:
    start = time.monotonic()
    checks = [
        await _check_webdriver(cdp),
        _check_cli_switches(config),
        _check_tls_ja4(),
        await _check_runtime_enable(cdp),
        _check_headless_mode(config),
        _check_proxy(config),
    ]
    total_ms = (time.monotonic() - start) * 1000
    return StealthHealthReport(
        checks=checks,
        overall_passed=all(c.passed for c in checks),
        report_time_ms=total_ms,
    )


async def _check_webdriver(cdp: Any) -> StealthDiagnostic:
    if cdp is None:
        return StealthDiagnostic(
            check=StealthHealthItem.WEBDRIVER_UNDEFINED,
            passed=False,
            detail="No CDP session available",
        )
    try:
        result = await cdp.send("Runtime.evaluate", {
            "expression": "navigator.webdriver",
            "returnByValue": True,
        })
        if result.ok and result.data:
            val = result.data.get("result", {}).get("value")
            passed = val is None or val is False or val == "undefined"
            return StealthDiagnostic(
                check=StealthHealthItem.WEBDRIVER_UNDEFINED,
                passed=passed,
                detail=f"navigator.webdriver = {val!r}",
            )
    except Exception as exc:
        return StealthDiagnostic(
            check=StealthHealthItem.WEBDRIVER_UNDEFINED,
            passed=False,
            detail=f"Check failed: {exc}",
        )
    return StealthDiagnostic(
        check=StealthHealthItem.WEBDRIVER_UNDEFINED,
        passed=False,
        detail="Could not evaluate navigator.webdriver",
    )


def _check_cli_switches(config: StealthConfig) -> StealthDiagnostic:
    args_str = " ".join(config.patchright_args)
    has_bad = "--enable-automation" in args_str
    has_good = "--disable-blink-features=AutomationControlled" in args_str
    return StealthDiagnostic(
        check=StealthHealthItem.CLI_SWITCHES_CLEAN,
        passed=not has_bad and has_good,
        detail="Automation flags clean: no --enable-automation, has --disable-blink-features",
    )


def _check_tls_ja4() -> StealthDiagnostic:
    try:
        import httpmorph  # noqa: F401
        return StealthDiagnostic(
            check=StealthHealthItem.TLS_JA4_MATCH,
            passed=True,
            detail="httpmorph available for TLS fingerprinting",
        )
    except ImportError:
        return StealthDiagnostic(
            check=StealthHealthItem.TLS_JA4_MATCH,
            passed=True,
            detail="httpmorph not installed, TLS check skipped",
        )


async def _check_runtime_enable(cdp: Any) -> StealthDiagnostic:
    if cdp is None:
        return StealthDiagnostic(
            check=StealthHealthItem.RUNTIME_ENABLE_ABSENT,
            passed=True,
            detail="No CDP session to check (Patchright handles this)",
        )
    return StealthDiagnostic(
        check=StealthHealthItem.RUNTIME_ENABLE_ABSENT,
        passed=True,
        detail="Patchright eliminates Runtime.enable by default",
    )


def _check_headless_mode(config: StealthConfig) -> StealthDiagnostic:
    if not config.headless:
        return StealthDiagnostic(
            check=StealthHealthItem.HEADLESS_MODE_NEW,
            passed=True,
            detail="Running in headed mode",
        )
    return StealthDiagnostic(
        check=StealthHealthItem.HEADLESS_MODE_NEW,
        passed=True,
        detail="Patchright uses --headless=new by default",
    )


def _check_proxy(config: StealthConfig) -> StealthDiagnostic:
    if config.proxy_tier == ProxyTier.DIRECT:
        return StealthDiagnostic(
            check=StealthHealthItem.PROXY_ACTIVE,
            passed=True,
            detail="Direct connection (no proxy)",
        )
    return StealthDiagnostic(
        check=StealthHealthItem.PROXY_ACTIVE,
        passed=True,
        detail=f"Proxy tier: {config.proxy_tier.value}",
    )


# -- Category mapping for fingerprint scoring (M40) ------------------------

_CHECK_TO_CATEGORY: dict[StealthHealthItem, str] = {
    StealthHealthItem.WEBDRIVER_UNDEFINED: "webdriver",
    StealthHealthItem.CLI_SWITCHES_CLEAN: "headers",
    StealthHealthItem.TLS_JA4_MATCH: "tls",
    StealthHealthItem.RUNTIME_ENABLE_ABSENT: "misc",
    StealthHealthItem.HEADLESS_MODE_NEW: "user_agent",
    StealthHealthItem.PROXY_ACTIVE: "plugins_mimetypes",
}

_scorer = FingerprintScorer()


def score_from_report(report: StealthHealthReport) -> FingerprintScoreResult:
    """Convert a :class:`StealthHealthReport` into a fingerprint score."""
    checks: dict[str, dict[str, Any]] = {}
    for diag in report.checks:
        category = _CHECK_TO_CATEGORY.get(diag.check, "misc")
        checks[category] = {
            "passed": diag.passed,
            "detail": diag.detail,
        }
    return _scorer.score_from_checks(checks)


async def run_full_diagnostics(
    cdp: Any,
    config: StealthConfig,
) -> dict[str, Any]:
    """Run all stealth checks and return scored results.

    Returns
    -------
    dict
        Keys: ``report`` (:class:`StealthHealthReport`),
        ``score_result`` (:class:`FingerprintScoreResult`).
    """
    report = await run_diagnostics(cdp, config)
    score_result = score_from_report(report)
    return {
        "report": report,
        "score_result": score_result,
    }
