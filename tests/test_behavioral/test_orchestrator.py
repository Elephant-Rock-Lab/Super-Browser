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
    async def test_click_calls_adapter_with_seed(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        """Orchestrator must derive and pass session seed to adapter."""
        await orchestrator.click(mock_page, "#btn")
        expected_seed = orchestrator.session_seed.derive("click", "#btn")
        mock_adapter.humanize_click.assert_called_once_with(
            mock_page, "#btn", seed=expected_seed,
        )

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

        async def mock_click(page: Any, selector: str, **kwargs: Any) -> None:
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
    async def test_type_calls_adapter_with_seed(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        """Orchestrator must derive and pass session seed to adapter."""
        await orchestrator.type(mock_page, "#input", "hello")
        expected_seed = orchestrator.session_seed.derive("type", "#input")
        mock_adapter.humanize_type.assert_called_once_with(
            mock_page, "#input", "hello", seed=expected_seed,
        )

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
    async def test_scroll_calls_adapter_with_seed(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        """Orchestrator must derive and pass session seed to adapter."""
        await orchestrator.scroll(mock_page, "down", 3)
        expected_seed = orchestrator.session_seed.derive("scroll", "down:3")
        mock_adapter.humanize_scroll.assert_called_once_with(
            mock_page, "down", 3, seed=expected_seed,
        )

    @pytest.mark.asyncio
    async def test_scroll_defaults_with_seed(
        self,
        orchestrator: BehaviorOrchestrator,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
    ) -> None:
        await orchestrator.scroll(mock_page)
        expected_seed = orchestrator.session_seed.derive("scroll", "down:1")
        mock_adapter.humanize_scroll.assert_called_once_with(
            mock_page, "down", 1, seed=expected_seed,
        )


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

    @pytest.mark.asyncio
    async def test_deterministic_seed_reproducibility(
        self,
        mock_adapter: MagicMock,
        mock_page: MagicMock,
        zero_dwell: DwellTimer,
    ) -> None:
        """Two orchestrators with same SessionSeed must pass identical seeds.

        Verifies that the same session seed + same action sequence produces
        byte-identical seed arguments to the adapter.
        """
        nav = NavigationVariator(
            config=NavigationConfig(style_weights={"direct": 1.0}),
            rng=random.Random(0),
        )
        orch1 = BehaviorOrchestrator(
            adapter=mock_adapter,
            dwell=zero_dwell,
            navigator=nav,
            session_seed=SessionSeed("repro-001"),
        )
        # Fresh mock for second orchestrator
        adapter2 = MagicMock()
        adapter2.humanize_click = AsyncMock()
        adapter2.humanize_type = AsyncMock()
        adapter2.humanize_scroll = AsyncMock()
        orch2 = BehaviorOrchestrator(
            adapter=adapter2,
            dwell=zero_dwell,
            navigator=NavigationVariator(
                config=NavigationConfig(style_weights={"direct": 1.0}),
                rng=random.Random(0),
            ),
            session_seed=SessionSeed("repro-001"),
        )

        # Run identical action sequences
        await orch1.click(mock_page, "#btn")
        await orch1.type(mock_page, "#email", "user@test.com")
        await orch1.scroll(mock_page, "down", 2)

        await orch2.click(mock_page, "#btn")
        await orch2.type(mock_page, "#email", "user@test.com")
        await orch2.scroll(mock_page, "down", 2)

        # Verify seeds match
        call1_click = mock_adapter.humanize_click.call_args
        call2_click = adapter2.humanize_click.call_args
        assert call1_click.kwargs["seed"] == call2_click.kwargs["seed"]

        call1_type = mock_adapter.humanize_type.call_args
        call2_type = adapter2.humanize_type.call_args
        assert call1_type.kwargs["seed"] == call2_type.kwargs["seed"]

        call1_scroll = mock_adapter.humanize_scroll.call_args
        call2_scroll = adapter2.humanize_scroll.call_args
        assert call1_scroll.kwargs["seed"] == call2_scroll.kwargs["seed"]

    @pytest.mark.asyncio
    async def test_nondeterministic_passes_empty_seed(
        self,
        mock_page: MagicMock,
        zero_dwell: DwellTimer,
    ) -> None:
        """Non-deterministic orchestrator passes empty seed to adapter.

        Empty seed ("") is falsy, so adapter falls back to internal
        time-based seed. This preserves non-deterministic production behavior.
        """
        adapter = MagicMock()
        adapter.humanize_click = AsyncMock()
        orch = BehaviorOrchestrator(
            adapter=adapter,
            dwell=zero_dwell,
            session_seed=SessionSeed(""),  # non-deterministic
        )
        await orch.click(mock_page, "#btn")

        # Empty seed should be passed (adapter falls back internally)
        seed_arg = adapter.humanize_click.call_args.kwargs["seed"]
        assert seed_arg == ""

    @pytest.mark.asyncio
    async def test_different_actions_produce_different_seeds(
        self,
        mock_page: MagicMock,
        zero_dwell: DwellTimer,
    ) -> None:
        """Same orchestrator, different actions → different seeds."""
        adapter = MagicMock()
        adapter.humanize_click = AsyncMock()
        orch = BehaviorOrchestrator(
            adapter=adapter,
            dwell=zero_dwell,
            session_seed=SessionSeed("test-session"),
        )
        await orch.click(mock_page, "#btn1")
        await orch.click(mock_page, "#btn2")

        seeds = [call.kwargs["seed"] for call in adapter.humanize_click.call_args_list]
        assert len(seeds) == 2
        assert seeds[0] != seeds[1]
        assert seeds[0] == "test-session:click:#btn1"
        assert seeds[1] == "test-session:click:#btn2"
