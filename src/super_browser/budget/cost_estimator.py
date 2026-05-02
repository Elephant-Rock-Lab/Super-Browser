"""CostEstimator — USD cost estimation for LLM calls."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from super_browser.budget.types import ModelPricing


class CostEstimator:
    _DEFAULTS: list[dict] = [
        {
            "model": "claude-haiku-4-20250414",
            "provider": "anthropic",
            "input_cost_per_1m": 0.80,
            "output_cost_per_1m": 4.00,
            "context_window": 200_000,
        },
        {
            "model": "claude-sonnet-4-20250514",
            "provider": "anthropic",
            "input_cost_per_1m": 3.00,
            "output_cost_per_1m": 15.00,
            "context_window": 200_000,
        },
        {
            "model": "claude-opus-4-20250514",
            "provider": "anthropic",
            "input_cost_per_1m": 15.00,
            "output_cost_per_1m": 75.00,
            "context_window": 200_000,
        },
    ]

    def __init__(self, pricing_file: Optional[Path] = None) -> None:
        self._pricing: dict[str, ModelPricing] = {}
        self._load_defaults()
        if pricing_file and pricing_file.exists():
            self._load_custom(pricing_file)

    def estimate(self, model: str, input_tokens: int, output_tokens: int) -> float:
        pricing = self._pricing.get(model)
        if pricing is None:
            return 0.0
        input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_1m
        return input_cost + output_cost

    def get_context_window(self, model: str) -> int:
        pricing = self._pricing.get(model)
        return pricing.context_window if pricing else 0

    def _load_defaults(self) -> None:
        for d in self._DEFAULTS:
            mp = ModelPricing(**d)
            self._pricing[mp.model] = mp

    def _load_custom(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            for d in data:
                mp = ModelPricing(**d)
                self._pricing[mp.model] = mp
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
