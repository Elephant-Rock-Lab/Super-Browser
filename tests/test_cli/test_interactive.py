"""Tests for BATCH-24/TASK-01 — Interactive Mode.

TEST-24-01-01: "open https://example.com" navigates
TEST-24-01-02: "click #btn" calls sb.click
TEST-24-01-03: "close" shuts down browser
TEST-24-01-04: Unknown command shows help
TEST-24-01-05: Browser persists between commands
"""

from __future__ import annotations

import io
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser import SuperBrowser
from super_browser.cli.commands import (
    COMMANDS,
    dispatch,
)
from super_browser.results import ActionResult, NavigateResult
from super_browser.testing import MockLLMClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _ok(**kwargs: object) -> ActionResult:
    """Helper to create a simple ok ActionResult."""
    return ActionResult(ok=True, **kwargs)


def _make_mock_sb() -> SuperBrowser:
    """Create a SuperBrowser with mocked internals for testing."""
    sb = SuperBrowser(llm_client=MockLLMClient())
    sb._running = True
    sb._page = MagicMock()
    sb._page.url = "https://example.com"
    sb._page.title = AsyncMock(return_value="Test Page")
    sb._page.evaluate = AsyncMock(return_value=None)
    sb._page.screenshot = AsyncMock(return_value=b"\x89PNG")
    sb._controller = MagicMock()
    sb._controller.click = AsyncMock(return_value=_ok())
    sb._controller.fill = AsyncMock(return_value=_ok())
    return sb


# ---------------------------------------------------------------------------
# TEST-24-01-01: "open https://example.com" navigates
# ---------------------------------------------------------------------------


class TestOpenCommand:
    """TEST-24-01-01: open command navigates to the given URL."""

    @pytest.mark.asyncio
    async def test_open_navigates_to_url(self) -> None:
        sb = _make_mock_sb()
        sb.navigate = AsyncMock(
            return_value=_ok(
                data=NavigateResult(
                    url="https://example.com",
                    final_url="https://example.com",
                    title="Example Domain",
                ),
            )
        )

        result = await dispatch(sb, "open https://example.com")

        assert result.ok is True
        sb.navigate.assert_awaited_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_open_without_url_shows_usage(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "open")
        assert result.ok is False
        assert "Usage" in result.output


# ---------------------------------------------------------------------------
# TEST-24-01-02: "click #btn" calls sb.click
# ---------------------------------------------------------------------------


class TestClickCommand:
    """TEST-24-01-02: click command calls sb.click with selector."""

    @pytest.mark.asyncio
    async def test_click_dispatches_to_sb_click(self) -> None:
        sb = _make_mock_sb()
        sb.click = AsyncMock(return_value=_ok())

        result = await dispatch(sb, "click #btn")

        assert result.ok is True
        sb.click.assert_awaited_once_with("#btn")

    @pytest.mark.asyncio
    async def test_click_without_selector_shows_usage(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "click")
        assert result.ok is False
        assert "Usage" in result.output


# ---------------------------------------------------------------------------
# TEST-24-01-03: "close" shuts down browser
# ---------------------------------------------------------------------------


class TestCloseCommand:
    """TEST-24-01-03: close command stops the browser."""

    @pytest.mark.asyncio
    async def test_close_stops_browser(self) -> None:
        sb = _make_mock_sb()
        sb.stop = AsyncMock()

        result = await dispatch(sb, "close")

        assert result.ok is True
        assert result.should_exit is True
        sb.stop.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_close_sets_not_running(self) -> None:
        sb = _make_mock_sb()

        async def fake_stop() -> None:
            sb._running = False

        sb.stop = fake_stop

        await dispatch(sb, "close")
        assert sb._running is False


# ---------------------------------------------------------------------------
# TEST-24-01-04: Unknown command shows help
# ---------------------------------------------------------------------------


class TestUnknownCommand:
    """TEST-24-01-04: unknown commands show help text, not crash."""

    @pytest.mark.asyncio
    async def test_unknown_command_shows_help(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "foobar")

        assert result.ok is False
        assert "Unknown command" in result.output
        assert "Available commands" in result.output

    @pytest.mark.asyncio
    async def test_help_command(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "help")
        assert result.ok is True
        assert "Available commands" in result.output

    @pytest.mark.asyncio
    async def test_empty_line_is_noop(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "")
        assert result.ok is True
        assert result.output == ""

    @pytest.mark.asyncio
    async def test_comment_line_is_noop(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "# this is a comment")
        assert result.ok is True
        assert result.output == ""


# ---------------------------------------------------------------------------
# TEST-24-01-05: Browser persists between commands
# ---------------------------------------------------------------------------


class TestBrowserPersistence:
    """TEST-24-01-05: Same browser instance used across multiple commands."""

    @pytest.mark.asyncio
    async def test_same_sb_across_two_commands(self) -> None:
        sb = _make_mock_sb()
        sb.navigate = AsyncMock(
            return_value=_ok(
                data=NavigateResult(
                    url="https://example.com",
                    final_url="https://example.com",
                    title="Example",
                ),
            )
        )
        sb.observe = AsyncMock(
            return_value=_ok(
                data={"url": "https://example.com", "title": "Example"},
            )
        )

        # Execute two commands on the same sb instance
        r1 = await dispatch(sb, "open https://example.com")
        r2 = await dispatch(sb, "observe")

        assert r1.ok is True
        assert r2.ok is True
        # Both commands used the same SuperBrowser instance
        sb.navigate.assert_awaited_once()
        sb.observe.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_all_nine_commands_registered(self) -> None:
        """Verify all 9 interactive commands are in the registry."""
        expected = {"open", "click", "fill", "extract", "scroll", "screenshot", "observe", "tabs", "close"}
        assert expected == set(COMMANDS.keys())


# ---------------------------------------------------------------------------
# Interactive REPL integration test
# ---------------------------------------------------------------------------


class TestInteractiveREPL:
    """Test the full REPL loop with simulated input."""

    @pytest.mark.asyncio
    async def test_repl_executes_commands_and_exits(self) -> None:
        from super_browser.cli.interactive import run_interactive

        input_lines = io.StringIO("observe\nquit\n")
        output_buf = io.StringIO()

        with patch("super_browser.cli.interactive.SuperBrowser") as MockSB:
            mock_sb = AsyncMock(spec=SuperBrowser)
            mock_sb.is_running = True
            mock_sb.observe = AsyncMock(
                return_value=_ok(
                    data={"url": "https://example.com", "title": "Test"},
                )
            )
            mock_sb.stop = AsyncMock()
            MockSB.return_value = mock_sb

            await run_interactive(
                prompt="sb> ",
                output=output_buf,
                input_stream=input_lines,
            )

        output = output_buf.getvalue()
        assert "Interactive REPL" in output


# ---------------------------------------------------------------------------
# Fill command additional coverage
# ---------------------------------------------------------------------------


class TestFillCommand:
    @pytest.mark.asyncio
    async def test_fill_dispatches(self) -> None:
        sb = _make_mock_sb()
        sb.fill = AsyncMock(return_value=_ok())
        result = await dispatch(sb, "fill #email test@example.com")
        assert result.ok is True
        sb.fill.assert_awaited_once_with("#email", "test@example.com")

    @pytest.mark.asyncio
    async def test_fill_without_args_shows_usage(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "fill")
        assert result.ok is False
        assert "Usage" in result.output


# ---------------------------------------------------------------------------
# Scroll command additional coverage
# ---------------------------------------------------------------------------


class TestScrollCommand:
    @pytest.mark.asyncio
    async def test_scroll_down(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "scroll down")
        assert result.ok is True
        assert "Scrolled down" in result.output
        sb._page.evaluate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_scroll_invalid_direction(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "scroll diagonal")
        assert result.ok is False

    @pytest.mark.asyncio
    async def test_scroll_without_direction(self) -> None:
        sb = _make_mock_sb()
        result = await dispatch(sb, "scroll")
        assert result.ok is False
        assert "Usage" in result.output
