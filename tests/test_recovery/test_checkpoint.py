"""Tests for CheckpointManager stub."""

import asyncio
from pathlib import Path

import pytest

from super_browser.recovery.checkpoint import CheckpointManager


class TestCheckpointManagerStub:
    def test_initialize_raises(self):
        async def _test():
            mgr = CheckpointManager(Path("/tmp/test-workspace"))
            with pytest.raises(NotImplementedError):
                await mgr.initialize()
        asyncio.run(_test())

    def test_create_checkpoint_raises(self):
        async def _test():
            mgr = CheckpointManager(Path("/tmp/test-workspace"))
            with pytest.raises(NotImplementedError):
                await mgr.create_checkpoint("test")
        asyncio.run(_test())

    def test_rollback_raises(self):
        async def _test():
            mgr = CheckpointManager(Path("/tmp/test-workspace"))
            with pytest.raises(NotImplementedError):
                await mgr.rollback("abc")
        asyncio.run(_test())

    def test_list_checkpoints_empty(self):
        mgr = CheckpointManager(Path("/tmp/test-workspace"))
        assert mgr.list_checkpoints() == []
