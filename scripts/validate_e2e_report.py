#!/usr/bin/env python3
"""Validate E2E report JSON against the stable schema (v3).

This is a lightweight stdlib validator — no external JSON Schema dependency.

Schema v3 contract:

    {
      "schema_version": 3,
      "timestamp_utc": str,           # ISO-8601 UTC
      "environment": {
        "backend": str,
        "headless": bool,
        "python_version": str,
        "platform": str,
        "live": bool
      },
      "config": {
        "suite_name": str,
        "budget_seconds": float
      },
      "summary": {
        "total": int,
        "passed": int,
        "failed": int,
        "skipped: int,
        "duration_s": float,
        "budget_exceeded": bool
      },
      "tests": [
        {
          "name": str,
          "status": "passed" | "failed" | "skipped",
          "duration_s": float,
          "file": str,                 # optional, nullable
          "error": str | null,         # optional
          "screenshot": str | null      # optional
        }
      ],
      "artifacts": {
        "json_path": str | null,
        "markdown_path": str | null
      }
    }

Usage::

    python scripts/validate_e2e_report.py path/to/e2e-report.json
    python scripts/validate_e2e_report.py --strict path/to/e2e-report.json

Exit codes:
    0 — valid
    1 — invalid (errors printed to stderr)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Allowed status values
_VALID_STATUSES = {"passed", "failed", "skipped"}


def validate_report(report: dict[str, Any]) -> list[str]:
    """Validate a report dict against schema v3.

    Returns a list of error strings. Empty list means valid.
    """
    errors: list[str] = []

    # --- Top-level required keys ---
    required_top = {"schema_version", "timestamp_utc", "environment", "config", "summary", "tests", "artifacts"}
    for key in required_top:
        if key not in report:
            errors.append(f"Missing top-level key: '{key}'")

    if errors:
        return errors  # can't continue without basics

    # --- schema_version ---
    sv = report.get("schema_version")
    if not isinstance(sv, int):
        errors.append(f"'schema_version' must be int, got {type(sv).__name__}")
    elif sv != 3:
        errors.append(f"'schema_version' must be 3, got {sv}")

    # --- timestamp_utc ---
    ts = report.get("timestamp_utc")
    if not isinstance(ts, str) or not ts:
        errors.append(f"'timestamp_utc' must be a non-empty string, got {type(ts).__name__}")

    # --- environment ---
    env = report.get("environment")
    if not isinstance(env, dict):
        errors.append(f"'environment' must be a dict, got {type(env).__name__}")
    else:
        env_required = {"backend", "headless", "python_version", "platform", "live"}
        for key in env_required:
            if key not in env:
                errors.append(f"Missing environment key: '{key}'")
        if "live" in env and not isinstance(env["live"], bool):
            errors.append(f"environment['live'] must be bool, got {type(env['live']).__name__}")
        if "headless" in env and not isinstance(env["headless"], bool):
            errors.append(f"environment['headless'] must be bool, got {type(env['headless']).__name__}")

    # --- config ---
    config = report.get("config")
    if not isinstance(config, dict):
        errors.append(f"'config' must be a dict, got {type(config).__name__}")
    else:
        if "suite_name" not in config:
            errors.append("Missing config key: 'suite_name'")
        if "budget_seconds" not in config:
            errors.append("Missing config key: 'budget_seconds'")
        elif not isinstance(config["budget_seconds"], (int, float)):
            errors.append(f"config['budget_seconds'] must be numeric, got {type(config['budget_seconds']).__name__}")

    # --- summary ---
    summary = report.get("summary")
    if not isinstance(summary, dict):
        errors.append(f"'summary' must be a dict, got {type(summary).__name__}")
    else:
        summary_required = {"total", "passed", "failed", "skipped", "duration_s", "budget_exceeded"}
        for key in summary_required:
            if key not in summary:
                errors.append(f"Missing summary key: '{key}'")

        # Type checks for summary
        for int_key in ("total", "passed", "failed", "skipped"):
            val = summary.get(int_key)
            if val is not None and not isinstance(val, int):
                errors.append(f"summary['{int_key}'] must be int, got {type(val).__name__}")

        if "duration_s" in summary and not isinstance(summary["duration_s"], (int, float)):
            errors.append(f"summary['duration_s'] must be numeric, got {type(summary['duration_s']).__name__}")

        if "budget_exceeded" in summary and not isinstance(summary["budget_exceeded"], bool):
            errors.append(f"summary['budget_exceeded'] must be bool, got {type(summary['budget_exceeded']).__name__}")

        # Cross-check: counts must add up
        total = summary.get("total", 0)
        parts = summary.get("passed", 0) + summary.get("failed", 0) + summary.get("skipped", 0)
        if isinstance(total, int) and total != parts:
            errors.append(
                f"summary counts don't add up: total={total} but passed+failed+skipped={parts}"
            )

    # --- tests[] ---
    tests = report.get("tests")
    if not isinstance(tests, list):
        errors.append(f"'tests' must be a list, got {type(tests).__name__}")
    else:
        for i, test in enumerate(tests):
            if not isinstance(test, dict):
                errors.append(f"tests[{i}] must be a dict, got {type(test).__name__}")
                continue

            # name (required)
            if "name" not in test or not isinstance(test["name"], str) or not test["name"]:
                errors.append(f"tests[{i}]: missing or invalid 'name'")

            # status (required)
            status = test.get("status")
            if status not in _VALID_STATUSES:
                errors.append(
                    f"tests[{i}]: 'status' must be one of {_VALID_STATUSES}, got {status!r}"
                )

            # duration_s (required)
            if "duration_s" not in test:
                errors.append(f"tests[{i}]: missing required 'duration_s'")
            elif not isinstance(test["duration_s"], (int, float)):
                errors.append(f"tests[{i}]: 'duration_s' must be numeric, got {type(test['duration_s']).__name__}")

            # file (optional)
            if "file" in test and test["file"] is not None:
                if not isinstance(test["file"], str):
                    errors.append(f"tests[{i}]: 'file' must be string or null")

            # error (optional, nullable)
            if "error" in test and test["error"] is not None:
                if not isinstance(test["error"], str):
                    errors.append(f"tests[{i}]: 'error' must be string or null")

            # screenshot (optional, nullable)
            if "screenshot" in test and test["screenshot"] is not None:
                if not isinstance(test["screenshot"], str):
                    errors.append(f"tests[{i}]: 'screenshot' must be string or null")

    # --- artifacts (required, nullable paths) ---
    artifacts = report.get("artifacts")
    if not isinstance(artifacts, dict):
        errors.append(f"'artifacts' must be a dict, got {type(artifacts).__name__ if artifacts is not None else 'NoneType'}")
    else:
        for key in ("json_path", "markdown_path"):
            if key in artifacts and artifacts[key] is not None:
                if not isinstance(artifacts[key], str):
                    errors.append(f"artifacts['{key}'] must be string or null")

    return errors


def validate_file(path: Path) -> list[str]:
    """Validate a JSON report file. Returns list of errors."""
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return [f"Invalid JSON: {exc}"]
    except FileNotFoundError:
        return [f"File not found: {path}"]

    if not isinstance(report, dict):
        return [f"Report root must be a dict, got {type(report).__name__}"]

    return validate_report(report)


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        prog="validate_e2e_report",
        description="Validate E2E report JSON against schema v3",
    )
    parser.add_argument("path", type=Path, help="Path to e2e-report.json")
    parser.add_argument("--strict", action="store_true", help="Fail on missing optional fields")
    args = parser.parse_args()

    errors = validate_file(args.path)

    if args.strict:
        # In strict mode, warn about missing optional fields
        try:
            report = json.loads(args.path.read_text(encoding="utf-8"))
            if isinstance(report, dict):
                if "artifacts" not in report:
                    errors.append("Missing recommended key: 'artifacts' (strict mode)")
                for test in report.get("tests", []):
                    if isinstance(test, dict):
                        idx = report["tests"].index(test)
                        for opt_key in ("file", "error"):
                            if opt_key not in test:
                                errors.append(
                                    f"tests[{idx}]: missing optional key '{opt_key}' (strict mode)"
                                )
        except (json.JSONDecodeError, FileNotFoundError):
            pass  # already caught above

    if errors:
        print(f"❌ {len(errors)} validation error(s):", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"✅ Valid E2E report (schema v3): {args.path}")
        sys.exit(0)


if __name__ == "__main__":
    main()
