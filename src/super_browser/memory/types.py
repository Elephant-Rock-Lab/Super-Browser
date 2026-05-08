"""Memory types — data models for per-domain agent memory."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ActionSequence:
    """A recorded sequence of browser actions for a specific task."""

    task: str
    actions: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True
    created_at: float = field(default_factory=time.time)
    used_count: int = 0


@dataclass
class DomainMemory:
    """Memory store for a single domain."""

    domain: str
    sequences: list[ActionSequence] = field(default_factory=list)
    selectors: dict[str, str] = field(default_factory=dict)
    preferences: dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON persistence."""
        import dataclasses

        return dataclasses.asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainMemory:
        """Deserialize from a plain dict, reconstructing nested types."""
        sequences = []
        for seq_data in data.get("sequences", []):
            sequences.append(ActionSequence(
                task=seq_data.get("task", ""),
                actions=seq_data.get("actions", []),
                success=seq_data.get("success", True),
                created_at=seq_data.get("created_at", time.time()),
                used_count=seq_data.get("used_count", 0),
            ))
        return cls(
            domain=data.get("domain", ""),
            sequences=sequences,
            selectors=data.get("selectors", {}),
            preferences=data.get("preferences", {}),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
        )
