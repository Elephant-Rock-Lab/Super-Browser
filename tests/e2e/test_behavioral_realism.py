"""E2E tests: behavioral realism integration.

Tests DwellTimer and BehaviorOrchestrator against a real browser.
All tests require SB_E2E=1.
"""

from __future__ import annotations

import random
from unittest.mock import patch

import pytest

from super_browser.behavioral.dwell import DwellConfig, DwellTimer
from super_browser.behavioral.navigation import (
    NavigationConfig,
    NavigationVariator,
)
from super_browser.behavioral.orchestrator import BehaviorOrchestrator
from super_browser.behavioral.session_seed import SessionSeed
from super_browser.stealth.human import HumanBehaviorAdapter
from super_browser.stealth.human_config import HumanConfig


@pytest.fixture
def zero_dwell() -> DwellTimer:
    """DwellTimer with zero delays (no real sleeping in tests)."""
    cfg = DwellConfig(
        pre_action_min_ms=0.0,
        pre_action_max_ms=0.0,
        post_action_min_ms=0.0,
        post_action_max_ms=0.0,
        page_settle_ms=0.0,
        variability=0.0,
    )
    return DwellTimer(config=cfg, rng=random.Random(0))


@pytest.fixture
def human_adapter() -> HumanBehaviorAdapter:
    return HumanBehaviorAdapter(config=HumanConfig(), backend="patchright")


@pytest.mark.asyncio
class TestBehavioralRealismE2E:
    """Behavioral realism integration with real browser."""

    async def test_orchestrator_navigate_local(
        self,
        human_adapter: HumanBehaviorAdapter,
        zero_dwell: DwellTimer,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """BehaviorOrchestrator.navigate() against local fixture."""
        url = e2e_context.fixture_url("behavioral.html")  # type: ignore[attr-defined]

        orch = BehaviorOrchestrator(
            adapter=human_adapter,
            dwell=zero_dwell,
            navigator=NavigationVariator(
                config=NavigationConfig(style_weights={"direct": 1.0}),
                rng=random.Random(0),
            ),
            session_seed=SessionSeed("e2e-test"),
        )

        with patch("super_browser.behavioral.orchestrator.asyncio.sleep"):
            await orch.navigate(browser_page, url)  # type: ignore[arg-type]

        # Verify navigation succeeded
        title = await browser_page.title()  # type: ignore[attr-defined]
        assert title == "Behavioral Page"

    async def test_orchestrator_click_with_seed(
        self,
        human_adapter: HumanBehaviorAdapter,
        zero_dwell: DwellTimer,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """BehaviorOrchestrator.click() with session seed on real page."""
        url = e2e_context.fixture_url("behavioral.html")  # type: ignore[attr-defined]

        orch = BehaviorOrchestrator(
            adapter=human_adapter,
            dwell=zero_dwell,
            session_seed=SessionSeed("e2e-click"),
        )

        await browser_page.goto(url)  # type: ignore[attr-defined]

        with patch("super_browser.behavioral.orchestrator.asyncio.sleep"):
            await orch.click(browser_page, "#action-btn")  # type: ignore[arg-type]

        # Verify click had effect
        display = await browser_page.query_selector("#result-display")  # type: ignore[attr-defined]
        assert display is not None
        value = await display.get_attribute("data-value")  # type: ignore[attr-defined]
        assert value == "clicked"

    async def test_orchestrator_type_with_seed(
        self,
        human_adapter: HumanBehaviorAdapter,
        zero_dwell: DwellTimer,
        browser_page: object,
        e2e_context: object,
    ) -> None:
        """BehaviorOrchestrator.type() with session seed on real page."""
        url = e2e_context.fixture_url("behavioral.html")  # type: ignore[attr-defined]

        orch = BehaviorOrchestrator(
            adapter=human_adapter,
            dwell=zero_dwell,
            session_seed=SessionSeed("e2e-type"),
        )

        await browser_page.goto(url)  # type: ignore[attr-defined]

        with patch("super_browser.behavioral.orchestrator.asyncio.sleep"):
            await orch.type(browser_page, "#search-field", "test query")  # type: ignore[arg-type]

        # Verify text was typed
        inp = await browser_page.query_selector("#search-field")  # type: ignore[attr-defined]
        assert inp is not None
        value = await inp.input_value()  # type: ignore[attr-defined]
        assert "test query" in value
