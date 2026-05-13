"""Super Browser CLI — command-line interface for browser automation."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys


def main() -> None:
    """Entry point for the ``super-browser`` CLI."""
    parser = argparse.ArgumentParser(
        prog="super-browser",
        description="Super Browser — AI browser automation CLI",
    )
    sub = parser.add_subparsers(dest="command")

    # version
    ver = sub.add_parser("version", help="Print version")  # noqa: F841

    # info
    info = sub.add_parser("info", help="Show system info")  # noqa: F841

    # run
    run = sub.add_parser("run", help="Run a simple automation task")
    run.add_argument("--url", default="https://example.com", help="URL to navigate to")
    run.add_argument("--action", default="observe", choices=["observe", "screenshot", "extract"], help="Action to perform")
    run.add_argument("--output", default="-", help="Output file (- for stdout)")

    # interactive
    interactive = sub.add_parser("interactive", help="Start interactive REPL with persistent browser")  # noqa: F841

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
    stealth_check = sub.add_parser("stealth-check", help="Run stealth fingerprint check (offline mode)")
    stealth_check.add_argument("--online", action="store_true", default=False, help="Run in online mode (requires browser)")
    stealth_check.add_argument("--format", default="markdown", choices=["markdown", "html"], help="Report format (default: markdown)")
    stealth_check.add_argument("--threshold", type=int, default=70, help="Pass threshold (default: 70)")

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

    args = parser.parse_args()

    if args.command == "version" or args.command is None:
        from super_browser import __version__
        print(f"super-browser {__version__}")
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
        return

    if args.command == "memory":
        _memory(args)
        return

    parser.print_help()


def _print_info() -> None:
    """Print system and dependency info."""
    from super_browser import __version__

    print(f"super-browser: {__version__}")
    print(f"python: {sys.version}")

    # Check optional deps
    deps = {
        "patchright": "browser",
        "anthropic": "anthropic",
        "openai": "openai",
        "cryptography": "security",
        "mcp": "mcp",
        "httpx": "cloud",
        "Pillow": "vision",
    }
    for mod, extra in deps.items():
        try:
            __import__(mod)
            print(f"  {mod}: installed [{extra}]")
        except ImportError:
            print(f"  {mod}: not installed (pip install super-browser[{extra}])")


async def _run(args: argparse.Namespace) -> None:
    """Run a simple automation task."""
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
            if hasattr(result.data, 'to_dict'):
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


def _memory(args: argparse.Namespace) -> None:
    """Handle memory CLI commands: list, show, clear, prune."""
    from pathlib import Path

    from super_browser.memory.store import MemoryStore

    memory_dir = args.dir or "~/.config/super-browser/memory"
    store = MemoryStore(Path(memory_dir).expanduser())

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
        store_with_ttl = MemoryStore(Path(memory_dir).expanduser(), ttl_days=args.ttl)
        removed = store_with_ttl.prune()
        print(f"Pruned {removed} expired entries.")
        return

    # No subcommand given
    print("Usage: super-browser memory {list|show|clear|prune}")


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


if __name__ == "__main__":
    main()
