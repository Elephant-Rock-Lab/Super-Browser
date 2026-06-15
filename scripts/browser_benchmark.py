#!/usr/bin/env python3
"""Real Browser Benchmark — offline fixture-backed performance measurement.

Launches a real Patchright browser and measures operations against local
fixture pages served via a built-in HTTP server. No network dependency.

Usage::

    python scripts/browser_benchmark.py \\
        --fixtures benchmarks/fixtures \\
        --out-dir benchmarks/results \\
        --iterations 5 \\
        --warmup 1

Optional flags::

    --headless 0       Visible browser (default: headless)
    --backend patchright   Browser backend (default: patchright)
    --json PATH        Write JSON to custom path
    --markdown PATH    Write Markdown to custom path
    --timeout-s 30     Per-operation timeout

Offline by default. All fixtures are served locally.
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

_THIS_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _THIS_SRC in sys.path:
    sys.path.remove(_THIS_SRC)
sys.path.insert(0, _THIS_SRC)

from super_browser import __version__ as sb_version  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_FIXTURES = Path(__file__).resolve().parent.parent / "benchmarks" / "fixtures"
DEFAULT_ITERATIONS = 5
DEFAULT_WARMUP = 1
DEFAULT_PORT = 18221
DEFAULT_TIMEOUT_S = 30

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _process_tree_rss() -> float:
    """Sum RSS of the current process and all recursive children (bytes).

    Returns 0.0 if psutil is unavailable.
    """
    try:
        import psutil

        parent = psutil.Process(os.getpid())
        rss = parent.memory_info().rss
        for child in parent.children(recursive=True):
            try:
                rss += child.memory_info().rss
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        return float(rss)
    except ImportError:
        return 0.0
    except Exception:
        return 0.0


def _summarize(name: str, unit: str, samples: list[float]) -> dict[str, Any]:
    """Build a metric dict with raw samples and statistics."""
    result: dict[str, Any] = {
        "name": name,
        "unit": unit,
        "samples": samples,
        "mean": round(statistics.mean(samples), 3) if samples else 0,
        "median": round(statistics.median(samples), 3) if samples else 0,
        "min": round(min(samples), 3) if samples else 0,
        "max": round(max(samples), 3) if samples else 0,
    }
    result["stdev"] = round(statistics.stdev(samples), 3) if len(samples) >= 2 else 0.0
    return result


def _start_fixture_server(fixtures_dir: Path, port: int) -> HTTPServer:
    """Start a background HTTP server serving fixture pages."""

    class FixtureHandler(SimpleHTTPRequestHandler):
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            super().__init__(*args, directory=str(fixtures_dir), **kwargs)

        def log_message(self, *args: Any) -> None:  # type: ignore[override]
            pass  # suppress stderr noise

    server = HTTPServer(("127.0.0.1", port), FixtureHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def _environment(headless: bool, backend: str) -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "browser_backend": backend,
        "headless": headless,
        "super_browser_version": sb_version,
    }


def discover_fixtures(fixtures_dir: Path) -> list[str]:
    """Return sorted list of fixture HTML filenames."""
    if not fixtures_dir.is_dir():
        return []
    return sorted(f.name for f in fixtures_dir.glob("*.html"))


# ---------------------------------------------------------------------------
# Benchmark functions
# ---------------------------------------------------------------------------

_headed = False  # set by CLI


async def _bench_launch(backend: str, runs: int) -> dict[str, Any]:
    """Measure browser engine start + stop cycle."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine

    samples: list[float] = []
    for _ in range(runs):
        engine = PatchrightEngine(type("C", (), {"backend": backend, "headless": not _headed})())
        t0 = time.monotonic()
        await engine.start()
        elapsed = (time.monotonic() - t0) * 1000
        await engine.stop()
        samples.append(round(elapsed, 3))
    return _summarize("browser_launch", "ms", samples)


async def _bench_new_page(base_url: str, runs: int) -> dict[str, Any]:
    """Measure new page creation time."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine

    engine = PatchrightEngine(type("C", (), {"backend": "patchright", "headless": not _headed})())
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
    return _summarize("new_page", "ms", samples)


async def _bench_navigate(base_url: str, fixture: str, runs: int, label: str) -> dict[str, Any]:
    """Measure navigation to a specific fixture page."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine

    engine = PatchrightEngine(type("C", (), {"backend": "patchright", "headless": not _headed})())
    await engine.start()
    try:
        page = await engine.new_page()
        url = f"{base_url}/{fixture}"
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await page.goto(url, wait_until="load")
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    finally:
        await engine.stop()
    return _summarize(f"navigate_{label}", "ms", samples)


async def _bench_dom_query(base_url: str, runs: int) -> dict[str, Any]:
    """Measure DOM query (selector resolution + count)."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine

    engine = PatchrightEngine(type("C", (), {"backend": "patchright", "headless": not _headed})())
    await engine.start()
    try:
        page = await engine.new_page()
        await page.goto(f"{base_url}/dom-heavy.html", wait_until="load")
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await page.query_selector_all("div")
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    finally:
        await engine.stop()
    return _summarize("dom_query", "ms", samples)


async def _bench_click_fill(base_url: str, runs: int) -> dict[str, Any]:
    """Measure click + fill combined interaction latency."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine

    engine = PatchrightEngine(type("C", (), {"backend": "patchright", "headless": not _headed})())
    await engine.start()
    try:
        page = await engine.new_page()
        await page.goto(f"{base_url}/form.html", wait_until="load")
        samples: list[float] = []
        for _ in range(runs):
            t0 = time.monotonic()
            await page.fill("#input-1", "benchmark test value")
            await page.click("#submit-button")
            elapsed = (time.monotonic() - t0) * 1000
            samples.append(round(elapsed, 3))
        await page.close()
    finally:
        await engine.stop()
    return _summarize("click_fill", "ms", samples)


async def _bench_screenshot(base_url: str, runs: int) -> dict[str, Any]:
    """Measure screenshot capture time."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine

    engine = PatchrightEngine(type("C", (), {"backend": "patchright", "headless": not _headed})())
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
    return _summarize("screenshot", "ms", samples)


async def _bench_memory(base_url: str, runs: int) -> dict[str, Any]:
    """Measure process-tree RSS delta after launch + page load."""
    from super_browser.browser.backends.patchright_backend import PatchrightEngine

    samples: list[float] = []
    rss_before_total = 0.0
    rss_after_total = 0.0

    for _ in range(runs):
        rss_before = _process_tree_rss()
        engine = PatchrightEngine(type("C", (), {"backend": "patchright", "headless": not _headed})())
        await engine.start()
        page = await engine.new_page()
        await page.goto(f"{base_url}/simple.html", wait_until="load")
        rss_after = _process_tree_rss()
        await engine.stop()

        if rss_before > 0 and rss_after > 0:
            delta_mb = round((rss_after - rss_before) / 1024 / 1024, 3)
            samples.append(delta_mb)
            rss_before_total = rss_before
            rss_after_total = rss_after

    if not samples:
        return {
            "unit": "mb",
            "rss_before_mb": None,
            "rss_after_mb": None,
            "delta_mb": None,
            "note": "psutil unavailable — memory metrics skipped",
        }

    return {
        "unit": "mb",
        "rss_before_mb": round(rss_before_total / 1024 / 1024, 3),
        "rss_after_mb": round(rss_after_total / 1024 / 1024, 3),
        "delta_mb": _summarize("memory_delta", "MB", samples),
    }


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


async def run_benchmarks(
    *,
    fixtures_dir: Path,
    iterations: int,
    warmup: int,
    headless: bool,
    backend: str,
    timeout_s: int,
) -> dict[str, Any]:
    """Run all benchmarks and return the full report dict."""
    global _headed
    _headed = not headless

    server = _start_fixture_server(fixtures_dir, DEFAULT_PORT)
    base_url = f"http://127.0.0.1:{DEFAULT_PORT}"

    # Warmup (not measured)
    if warmup > 0:
        print(f"Warming up ({warmup} iteration)...\n")
        await _bench_launch(backend, warmup)

    metrics: list[dict[str, Any]] = []

    print(f"Running {iterations} iterations per metric...\n")

    print("  browser_launch...")
    metrics.append(await _bench_launch(backend, iterations))

    print("  new_page...")
    metrics.append(await _bench_new_page(base_url, iterations))

    print("  navigate_simple...")
    metrics.append(await _bench_navigate(base_url, "simple.html", iterations, "simple"))

    print("  navigate_form...")
    metrics.append(await _bench_navigate(base_url, "form.html", iterations, "form"))

    print("  navigate_dom_heavy...")
    metrics.append(await _bench_navigate(base_url, "dom-heavy.html", iterations, "dom_heavy"))

    print("  dom_query...")
    metrics.append(await _bench_dom_query(base_url, iterations))

    print("  click_fill...")
    metrics.append(await _bench_click_fill(base_url, iterations))

    print("  screenshot...")
    metrics.append(await _bench_screenshot(base_url, iterations))

    print("  memory_delta...")
    memory = await _bench_memory(base_url, iterations)

    server.shutdown()

    return {
        "schema_version": 1,
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "environment": _environment(headless, backend),
        "config": {
            "iterations": iterations,
            "warmup": warmup,
            "fixtures_dir": str(fixtures_dir),
            "timeout_s": timeout_s,
        },
        "metrics": metrics,
        "memory": memory,
    }


def format_markdown(report: dict[str, Any]) -> str:
    """Format the report as a Markdown table."""
    env = report["environment"]
    cfg = report["config"]
    lines = [
        "# Benchmark Results",
        "",
        f"- **Timestamp:** {report['timestamp_utc']}",
        f"- **Super Browser:** v{env['super_browser_version']}",
        f"- **Backend:** {env['browser_backend']}",
        f"- **Headless:** {env['headless']}",
        f"- **Python:** {env['python']}",
        f"- **Platform:** {env['platform']}",
        f"- **Iterations:** {cfg['iterations']}",
        f"- **Warmup:** {cfg['warmup']}",
        "",
        "| Metric | Mean | Median | Min | Max | Stdev | Unit |",
        "|:-------|-----:|-------:|----:|----:|------:|:-----|",
    ]

    for m in report["metrics"]:
        lines.append(
            f"| {m['name']} | {m['mean']:.1f} | {m['median']:.1f} | "
            f"{m['min']:.1f} | {m['max']:.1f} | {m['stdev']:.1f} | {m['unit']} |"
        )

    mem = report.get("memory", {})
    if mem.get("delta_mb") and isinstance(mem["delta_mb"], dict):
        d = mem["delta_mb"]
        lines.append(
            f"| {d['name']} | {d['mean']:.1f} | {d['median']:.1f} | "
            f"{d['min']:.1f} | {d['max']:.1f} | {d['stdev']:.1f} | {d['unit']} |"
        )
    elif mem.get("note"):
        lines.append("| memory_delta | — | — | — | — | — | skipped |")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="browser_benchmark",
        description="Real Browser Benchmark — offline fixture-backed measurement",
    )
    parser.add_argument("--fixtures", type=Path, default=DEFAULT_FIXTURES, help="Fixtures directory")
    parser.add_argument("--out-dir", type=Path, default=Path("benchmarks/results"), help="Output directory")
    parser.add_argument("--iterations", type=int, default=DEFAULT_ITERATIONS, help="Iterations per metric")
    parser.add_argument("--warmup", type=int, default=DEFAULT_WARMUP, help="Warmup iterations (not measured)")
    parser.add_argument("--headless", type=int, default=1, help="1=headless (default), 0=headed")
    parser.add_argument("--backend", type=str, default="patchright", help="Browser backend")
    parser.add_argument("--json", type=Path, default=None, help="Custom JSON output path")
    parser.add_argument("--markdown", type=Path, default=None, help="Custom Markdown output path")
    parser.add_argument("--timeout-s", type=int, default=DEFAULT_TIMEOUT_S, help="Per-operation timeout")
    args = parser.parse_args()

    fixtures = args.fixtures.resolve()
    if not fixtures.is_dir():
        print(f"Error: fixtures directory not found: {fixtures}", file=sys.stderr)
        sys.exit(1)

    discovered = discover_fixtures(fixtures)
    if not discovered:
        print(f"Error: no HTML fixtures found in {fixtures}", file=sys.stderr)
        sys.exit(1)

    print(f"Fixtures discovered: {', '.join(discovered)}")
    print(f"Iterations: {args.iterations}, Warmup: {args.warmup}")
    print()

    report = asyncio.run(
        run_benchmarks(
            fixtures_dir=fixtures,
            iterations=args.iterations,
            warmup=args.warmup,
            headless=bool(args.headless),
            backend=args.backend,
            timeout_s=args.timeout_s,
        )
    )

    md = format_markdown(report)
    print("\n" + md)

    # Determine output paths
    json_path = args.json or (args.out_dir / "benchmark-results.json")
    md_path = args.markdown or (args.out_dir / "benchmark-results.md")

    json_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"JSON written to {json_path}")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"Markdown written to {md_path}")


if __name__ == "__main__":
    main()
