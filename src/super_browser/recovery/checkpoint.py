"""CheckpointManager — stub implementation (requires git CLI, deferred)."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from super_browser.recovery.types import Checkpoint


class CheckpointManager:
    def __init__(self, workspace: Path, checkpoint_dir: Optional[Path] = None) -> None:
        self._workspace = workspace
        self._checkpoint_dir = checkpoint_dir or workspace / ".super-browser" / "checkpoints"

    async def initialize(self) -> None:
        raise NotImplementedError("CheckpointManager requires git CLI; deferred to post-GAP-04")

    async def create_checkpoint(self, message: str) -> Checkpoint:
        raise NotImplementedError("CheckpointManager requires git CLI; deferred to post-GAP-04")

    async def rollback(self, checkpoint_id: str) -> bool:
        raise NotImplementedError("CheckpointManager requires git CLI; deferred to post-GAP-04")

    def list_checkpoints(self, limit: int = 20) -> list[Checkpoint]:
        return []
