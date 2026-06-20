"""Tests for vector implementations.

Verifies: structural integrity, ID format, tier consistency, evaluation
logic with stub backend, and protocol compliance.
"""

from __future__ import annotations

import re

import pytest
from adversarial3.backends import StubBackend
from adversarial3.core import (
    EvaluationContext,
    Severity,
    Tier,
    VectorResult,
    Verdict,
)
from adversarial3.vectors import ALL_VECTORS
from adversarial3.vectors.automation import AUTOMATION_VECTORS
from adversarial3.vectors.behavioral import BEHAVIORAL_VECTORS
from adversarial3.vectors.controlled import CONTROLLED_VECTORS
from adversarial3.vectors.ejector import EJECTOR_VECTORS
from adversarial3.vectors.fingerprint import FINGERPRINT_VECTORS
from adversarial3.vectors.network import NETWORK_VECTORS


class TestVectorRegistry:
    """Test vector registry integrity."""

    def test_all_vectors_have_unique_ids(self):
        ids = [v.vector_id for v in ALL_VECTORS]
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {[x for x in ids if ids.count(x) > 1]}"

    def test_vector_id_format(self):
        for v in ALL_VECTORS:
            assert re.match(r"^T[1-6]-\d{3}$", v.vector_id), f"{v.vector_id}: invalid format"

    def test_tier_consistency(self):
        for v in ALL_VECTORS:
            expected_prefix = {
                Tier.FINGERPRINT: "T1",
                Tier.AUTOMATION: "T2",
                Tier.EJECTOR: "T3",
                Tier.BEHAVIORAL: "T4",
                Tier.NETWORK: "T5",
                Tier.EXTERNAL_VENDOR: "T7",
                Tier.CONTROLLED: "T6",
            }
            prefix = expected_prefix.get(v.tier)
            if prefix:
                assert v.vector_id.startswith(prefix), f"{v.vector_id}: tier {v.tier} mismatch"

    def test_names_non_empty(self):
        for v in ALL_VECTORS:
            assert len(v.name) > 0, f"{v.vector_id}: empty name"

    def test_descriptions_non_empty(self):
        for v in ALL_VECTORS:
            assert len(v.description) > 0, f"{v.vector_id}: empty description"

    def test_severity_valid(self):
        for v in ALL_VECTORS:
            assert isinstance(v.severity, Severity), f"{v.vector_id}: invalid severity type"

    def test_tier_counts(self):
        assert len(FINGERPRINT_VECTORS) >= 1
        assert len(AUTOMATION_VECTORS) >= 1
        assert len(EJECTOR_VECTORS) >= 1
        assert len(BEHAVIORAL_VECTORS) >= 1
        assert len(NETWORK_VECTORS) >= 1
        assert len(CONTROLLED_VECTORS) >= 1


class TestVectorEvaluation:
    """Test vector evaluation with stub backend."""

    @pytest.fixture
    def stub_backend(self):
        return StubBackend()

    @pytest.fixture
    def eval_context(self, stub_backend):
        return EvaluationContext(
            page=None,
            browser=stub_backend,
            server_url="http://localhost:9999",
            headers={},
        )

    @pytest.mark.asyncio
    async def test_fingerprint_vectors_return_results(self, eval_context):
        for vector in FINGERPRINT_VECTORS:
            result = await vector.evaluate(eval_context)
            assert isinstance(result, VectorResult), f"{vector.vector_id}: not a VectorResult"
            assert result.vector_id == vector.vector_id
            assert result.tier == vector.tier

    @pytest.mark.asyncio
    async def test_automation_vectors_return_results(self, eval_context):
        for vector in AUTOMATION_VECTORS:
            result = await vector.evaluate(eval_context)
            assert isinstance(result, VectorResult)
            assert result.vector_id == vector.vector_id

    @pytest.mark.asyncio
    async def test_ejector_vectors_return_results(self, eval_context):
        for vector in EJECTOR_VECTORS:
            result = await vector.evaluate(eval_context)
            assert isinstance(result, VectorResult)
            assert result.vector_id == vector.vector_id

    @pytest.mark.asyncio
    async def test_network_vectors_require_browser(self, eval_context):
        """Network vectors need browser navigation to capture request headers."""
        for vector in NETWORK_VECTORS:
            assert vector.requires_browser is True
            result = await vector.evaluate(eval_context)
            assert isinstance(result, VectorResult)
            # With empty context headers (no captured request), returns INCONCLUSIVE
            assert result.verdict.value == "inconclusive"

    @pytest.mark.asyncio
    async def test_behavioral_vectors_return_skipped(self, eval_context):
        """Behavioral vectors must return SKIPPED until telemetry harness exists."""
        for vector in BEHAVIORAL_VECTORS:
            assert vector.requires_interaction is True
            result = await vector.evaluate(eval_context)
            assert isinstance(result, VectorResult)
            assert result.verdict == Verdict.SKIPPED
            assert "reason" in result.details


class TestSpecificVectors:
    """Test specific vector logic."""

    @pytest.mark.asyncio
    async def test_webdriver_vector_detects_true(self):
        from adversarial3.vectors.automation import NavigatorWebdriver
        vector = NavigatorWebdriver()
        backend = StubBackend()
        page = await backend.new_page()
        # Configure stub to return True for webdriver
        page.set_js_response("navigator.webdriver", True)

        ctx = EvaluationContext(page=page, browser=backend, server_url="", headers={})
        result = await vector.evaluate(ctx)

        assert result.verdict == Verdict.FLAGGED
        assert result.score == 0.0

    @pytest.mark.asyncio
    async def test_webdriver_vector_passes_false(self):
        from adversarial3.vectors.automation import NavigatorWebdriver
        vector = NavigatorWebdriver()
        backend = StubBackend()
        page = await backend.new_page()
        page.set_js_response("navigator.webdriver", False)

        ctx = EvaluationContext(page=page, browser=backend, server_url="", headers={})
        result = await vector.evaluate(ctx)

        assert result.verdict == Verdict.CLEAN
        assert result.score == 1.0

    @pytest.mark.asyncio
    async def test_hardware_concurrency_plausible(self):
        from adversarial3.vectors.fingerprint import HardwareConcurrencyPlausibility
        vector = HardwareConcurrencyPlausibility()
        backend = StubBackend()
        page = await backend.new_page()
        page.set_js_response("navigator.hardwareConcurrency", 8)

        ctx = EvaluationContext(page=page, browser=backend, server_url="", headers={})
        result = await vector.evaluate(ctx)

        assert result.verdict == Verdict.CLEAN

    @pytest.mark.asyncio
    async def test_hardware_concurrency_implausible(self):
        from adversarial3.vectors.fingerprint import HardwareConcurrencyPlausibility
        vector = HardwareConcurrencyPlausibility()
        backend = StubBackend()
        page = await backend.new_page()
        page.set_js_response("navigator.hardwareConcurrency", 0)

        ctx = EvaluationContext(page=page, browser=backend, server_url="", headers={})
        result = await vector.evaluate(ctx)

        assert result.verdict == Verdict.FLAGGED
