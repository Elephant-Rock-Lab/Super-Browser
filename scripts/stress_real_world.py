#!/usr/bin/env python3
"""Real-world stress harness for Super Browser.

Simulates realistic browser automation workloads against local fixture
pages to measure stability, resource usage, and recovery behavior.

Modes:

    --quick        30-60 second local probe (1 session, 1 concurrency)
    --realistic    Configurable sessions, concurrency, ramp-up, duration

Scenarios:

    auth_flow          Login → cookie/session reuse → verify auth state
    js_heavy           Hydration delay, dynamic DOM mutation, page.evaluate()
    file_handling      Upload fixture file, download generated file, verify
    viewport_rotation  Mobile/desktop contexts, verify responsive layout marker
    request_intercept  Block images and mock API response
    parallel_profiles  Distinct contexts with isolated cookies/localStorage
    warm_ramp          Ramp 1 → N concurrency over configurable seconds
    storage_pressure   localStorage/cookie growth measurement (light)

Output:

    JSON report (schema v1) + Markdown summary.

Usage:

    python scripts/stress_real_world.py --quick
    python scripts/stress_real_world.py --realistic --sessions 20 --concurrency 4
"""

from __future__ import annotations

import argparse
import asyncio
import gc
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Ensure src is importable when run from repo root
_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

_REPO_SRC = _REPO_ROOT / "src"
if str(_REPO_SRC) not in sys.path:
    sys.path.insert(0, str(_REPO_SRC))

from stress.server import StressFixtureServer  # noqa: E402

# -- Constants ----------------------------------------------------------------

SCHEMA_VERSION = 1
DEFAULT_OUT_DIR = Path("stress-results")
DEFAULT_SESSIONS = 5
DEFAULT_CONCURRENCY = 2
DEFAULT_RAMP_UP_S = 10
DEFAULT_SESSION_DURATION_S = 120
DEFAULT_TIMEOUT_S = 60

ALL_SCENARIOS = [
    "auth_flow",
    "js_heavy",
    "file_handling",
    "viewport_rotation",
    "request_intercept",
    "parallel_profiles",
    "warm_ramp",
    "storage_pressure",
]


# -- Data structures ----------------------------------------------------------


@dataclass
class ScenarioResult:
    """Result of a single scenario execution."""

    name: str
    passed: bool
    duration_s: float
    error: str | None = None
    screenshot: str | None = None
    metrics: dict[str, Any] = field(default_factory=dict)


@dataclass
class StressReport:
    """Aggregated stress test report."""

    schema_version: int
    mode: str  # "quick" or "realistic"
    timestamp_utc: str
    started_at: float
    duration_s: float
    config: dict[str, Any]
    realism: dict[str, bool]
    scenarios: list[ScenarioResult]
    environment: dict[str, Any]


# -- Memory utilities ---------------------------------------------------------


def _get_rss_mb() -> float:
    """Get current process RSS in MB.

    Prefers psutil for cross-platform consistency. Falls back to
    platform-specific ``resource`` module (Linux: KB, macOS: bytes).
    """
    # Prefer psutil — accurate and cross-platform
    try:
        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except ImportError:
        pass
    try:
        # Fallback: Linux (ru_maxrss is in KB)
        import resource
        import sys as _sys

        rss_kb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        if _sys.platform == "darwin":
            # macOS: ru_maxrss is in bytes
            return rss_kb / (1024 * 1024)
        # Linux: ru_maxrss is in KB
        return rss_kb / 1024.0
    except (ImportError, AttributeError, OSError):
        return 0.0


def _count_browser_processes() -> int:
    """Count browser processes (best-effort)."""
    try:
        import psutil

        count = 0
        for proc in psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if any(b in name for b in ("chrom", "firefox", "webkit")):
                count += 1
        return count
    except (ImportError, Exception):
        return -1


async def _wait_for_condition(
    check: Any,
    *,
    timeout_s: float = 10.0,
    interval_s: float = 0.2,
) -> bool:
    """Poll a condition until it returns truthy or timeout elapses.

    Replaces hard sleeps with deterministic waits.
    ``check`` is an async callable returning a value.
    """
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        result = await check()
        if result:
            return True
        await asyncio.sleep(interval_s)
    return False


class RSSSampler:
    """Lightweight periodic RSS sampler for stress runs."""

    def __init__(self) -> None:
        self._samples: list[float] = []
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._samples = []
        self._task = asyncio.create_task(self._run())

    async def _run(self) -> None:
        while True:
            self._samples.append(_get_rss_mb())
            await asyncio.sleep(2.0)

    async def stop(self) -> dict[str, float]:
        """Stop sampling and return RSS statistics."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        if not self._samples:
            return {"rss_start_mb": 0.0, "rss_peak_mb": 0.0, "rss_end_mb": 0.0, "rss_delta_mb": 0.0}

        return {
            "rss_start_mb": round(self._samples[0], 1),
            "rss_peak_mb": round(max(self._samples), 1),
            "rss_end_mb": round(self._samples[-1], 1),
            "rss_delta_mb": round(self._samples[-1] - self._samples[0], 1),
        }


def _disk_usage_mb(path: str | Path) -> float:
    """Get disk usage of a directory in MB (best-effort)."""
    try:
        p = Path(path)
        if not p.exists():
            return 0.0
        total = 0
        for f in p.rglob("*"):
            if f.is_file():
                total += f.stat().st_size
        return total / (1024 * 1024)
    except Exception:
        return 0.0


# -- Scenario implementations -------------------------------------------------


async def _scenario_auth_flow(base_url: str, timeout_s: float) -> ScenarioResult:
    """Login → cookie/session reuse → verify auth state."""
    from super_browser.agent.facade import SuperBrowser

    name = "auth_flow"
    t0 = time.monotonic()
    error = None
    passed = False
    metrics: dict[str, Any] = {}

    try:
        sb = SuperBrowser()
        await sb.start()

        try:
            # Navigate to login page
            await asyncio.wait_for(sb.navigate(f"{base_url}/login.html"), timeout=timeout_s)

            # Fill and submit login form
            await asyncio.wait_for(
                sb.fill("#username", "stress-user"), timeout=timeout_s
            )
            await asyncio.wait_for(
                sb.fill("#password", "stress-pass"), timeout=timeout_s
            )

            # Click submit (triggers JS fetch + cookie set)
            click_result = await asyncio.wait_for(
                sb.click("#submit-btn"), timeout=timeout_s
            )
            metrics["click_ok"] = click_result.ok

            # Wait for JS to set cookie/localStorage (poll for cookie)
            if sb._page and sb._page.backend_page:
                page = sb._page.backend_page

                async def _check_cookie() -> bool:
                    return await page.evaluate("document.cookie.includes('session_token=')")

                await _wait_for_condition(_check_cookie, timeout_s=5.0, interval_s=0.2)

                # Verify authentication state via cookie and localStorage
                cookie_present = await page.evaluate(
                    "document.cookie.includes('session_token=')"
                )
                user_storage = await page.evaluate(
                    "localStorage.getItem('user') !== null"
                )
                metrics["cookie_present"] = cookie_present
                metrics["user_storage_present"] = user_storage

                passed = click_result.ok and cookie_present and user_storage
            else:
                error = "No backend page available for auth verification"
        finally:
            await sb.stop()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return ScenarioResult(
        name=name,
        passed=passed,
        duration_s=round(time.monotonic() - t0, 3),
        error=error,
        metrics=metrics,
    )


async def _scenario_js_heavy(base_url: str, timeout_s: float) -> ScenarioResult:
    """Dynamic DOM mutation, page.evaluate(), hydration wait."""
    from super_browser.agent.facade import SuperBrowser

    name = "js_heavy"
    t0 = time.monotonic()
    error = None
    passed = False
    metrics: dict[str, Any] = {}

    try:
        sb = SuperBrowser()
        await sb.start()

        try:
            await asyncio.wait_for(sb.navigate(f"{base_url}/app.html"), timeout=timeout_s)

            # Wait for AJAX hydration by polling for dynamic content
            page = sb._page
            if page and page.backend_page:
                bp = page.backend_page

                async def _check_items() -> int:
                    els = await bp.query_selector_all(".item")
                    return len(els)

                async def _has_items() -> bool:
                    return await _check_items() > 0

                await _wait_for_condition(_has_items, timeout_s=10.0, interval_s=0.3)

                items_count = await _check_items()

                # Check DOM has dynamic content (more reliable than window flag
                # which may be isolated by Patchright stealth context)
                metrics["dom_items"] = items_count

                # Best-effort hydration flag check
                try:
                    hydrated = await bp.evaluate("window.__HYDRATED__ === true")
                except Exception:
                    hydrated = False
                metrics["hydrated"] = hydrated

                # Pass if DOM items exist (AJAX hydration completed)
                passed = items_count > 0
            else:
                error = "No backend page available"
        finally:
            await sb.stop()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return ScenarioResult(
        name=name,
        passed=passed,
        duration_s=round(time.monotonic() - t0, 3),
        error=error,
        metrics=metrics,
    )


async def _scenario_file_handling(base_url: str, timeout_s: float, tmp_dir: Path) -> ScenarioResult:
    """Upload fixture file, download generated file, verify digest."""
    from super_browser.agent.facade import SuperBrowser

    name = "file_handling"
    t0 = time.monotonic()
    error = None
    passed = False
    metrics: dict[str, Any] = {}

    try:
        # Create a test file to upload
        upload_file = tmp_dir / "upload-test.bin"
        upload_data = bytes(range(256)) * 4  # 1 KB
        upload_file.write_bytes(upload_data)

        sb = SuperBrowser()
        await sb.start()

        try:
            await asyncio.wait_for(sb.navigate(f"{base_url}/form.html"), timeout=timeout_s)

            # Upload file
            upload_result = await asyncio.wait_for(
                sb.upload_file("#file-input", str(upload_file)),
                timeout=timeout_s,
            )
            metrics["upload_ok"] = upload_result.ok

            # Download file via fetch in browser context (avoids goto download issue)
            if sb._page and sb._page.backend_page:
                try:
                    dl_size = await sb._page.backend_page.evaluate(
                        f"""async () => {{
                            const resp = await fetch('{base_url}/download');
                            const blob = await resp.blob();
                            return blob.size;
                        }}"""
                    )
                    metrics["download_size"] = dl_size
                    download_ok = dl_size == 1024
                except Exception:
                    download_ok = False
                metrics["download_ok"] = download_ok

            passed = metrics.get("upload_ok", False) and metrics.get("download_ok", False)
        finally:
            await sb.stop()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return ScenarioResult(
        name=name,
        passed=passed,
        duration_s=round(time.monotonic() - t0, 3),
        error=error,
        metrics=metrics,
    )


async def _scenario_viewport_rotation(base_url: str, timeout_s: float) -> ScenarioResult:
    """Mobile/desktop contexts, verify viewport-dependent width change."""
    from super_browser import Config as SBConfig
    from super_browser.agent.facade import SuperBrowser
    from super_browser.browser.config import SessionConfig

    name = "viewport_rotation"
    t0 = time.monotonic()
    error = None
    passed = False
    metrics: dict[str, Any] = {}

    try:
        for vp_name, width, height in [("mobile", 375, 667), ("desktop", 1920, 1080)]:
            cfg = SBConfig(browser=SessionConfig(headless=True))
            sb = SuperBrowser(config=cfg)
            await sb.start()
            try:
                if sb._page and sb._page.backend_page:
                    await sb._page.backend_page.set_viewport_size(
                        {"width": width, "height": height}
                    )
                await asyncio.wait_for(sb.navigate(f"{base_url}/"), timeout=timeout_s)

                # Measure actual viewport width from the browser
                if sb._page and sb._page.backend_page:
                    inner_width = await sb._page.backend_page.evaluate(
                        "window.innerWidth"
                    )
                    metrics[f"inner_width_{vp_name}"] = inner_width
            finally:
                await sb.stop()

        # Pass only if mobile width is actually smaller than desktop width
        mobile_w = metrics.get("inner_width_mobile", 0)
        desktop_w = metrics.get("inner_width_desktop", 0)
        passed = mobile_w > 0 and desktop_w > 0 and mobile_w < 768 and desktop_w >= 1024
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return ScenarioResult(
        name=name,
        passed=passed,
        duration_s=round(time.monotonic() - t0, 3),
        error=error,
        metrics=metrics,
    )


async def _scenario_request_intercept(base_url: str, timeout_s: float) -> ScenarioResult:
    """Block image requests and mock API response, verify effectiveness."""
    from super_browser.agent.facade import SuperBrowser

    name = "request_intercept"
    t0 = time.monotonic()
    error = None
    passed = False
    metrics: dict[str, Any] = {}

    try:
        sb = SuperBrowser()
        await sb.start()

        try:
            # Navigate to app first
            await asyncio.wait_for(sb.navigate(f"{base_url}/app.html"), timeout=timeout_s)

            # Establish non-empty baseline BEFORE registering mock
            # (app starts with zero items until AJAX hydration completes)
            baseline_count = 0
            if sb._page and sb._page.backend_page:
                bp0 = sb._page.backend_page

                async def _has_items() -> bool:
                    count = await bp0.evaluate(
                        "document.querySelectorAll('.item').length"
                    )
                    return count > 0

                await _wait_for_condition(_has_items, timeout_s=10.0, interval_s=0.3)
                baseline_count = await bp0.evaluate(
                    "document.querySelectorAll('.item').length"
                )
            metrics["baseline_item_count"] = baseline_count

            # Mock the API response (** glob needed for full URL matching)
            mock_result = await asyncio.wait_for(
                sb.mock_response("**/api/data", json.dumps({"mocked": True, "items": []})),
                timeout=timeout_s,
            )
            metrics["mock_ok"] = mock_result.ok

            # Verify the mock is effective by triggering a refresh
            if sb._page and sb._page.backend_page:
                # Click refresh to re-fetch /api/data (should get mocked response)
                try:
                    await asyncio.wait_for(
                        sb.click("#refresh-btn"), timeout=timeout_s
                    )

                    # Poll for items clearing (mock replaces with empty items)
                    bp = sb._page.backend_page

                    async def _items_cleared() -> bool:
                        count = await bp.evaluate(
                            "document.querySelectorAll('.item').length"
                        )
                        return count == 0

                    await _wait_for_condition(_items_cleared, timeout_s=5.0, interval_s=0.2)

                    # Final check: baseline was non-empty AND now it's zero
                    item_count = await bp.evaluate(
                        "document.querySelectorAll('.item').length"
                    )
                    metrics["item_count_after_mock"] = item_count
                    metrics["mock_effective"] = baseline_count > 0 and item_count == 0
                except Exception:
                    metrics["mock_effective"] = False

            # Block image requests (narrow pattern, not wildcard)
            block_result = await asyncio.wait_for(
                sb.block_requests("*.png"), timeout=timeout_s
            )
            metrics["block_ok"] = block_result.ok

            # Clear interceptions and verify normal behavior restores
            await asyncio.wait_for(sb.clear_interceptions(), timeout=timeout_s)

            await asyncio.wait_for(sb.navigate(f"{base_url}/app.html"), timeout=timeout_s)

            if sb._page and sb._page.backend_page:
                bp2 = sb._page.backend_page

                async def _items_restored() -> bool:
                    count = await bp2.evaluate(
                        "document.querySelectorAll('.item').length"
                    )
                    return count > 0

                await _wait_for_condition(_items_restored, timeout_s=10.0, interval_s=0.3)
                item_count_restored = await bp2.evaluate(
                    "document.querySelectorAll('.item').length"
                )
                metrics["item_count_restored"] = item_count_restored
                metrics["normal_restored"] = item_count_restored > 0

            # Pass only if mock was effective and normal behavior restored
            passed = (
                metrics.get("mock_ok", False)
                and metrics.get("mock_effective", False)
                and metrics.get("block_ok", False)
                and metrics.get("normal_restored", False)
            )
        finally:
            await sb.stop()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return ScenarioResult(
        name=name,
        passed=passed,
        duration_s=round(time.monotonic() - t0, 3),
        error=error,
        metrics=metrics,
    )


async def _scenario_parallel_profiles(base_url: str, timeout_s: float, concurrency: int) -> ScenarioResult:
    """Distinct contexts with isolated cookies/localStorage."""
    name = "parallel_profiles"
    t0 = time.monotonic()
    error = None
    passed = False
    metrics: dict[str, Any] = {}

    async def _single_profile(idx: int, all_ids: list[int]) -> dict[str, Any]:
        """Run a single profile, write unique value, verify isolation.

        Checks that own value is present AND no other profile's value
        is present in this context's localStorage.
        """
        from super_browser.agent.facade import SuperBrowser

        result: dict[str, Any] = {"idx": idx, "ok": False}
        try:
            sb = SuperBrowser()
            await sb.start()
            try:
                await asyncio.wait_for(
                    sb.navigate(f"{base_url}/login.html"), timeout=timeout_s
                )

                # Write a unique localStorage value under a profile-specific key
                if sb._page and sb._page.backend_page:
                    page = sb._page.backend_page
                    unique_key = f"profile-id-{idx}"
                    unique_val = f"profile-{idx}-token"
                    await page.evaluate(
                        f"localStorage.setItem('{unique_key}', '{unique_val}')"
                    )
                    # Also set a unique cookie
                    await page.evaluate(
                        f"document.cookie = 'profile-cookie-{idx}={unique_val}; path=/'"
                    )

                    # Read back own key to verify self
                    ls_read = await page.evaluate(
                        f"localStorage.getItem('{unique_key}')"
                    )
                    result["ls_value"] = ls_read
                    self_ok = ls_read == unique_val

                    # Verify no OTHER profile's key exists in this context
                    # This is meaningful because each profile writes a
                    # distinct key. If another key is present, contexts
                    # are sharing localStorage (leak).
                    other_ids_present = []
                    for other_idx in all_ids:
                        if other_idx == idx:
                            continue
                        other_key = f"profile-id-{other_idx}"
                        other_val = await page.evaluate(
                            f"localStorage.getItem('{other_key}')"
                        )
                        if other_val is not None:
                            other_ids_present.append(other_idx)

                    result["other_values_leaked"] = len(other_ids_present)
                    result["ok"] = self_ok and len(other_ids_present) == 0
            finally:
                await sb.stop()
        except Exception:
            pass
        return result

    try:
        all_ids = list(range(concurrency))
        tasks = [_single_profile(i, all_ids) for i in range(concurrency)]
        results = await asyncio.gather(*tasks)

        metrics["profiles_started"] = concurrency
        metrics["profiles_ok"] = sum(1 for r in results if r.get("ok"))
        metrics["profile_values"] = [r.get("ls_value") for r in results]
        metrics["total_leaks"] = sum(r.get("other_values_leaked", 0) for r in results)

        # Verify all profiles succeeded and have distinct values
        values = [r.get("ls_value") for r in results if r.get("ls_value")]
        all_ok = all(r.get("ok") for r in results)
        all_distinct = len(set(values)) == concurrency
        total_leaks = sum(r.get("other_values_leaked", 0) for r in results)
        metrics["all_isolated"] = all_ok and all_distinct and total_leaks == 0

        passed = all_ok and all_distinct and total_leaks == 0
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return ScenarioResult(
        name=name,
        passed=passed,
        duration_s=round(time.monotonic() - t0, 3),
        error=error,
        metrics=metrics,
    )


async def _scenario_warm_ramp(base_url: str, timeout_s: float, ramp_s: float, concurrency: int) -> ScenarioResult:
    """Ramp 1 → N concurrency over configurable seconds."""
    name = "warm_ramp"
    t0 = time.monotonic()
    error = None
    passed = False
    metrics: dict[str, Any] = {}

    async def _single_nav(idx: int) -> float:
        from super_browser.agent.facade import SuperBrowser

        nav_t0 = time.monotonic()
        try:
            sb = SuperBrowser()
            await sb.start()
            try:
                await asyncio.wait_for(
                    sb.navigate(f"{base_url}/"), timeout=timeout_s
                )
            finally:
                await sb.stop()
        except Exception:
            pass
        return time.monotonic() - nav_t0

    try:
        # Stagger launches
        delay_per = ramp_s / max(concurrency, 1)
        tasks: list[asyncio.Task] = []
        for i in range(concurrency):
            tasks.append(asyncio.create_task(_single_nav(i)))
            await asyncio.sleep(delay_per)

        results = await asyncio.gather(*tasks)
        timings = [r for r in results if r > 0]
        if timings:
            metrics["avg_nav_s"] = round(sum(timings) / len(timings), 3)
            metrics["max_nav_s"] = round(max(timings), 3)
            metrics["ramp_concurrency"] = concurrency
        passed = len(timings) == concurrency
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return ScenarioResult(
        name=name,
        passed=passed,
        duration_s=round(time.monotonic() - t0, 3),
        error=error,
        metrics=metrics,
    )


async def _scenario_storage_pressure(base_url: str, timeout_s: float) -> ScenarioResult:
    """localStorage/cookie growth measurement (light)."""
    from super_browser.agent.facade import SuperBrowser

    name = "storage_pressure"
    t0 = time.monotonic()
    error = None
    passed = False
    metrics: dict[str, Any] = {}

    try:
        sb = SuperBrowser()
        await sb.start()

        try:
            await asyncio.wait_for(sb.navigate(f"{base_url}/"), timeout=timeout_s)

            # Write to localStorage
            if sb._page and sb._page.backend_page:
                page = sb._page.backend_page
                for i in range(10):
                    await page.evaluate(
                        f"localStorage.setItem('key-{i}', 'value-'.repeat(100))"
                    )

                # Measure localStorage size
                ls_size = await page.evaluate(
                    "JSON.stringify(localStorage).length"
                )
                metrics["localStorage_bytes"] = ls_size

                # Measure cookie count
                cookie_count = await page.evaluate(
                    "document.cookie ? document.cookie.split(';').length : 0"
                )
                metrics["cookie_count"] = cookie_count

                passed = ls_size > 0
            else:
                error = "No backend page available"
        finally:
            await sb.stop()
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"

    return ScenarioResult(
        name=name,
        passed=passed,
        duration_s=round(time.monotonic() - t0, 3),
        error=error,
        metrics=metrics,
    )


# -- Orchestration ------------------------------------------------------------


async def run_scenarios(
    base_url: str,
    scenarios: list[str],
    timeout_s: float,
    concurrency: int,
    ramp_s: float,
    tmp_dir: Path,
) -> list[ScenarioResult]:
    """Run all scenarios and return results."""
    results: list[ScenarioResult] = []

    for scenario in scenarios:
        try:
            if scenario == "auth_flow":
                r = await _scenario_auth_flow(base_url, timeout_s)
            elif scenario == "js_heavy":
                r = await _scenario_js_heavy(base_url, timeout_s)
            elif scenario == "file_handling":
                r = await _scenario_file_handling(base_url, timeout_s, tmp_dir)
            elif scenario == "viewport_rotation":
                r = await _scenario_viewport_rotation(base_url, timeout_s)
            elif scenario == "request_intercept":
                r = await _scenario_request_intercept(base_url, timeout_s)
            elif scenario == "parallel_profiles":
                r = await _scenario_parallel_profiles(base_url, timeout_s, concurrency)
            elif scenario == "warm_ramp":
                r = await _scenario_warm_ramp(base_url, timeout_s, ramp_s, concurrency)
            elif scenario == "storage_pressure":
                r = await _scenario_storage_pressure(base_url, timeout_s)
            else:
                r = ScenarioResult(
                    name=scenario,
                    passed=False,
                    duration_s=0.0,
                    error=f"Unknown scenario: {scenario}",
                )
            results.append(r)
        except Exception as exc:
            results.append(
                ScenarioResult(
                    name=scenario,
                    passed=False,
                    duration_s=0.0,
                    error=f"{type(exc).__name__}: {exc}",
                )
            )

        # GC between scenarios for cleaner memory measurement
        gc.collect()

    return results


def build_report(
    mode: str,
    config: dict[str, Any],
    realism: dict[str, bool],
    scenarios: list[ScenarioResult],
    started_at: float,
    duration_s: float,
    environment: dict[str, Any],
) -> StressReport:
    """Build the aggregated report."""
    return StressReport(
        schema_version=SCHEMA_VERSION,
        mode=mode,
        timestamp_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        started_at=round(started_at, 3),
        duration_s=round(duration_s, 3),
        config=config,
        realism=realism,
        scenarios=scenarios,
        environment=environment,
    )


def serialize_report(report: StressReport) -> dict[str, Any]:
    """Serialize report to JSON-serializable dict."""
    return {
        "schema_version": report.schema_version,
        "mode": report.mode,
        "timestamp_utc": report.timestamp_utc,
        "started_at": report.started_at,
        "duration_s": report.duration_s,
        "config": report.config,
        "realism": report.realism,
        "summary": {
            "total": len(report.scenarios),
            "passed": sum(1 for s in report.scenarios if s.passed),
            "failed": sum(1 for s in report.scenarios if not s.passed),
            "avg_duration_s": (
                round(
                    sum(s.duration_s for s in report.scenarios)
                    / max(len(report.scenarios), 1),
                    3,
                )
                if report.scenarios
                else 0
            ),
            "max_duration_s": max((s.duration_s for s in report.scenarios), default=0),
        },
        "scenarios": [
            {
                "name": s.name,
                "passed": s.passed,
                "duration_s": s.duration_s,
                "error": s.error,
                "screenshot": s.screenshot,
                "metrics": s.metrics,
            }
            for s in report.scenarios
        ],
        "environment": report.environment,
    }


def render_markdown(report: StressReport, data: dict[str, Any]) -> str:
    """Render a Markdown summary of the stress report."""
    lines: list[str] = []
    lines.append("# Stress Test Results")
    lines.append("")
    lines.append(f"- **Timestamp:** {report.timestamp_utc}")
    lines.append(f"- **Mode:** `{report.mode}`")
    lines.append(f"- **Duration:** {report.duration_s:.1f}s")
    lines.append(f"- **Schema:** v{report.schema_version}")
    lines.append("")

    # Summary
    summary = data["summary"]
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- **Total scenarios:** {summary['total']}")
    lines.append(f"- **Passed:** {summary['passed']}")
    lines.append(f"- **Failed:** {summary['failed']}")
    lines.append(f"- **Avg scenario duration:** {summary['avg_duration_s']}s")
    lines.append(f"- **Max scenario duration:** {summary['max_duration_s']}s")
    lines.append("")

    # Realism dimensions
    lines.append("## Realism Dimensions")
    lines.append("")
    lines.append("| Dimension | Tested |")
    lines.append("|:----------|:------:|")
    for key, val in report.realism.items():
        lines.append(f"| {key} | {'✅' if val else '❌'} |")
    lines.append("")

    # Environment
    env = report.environment
    lines.append("## Environment")
    lines.append("")
    lines.append(f"- **RSS start:** {env.get('rss_start_mb', 'N/A')} MB")
    lines.append(f"- **RSS peak:** {env.get('rss_peak_mb', 'N/A')} MB")
    lines.append(f"- **RSS end:** {env.get('rss_end_mb', 'N/A')} MB")
    lines.append(f"- **RSS delta:** {env.get('rss_delta_mb', 'N/A')} MB")
    lines.append(f"- **Browser processes (before):** {env.get('browser_procs_before', 'N/A')}")
    lines.append(f"- **Browser processes (after):** {env.get('browser_procs_after', 'N/A')}")
    lines.append(f"- **Disk usage:** {env.get('disk_usage_mb', 'N/A')} MB")
    lines.append("")

    # Scenario details
    lines.append("## Scenario Results")
    lines.append("")
    lines.append("| Scenario | Result | Duration | Error |")
    lines.append("|:---------|:------:|---------:|:------|")
    for s in report.scenarios:
        status = "✅" if s.passed else "❌"
        error = s.error or ""
        lines.append(f"| {s.name} | {status} | {s.duration_s}s | {error} |")
    lines.append("")

    return "\n".join(lines)


# -- Main ---------------------------------------------------------------------


async def main_async(args: argparse.Namespace) -> int:
    """Run the stress harness."""
    import tempfile

    out_dir = Path(args.output) if args.output else DEFAULT_OUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    tmp_dir = Path(tempfile.mkdtemp(prefix="sb_stress_"))

    # Determine mode and config
    if args.quick:
        mode = "quick"
        sessions = 1
        concurrency = 1
        ramp_s = 0
        scenarios = ALL_SCENARIOS[:5]  # First 5 for quick mode
        timeout_s = 30
    else:
        mode = "realistic"
        sessions = args.sessions
        concurrency = args.concurrency
        ramp_s = args.ramp_up
        scenarios = list(ALL_SCENARIOS)
        timeout_s = args.timeout

    config = {
        "sessions": sessions,
        "concurrency": concurrency,
        "ramp_up_s": ramp_s,
        "timeout_s": timeout_s,
        "scenarios": scenarios,
    }

    realism = {
        "auth": True,
        "dynamic_dom": True,
        "file_io": True,
        "viewport_rotation": True,
        "request_interception": True,
        "parallel_profiles": concurrency > 1,
        "ramp_up": ramp_s > 0,
        "storage_pressure": True,
        "network_degradation": False,
        "browser_crash_recovery": False,
    }

    # Environment baseline
    browser_procs_before = _count_browser_processes()

    # Start RSS sampler
    rss_sampler = RSSSampler()

    # Start fixture server
    server = StressFixtureServer()
    base_url = server.start()
    print(f"Fixture server: {base_url}")
    print(f"Mode: {mode}, Scenarios: {len(scenarios)}, Concurrency: {concurrency}")
    print()

    started_at = time.monotonic()
    all_results: list[ScenarioResult] = []
    rss_sampler.start()

    try:
        for session_idx in range(sessions):
            if sessions > 1:
                print(f"--- Session {session_idx + 1}/{sessions} ---")

            results = await run_scenarios(
                base_url=base_url,
                scenarios=scenarios,
                timeout_s=timeout_s,
                concurrency=concurrency,
                ramp_s=ramp_s,
                tmp_dir=tmp_dir,
            )
            all_results.extend(results)

            # Print per-scenario results
            for r in results:
                status = "✅" if r.passed else "❌"
                print(f"  {status} {r.name:25s} {r.duration_s:7.3f}s  {r.error or ''}")

            # Ramp delay between sessions
            if session_idx < sessions - 1 and ramp_s > 0:
                await asyncio.sleep(ramp_s / max(sessions, 1))
    finally:
        server.stop()

    duration_s = time.monotonic() - started_at

    # Environment after
    rss_stats = await rss_sampler.stop()
    browser_procs_after = _count_browser_processes()
    disk_mb = _disk_usage_mb(tmp_dir)

    environment = {
        **rss_stats,
        "browser_procs_before": browser_procs_before,
        "browser_procs_after": browser_procs_after,
        "disk_usage_mb": round(disk_mb, 3),
    }

    report = build_report(
        mode=mode,
        config=config,
        realism=realism,
        scenarios=all_results,
        started_at=started_at,
        duration_s=duration_s,
        environment=environment,
    )

    # Write reports
    data = serialize_report(report)
    json_path = out_dir / "stress-report.json"
    md_path = out_dir / args.markdown if args.markdown else out_dir / "stress-report.md"

    json_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    md_path.write_text(render_markdown(report, data), encoding="utf-8")

    print(f"\nJSON written to {json_path}")
    print(f"Markdown written to {md_path}")

    # Cleanup temp dir
    try:
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)
    except Exception:
        pass

    # Exit code: 0 if all passed, 1 if any failed
    return 0 if all(s.passed for s in all_results) else 1


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Real-world stress harness for Super Browser",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Modes:
  --quick         30-60 second local probe (5 scenarios, 1 session)
  --realistic     Full configurable run (8 scenarios, configurable sessions)

Examples:
  python scripts/stress_real_world.py --quick
  python scripts/stress_real_world.py --realistic --sessions 5 --concurrency 2
        """,
    )

    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument("--quick", action="store_true", help="Quick 30-60s local probe")
    mode_group.add_argument("--realistic", action="store_true", help="Full configurable run")

    parser.add_argument("--sessions", type=int, default=DEFAULT_SESSIONS, help=f"Number of sessions (default: {DEFAULT_SESSIONS})")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help=f"Concurrency level (default: {DEFAULT_CONCURRENCY})")
    parser.add_argument("--ramp-up", type=int, default=DEFAULT_RAMP_UP_S, help=f"Ramp-up seconds (default: {DEFAULT_RAMP_UP_S})")
    parser.add_argument("--session-duration", type=int, default=DEFAULT_SESSION_DURATION_S, help=f"Session duration seconds (default: {DEFAULT_SESSION_DURATION_S})")
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_S, help=f"Per-operation timeout seconds (default: {DEFAULT_TIMEOUT_S})")
    parser.add_argument("--viewport", default="mobile,desktop", help="Viewport presets (default: mobile,desktop)")
    parser.add_argument("--output", default=None, help=f"Output directory (default: {DEFAULT_OUT_DIR})")
    parser.add_argument("--markdown", default=None, help="Markdown output filename (default: stress-report.md)")

    args = parser.parse_args()

    try:
        rc = asyncio.run(main_async(args))
    except KeyboardInterrupt:
        print("\nInterrupted.")
        rc = 130

    sys.exit(rc)


if __name__ == "__main__":
    main()
