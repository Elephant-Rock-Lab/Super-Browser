"""CLI subpackage — interactive mode, script execution, replay, and memory commands."""

from __future__ import annotations

import argparse
import json as json_mod
from pathlib import Path

from super_browser.results import (
    ActionError,
    ActionResult,
    ErrorCategory,
    FailureCategory,
    NextAction,
    PageFingerprint,
    SuccessCategory,
    compute_page_change,
)


def memory_handler(args: argparse.Namespace) -> None:
    """Handle ``super-browser memory`` CLI commands: list, show, clear, prune."""
    from super_browser.memory.store import MemoryStore

    memory_dir = getattr(args, "dir", None) or "~/.config/super-browser/memory"
    ttl = getattr(args, "ttl", 30)
    store = MemoryStore(Path(memory_dir).expanduser(), ttl_days=ttl)

    if args.memory_command == "list":
        domains = store.list_domains()
        if not domains:
            print("No domains with memory.")
        else:
            print(f"Domains with memory ({len(domains)}):")
            for d in domains:
                mem = store.load(d)
                seq_count = len(mem.sequences)
                sel_count = len(mem.selectors)
                print(f"  {d}  ({seq_count} sequences, {sel_count} selectors)")
        return

    if args.memory_command == "show":
        mem = store.load(args.domain)
        if not mem.sequences and not mem.selectors and not mem.preferences:
            print(f"No memory for domain: {args.domain}")
        else:
            print(f"Memory for {args.domain}:")
            if mem.sequences:
                print(f"  Sequences ({len(mem.sequences)}):")
                for seq in mem.sequences:
                    status = "✓" if seq.success else "✗"
                    print(f"    {status} {seq.task} ({len(seq.actions)} actions, used {seq.used_count}x)")
            if mem.selectors:
                print(f"  Selectors ({len(mem.selectors)}):")
                for element, selector in mem.selectors.items():
                    print(f"    {element}: {selector}")
            if mem.preferences:
                print("  Preferences:")
                for key, value in mem.preferences.items():
                    print(f"    {key}: {value}")
        return

    if args.memory_command == "clear":
        store.clear(args.domain)
        print(f"Cleared memory for domain: {args.domain}")
        return

    if args.memory_command == "prune":
        removed = store.prune()
        print(f"Pruned {removed} expired entries.")
        return

    print("Usage: superbrowser memory {list|show|clear|prune}")


def stealth_validate_handler(args: argparse.Namespace) -> None:
    """Handle ``super-browser stealth-validate`` CLI commands."""
    import sys

    from super_browser.stealth.consistency.derive import derive_matrix
    from super_browser.stealth.profiles import load_profile
    from super_browser.stealth.validation.harness import StealthRegressionHarness
    from super_browser.stealth.validation.suite import FingerprintValidationSuite

    profile_id = getattr(args, "profile", None) or "windows-chrome-stable"
    seed = getattr(args, "seed", None) or "default"
    baseline_dir = Path(
        getattr(args, "baseline_dir", None) or "~/.config/super-browser/baselines"
    ).expanduser()

    profile = load_profile(profile_id)
    matrix = derive_matrix(profile, seed)
    suite = FingerprintValidationSuite()
    report = suite.run(matrix, profile)
    harness = StealthRegressionHarness(baseline_dir=baseline_dir)

    if getattr(args, "capture_baseline", False):
        harness.capture_baseline(profile, seed, matrix, report)
        print(f"Baseline captured for {profile_id} (seed={seed})")
        return

    if getattr(args, "ci", False):
        try:
            baseline = harness.load_baseline(profile_id)
        except FileNotFoundError:
            print(f"ERROR: No baseline found for {profile_id}. Run --capture-baseline first.")
            sys.exit(1)
        regressed = harness.detect_regression(report, baseline)
        if regressed:
            for check in regressed:
                print(f"REGRESSION: {check.name} ({check.check_id})")
            sys.exit(1)
        print(f"All checks passed for {profile_id}")
        return

    print(f"Profile: {profile_id}, Seed: {seed}")
    print(f"Score: {report.score:.0f}/100, Passed: {report.passed}")
    for check in report.checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"  [{status}] {check.name}: {check.actual}")


def _result_demo_handler(args: argparse.Namespace) -> None:
    """Demonstrate structured result categories with optional JSON output."""
    if args.stale:
        result = ActionResult(
            ok=False,
            error=ActionError(
                category=ErrorCategory.SELECTOR_NOT_FOUND,
                message="Element @e5 not found — stale ref",
                recoverable=True,
                retry_hint="Re-run snapshot -i to refresh refs",
            ),
            failure_category=FailureCategory.STALE_REF,
            next_actions=[
                NextAction(action_id="refresh_snapshot", description="Re-run snapshot -i to refresh refs"),
                NextAction(action_id="retry_click", description="Retry click with fresh refs", compiled_args={"selector": "@e5"}),
            ],
        )
    elif args.fail:
        result = ActionResult(
            ok=False,
            error=ActionError(
                category=ErrorCategory.TIMEOUT,
                message="Action timed out after 5s",
                recoverable=True,
                retry_hint="Increase timeout or simplify selector",
            ),
            failure_category=FailureCategory.TIMEOUT,
        )
    else:
        fp_before = PageFingerprint(url="https://example.com", title="Example", node_count=42, interactive_count=5)
        fp_after = PageFingerprint(url="https://example.com/page2", title="Page 2", node_count=38, interactive_count=4)
        summary = compute_page_change(fp_before, fp_after)
        result = ActionResult(
            ok=True,
            success_category=SuccessCategory.NAVIGATION,
            page_change_summary=summary,
        )

    result.result_category = "success" if result.ok else "failure"

    if args.json:
        print(json_mod.dumps(result.to_dict(), indent=2, default=str))
    else:
        print(f"Result: {'OK' if result.ok else 'FAIL'}")
        print(f"Category: {result.result_category}")
        if result.success_category:
            print(f"Success: {result.success_category.value}")
        if result.failure_category:
            print(f"Failure: {result.failure_category.value}")
        if result.next_actions:
            print(f"Next actions: {len(result.next_actions)}")
        if result.page_change_summary:
            pcs = result.page_change_summary
            print(f"Page change: {pcs.change_type} — {pcs.summary}")


def main() -> None:
    """Entry point for ``super-browser`` CLI."""
    parser = argparse.ArgumentParser(
        prog="superbrowser",
        description="Super Browser CLI",
    )
    sub = parser.add_subparsers(dest="command")

    mem_parser = sub.add_parser("memory", help="Agent memory management")
    mem_parser.add_argument("memory_command", choices=["list", "show", "clear", "prune"])
    mem_parser.add_argument("--domain", default=None)
    mem_parser.add_argument("--dir", default=None)
    mem_parser.add_argument("--ttl", type=int, default=30)

    sv_parser = sub.add_parser("stealth-validate", help="Fingerprint validation")
    sv_parser.add_argument("--profile", default=None, help="Device profile ID")
    sv_parser.add_argument("--seed", default=None, help="Seed for matrix derivation")
    sv_parser.add_argument("--baseline-dir", default=None, help="Baseline directory")
    sv_parser.add_argument("--capture-baseline", action="store_true")
    sv_parser.add_argument("--ci", action="store_true")

    json_parser = sub.add_parser("result-demo", help="Demonstrate structured result categories")
    json_parser.add_argument("--json", action="store_true", help="Output as JSON")
    json_parser.add_argument("--fail", action="store_true", help="Generate a failure result")
    json_parser.add_argument("--stale", action="store_true", help="Generate a stale-ref failure")

    args = parser.parse_args()

    if args.command == "memory":
        memory_handler(args)
    elif args.command == "stealth-validate":
        stealth_validate_handler(args)
    elif args.command == "result-demo":
        _result_demo_handler(args)
    else:
        parser.print_help()
