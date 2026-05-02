"""TEST-09-03: CheckpointManager save/restore/list/delete tests (H6)."""

import asyncio
import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from super_browser.browser.cdp import CDPResult
from super_browser.recovery.checkpoint import CheckpointManager


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cdp(url="https://example.com/page"):
    """Create a mock CDP bridge with realistic responses."""
    cdp = AsyncMock()

    # evaluate for scroll capture
    cdp.evaluate = AsyncMock(return_value=CDPResult(
        ok=True,
        data={"result": {"value": json.dumps({"x": 0, "y": 250})}},
        error=None, method="Runtime.evaluate", duration_ms=1.0,
    ))

    # send for cookies
    cdp.send = AsyncMock(return_value=CDPResult(
        ok=True,
        data={"cookies": [{"name": "session", "value": "abc123"}]},
        error=None, method="Network.getAllCookies", duration_ms=1.0,
    ))

    return cdp


def _make_page(url="https://example.com/page"):
    page = MagicMock()
    page.url = url
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value="Test")
    return page


def _make_manager(tmp_path, cdp=None, page=None, session_id=None):
    # Use tmp_path-based directory for test isolation
    ckpt_dir = tmp_path / "checkpoints" / (session_id or "test-session")
    return CheckpointManager(
        workspace=tmp_path,
        checkpoint_dir=ckpt_dir,
        session_id=session_id or "test-session",
        cdp=cdp or _make_cdp(),
        page=page or _make_page(),
    )


# ---------------------------------------------------------------------------
# TEST-09-03-01: save() creates checkpoint with URL + forms + cookies
# ---------------------------------------------------------------------------

class TestSave:
    def test_save_creates_checkpoint_file(self, tmp_path):
        """TEST-09-03-01a: save() creates a JSON checkpoint file."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            checkpoint = await mgr.save(label="before-submit")

            # Check checkpoint metadata
            assert checkpoint.checkpoint_id
            assert checkpoint.message == "before-submit"
            assert checkpoint.created_at > 0

            # Check file was created
            file_path = mgr._checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
            assert file_path.exists()

            # Check file contents
            data = json.loads(file_path.read_text())
            assert data["url"] == "https://example.com/page"
            assert "scroll_x" in data
            assert "scroll_y" in data
            assert "form_values" in data
            assert "cookies" in data
        asyncio.run(_test())

    def test_save_captures_cookies(self, tmp_path):
        """TEST-09-03-01b: save() captures cookies from CDP."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            checkpoint = await mgr.save(label="cookie-test")

            file_path = mgr._checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
            data = json.loads(file_path.read_text())
            assert len(data["cookies"]) == 1
            assert data["cookies"][0]["name"] == "session"
        asyncio.run(_test())

    def test_save_captures_scroll_position(self, tmp_path):
        """TEST-09-03-01c: save() captures scroll position."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            checkpoint = await mgr.save(label="scroll-test")

            file_path = mgr._checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
            data = json.loads(file_path.read_text())
            assert data["scroll_y"] == 250
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-09-03-02: restore() returns page to saved state
# ---------------------------------------------------------------------------

class TestRestore:
    def test_restore_navigates_to_saved_url(self, tmp_path):
        """TEST-09-03-02a: restore() navigates to the saved URL."""
        async def _test():
            page = _make_page()
            mgr = _make_manager(tmp_path, page=page)
            await mgr.initialize()
            checkpoint = await mgr.save(label="pre-nav")

            # Reset mock to track restore navigation
            page.goto.reset_mock()

            result = await mgr.restore(checkpoint.checkpoint_id)
            assert result is True
            page.goto.assert_called_once_with("https://example.com/page")
        asyncio.run(_test())

    def test_restore_returns_false_for_missing(self, tmp_path):
        """TEST-09-03-02b: restore() returns False for unknown checkpoint."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            result = await mgr.restore("nonexistent-id")
            assert result is False
        asyncio.run(_test())

    def test_restore_roundtrip(self, tmp_path):
        """TEST-09-03-02c: Full save/restore cycle preserves state."""
        async def _test():
            page = _make_page("https://example.com/form")
            cdp = _make_cdp("https://example.com/form")

            mgr = _make_manager(tmp_path, cdp=cdp, page=page)
            await mgr.initialize()
            checkpoint = await mgr.save(label="roundtrip")

            page.goto.reset_mock()
            ok = await mgr.restore(checkpoint.checkpoint_id)
            assert ok is True
            page.goto.assert_called_once_with("https://example.com/form")
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-09-03-03: list_checkpoints() returns saved checkpoints
# ---------------------------------------------------------------------------

class TestListCheckpoints:
    def test_returns_empty_when_none(self, tmp_path):
        """TEST-09-03-03a: list_checkpoints() returns [] when no checkpoints."""
        mgr = _make_manager(tmp_path)
        assert mgr.list_checkpoints() == []

    def test_returns_saved_checkpoints(self, tmp_path):
        """TEST-09-03-03b: list_checkpoints() returns saved checkpoints."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            await mgr.save(label="first")
            await mgr.save(label="second")

            checkpoints = mgr.list_checkpoints()
            assert len(checkpoints) == 2
            # Newest first
            assert checkpoints[0].message == "second"
            assert checkpoints[1].message == "first"
        asyncio.run(_test())

    def test_respects_limit(self, tmp_path):
        """TEST-09-03-03c: list_checkpoints() respects limit parameter."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            for i in range(5):
                await mgr.save(label=f"cp-{i}")

            checkpoints = mgr.list_checkpoints(limit=3)
            assert len(checkpoints) == 3
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# TEST-09-03-04: delete() removes checkpoint file
# ---------------------------------------------------------------------------

class TestDelete:
    def test_delete_removes_file(self, tmp_path):
        """TEST-09-03-04a: delete() removes the checkpoint file."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            checkpoint = await mgr.save(label="to-delete")

            file_path = mgr._checkpoint_dir / f"{checkpoint.checkpoint_id}.json"
            assert file_path.exists()

            result = mgr.delete(checkpoint.checkpoint_id)
            assert result is True
            assert not file_path.exists()
        asyncio.run(_test())

    def test_delete_returns_false_for_missing(self, tmp_path):
        """TEST-09-03-04b: delete() returns False for nonexistent checkpoint."""
        mgr = _make_manager(tmp_path)
        result = mgr.delete("nonexistent-id")
        assert result is False

    def test_delete_reflected_in_list(self, tmp_path):
        """TEST-09-03-04c: After delete, checkpoint no longer appears in list."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            cp1 = await mgr.save(label="keep")
            cp2 = await mgr.save(label="delete-me")

            mgr.delete(cp2.checkpoint_id)
            checkpoints = mgr.list_checkpoints()
            assert len(checkpoints) == 1
            assert checkpoints[0].checkpoint_id == cp1.checkpoint_id
        asyncio.run(_test())


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

class TestBackwardCompatibility:
    def test_create_checkpoint_alias(self, tmp_path):
        """create_checkpoint() is an alias for save()."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            checkpoint = await mgr.create_checkpoint("legacy-test")
            assert checkpoint.message == "legacy-test"
        asyncio.run(_test())

    def test_rollback_alias(self, tmp_path):
        """rollback() is an alias for restore()."""
        async def _test():
            mgr = _make_manager(tmp_path)
            await mgr.initialize()
            checkpoint = await mgr.save(label="rollback-test")
            result = await mgr.rollback(checkpoint.checkpoint_id)
            assert result is True
        asyncio.run(_test())
