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
    ver = sub.add_parser("version", help="Print version")

    # info
    info = sub.add_parser("info", help="Show system info")

    # run
    run = sub.add_parser("run", help="Run a simple automation task")
    run.add_argument("--url", default="https://example.com", help="URL to navigate to")
    run.add_argument("--action", default="observe", choices=["observe", "screenshot", "extract"], help="Action to perform")
    run.add_argument("--output", default="-", help="Output file (- for stdout)")

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


if __name__ == "__main__":
    main()
