"""GAP-02 data types — Tier enums, cascade records, AX snapshot, vision types."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import IntEnum, StrEnum
from typing import Optional

# ---------------------------------------------------------------------------
# Tier definitions
# ---------------------------------------------------------------------------

class Tier(IntEnum):
    """Interaction tiers in priority order. Lower = cheaper and faster."""
    SELECTOR = 1
    COORDINATE = 2
    VISION = 3


class TierOutcome(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class TierAttempt:
    tier: Tier
    outcome: TierOutcome
    duration_ms: float
    error: Optional[str] = None
    coordinates: Optional[tuple[float, float]] = None


@dataclass(frozen=True)
class CascadeResult:
    action: str
    target: str
    attempts: tuple[TierAttempt, ...]
    succeeded_tier: Optional[Tier] = None
    total_duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# AX snapshot (P1 — agent-browser adoption)
# ---------------------------------------------------------------------------

_INTERACTIVE_ROLES = frozenset({
    "button", "link", "textbox", "combobox", "checkbox",
    "radio", "menuitem", "tab", "slider", "searchbox",
    "spinbutton", "switch", "option", "treeitem",
})


@dataclass
class AXNode:
    ref: str
    role: str
    name: str
    url: Optional[str] = None
    value: Optional[str] = None
    description: Optional[str] = None
    bounds: Optional[tuple[float, float, float, float]] = None  # (x, y, w, h)
    focused: bool = False
    disabled: bool = False

    @property
    def center(self) -> Optional[tuple[float, float]]:
        if self.bounds:
            return (self.bounds[0] + self.bounds[2] / 2,
                    self.bounds[1] + self.bounds[3] / 2)
        return None

    @property
    def is_interactive(self) -> bool:
        return self.role in _INTERACTIVE_ROLES


@dataclass
class AXSnapshot:
    url: str
    title: str
    nodes: dict[str, AXNode] = field(default_factory=dict)
    captured_at: float = field(default_factory=time.monotonic)
    token_count: int = 0

    def resolve(self, ref: str) -> Optional[AXNode]:
        return self.nodes.get(ref.lstrip("@"))

    def find_by_text(self, text: str) -> list[AXNode]:
        text_lower = text.lower()
        return [n for n in self.nodes.values()
                if n.is_interactive and text_lower in n.name.lower()]

    def find_by_role(self, role: str) -> list[AXNode]:
        return [n for n in self.nodes.values() if n.role == role]

    def to_compact_str(self) -> str:
        lines = []
        for ref, node in sorted(self.nodes.items(), key=lambda x: int(x[0][1:])):
            parts = [f"[{node.ref}]", node.role, f'"{node.name}"']
            if node.url:
                parts.append(f"url={node.url}")
            if node.value:
                parts.append(f"value={node.value}")
            if node.disabled:
                parts.append("[disabled]")
            lines.append(" ".join(parts))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Vision types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VisionRequest:
    screenshot: bytes
    element_description: str
    page_url: str
    viewport_size: tuple[int, int]


@dataclass(frozen=True)
class VisionResponse:
    found: bool
    x: Optional[float] = None
    y: Optional[float] = None
    confidence: float = 0.0
    raw_response: Optional[str] = None
    model: Optional[str] = None
    token_cost: float = 0.0
    duration_ms: float = 0.0
