#!/usr/bin/env python3
"""Basic Usage Example — Super Browser.

Demonstrates the core workflow: launch, navigate, click, extract, and close.
Uses MockLLMClient so no API keys are needed.

Run:
    python examples/basic_usage.py
"""

import asyncio
import logging

from super_browser.agent.facade import SuperBrowser

# Configure logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-30s  %(levelname)-7s  %(message)s",
)


# ---------------------------------------------------------------------------
# Mock LLM Client (no API keys needed)
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Minimal mock that satisfies the LLMClient protocol.

    In production, use `create_llm()` to get a real Anthropic or OpenAI client.
    """

    async def propose_action(self, prompt: str, *, tools=None) -> dict:
        """Return 'done' immediately — simulates a successful LLM response."""
        return {"done": True, "summary": "Mock task completed successfully"}

    async def create_plan(self, instruction: str, *, tools) -> list[dict]:
        """Return a trivial plan."""
        return [{"step": "Complete task", "tool": "done"}]

    async def replan(
        self, *, instruction, original_plan, failed_step, error
    ) -> list[dict]:
        """Return the original plan unchanged."""
        return original_plan


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    """Run the basic usage demonstration."""

    # 1. Create SuperBrowser with the mock LLM client.
    #    The context manager handles start/stop automatically.
    #    Config() is the composition root — accepts browser, agent, budget, etc.
    #    You can also pass Config explicitly: SuperBrowser(config=Config(...))
    async with SuperBrowser(llm_client=MockLLMClient()) as sb:
        print("=" * 60)
        print("Super Browser — Basic Usage Example")
        print("=" * 60)

        # ── Navigate ────────────────────────────────────────────────
        print("\n1. Navigating to example.com ...")
        result = await sb.navigate("https://example.com")

        if result.ok:
            print(f"   ✓ Title:  {result.data.title}")
            print(f"   ✓ URL:    {result.data.final_url}")
            print(f"   ✓ Time:   {result.meta.duration_ms:.0f}ms")
        else:
            print(f"   ✗ Navigation failed: {result.error.message}")
            return

        # ── Observe the page ────────────────────────────────────────
        print("\n2. Observing page state ...")
        obs = await sb.observe()

        if obs.ok:
            print(f"   ✓ URL:                  {obs.data['url']}")
            print(f"   ✓ Title:                {obs.data['title']}")
            print(f"   ✓ Interactive elements: {obs.data['interactive_elements']}")
            print(f"   ✓ Total elements:       {obs.data['total_elements']}")
        else:
            print("   ✗ Observation failed")

        # ── Extract data ────────────────────────────────────────────
        print("\n3. Extracting page heading ...")
        extracted = await sb.extract("page heading", selector="h1")

        if extracted.ok and extracted.data.extracted:
            print(f"   ✓ Heading: {extracted.data.extracted.strip()}")
        else:
            print("   ✓ Extracted full accessibility tree (no selector match)")

        # ── Click a link ────────────────────────────────────────────
        print("\n4. Clicking the 'More information' link ...")
        click_result = await sb.click(
            "a", description="Click the first link on the page"
        )
        print(f"   ✓ Click result: ok={click_result.ok}")

        # ── Fill a form field (demonstration) ───────────────────────
        #    example.com doesn't have forms, so this shows the API.
        #    In a real scenario:
        #       await sb.fill("#search", "python automation")
        print("\n5. Fill example (API demonstration) ...")
        print("   fill() API: await sb.fill('#input', 'text', clear_first=True)")
        print("   ✓ API available for form interaction")

        # ── Agent-powered action ────────────────────────────────────
        print("\n6. Using agent to complete a task ...")
        act_result = await sb.act(
            "Find the main heading text on this page",
            max_steps=5,
        )

        if act_result.ok:
            print(f"   ✓ Agent completed in {act_result.data.steps_executed} step(s)")
            print(f"   ✓ Reason: {act_result.data.completion_reason}")
        else:
            print(f"   ✗ Agent failed: {act_result.error.message if act_result.error else 'unknown'}")

        # ── Delegate multiple tasks ─────────────────────────────────
        print("\n7. Delegating multiple tasks in parallel ...")
        delegation = await sb.delegate(
            [
                "Get the page title",
                "Count the paragraphs",
                "Find all links",
            ],
            max_concurrency=3,
        )
        print(f"   ✓ Completed: {delegation.completed_count}")
        print(f"   ✓ Failed:    {delegation.failed_count}")
        print(f"   ✓ Cancelled: {delegation.cancelled_count}")

        print("\n" + "=" * 60)
        print("Done! Browser will close automatically.")
        print("=" * 60)

    # Browser is now closed — the async context manager called sb.stop()


if __name__ == "__main__":
    asyncio.run(main())
