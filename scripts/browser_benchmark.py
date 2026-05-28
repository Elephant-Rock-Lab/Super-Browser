#!/usr/bin/env python3
"""Real Browser Benchmark — Patchright baseline metrics.

Launches a real Patchright browser and measures operations against local
fixture pages served via a built-in HTTP server.

Usage:
    python scripts/browser_benchmark.py [--live] [--json PATH] [--md PATH] [--runs N]

Offline by default.  Use --live to include external navigation metrics.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import platform
import statistics
import sys
import time
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from threading import Thread
from typing import Any

# Ensure local super_browser is preferred.
_THIS_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _THIS_SRC in sys.path:
    sys.path.remove(_THIS_SRC)
sys.path.insert(0, _THIS_SRC)

import psutil  # noqa: E402

from super_browser import __version__ as sb_version  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "benchmarks" / "fixtures"
DEFAULT_RUNS = 3
DEFAULT_PORT = 18221


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _process_tree_rss() -> int:
    """Sum RSS of the current process and all recursive children (bytes)."""
    try:
        parent = psutil.Process(os.getpid())
        rss = parent.memory_info().rss
        for child in parent.children(recursive=True):
            try:
                rss += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return rss
    except Exception:
        return 0


def _summarize(name: str, unit: str, samples: list[float]) -> dict[str, Any]:
    """Build a result dict with raw samples, mean, median, min, max."""
    return {
        "name": name,
        "unit": unit,
        "samples": samples,
        "mean": round(statistics.mean(samples), 3),
        "median": round(statistics.median(samples), 3),
        "min": round(min(samples), 3),
        "max": round(max(samples), 3),
    }


def _start_fixture_server(port: int) -> HTTPServer:
    """Start a background HTTP server serving fixture pages."""
    handler = type(
        "FixtureHandler",
        (SimpleHTTPRequestHandler,),
        {"__init__": lambda self, *a, **kw: SimpleHTTPRequestHandler.__init__(
            self, *a, directory=str(FIXTURES_DIR), **kw
        )},
    )
    server = HTTPServer(("127.0.0.1", port), handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _metadata() -> dict[str, Any]:
    return {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cpu_count": os.cpu_count(),
        "super_browser_version": sb_version,
    }


# ---------------------------------------------------------------------------
# Benchmark functions
# ---------------------------------------------------------------------------


async def bench_browser_launch(base_url: str, runs: int) -> dict[str, Any]:
    """Measure browser engine start + stop cycle time."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    samples: list[float] = []
    config = SessionConfig(backend="patchright")
    for _ in range(runs):
        engine = PatchrightEngine(config)
        t0 = time.monotonic()
        await engine.start()
        elapsed = (time.monotonic() - t0) * 1000
        await engine.stop()
        samples.append(round(elapsed, 3))

    return _summarize("browser_launch_time", "ms", samples)


async def bench_new_page(base_url: str, runs: int) -> dict[str, Any]:
    """Measure new page creation time on an already-running engine."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    engine = PatchrightEngine(config)
    await engine.start()
    try:
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            page = await engine.new_page()
            elapsed = (time.monotonic() - t0) * 1000
            await page.close()
            samples.append(round(elapsed, 3))
    finally:
        await engine.stop()

    return _summarize("new_page_time", "ms", samples)


async def bench_local_navigation(base_url: str, runs: int) -> dict[str, Any]:
    """Measure navigation to a local fixture page."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    engine = PatchrightEngine(config)
    await engine.start()
    try:
        page = await engine.new_page()
        url = f"{base_url}/simple.html"
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await page.goto(url, wait_until="load")
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    finally:
        await engine.stop()

    return _summarize("local_navigation_time", "ms", samples)


async def bench_external_navigation(base_url: str, runs: int) -> dict[str, Any]:
    """Measure navigation to an external page (requires --live)."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    engine = PatchrightEngine(config)
    await engine.start()
    try:
        page = await engine.new_page()
        url = "https://example.com"
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await page.goto(url, wait_until="load", timeout=15_000)
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    except Exception as exc:
        return {"name": "external_navigation_time", "unit": "ms",
                "error": str(exc), "samples": []}
    finally:
        await engine.stop()

    return _summarize("external_navigation_time", "ms", samples)


async def bench_click(base_url: str, runs: int) -> dict[str, Any]:
    """Measure click latency on the submit button (non-navigating)."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    engine = PatchrightEngine(config)
    await engine.start()
    try:
        page = await engine.new_page()
        await page.goto(f"{base_url}/form.html", wait_until="load")
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await page.click("#submit-button")
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    finally:
        await engine.stop()

    return _summarize("click_latency", "ms", samples)


async def bench_fill(base_url: str, runs: int) -> dict[str, Any]:
    """Measure fill latency on a text input."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    engine = PatchrightEngine(config)
    await engine.start()
    try:
        page = await engine.new_page()
        await page.goto(f"{base_url}/form.html", wait_until="load")
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await page.fill("#input-1", "benchmark test value")
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    finally:
        await engine.stop()

    return _summarize("fill_latency", "ms", samples)


async def bench_screenshot(base_url: str, runs: int) -> dict[str, Any]:
    """Measure screenshot capture time."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    engine = PatchrightEngine(config)
    await engine.start()
    try:
        page = await engine.new_page()
        await page.goto(f"{base_url}/simple.html", wait_until="load")
        await page.raw_page.set_viewport_size({"width": 1280, "height": 720})
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await page.screenshot()
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    finally:
        await engine.stop()

    return _summarize("screenshot_latency", "ms", samples)


async def bench_cdp_roundtrip(base_url: str, runs: int) -> dict[str, Any]:
    """Measure CDP round-trip time for Runtime.evaluate."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    engine = PatchrightEngine(config)
    await engine.start()
    try:
        page = await engine.new_page()
        await page.goto(f"{base_url}/simple.html", wait_until="load")
        cdp = await page.raw_page.context.new_cdp_session(page.raw_page)
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await cdp.send("Runtime.evaluate", {"expression": "1+1"})
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    finally:
        await engine.stop()

    return _summarize("cdp_roundtrip_latency", "ms", samples)


async def bench_stealth_overhead(base_url: str, runs: int) -> dict[str, Any]:
    """Paired benchmark: launch with stealth minus launch without stealth.

    Measures the overhead of stealth injection at the new_page level,
    which is where the inject script is applied.
    """
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    plain_samples: list[float] = []
    stealth_samples: list[float] = []

    for _ in range(runs):
        # Plain launch + new_page
        engine = PatchrightEngine(config)
        await engine.start()
        t0 = time.monotonic()
        page = await engine.new_page()
        plain_elapsed = (time.monotonic() - t0) * 1000
        await page.close()
        await engine.stop()
        plain_samples.append(round(plain_elapsed, 3))

    # Stealth launch — inject a minimal payload via add_init_script
    stealth_js = "(function(){ window.__bench_stealth_marker = true; })();"

    for _ in range(runs):
        engine = PatchrightEngine(config)
        await engine.start()
        ctx = engine._browser_context if hasattr(engine, "_browser_context") else None
        if ctx:
            await ctx.add_init_script(stealth_js)
        t0 = time.monotonic()
        page = await engine.new_page()
        stealth_elapsed = (time.monotonic() - t0) * 1000
        await page.close()
        await engine.stop()
        stealth_samples.append(round(stealth_elapsed, 3))

    overhead_samples = [s - p for s, p in zip(stealth_samples, plain_samples)]

    return {
        "name": "stealth_injection_overhead",
        "unit": "ms",
        "samples": overhead_samples,
        "mean": round(statistics.mean(overhead_samples), 3) if overhead_samples else 0,
        "median": round(statistics.median(overhead_samples), 3) if overhead_samples else 0,
        "min": round(min(overhead_samples), 3) if overhead_samples else 0,
        "max": round(max(overhead_samples), 3) if overhead_samples else 0,
        "paired_plain_samples": plain_samples,
        "paired_stealth_samples": stealth_samples,
    }


async def bench_session_save_load(base_url: str, runs: int) -> dict[str, Any]:
    """Measure session save and load time."""
    import tempfile

    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    save_samples: list[float] = []
    load_samples: list[float] = []

    for _ in range(runs):
        # Save
        engine = PatchrightEngine(config)
        await engine.start()
        page = await engine.new_page()
        await page.goto(f"{base_url}/simple.html", wait_until="load")
        cookies = await page.raw_page.context.cookies()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False, mode="w") as f:
            path = f.name
            t0 = time.monotonic()
            json.dump(cookies, f)
            save_elapsed = (time.monotonic() - t0) * 1000
            save_samples.append(round(save_elapsed, 3))

        await page.close()
        await engine.stop()

        # Load
        engine2 = PatchrightEngine(config)
        await engine2.start()
        page2 = await engine2.new_page()
        t0 = time.monotonic()
        with open(path) as f:
            loaded = json.load(f)
        await page2.raw_page.context.add_cookies(loaded)
        load_elapsed = (time.monotonic() - t0) * 1000
        load_samples.append(round(load_elapsed, 3))

        await page2.close()
        await engine2.stop()
        os.unlink(path)

    return {
        "save": _summarize("session_save_time", "ms", save_samples),
        "load": _summarize("session_load_time", "ms", load_samples),
    }


async def bench_memory(base_url: str, runs: int) -> dict[str, Any]:
    """Measure process-tree RSS after launch and after 5 tabs."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine
    from super_browser.browser.config import SessionConfig

    config = SessionConfig(backend="patchright")
    launch_samples: list[float] = []
    tabs_samples: list[float] = []

    for _ in range(runs):
        rss_before = _process_tree_rss()
        engine = PatchrightEngine(config)
        await engine.start()
        page = await engine.new_page()
        await page.goto(f"{base_url}/simple.html", wait_until="load")
        rss_after_launch = _process_tree_rss()
        launch_samples.append(round((rss_after_launch - rss_before) / 1024 / 1024, 3))

        # Open 4 more tabs
        for __ in range(4):
            p = await engine.new_page()
            await p.goto(f"{base_url}/dom-heavy.html", wait_until="load")

        rss_after_5 = _process_tree_rss()
        tabs_samples.append(round((rss_after_5 - rss_before) / 1024 / 1024, 3))

        await engine.stop()

    return {
        "after_launch": _summarize("memory_delta_after_launch", "MB", launch_samples),
        "after_5_tabs": _summarize("memory_delta_after_5_tabs", "MB", tabs_samples),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def run_all(*, live: bool, runs: int) -> dict[str, Any]:
    """Run all benchmarks and return the full result dict."""
    server = _start_fixture_server(DEFAULT_PORT)
    base_url = f"http://127.0.0.1:{DEFAULT_PORT}"

    results: list[dict[str, Any]] = []

    print(f"Running {runs} iteration(s) per metric...\n")

    print("  browser_launch_time...")
    results.append(await bench_browser_launch(base_url, runs))

    print("  new_page_time...")
    results.append(await bench_new_page(base_url, runs))

    print("  local_navigation_time...")
    results.append(await bench_local_navigation(base_url, runs))

    if live:
        print("  external_navigation_time (live)...")
        results.append(await bench_external_navigation(base_url, runs))

    print("  click_latency...")
    results.append(await bench_click(base_url, runs))

    print("  fill_latency...")
    results.append(await bench_fill(base_url, runs))

    print("  screenshot_latency...")
    results.append(await bench_screenshot(base_url, runs))

    print("  cdp_roundtrip_latency...")
    results.append(await bench_cdp_roundtrip(base_url, runs))

    print("  stealth_injection_overhead (paired)...")
    results.append(await bench_stealth_overhead(base_url, runs))

    print("  session_save_load...")
    save_load = await bench_session_save_load(base_url, runs)
    results.append(save_load["save"])
    results.append(save_load["load"])

    print("  memory_metrics...")
    mem = await bench_memory(base_url, runs)
    results.append(mem["after_launch"])
    results.append(mem["after_5_tabs"])

    server.shutdown()

    return {
        "schema_version": 1,
        "benchmark_name": "real-browser-baseline",
        "backend": "patchright",
        "live": live,
        "runs": runs,
        "metadata": _metadata(),
        "results": results,
    }


def format_markdown(report: dict[str, Any]) -> str:
    """Format the report as a Markdown table."""
    lines = [
        f"# Browser Benchmark: {report['backend']}",
        f"",
        f"- **Date:** {report['metadata']['timestamp']}",
        f"- **Super Browser:** v{report['metadata']['super_browser_version']}",
        f"- **Python:** {report['metadata']['python_version']}",
        f"- **Platform:** {report['metadata']['platform']}",
        f"- **Runs:** {report['runs']}",
        f"- **Live:** {report['live']}",
        f"",
        f"| Metric | Mean | Median | Min | Max | Unit |",
        f"|:-------|-----:|-------:|----:|----:|:-----|",
    ]
    for r in report["results"]:
        if "error" in r:
            lines.append(f"| {r['name']} | ERROR | — | — | — | {r.get('unit', '?')} |")
        else:
            lines.append(
                f"| {r['name']} | {r['mean']:.1f} | {r['median']:.1f} | "
                f"{r['min']:.1f} | {r['max']:.1f} | {r['unit']} |"
            )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Real Browser Benchmark")
    parser.add_argument("--live", action="store_true", help="Include external navigation")
    parser.add_argument("--json", type=str, help="Write JSON results to file")
    parser.add_argument("--md", type=str, help="Write Markdown report to file")
    parser.add_argument("--runs", type=int, default=DEFAULT_RUNS, help="Iterations per metric")
    args = parser.parse_args()

    report = asyncio.run(run_all(live=args.live, runs=args.runs))

    md = format_markdown(report)
    print("\n" + md)

    if args.json:
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"JSON written to {args.json}")

    if args.md:
        Path(args.md).parent.mkdir(parents=True, exist_ok=True)
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Markdown written to {args.md}")


if __name__ == "__main__":
    main()
