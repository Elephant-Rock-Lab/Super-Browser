#!/usr/bin/env python3
"""E2E historical trend tracker.

Consumes validated schema v3 ``e2e-report.json`` files, archives them
into a compact ``e2e-history.json``, and renders a ``e2e-trend.md``
summary. No thresholds, no regression gates, no CI failure policy.

Usage::

    python scripts/e2e_trend.py \\
        --reports tests/e2e/artifacts/e2e-report.json \\
        --history tests/e2e/artifacts/e2e-history.json \\
        --markdown tests/e2e/artifacts/e2e-trend.md \\
        --max-runs 30

Multiple reports can be appended in a single invocation by passing
``--reports file1.json file2.json ...``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Validator import (reuse scripts/validate_e2e_report.py)
# ---------------------------------------------------------------------------

_THIS_DIR = Path(__file__).resolve().parent
if str(_THIS_DIR) not in sys.path:
    sys.path.insert(0, str(_THIS_DIR))

from validate_e2e_report import validate_report  # noqa: E402

# ---------------------------------------------------------------------------
# Core logic
# ---------------------------------------------------------------------------


def load_history(path: Path) -> dict[str, Any]:
    """Load an existing history file, or return an empty history shell.

    Returns a dict with ``schema_version``, ``updated_utc``, ``max_runs``,
    and ``runs`` keys.
    """
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and "runs" in data:
                return data
        except (json.JSONDecodeError, OSError):
            pass  # fall through to empty
    return {
        "schema_version": 1,
        "updated_utc": "",
        "max_runs": 30,
        "runs": [],
    }


def extract_run_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Extract a compact run summary from a validated v3 report."""
    env = report.get("environment", {})
    config = report.get("config", {})
    summary = report.get("summary", {})
    tests = report.get("tests", [])

    failed_tests = [
        t["name"] for t in tests
        if t.get("status") == "failed"
    ]

    return {
        "timestamp_utc": report.get("timestamp_utc", ""),
        "suite_name": config.get("suite_name", "unknown"),
        "backend": env.get("backend", "unknown"),
        "headless": env.get("headless", True),
        "live": env.get("live", False),
        "total": summary.get("total", 0),
        "passed": summary.get("passed", 0),
        "failed": summary.get("failed", 0),
        "skipped": summary.get("skipped", 0),
        "duration_s": summary.get("duration_s", 0.0),
        "budget_exceeded": summary.get("budget_exceeded", False),
        "failed_tests": failed_tests,
    }


def append_run(
    history: dict[str, Any],
    run: dict[str, Any],
    max_runs: int,
) -> dict[str, Any]:
    """Append a run summary to history, dedup by timestamp, truncate.

    If a run with the same ``timestamp_utc`` already exists, it is
    replaced in-place. After append, the history is truncated to
    ``max_runs`` most recent entries (sorted by timestamp descending).
    """
    runs: list[dict[str, Any]] = history.get("runs", [])
    ts = run.get("timestamp_utc", "")

    # Dedup: replace existing entry with same timestamp
    runs = [r for r in runs if r.get("timestamp_utc") != ts]
    runs.append(run)

    # Sort by timestamp descending (newest first)
    runs.sort(key=lambda r: r.get("timestamp_utc", ""), reverse=True)

    # Truncate to max_runs
    runs = runs[:max_runs]

    history["runs"] = runs
    history["max_runs"] = max_runs
    history["updated_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    history["schema_version"] = 1

    return history


def process_reports(
    report_paths: list[Path],
    history: dict[str, Any],
    max_runs: int,
) -> tuple[dict[str, Any], list[str]]:
    """Validate and append reports to history.

    Returns ``(updated_history, errors)`` where errors contains messages
    for reports that failed validation and were skipped.
    """
    errors: list[str] = []

    for path in report_paths:
        try:
            report = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{path}: invalid JSON ({exc})")
            continue
        except FileNotFoundError:
            errors.append(f"{path}: file not found")
            continue

        if not isinstance(report, dict):
            errors.append(f"{path}: root must be a dict")
            continue

        val_errors = validate_report(report)
        if val_errors:
            errors.append(f"{path}: schema validation failed: {'; '.join(val_errors[:3])}")
            continue

        run = extract_run_summary(report)
        history = append_run(history, run, max_runs)

    return history, errors


def render_trend_markdown(history: dict[str, Any]) -> str:
    """Render the trend summary as Markdown."""
    runs: list[dict[str, Any]] = history.get("runs", [])
    max_runs = history.get("max_runs", 30)

    lines: list[str] = [
        "# E2E Trend Summary",
        "",
        f"- **Runs tracked:** {len(runs)} (max {max_runs})",
        f"- **History updated:** {history.get('updated_utc', 'N/A')}",
        "",
    ]

    if not runs:
        lines.append("_No runs recorded yet._")
        return "\n".join(lines) + "\n"

    latest = runs[0]  # newest first
    prev = runs[1] if len(runs) > 1 else None

    # Latest result
    latest_status = (
        f"{latest['passed']}/{latest['total']} passed"
        if latest["failed"] == 0
        else f"{latest['failed']} failed"
    )
    lines.append(f"- **Latest result:** {latest_status}")

    # Pass rate trend
    if prev is not None:
        latest_rate = latest["passed"] / latest["total"] if latest["total"] > 0 else 0
        prev_rate = prev["passed"] / prev["total"] if prev["total"] > 0 else 0
        delta = latest_rate - prev_rate
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
        lines.append(
            f"- **Pass rate trend:** {latest_rate:.1%} ({arrow} {abs(delta):.1%} vs previous)"
        )
    else:
        lines.append("- **Pass rate trend:** N/A (first run)")

    # Duration trend
    if prev is not None:
        dur_delta = latest["duration_s"] - prev["duration_s"]
        arrow = "↑" if dur_delta > 0 else ("↓" if dur_delta < 0 else "→")
        lines.append(
            f"- **Duration trend:** {latest['duration_s']:.1f}s "
            f"({arrow} {abs(dur_delta):.1f}s vs previous)"
        )
    else:
        lines.append(f"- **Duration trend:** {latest['duration_s']:.1f}s (first run)")

    # Budget exceeded
    budget_count = sum(1 for r in runs if r.get("budget_exceeded", False))
    lines.append(f"- **Budget exceeded:** {budget_count}/{len(runs)} runs")

    # Recent failures (collect from all runs, newest first)
    all_failures: list[tuple[str, str]] = []
    for r in runs:
        for ft in r.get("failed_tests", []):
            all_failures.append((ft, r.get("timestamp_utc", "")))

    lines.append("")
    if all_failures:
        lines.append("## Recent Failures")
        lines.append("")
        for name, ts in all_failures[:10]:
            lines.append(f"- `{name}` — {ts}")
    else:
        lines.append("## Recent Failures")
        lines.append("")
        lines.append("_No failures in recent history._")

    lines.append("")
    return "\n".join(lines)


def write_history(history: dict[str, Any], path: Path) -> None:
    """Write history JSON to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")


def write_markdown(md: str, path: Path) -> None:
    """Write trend Markdown to file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(md, encoding="utf-8")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="e2e_trend",
        description="E2E historical trend tracker — observational only, no gates",
    )
    parser.add_argument(
        "--reports",
        nargs="+",
        type=Path,
        required=True,
        help="One or more e2e-report.json files to append",
    )
    parser.add_argument(
        "--history",
        type=Path,
        default=Path("tests/e2e/artifacts/e2e-history.json"),
        help="History JSON file (read + updated)",
    )
    parser.add_argument(
        "--markdown",
        type=Path,
        default=Path("tests/e2e/artifacts/e2e-trend.md"),
        help="Trend Markdown output path",
    )
    parser.add_argument(
        "--max-runs",
        type=int,
        default=30,
        help="Maximum number of runs to keep in history (default: 30)",
    )
    args = parser.parse_args()

    # Load existing history
    history = load_history(args.history)

    # Process reports
    history, errors = process_reports(args.reports, history, args.max_runs)

    # Write outputs
    write_history(history, args.history)
    md = render_trend_markdown(history)
    write_markdown(md, args.markdown)

    print(md)

    if errors:
        print(f"\n⚠ {len(errors)} report(s) skipped:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)


if __name__ == "__main__":
    main()
