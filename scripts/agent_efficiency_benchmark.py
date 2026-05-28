#!/usr/bin/env python3
"""Agent Efficiency Benchmark — deterministic mock-based workflow measurement.

Measures tool call count, output bytes, stale-ref rate, and category coverage
for representative agent workflows. Outputs JSON + Markdown reports.

Usage:
    python scripts/agent_efficiency_benchmark.py [--json out.json] [--md out.md] [--compare baseline.json]
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Ensure the local super_browser package is preferred over other installs
_THIS_SRC = str(Path(__file__).resolve().parent.parent / "src")
if _THIS_SRC in sys.path:
    sys.path.remove(_THIS_SRC)
sys.path.insert(0, _THIS_SRC)

# Import project types (no browser dependency)
from super_browser import __version__  # noqa: E402

# ---------------------------------------------------------------------------
# Mock data structures
# ---------------------------------------------------------------------------


@dataclass
class MockAction:
    """A single simulated agent action."""

    action: str
    params: dict[str, Any]
    ok: bool = True
    success_category: str | None = None
    failure_category: str | None = None
    output_size_bytes: int = 100


@dataclass
class MockWorkflow:
    """A named sequence of mock actions representing an agent workflow."""

    name: str
    actions: list[MockAction] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Hard-coded workflow models
# ---------------------------------------------------------------------------


def _build_workflows() -> list[MockWorkflow]:
    """Return the four representative benchmark workflows."""

    return [
        # navigate → observe → extract → screenshot
        MockWorkflow(
            name="navigate_and_extract",
            actions=[
                MockAction("navigate", {"url": "https://example.com"}, ok=True,
                           success_category="navigation", output_size_bytes=512),
                MockAction("observe", {"selector": "table"}, ok=True,
                           success_category="inspection", output_size_bytes=2048),
                MockAction("extract", {"selector": "table td"}, ok=True,
                           success_category="inspection", output_size_bytes=4096),
                MockAction("screenshot", {"path": "out.png"}, ok=True,
                           success_category="artifact", output_size_bytes=15000),
            ],
        ),
        # navigate → fill → fill → click → assert
        MockWorkflow(
            name="form_fill",
            actions=[
                MockAction("navigate", {"url": "https://form.example.com"}, ok=True,
                           success_category="navigation", output_size_bytes=512),
                MockAction("fill", {"selector": "#name", "value": "Alice"}, ok=True,
                           success_category="mutation", output_size_bytes=64),
                MockAction("fill", {"selector": "#email", "value": "a@b.com"}, ok=True,
                           success_category="mutation", output_size_bytes=64),
                MockAction("click", {"selector": "button[type=submit]"}, ok=True,
                           success_category="navigation", output_size_bytes=256),
                MockAction("assert_text", {"selector": ".success", "text": "Done"}, ok=True,
                           success_category="inspection", output_size_bytes=128),
            ],
        ),
        # open → wait → assert → network_check → screenshot
        MockWorkflow(
            name="qa_smoke",
            actions=[
                MockAction("open", {"url": "https://qa.example.com"}, ok=True,
                           success_category="navigation", output_size_bytes=512),
                MockAction("wait", {"seconds": 2.0}, ok=True,
                           success_category="unchanged", output_size_bytes=32),
                MockAction("assert_text", {"text": "Welcome"}, ok=True,
                           success_category="inspection", output_size_bytes=128),
                MockAction("network_check", {"check_console_errors": True}, ok=True,
                           success_category="inspection", output_size_bytes=256),
                MockAction("screenshot", {"path": "qa_smoke.png"}, ok=True,
                           success_category="artifact", output_size_bytes=15000),
            ],
        ),
        # click (stale) → retry → click (ok) → verify
        MockWorkflow(
            name="error_recovery",
            actions=[
                MockAction("click", {"selector": ".btn"}, ok=False,
                           failure_category="stale_ref", output_size_bytes=128),
                MockAction("navigate", {"url": "https://example.com"}, ok=True,
                           success_category="navigation", output_size_bytes=512),
                MockAction("click", {"selector": ".btn"}, ok=True,
                           success_category="navigation", output_size_bytes=256),
                MockAction("verify", {"selector": ".btn", "state": "visible"}, ok=True,
                           success_category="inspection", output_size_bytes=64),
            ],
        ),
    ]


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def measure_workflow(workflow: MockWorkflow) -> dict:
    """Measure a single workflow's metrics."""
    call_count = 0
    output_bytes = 0
    stale_ref_count = 0
    category_dist: dict[str, int] = {}
    start = time.perf_counter()

    for action in workflow.actions:
        call_count += 1
        output_bytes += action.output_size_bytes

        cat = action.failure_category if not action.ok else action.success_category
        if cat:
            category_dist[cat] = category_dist.get(cat, 0) + 1

        if action.failure_category == "stale_ref":
            stale_ref_count += 1

    duration_ms = (time.perf_counter() - start) * 1000

    return {
        "call_count": call_count,
        "output_bytes": output_bytes,
        "stale_ref_count": stale_ref_count,
        "stale_ref_rate": round(stale_ref_count / max(call_count, 1), 3),
        "category_distribution": category_dist,
        "duration_ms": round(duration_ms, 3),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def build_report(workflows: list[MockWorkflow]) -> dict:
    """Run all workflows and build the full report dict."""
    wf_results: dict[str, dict] = {}
    total_calls = 0
    total_output_bytes = 0
    total_stale_refs = 0
    all_categories: set[str] = set()

    for wf in workflows:
        result = measure_workflow(wf)
        wf_results[wf.name] = result
        total_calls += result["call_count"]
        total_output_bytes += result["output_bytes"]
        total_stale_refs += result["stale_ref_count"]
        all_categories.update(result["category_distribution"].keys())

    return {
        "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        "version": __version__,
        "workflows": wf_results,
        "aggregate": {
            "total_calls": total_calls,
            "total_output_bytes": total_output_bytes,
            "overall_stale_ref_rate": round(
                total_stale_refs / max(total_calls, 1), 3
            ),
            "category_coverage": sorted(all_categories),
        },
    }


# ---------------------------------------------------------------------------
# Comparison
# ---------------------------------------------------------------------------


def compare_with_baseline(report: dict, baseline: dict) -> dict:
    """Compare current report against baseline, flag regressions."""
    regressions: list[str] = []
    agg = report["aggregate"]
    base_agg = baseline["aggregate"]

    if agg["total_calls"] > base_agg["total_calls"] * 1.2:
        regressions.append(
            f"call_count: {agg['total_calls']} > {base_agg['total_calls']} * 1.2"
        )
    if agg["total_output_bytes"] > base_agg["total_output_bytes"] * 1.3:
        regressions.append(
            f"output_bytes: {agg['total_output_bytes']} > "
            f"{base_agg['total_output_bytes']} * 1.3"
        )
    if agg["overall_stale_ref_rate"] > base_agg["overall_stale_ref_rate"] * 1.5:
        regressions.append(
            f"stale_ref_rate: {agg['overall_stale_ref_rate']} > "
            f"{base_agg['overall_stale_ref_rate']} * 1.5"
        )

    return {
        "regression_detected": len(regressions) > 0,
        "regressions": regressions,
        "baseline_version": baseline.get("version", "unknown"),
    }


# ---------------------------------------------------------------------------
# Markdown output
# ---------------------------------------------------------------------------


def generate_markdown(report: dict) -> str:
    """Generate a Markdown summary table."""
    lines = ["# Agent Efficiency Benchmark Report\n"]
    lines.append(f"**Version:** {report['version']}")
    lines.append(f"**Timestamp:** {report['timestamp']}\n")

    lines.append("## Workflow Results\n")
    lines.append(
        "| Workflow | Calls | Output (bytes) | Stale Refs | Categories |"
    )
    lines.append(
        "|:---------|:------|:---------------|:-----------|:-----------|"
    )
    for name, wf in report["workflows"].items():
        cats = ", ".join(f"{k}={v}" for k, v in wf["category_distribution"].items())
        lines.append(
            f"| {name} | {wf['call_count']} | {wf['output_bytes']} "
            f"| {wf['stale_ref_count']} | {cats} |"
        )

    lines.append("\n## Aggregate\n")
    agg = report["aggregate"]
    lines.append(f"- Total calls: {agg['total_calls']}")
    lines.append(f"- Total output: {agg['total_output_bytes']} bytes")
    lines.append(f"- Stale ref rate: {agg['overall_stale_ref_rate']}")
    lines.append(f"- Category coverage: {', '.join(agg['category_coverage'])}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> None:
    """Entry point for the benchmark CLI."""
    parser = argparse.ArgumentParser(
        description="Agent Efficiency Benchmark — deterministic mock-based measurement"
    )
    parser.add_argument(
        "--json", metavar="FILE", help="Write JSON report to FILE (stdout if omitted)"
    )
    parser.add_argument(
        "--md", metavar="FILE", help="Write Markdown report to FILE (stdout if omitted)"
    )
    parser.add_argument(
        "--compare", metavar="BASELINE", help="Compare against baseline JSON file"
    )
    args = parser.parse_args(argv)

    workflows = _build_workflows()
    report = build_report(workflows)

    # JSON output
    json_str = json.dumps(report, indent=2)
    if args.json:
        Path(args.json).write_text(json_str, encoding="utf-8")
    else:
        print(json_str)

    # Markdown output
    md_str = generate_markdown(report)
    if args.md:
        Path(args.md).write_text(md_str, encoding="utf-8")
    else:
        print()
        print(md_str)

    # Comparison
    if args.compare:
        baseline_path = Path(args.compare)
        if not baseline_path.exists():
            print(f"\nERROR: baseline file not found: {baseline_path}", file=sys.stderr)
            sys.exit(1)
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        comparison = compare_with_baseline(report, baseline)
        print("\n## Comparison with Baseline\n")
        print(f"- Baseline version: {comparison['baseline_version']}")
        print(f"- Regression detected: {comparison['regression_detected']}")
        if comparison["regressions"]:
            for r in comparison["regressions"]:
                print(f"  - ⚠ {r}")
        else:
            print("  - No regressions detected ✓")


if __name__ == "__main__":
    main()
