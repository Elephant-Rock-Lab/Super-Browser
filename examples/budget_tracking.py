#!/usr/bin/env python3
"""Budget Tracking Example — Super Browser.

Demonstrates the budget system:
  - Configuring daily, per-action, and per-turn limits
  - Recording token usage
  - Checking budget before operations
  - Responding to budget alerts (warning, critical, exhausted)
  - Using the model cascade for cost optimisation

No API keys required — uses mock data for demonstration.

Run:
    python examples/budget_tracking.py
"""

import asyncio
import logging
from pathlib import Path

from super_browser.agent.facade import SuperBrowser
from super_browser.agent.llm.protocol import LLMClient
from super_browser.budget.governor import TokenBudgetGovernor
from super_browser.budget.types import (
    AlertLevel,
    BudgetAlert,
    BudgetConfig,
    BudgetScope,
    TokenUsageRecord,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)-30s  %(levelname)-7s  %(message)s",
)


# ---------------------------------------------------------------------------
# Mock LLM Client
# ---------------------------------------------------------------------------


class MockLLMClient:
    """Simulates LLM responses with token metadata."""

    async def propose_action(self, prompt: str, *, tools=None) -> dict:
        return {
            "done": True,
            "summary": "Mock action completed",
            "tokens": {"input": 1500, "output": 300},
        }

    async def create_plan(self, instruction: str, *, tools) -> list[dict]:
        return [{"step": "Complete task", "tool": "done"}]

    async def replan(
        self, *, instruction, original_plan, failed_step, error
    ) -> list[dict]:
        return original_plan


# ---------------------------------------------------------------------------
# Budget Alert Handler
# ---------------------------------------------------------------------------


def handle_budget_alert(alert: BudgetAlert) -> None:
    """Custom alert handler — could send Slack, email, etc."""
    emoji = {
        AlertLevel.WARNING: "⚠️",
        AlertLevel.CRITICAL: "🔴",
        AlertLevel.EXHAUSTED: "🚫",
    }
    print(
        f"   {emoji.get(alert.level, '❓')} Budget Alert: "
        f"{alert.level.value.upper()} — "
        f"${alert.current_spend:.4f} / ${alert.cap:.2f} "
        f"({alert.usage_pct:.1f}%) "
        f"[{alert.scope.value}]"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    """Demonstrate budget tracking features."""

    print("=" * 60)
    print("Super Browser — Budget Tracking Example")
    print("=" * 60)

    # ── 1. Configure Budget ─────────────────────────────────────────
    print("\n1. Configuring budget limits ...")

    budget_config = BudgetConfig(
        daily_cap_usd=1.00,          # $1.00 daily cap (low for demo)
        per_action_cap_usd=0.30,     # $0.30 per action
        per_turn_token_limit=50_000, # 50K tokens per turn
        warning_threshold=0.50,      # Alert at 50%
        critical_threshold=0.80,     # Critical at 80%
    )

    print(f"   Daily cap:        ${budget_config.daily_cap_usd:.2f}")
    print(f"   Per-action cap:   ${budget_config.per_action_cap_usd:.2f}")
    print(f"   Per-turn limit:   {budget_config.per_turn_token_limit:,} tokens")
    print(f"   Warning at:       {budget_config.warning_threshold:.0%}")
    print(f"   Critical at:      {budget_config.critical_threshold:.0%}")

    # ── 2. Create Governor with Alert Callback ──────────────────────
    print("\n2. Creating TokenBudgetGovernor ...")

    governor = TokenBudgetGovernor(
        config=budget_config,
        alert_callback=handle_budget_alert,
    )

    print(f"   Daily remaining:  ${governor.daily_remaining:.2f}")

    # ── 3. Simulate LLM Calls ───────────────────────────────────────
    print("\n3. Simulating LLM token usage ...")

    # Model: Claude Sonnet 4 — $0.003/1K input, $0.015/1K output
    simulated_calls = [
        {"model": "claude-sonnet-4-20250514", "input": 5000, "output": 1000, "action": "propose_action"},
        {"model": "claude-sonnet-4-20250514", "input": 8000, "output": 2000, "action": "create_plan"},
        {"model": "claude-sonnet-4-20250514", "input": 6000, "output": 1500, "action": "propose_action"},
        {"model": "claude-sonnet-4-20250514", "input": 12000, "output": 3000, "action": "propose_action"},
        {"model": "claude-sonnet-4-20250514", "input": 10000, "output": 2500, "action": "replan"},
        {"model": "claude-sonnet-4-20250514", "input": 15000, "output": 4000, "action": "propose_action"},
    ]

    for i, call in enumerate(simulated_calls, 1):
        # Estimate cost: (input_tokens * input_price + output_tokens * output_price) / 1000
        input_price = 0.003  # per 1K tokens for Sonnet
        output_price = 0.015  # per 1K tokens for Sonnet
        estimated_cost = (call["input"] * input_price + call["output"] * output_price) / 1000

        # Check if we can afford this call
        if not governor.can_spend(estimated_cost):
            print(f"   ✗ Call {i} BLOCKED — budget would be exceeded!")
            break

        # Record the usage
        record = TokenUsageRecord(
            model=call["model"],
            input_tokens=call["input"],
            output_tokens=call["output"],
            estimated_cost_usd=estimated_cost,
            action_name=call["action"],
        )
        alert = governor.record_usage(record)

        print(
            f"   ✓ Call {i}: {call['action']:20s} "
            f"in={call['input']:>6,} out={call['output']:>5,} "
            f"cost=${estimated_cost:.4f} "
            f"remaining=${governor.daily_remaining:.4f}"
        )

        # If we hit critical, consider model cascade
        if alert and alert.level == AlertLevel.CRITICAL:
            print(f"   ↳ Critical threshold reached — consider switching to a cheaper model")

    # ── 4. Budget Summary ───────────────────────────────────────────
    print("\n4. Budget summary ...")
    print(f"   Total spent:     ${governor.daily_spend:.4f}")
    print(f"   Daily cap:       ${budget_config.daily_cap_usd:.2f}")
    print(f"   Remaining:       ${governor.daily_remaining:.4f}")
    print(f"   Usage records:   {len(governor.records)}")

    # ── 5. Scope-Specific Checks ────────────────────────────────────
    print("\n5. Checking budget scopes ...")

    # Daily scope
    daily_block = governor.check_budget(BudgetScope.DAILY, estimated_cost_usd=0.50)
    print(f"   Daily:    {'BLOCKED' if daily_block else 'OK'} (can spend $0.50?)")

    # Per-action scope
    governor.new_action()  # Reset action spend
    action_block = governor.check_budget(BudgetScope.PER_ACTION, estimated_cost_usd=0.10)
    print(f"   Per-action: {'BLOCKED' if action_block else 'OK'} (can spend $0.10?)")

    # Per-turn scope
    governor.new_turn()  # Reset turn tokens
    turn_block = governor.check_budget(BudgetScope.PER_TURN, estimated_tokens=10000)
    print(f"   Per-turn:  {'BLOCKED' if turn_block else 'OK'} (10K tokens?)")

    # ── 6. Model Cascade Strategy ───────────────────────────────────
    print("\n6. Model cascade for cost optimisation ...")
    print("   When budget is tight, cascade to cheaper models:")
    print("   ┌────────────────────────┬─────────────┬──────────────┐")
    print("   │ Model                  │ In/1K tokens│ Out/1K tokens│")
    print("   ├────────────────────────┼─────────────┼──────────────┤")
    print("   │ claude-haiku-4         │ $0.0008     │ $0.004       │")
    print("   │ claude-sonnet-4        │ $0.003      │ $0.015       │")
    print("   │ claude-opus-4          │ $0.015      │ $0.075       │")
    print("   │ gpt-4o-mini            │ $0.00015    │ $0.0006      │")
    print("   │ gpt-4o                 │ $0.0025     │ $0.01        │")
    print("   └────────────────────────┴─────────────┴──────────────┘")

    # ── 7. Reset Budget ─────────────────────────────────────────────
    print("\n7. Resetting daily budget ...")
    governor.reset_daily()
    print(f"   ✓ Daily spend reset: ${governor.daily_spend:.4f}")
    print(f"   ✓ Daily remaining:   ${governor.daily_remaining:.2f}")

    print("\n" + "=" * 60)
    print("Budget tracking example complete!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
