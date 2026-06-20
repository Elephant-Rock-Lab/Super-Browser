"""Super Browser CLI — unified command-line interface.

This package is the single source of truth for the ``superbrowser`` CLI
entry point. All subcommands are registered here.

Commands:
  version         — Print version
  info            — Show system and dependency info
  run             — Run a simple automation task
  interactive     — Start interactive REPL with persistent browser
  script          — Execute a YAML script file
  replay          — Replay a recording JSON file
  act             — Run a one-shot agent instruction
  stealth-check   — Run offline fingerprint scoring and report
  stealth-validate — Validate fingerprint against baselines (CI/regression mode)
  memory          — Manage per-domain agent memory
  result-demo     — Internal: result-type demo (not a primary command)
"""

from __future__ import annotations

import argparse
import asyncio
import json as json_mod
import sys
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


def main() -> None:
    """Entry point for the ``superbrowser`` CLI."""
    parser = argparse.ArgumentParser(
        prog="superbrowser",
        description="Super Browser — AI browser automation CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # version
    sub.add_parser("version", help="Print version")

    # info
    sub.add_parser("info", help="Show system info")

    # run
    run = sub.add_parser("run", help="Run a simple automation task")
    run.add_argument("--url", default="https://example.com", help="URL to navigate to")
    run.add_argument("--action", default="observe", choices=["observe", "screenshot", "extract"], help="Action to perform")
    run.add_argument("--output", default="-", help="Output file (- for stdout)")

    # interactive
    sub.add_parser("interactive", help="Start interactive REPL with persistent browser")

    # script
    script_parser = sub.add_parser("script", help="Execute a YAML script file")
    script_parser.add_argument("file", help="Path to YAML script file")
    script_parser.add_argument("--output", default=None, help="Write results to JSON file")

    # replay
    replay_parser = sub.add_parser("replay", help="Replay a recording JSON file")
    replay_parser.add_argument("file", help="Path to recording JSON file")
    replay_parser.add_argument("--delay", type=float, default=100, help="Delay between actions in ms (default: 100)")

    # act
    act_parser = sub.add_parser("act", help="Run a one-shot agent instruction")
    act_parser.add_argument("instruction", help="Natural language instruction")
    act_parser.add_argument("--url", default=None, help="URL to navigate to first")
    act_parser.add_argument("--max-steps", type=int, default=50, help="Max agent steps (default: 50)")

    # stealth-check
    stealth_check = sub.add_parser("stealth-check", help="Run offline fingerprint scoring and report")
    stealth_check.add_argument("--online", action="store_true", default=False, help="Run in online mode (requires browser)")
    stealth_check.add_argument("--format", default="markdown", choices=["markdown", "html"], help="Report format (default: markdown)")
    stealth_check.add_argument("--threshold", type=int, default=70, help="Pass threshold (default: 70)")

    # stealth-validate
    sv_parser = sub.add_parser("stealth-validate", help="Validate fingerprint against baselines (CI/regression mode)")
    sv_parser.add_argument("--profile", default=None, help="Device profile ID")
    sv_parser.add_argument("--seed", default=None, help="Seed for matrix derivation")
    sv_parser.add_argument("--baseline-dir", default=None, help="Baseline directory")
    sv_parser.add_argument("--capture-baseline", action="store_true")
    sv_parser.add_argument("--ci", action="store_true")

    # memory
    memory_parser = sub.add_parser("memory", help="Manage per-domain agent memory")
    memory_sub = memory_parser.add_subparsers(dest="memory_command")
    memory_list = memory_sub.add_parser("list", help="List domains with memory")
    memory_list.add_argument("--dir", default=None, help="Memory directory (default: ~/.config/super-browser/memory)")
    memory_show = memory_sub.add_parser("show", help="Show memory for a domain")
    memory_show.add_argument("domain", help="Domain to show")
    memory_show.add_argument("--dir", default=None, help="Memory directory")
    memory_clear = memory_sub.add_parser("clear", help="Clear memory for a domain")
    memory_clear.add_argument("domain", help="Domain to clear")
    memory_clear.add_argument("--dir", default=None, help="Memory directory")
    memory_prune = memory_sub.add_parser("prune", help="Prune expired memory entries")
    memory_prune.add_argument("--dir", default=None, help="Memory directory")
    memory_prune.add_argument("--ttl", type=int, default=30, help="TTL in days (default: 30)")

    # result-demo (internal — not a primary command, kept for backward compat)
    json_parser = sub.add_parser("result-demo", help="internal: result-type demo")
    json_parser.add_argument("--json", action="store_true", help="Output as JSON")
    json_parser.add_argument("--fail", action="store_true", help="Generate a failure result")
    json_parser.add_argument("--stale", action="store_true", help="Generate a stale-ref failure")

    args = parser.parse_args()

    # Dispatch
    if args.command == "version" or args.command is None:
        from super_browser import __version__
        print(f"superbrowser {__version__}")
        return

    if args.command == "info":
        _print_info()
        return

    if args.command == "run":
        asyncio.run(_run(args))
        return

    if args.command == "interactive":
        asyncio.run(_interactive(args))
        return

    if args.command == "script":
        asyncio.run(_script(args))
        return

    if args.command == "replay":
        asyncio.run(_replay(args))
        return

    if args.command == "act":
        asyncio.run(_act(args))
        return

    if args.command == "stealth-check":
        sys.exit(asyncio.run(_stealth_check(args)))

    if args.command == "stealth-validate":
        _stealth_validate(args)
        return

    if args.command == "memory":
        _memory(args)
        return

    if args.command == "result-demo":
        _result_demo(args)
        return

    parser.print_help()


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


def _print_info() -> None:
    """Print system and dependency info."""
    from super_browser import __version__

    print(f"superbrowser: {__version__}")
    print(f"python: {sys.version}")

    deps = {
        "patchright": "browser",
        "anthropic": "anthropic",
        "openai": "openai",
        "cryptography": "security",
        "mcp": "mcp",
        "httpx": "cloud",
        # Pillow ships in the [patchright] extra (for screenshot encoding);
        # there is no [vision] extra -- the previous suggestion pointed users
        # at a non-existent install target.
        "Pillow": "patchright",
    }
    for mod, extra in deps.items():
        try:
            __import__(mod)
            print(f"  {mod}: installed [{extra}]")
        except ImportError:
            print(f"  {mod}: not installed (pip install superbrowser-sdk[{extra}])")


async def _run(args: argparse.Namespace) -> None:
    """Run a simple automation task."""
    import json

    from super_browser import SuperBrowser
    from super_browser.testing import MockLLMClient

    sb = SuperBrowser(llm_client=MockLLMClient())
    await sb.start()
    try:
        await sb.navigate(args.url)
        if args.action == "observe":
            result = await sb.observe()
            output = json.dumps(result.data, indent=2, default=str)
        elif args.action == "screenshot":
            result = await sb._page.screenshot(full_page=False)
            output = f"Screenshot: {len(result)} bytes"
        elif args.action == "extract":
            result = await sb.extract("page content")
            if hasattr(result.data, "to_dict"):
                output = json.dumps(result.data.to_dict(), indent=2, default=str)
            else:
                output = json.dumps({"extracted": str(result.data.extracted)[:200]}, indent=2)
        else:
            output = "Unknown action"

        if args.output == "-":
            print(output)
        else:
            with open(args.output, "w") as f:
                f.write(output)
            print(f"Output written to {args.output}")
    finally:
        await sb.stop()


async def _interactive(args: argparse.Namespace) -> None:
    """Launch interactive REPL with persistent browser."""
    from super_browser.cli.interactive import run_interactive
    await run_interactive()


async def _script(args: argparse.Namespace) -> None:
    """Execute a YAML script file."""
    from super_browser.cli.script import run_script
    await run_script(args.file, output_path=args.output)


async def _replay(args: argparse.Namespace) -> None:
    """Replay a recording JSON file."""
    from super_browser.cli.script import run_replay
    await run_replay(args.file, delay_ms=args.delay)


async def _act(args: argparse.Namespace) -> None:
    """Run a one-shot agent instruction."""
    from super_browser.cli.script import run_act
    await run_act(args.instruction, url=args.url, max_steps=args.max_steps)


def _stealth_validate(args: argparse.Namespace) -> None:
    """Handle ``superbrowser stealth-validate`` CLI commands."""
    from super_browser.stealth.consistency.derive import derive_matrix
    from super_browser.stealth.profiles import load_profile
    from super_browser.stealth.validation.harness import StealthRegressionHarness
    from super_browser.stealth.validation.suite import FingerprintValidationSuite

    profile_id = args.profile or "windows-chrome-stable"
    seed = args.seed or "default"
    baseline_dir = Path(args.baseline_dir or "~/.config/super-browser/baselines").expanduser()

    profile = load_profile(profile_id)
    matrix = derive_matrix(profile, seed)
    suite = FingerprintValidationSuite()
    report = suite.run(matrix, profile)
    harness = StealthRegressionHarness(baseline_dir=baseline_dir)

    if args.capture_baseline:
        harness.capture_baseline(profile, seed, matrix, report)
        print(f"Baseline captured for {profile_id} (seed={seed})")
        return

    if args.ci:
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


async def _stealth_check(args: argparse.Namespace) -> int:
    """Run stealth fingerprint check and print report."""
    from super_browser.stealth.fingerprint_scanner import FingerprintScanner
    from super_browser.stealth.report import StealthReport

    scanner = FingerprintScanner(scanner_config={"offline": not args.online})
    score = await scanner.scan()

    if args.format == "html":
        report = StealthReport.generate_html(score)
    else:
        report = StealthReport.generate_markdown(score)

    print(report)

    if score.overall >= args.threshold:
        return 0
    return 1


def _memory(args: argparse.Namespace) -> None:
    """Handle ``superbrowser memory`` CLI commands: list, show, clear, prune."""
    from super_browser.memory.store import MemoryStore

    memory_dir = args.dir or "~/.config/super-browser/memory"
    store = MemoryStore(Path(memory_dir).expanduser(), ttl_days=getattr(args, "ttl", 30))

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


def _result_demo(args: argparse.Namespace) -> None:
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


# ---------------------------------------------------------------------------
# Backward-compat aliases — pre-unification public handler names
# ---------------------------------------------------------------------------
# Issue #148: Before the CLI unification, ``memory_handler`` and
# ``stealth_validate_handler`` were public functions on the ``cli`` package.
# External code and tests may still import them by name.

memory_handler = _memory
stealth_validate_handler = _stealth_validate
_result_demo_handler = _result_demo


if __name__ == "__main__":
    main()
