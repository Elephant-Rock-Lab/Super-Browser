"""Tests for CostEstimator."""

import json
from pathlib import Path

from super_browser.budget.cost_estimator import CostEstimator


class TestCostEstimator:
    def test_default_pricing_loaded(self):
        est = CostEstimator()
        assert "claude-haiku-4-20250414" in est._pricing
        assert "claude-sonnet-4-20250514" in est._pricing
        assert "claude-opus-4-20250514" in est._pricing

    def test_estimate_known_model(self):
        est = CostEstimator()
        cost = est.estimate("claude-sonnet-4-20250514", input_tokens=1_000_000, output_tokens=100_000)
        expected_input = 1_000_000 / 1_000_000 * 3.0
        expected_output = 100_000 / 1_000_000 * 15.0
        assert abs(cost - (expected_input + expected_output)) < 0.001

    def test_estimate_unknown_model(self):
        est = CostEstimator()
        assert est.estimate("unknown-model", 1000, 500) == 0.0

    def test_estimate_haiku(self):
        est = CostEstimator()
        cost = est.estimate("claude-haiku-4-20250414", 1_000_000, 1_000_000)
        assert abs(cost - (0.80 + 4.00)) < 0.001

    def test_estimate_opus(self):
        est = CostEstimator()
        cost = est.estimate("claude-opus-4-20250514", 1_000_000, 100_000)
        expected = 15.0 + (100_000 / 1_000_000 * 75.0)
        assert abs(cost - expected) < 0.001

    def test_get_context_window_known(self):
        est = CostEstimator()
        assert est.get_context_window("claude-sonnet-4-20250514") == 200_000

    def test_get_context_window_unknown(self):
        est = CostEstimator()
        assert est.get_context_window("unknown") == 0

    def test_custom_pricing_file(self, tmp_path):
        pricing_file = tmp_path / "pricing.json"
        pricing_file.write_text(json.dumps([{
            "model": "custom-model",
            "provider": "test",
            "input_cost_per_1m": 5.0,
            "output_cost_per_1m": 10.0,
            "context_window": 128_000,
        }]))
        est = CostEstimator(pricing_file=pricing_file)
        assert est.estimate("custom-model", 1_000_000, 1_000_000) == 15.0
        assert est.get_context_window("custom-model") == 128_000

    def test_custom_pricing_overrides_default(self, tmp_path):
        pricing_file = tmp_path / "pricing.json"
        pricing_file.write_text(json.dumps([{
            "model": "claude-haiku-4-20250414",
            "provider": "anthropic",
            "input_cost_per_1m": 99.0,
            "output_cost_per_1m": 99.0,
            "context_window": 50_000,
        }]))
        est = CostEstimator(pricing_file=pricing_file)
        assert est.estimate("claude-haiku-4-20250414", 1_000_000, 0) == 99.0

    def test_invalid_pricing_file(self, tmp_path):
        pricing_file = tmp_path / "bad.json"
        pricing_file.write_text("not json")
        est = CostEstimator(pricing_file=pricing_file)
        assert est.estimate("claude-sonnet-4-20250514", 1_000_000, 0) > 0

    def test_missing_pricing_file(self):
        est = CostEstimator(pricing_file=Path("/nonexistent/pricing.json"))
        assert "claude-sonnet-4-20250514" in est._pricing

    def test_zero_tokens(self):
        est = CostEstimator()
        assert est.estimate("claude-sonnet-4-20250514", 0, 0) == 0.0
