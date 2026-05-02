"""ModelCascade — 5-tier model mapping with escalation."""

from __future__ import annotations

from typing import Any, Optional

from super_browser.budget.types import (
    CascadeConfig,
    CascadeResult,
    CascadeTier,
    CostTier,
)

_ACTION_TIER_MAP: dict[str, CostTier] = {
    "click": CostTier.TIER_1,
    "fill": CostTier.TIER_1,
    "navigate": CostTier.TIER_1,
    "observe": CostTier.TIER_1,
    "scroll": CostTier.TIER_1,
    "keypress": CostTier.TIER_1,
    "compositor_click": CostTier.TIER_2,
    "compositor_type": CostTier.TIER_2,
    "extract": CostTier.TIER_2,
    "select_element": CostTier.TIER_2,
    "vision_locate": CostTier.TIER_3_MINI,
    "captcha_solve": CostTier.TIER_3_SONNET,
    "interpret": CostTier.TIER_3_SONNET,
    "judgment_call": CostTier.TIER_3_OPUS,
}

_TIER_ORDER: list[CostTier] = [
    CostTier.TIER_1,
    CostTier.TIER_2,
    CostTier.TIER_3_MINI,
    CostTier.TIER_3_SONNET,
    CostTier.TIER_3_OPUS,
]

DEFAULT_TIERS: tuple[CascadeTier, ...] = (
    CascadeTier(tier=CostTier.TIER_1, model="claude-haiku-4-20250414", provider="anthropic", cost_multiplier=1.0),
    CascadeTier(tier=CostTier.TIER_2, model="claude-sonnet-4-20250514", provider="anthropic", cost_multiplier=1.2),
    CascadeTier(tier=CostTier.TIER_3_MINI, model="claude-haiku-4-20250414", provider="anthropic", cost_multiplier=10.0),
    CascadeTier(tier=CostTier.TIER_3_SONNET, model="claude-sonnet-4-20250514", provider="anthropic", cost_multiplier=50.0),
    CascadeTier(tier=CostTier.TIER_3_OPUS, model="claude-opus-4-20250514", provider="anthropic", cost_multiplier=200.0),
)


class ModelCascade:

    def __init__(
        self,
        config: Optional[CascadeConfig] = None,
        governor: Optional[Any] = None,
        credential_pool: Optional[Any] = None,
    ) -> None:
        if config and config.tiers:
            self._config = config
        else:
            self._config = CascadeConfig(
                tiers=DEFAULT_TIERS,
                default_tier=config.default_tier if config else CostTier.TIER_1,
                max_total_escalations=config.max_total_escalations if config else 3,
            )
        self._governor = governor
        self._credential_pool = credential_pool
        self._tier_map: dict[CostTier, CascadeTier] = {t.tier: t for t in self._config.tiers}
        self._escalation_counts: dict[CostTier, int] = {}

    def select_model(
        self,
        action_type: str,
        *,
        complexity: str = "simple",
    ) -> CascadeResult:
        tier_key = _ACTION_TIER_MAP.get(action_type, self._config.default_tier)
        cascade_tier = self._tier_map.get(tier_key)
        if cascade_tier is None and self._config.tiers:
            cascade_tier = self._config.tiers[0]

        return CascadeResult(
            selected_tier=cascade_tier,
            model=cascade_tier.model,
            provider=cascade_tier.provider,
            estimated_cost_usd=0.0,
        )

    def escalate(
        self,
        current_tier: CostTier,
        reason: str,
    ) -> Optional[CascadeResult]:
        total_escalations = sum(self._escalation_counts.values())
        if total_escalations >= self._config.max_total_escalations:
            return None

        try:
            idx = _TIER_ORDER.index(current_tier)
        except ValueError:
            return None

        if idx + 1 >= len(_TIER_ORDER):
            return None

        next_tier_key = _TIER_ORDER[idx + 1]
        next_cascade = self._tier_map.get(next_tier_key)
        if next_cascade is None:
            return None

        self._escalation_counts[current_tier] = self._escalation_counts.get(current_tier, 0) + 1

        return CascadeResult(
            selected_tier=next_cascade,
            model=next_cascade.model,
            provider=next_cascade.provider,
            escalated_from=current_tier,
            escalation_count=sum(self._escalation_counts.values()),
            estimated_cost_usd=0.0,
        )

    def get_tier(self, tier: CostTier) -> Optional[CascadeTier]:
        return self._tier_map.get(tier)

    def reset_escalations(self) -> None:
        self._escalation_counts.clear()
