#!/usr/bin/env python3
"""Multi-Tab Workflow Example — Super Browser.

Demonstrates tab management: opening, switching, listing, and closing
tabs, plus parallel subagent delegation.

Run:
    python examples/multi_tab_workflow.py
"""

import asyncio
import logging

from super_browser import SuperBrowser

logging.basicConfig(level=logging.INFO, format="%(name)s  %(levelname)s  %(message)s")
logger = logging.getLogger(__name__)


async def demo_tab_management() -> None:
    """Show tab lifecycle: open, list, switch, close."""
    print("=" * 60)
    print("Super Browser — Multi-Tab Workflow")
    print("=" * 60)

    async with SuperBrowser() as sb:
        # ── Start on the first tab ───────────────────────────────
        await sb.navigate("https://example.com")
        print("\n1. Initial page loaded")

        # ── List current tabs ────────────────────────────────────
        tabs = await sb.list_tabs()
        if tabs.ok:
            print(f"   Tabs open: {len(tabs.data)}")
            for tab in tabs.data:
                print(f"     [{tab.get('id', '?')}] {tab.get('url', '?')}")

        # ── Open a second tab ────────────────────────────────────
        result = await sb.open_tab("https://httpbin.org/headers")
        if result.ok:
            print("\n2. Opened new tab")

        # ── Open a third tab ────────────────────────────────────
        result = await sb.open_tab("https://httpbin.org/ip")
        if result.ok:
            print("3. Opened another tab")

        # ── List all tabs ────────────────────────────────────────
        tabs = await sb.list_tabs()
        if tabs.ok:
            print(f"\n   Total tabs: {len(tabs.data)}")

        # ── Switch back to first tab ─────────────────────────────
        switch = await sb.switch_tab(0)
        if switch.ok:
            print("\n4. Switched to tab 0 (example.com)")

        # ── Close tab 1 ──────────────────────────────────────────
        close = await sb.close_tab(1)
        if close.ok:
            print("5. Closed tab 1")

        # ── Final tab count ──────────────────────────────────────
        tabs = await sb.list_tabs()
        if tabs.ok:
            print(f"\n   Remaining tabs: {len(tabs.data)}")

    print(f"\n{'='*60}")
    print("Tab management complete.")
    print(f"{'='*60}")


async def demo_delegation() -> None:
    """Show parallel task delegation across tabs."""
    print("\n\nParallel Delegation")
    print("-" * 40)
    print("delegate(tasks) runs multiple instructions concurrently.")
    print("Each task gets its own browser tab.")
    print()
    print("Example usage:")
    print()
    print("  tasks = [")
    print('    "Go to example.com and extract the page title",')
    print('    "Go to httpbin.org/ip and extract the IP address",')
    print("  ]")
    print()
    print("  result = await sb.delegate(tasks, max_concurrency=2)")
    print("  for task_result in result.task_results:")
    print("      print(task_result)")
    print()
    print("(Skipped execution — requires LLM client configuration)")
    print("-" * 40)


async def main() -> None:
    """Run all multi-tab demonstrations."""
    await demo_tab_management()
    await demo_delegation()


if __name__ == "__main__":
    asyncio.run(main())
