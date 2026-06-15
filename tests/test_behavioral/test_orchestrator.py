"""Tests for BehaviorOrchestrator — Track C slice 2 (Wave 23).

Covers action delegation, dwell injection, navigation variation,
seed propagation, and asyncio.sleep mocking.
"""

from __future__ import annotations

import random
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.behavioral.dwell import DwellConfig, DwellTimer
from super_browser.behavioral.navigation import (
    NavigationConfig,
    NavigationStyle,
    NavigationVariator,
)
from super_browser.behavioral.orchestrator import BehaviorOrchestrator
from super_browser.behavioral.session_seed import SessionSeed

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_adapter() -> MagicMock:
    """Mock HumanBehaviorAdapter."""
    adapter = MagicMock()
    adapter.humanize_click = AsyncMock()
    adapter.humanize_type = AsyncMock()
    adapter.humanize_scroll = AsyncMock()
    return adapter


@pytest.fixture
def mock_page() -> MagicMock:
    """Mock browser page."""
    page = MagicMock()
    page.goto = AsyncMock()
    page.set_extra_http_headers = AsyncMock()
    return page


@pytest.fixture
def zero_dwell() -> DwellTimer:
    """DwellTimer that always returns ~0 delays (zero variability)."""
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
def orchestrator(
    mock_adapter: MagicMock,
    zero_dwell: DwellTimer,
) -> BehaviorOrchestrator:
    return BehaviorOrchestrator(
        adapter=mock_adapter,
        dwell=zero_dwell,
        navigator=NavigationVariator(
            config=NavigationConfig(style_weights={"direct": 1.0}),
            rng=random.Random(0),
        ),
        session_seed=SessionSeed("test"),
    )


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestConstruction:
    def test_creates_with_defaults(self, mock_adapter: MagicMock) -> None:
        orch = BehaviorOrchestrator(adapter=mock_adapter)
        assert orch.adapter is mock_adapter
        assert isinstance(orch.dwell, DwellTimer)
        assert isinstance(orch.navigator, NavigationVariator)
        assert isinstance(orch.session_seed, SessionSeed)

    def test_custom_components(self, mock_adapter: MagicMock) -> None:
        dwell = DwellTimer(rng=random.Random(1))
        nav = NavigationVariator(rng=random.Random(2))
        seed = SessionSeed("custom")
        orch = BehaviorOrchestrator(
            adapter=mock_adapter,
            dwell=dwell,
            navigator=nav,
            session_seed=seed,
        )
        assert orch.dwell is dwell
        assert orch.navigator is nav
        assert orch.session_seed is seed


# ---------------------------------------------------------------------------
# Click
# ---------------------------------------------------------------------------


class TestClick:
    @pytest.mark.asyncio
    async def test_click_calls_adapter(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        await orchestrator.click(mock_page, "#btn")
        mock_adapter.humanize_click.assert_called_once_with(mock_page, "#btn")

    @pytest.mark.asyncio
    async def test_click_with_dwell(
        self,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        """Click should call asyncio.sleep for pre and post dwell."""
        sleep_calls: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        cfg = DwellConfig(
            pre_action_min_ms=100.0,
            pre_action_max_ms=100.0,
            post_action_min_ms=200.0,
            post_action_max_ms=200.0,
            variability=0.0,
        )
        orch = BehaviorOrchestrator(
            adapter=mock_adapter,
            dwell=DwellTimer(config=cfg, rng=random.Random(0)),
        )

        with patch("super_browser.behavioral.orchestrator.asyncio.sleep", side_effect=mock_sleep):
            await orch.click(mock_page, "#btn")

        assert len(sleep_calls) == 2
        assert sleep_calls[0] > 0  # pre-action
        assert sleep_calls[1] > 0  # post-action

    @pytest.mark.asyncio
    async def test_click_order(
        self,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
        zero_dwell: DwellTimer,
    ) -> None:
        """Verify call order: sleep → adapter → sleep."""
        call_log: list[str] = []

        async def mock_sleep(delay: float) -> None:
            call_log.append(f"sleep:{delay:.4f}")

        async def mock_click(page: Any, selector: str) -> None:
            call_log.append(f"click:{selector}")

        mock_adapter.humanize_click = mock_click
        orch = BehaviorOrchestrator(
            adapter=mock_adapter,
            dwell=zero_dwell,
        )

        with patch("super_browser.behavioral.orchestrator.asyncio.sleep", side_effect=mock_sleep):
            await orch.click(mock_page, "#submit")

        # Verify order: pre-sleep, click, post-sleep
        assert call_log[0].startswith("sleep:")
        assert call_log[1] == "click:#submit"
        assert call_log[2].startswith("sleep:")


# ---------------------------------------------------------------------------
# Type
# ---------------------------------------------------------------------------


class TestType:
    @pytest.mark.asyncio
    async def test_type_calls_adapter(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        await orchestrator.type(mock_page, "#input", "hello")
        mock_adapter.humanize_type.assert_called_once_with(mock_page, "#input", "hello")

    @pytest.mark.asyncio
    async def test_type_with_dwell(
        self,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        sleep_calls: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        cfg = DwellConfig(
            pre_action_min_ms=50.0,
            pre_action_max_ms=50.0,
            post_action_min_ms=80.0,
            post_action_max_ms=80.0,
            variability=0.0,
        )
        orch = BehaviorOrchestrator(
            adapter=mock_adapter,
            dwell=DwellTimer(config=cfg, rng=random.Random(0)),
        )

        with patch("super_browser.behavioral.orchestrator.asyncio.sleep", side_effect=mock_sleep):
            await orch.type(mock_page, "#email", "user@test.com")

        assert len(sleep_calls) == 2


# ---------------------------------------------------------------------------
# Scroll
# ---------------------------------------------------------------------------


class TestScroll:
    @pytest.mark.asyncio
    async def test_scroll_calls_adapter(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        await orchestrator.scroll(mock_page, "down", 3)
        mock_adapter.humanize_scroll.assert_called_once_with(mock_page, "down", 3)

    @pytest.mark.asyncio
    async def test_scroll_defaults(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        await orchestrator.scroll(mock_page)
        mock_adapter.humanize_scroll.assert_called_once_with(mock_page, "down", 1)


# ---------------------------------------------------------------------------
# Navigate
# ---------------------------------------------------------------------------


class TestNavigate:
    @pytest.mark.asyncio
    async def test_navigate_calls_goto(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_page: MagicMock,
    ) -> None:
        style = await orchestrator.navigate(mock_page, "https://example.com")
        mock_page.goto.assert_called_once_with("https://example.com")
        assert style == NavigationStyle.DIRECT

    @pytest.mark.asyncio
    async def test_navigate_referrer_sets_header(
        self,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
        zero_dwell: DwellTimer,
    ) -> None:
        orch = BehaviorOrchestrator(
            adapter=mock_adapter,
            dwell=zero_dwell,
            navigator=NavigationVariator(
                config=NavigationConfig(
                    style_weights={"referrer": 1.0},
                    referrer_pool=("https://google.com/",),
                ),
                rng=random.Random(0),
            ),
        )
        style = await orch.navigate(mock_page, "https://target.com")
        assert style == NavigationStyle.REFERRER
        mock_page.set_extra_http_headers.assert_called_once_with({"Referer": "https://google.com/"})
        mock_page.goto.assert_called_once_with("https://target.com")

    @pytest.mark.asyncio
    async def test_navigate_type_enter_adds_delay(
        self,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
        zero_dwell: DwellTimer,
    ) -> None:
        sleep_calls: list[float] = []

        async def mock_sleep(delay: float) -> None:
            sleep_calls.append(delay)

        orch = BehaviorOrchestrator(
            adapter=mock_adapter,
            dwell=zero_dwell,
            navigator=NavigationVariator(
                config=NavigationConfig(
                    style_weights={"type_enter": 1.0},
                    type_url_delay_ms=(100.0, 100.0),
                ),
                rng=random.Random(0),
            ),
        )

        with patch("super_browser.behavioral.orchestrator.asyncio.sleep", side_effect=mock_sleep):
            style = await orch.navigate(mock_page, "https://example.com")

        assert style == NavigationStyle.TYPE_AND_ENTER
        # At least 3 sleeps: pre-action dwell, type delay, page settle
        assert len(sleep_calls) >= 3

    @pytest.mark.asyncio
    async def test_navigate_returns_style(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_page: MagicMock,
    ) -> None:
        style = await orchestrator.navigate(mock_page, "https://test.com")
        assert isinstance(style, NavigationStyle)

    @pytest.mark.asyncio
    async def test_navigate_referrer_no_set_headers_method(
        self,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
        zero_dwell: DwellTimer,
    ) -> None:
        """Page without set_extra_http_headers should not crash."""
        # Remove the method
        del mock_page.set_extra_http_headers

        orch = BehaviorOrchestrator(
            adapter=mock_adapter,
            dwell=zero_dwell,
            navigator=NavigationVariator(
                config=NavigationConfig(
                    style_weights={"referrer": 1.0},
                    referrer_pool=("https://google.com/",),
                ),
                rng=random.Random(0),
            ),
        )
        # Should not raise
        style = await orch.navigate(mock_page, "https://target.com")
        assert style == NavigationStyle.REFERRER
        mock_page.goto.assert_called_once()


# ---------------------------------------------------------------------------
# Session seed propagation
# ---------------------------------------------------------------------------


class TestSessionSeed:
    def test_session_seed_stored(
        self,
        mock_adapter: MagicMock,
    ) -> None:
        seed = SessionSeed("repro-001")
        orch = BehaviorOrchestrator(
            adapter=mock_adapter,
            session_seed=seed,
        )
        assert orch.session_seed.is_deterministic
        assert orch.session_seed.base == "repro-001"

    def test_empty_session_seed_nondeterministic(
        self,
        mock_adapter: MagicMock,
    ) -> None:
        orch = BehaviorOrchestrator(adapter=mock_adapter)
        assert not orch.session_seed.is_deterministic
