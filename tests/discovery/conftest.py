"""Shared fixtures for discovery integration tests.

Reads environment variables to configure the LLM client and browser:
  SB_LLM_PROVIDER  — "openai" or "anthropic" (default: "openai")
  SB_LLM_MODEL     — model identifier (default: "gpt-4o")
  SB_LLM_API_KEY   — API key (falls back to OPENAI_API_KEY / ANTHROPIC_API_KEY)
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from super_browser.agent.config import SuperBrowserConfig
from super_browser.agent.facade import SuperBrowser
from super_browser.agent.llm.factory import create_llm

# ---------------------------------------------------------------------------
# Marker registration
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "live: requires live LLM API + Patchright browser (deselect with '-m \"not live\"')"
    )


# ---------------------------------------------------------------------------
# Fixture: LLM client
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def llm_client():
    """Create a real LLM client from environment variables."""
    provider = os.environ.get("SB_LLM_PROVIDER", "openai")
    model = os.environ.get("SB_LLM_MODEL", "gpt-4o")

    api_key = os.environ.get("SB_LLM_API_KEY")
    if not api_key:
        # Fall back to provider-specific env vars
        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
        elif provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        pytest.skip("No LLM API key available (set SB_LLM_API_KEY)")

    return create_llm(provider, model, api_key)


# ---------------------------------------------------------------------------
# Fixture: SuperBrowser instance (one per test, fresh browser context)
# ---------------------------------------------------------------------------

@pytest.fixture
async def sb(llm_client):
    """Provide a running SuperBrowser instance with a real LLM client."""
    config = SuperBrowserConfig(
        enable_recovery=False,
        enable_budget=False,
        enable_security=False,
        enable_vision=False,
        enable_stealth=False,
        enable_skills=False,
        trace_enabled=False,
    )
    browser = SuperBrowser(config=config, llm_client=llm_client)
    await browser.start()
    yield browser
    await browser.stop()


# ---------------------------------------------------------------------------
# Fixture: bare browser (no LLM) for Tier-1 navigation-only tasks
# ---------------------------------------------------------------------------

@pytest.fixture
async def sb_browser():
    """Provide a running SuperBrowser WITHOUT an LLM client (Tier-1 only)."""
    config = SuperBrowserConfig(
        enable_recovery=False,
        enable_budget=False,
        enable_security=False,
        enable_vision=False,
        enable_stealth=False,
        enable_skills=False,
        trace_enabled=False,
    )
    browser = SuperBrowser(config=config)
    await browser.start()
    yield browser
    await browser.stop()


# ---------------------------------------------------------------------------
# Helper: build a structured result dict
# ---------------------------------------------------------------------------

def make_result(
    *,
    success: bool,
    expected: str,
    actual: str,
    error: str | None = None,
    tier_used: str = "selector",
    cost: float = 0.0,
    latency_ms: float = 0.0,
) -> dict[str, Any]:
    """Build a standardised result dict for the Discovery Report."""
    return {
        "_success": success,
        "expected": expected,
        "actual": actual,
        "error": error,
        "tier_used": tier_used,
        "cost": cost,
        "latency_ms": round(latency_ms, 1),
    }
