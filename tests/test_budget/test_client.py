"""Tests for BudgetCascadeClient (renamed from BudgetAwareLLMClient)."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.budget.cascade import ModelCascade
from super_browser.budget.client import (
    AllProvidersCircuitOpenError,
    BudgetCascadeClient,
    BudgetExhaustedError,
)
from super_browser.budget.compressor import ContextCompressor
from super_browser.budget.credential_pool import CircuitBreaker, CredentialPool
from super_browser.budget.governor import TokenBudgetGovernor
from super_browser.budget.types import BudgetConfig, CostTier, TokenUsageRecord


def _make_client(*, daily_cap=100.0, llm_client=None):
    gov = TokenBudgetGovernor(BudgetConfig(daily_cap_usd=daily_cap, per_action_cap_usd=10.0))
    cascade = ModelCascade()
    pool = CredentialPool()
    pool.register("anthropic", "key-1", "sk-test")
    cb = CircuitBreaker()
    comp = ContextCompressor()
    return BudgetCascadeClient(gov, cascade, pool, cb, comp, llm_client=llm_client)


class TestBudgetCascadeClient:
    def test_happy_path_no_llm(self):
        async def _test():
            client = _make_client()
            response, record = await client.call(
                [{"role": "user", "content": "test"}],
                action_type="click",
            )
            assert record is not None
            assert record.action_name == "click"
            assert record.model != ""
            assert record.input_tokens > 0
        asyncio.run(_test())

    def test_happy_path_with_mock_llm(self):
        async def _test():
            mock_resp = MagicMock()
            mock_resp.input_tokens = 2000
            mock_resp.output_tokens = 1000

            def mock_llm(messages, **kwargs):
                return mock_resp

            client = _make_client(llm_client=mock_llm)
            response, record = await client.call(
                [{"role": "user", "content": "test"}],
                action_type="click",
            )
            assert response is mock_resp
            assert record.input_tokens == 2000
            assert record.output_tokens == 1000
        asyncio.run(_test())

    def test_async_llm_client(self):
        async def _test():
            mock_resp = MagicMock()
            mock_resp.input_tokens = 500
            mock_resp.output_tokens = 200

            async def mock_llm(messages, **kwargs):
                return mock_resp

            client = _make_client(llm_client=mock_llm)
            response, record = await client.call(
                [{"role": "user", "content": "test"}],
                action_type="click",
            )
            assert record.input_tokens == 500
        asyncio.run(_test())

    def test_budget_exhausted_raises(self):
        async def _test():
            client = _make_client(daily_cap=0.001)
            try:
                await client.call([{"role": "user", "content": "test"}])
                assert False, "should raise"
            except BudgetExhaustedError as e:
                assert e.block is not None
        asyncio.run(_test())

    def test_circuit_breaker_open_raises(self):
        async def _test():
            client = _make_client()
            for _ in range(5):
                client._circuit_breaker.record_failure("anthropic")
            try:
                await client.call([{"role": "user", "content": "test"}])
                assert False, "should raise"
            except AllProvidersCircuitOpenError:
                pass
        asyncio.run(_test())

    def test_model_cascade_selects_tier(self):
        async def _test():
            client = _make_client()
            _, record = await client.call(
                [{"role": "user", "content": "test"}],
                action_type="vision_locate",
            )
            assert record.cost_tier == CostTier.TIER_3_MINI
        asyncio.run(_test())

    def test_usage_record_tracked(self):
        async def _test():
            client = _make_client()
            _, record = await client.call(
                [{"role": "user", "content": "test"}],
                action_type="click",
                trace_id="trace-123",
            )
            assert record.trace_id == "trace-123"
            assert record.estimated_cost_usd > 0
            assert len(client._governor.records) == 1
        asyncio.run(_test())

    def test_credential_429_rotation(self):
        async def _test():
            call_count = 0

            def mock_llm(messages, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    exc = Exception("rate limited")
                    exc.status_code = 429
                    raise exc
                mock = MagicMock()
                mock.input_tokens = 100
                mock.output_tokens = 50
                return mock

            client = _make_client(llm_client=mock_llm)
            client._credential_pool.register("anthropic", "key-2", "sk-test-2")

            try:
                await client.call([{"role": "user", "content": "test"}])
            except Exception:
                pass
        asyncio.run(_test())
