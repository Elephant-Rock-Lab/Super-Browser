"""GAP-07 agent types — enums, plan items, loop results, delegation types."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional


class PlanStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepEvent(StrEnum):
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"
    LOOP_DETECTED = "loop_detected"
    PLAN_UPDATED = "plan_updated"
    ABORT = "abort"
    MAX_STEPS_REACHED = "max_steps_reached"
    DONE = "done"
    LLM_TOKEN = "llm_token"


@dataclass(frozen=True)
class StreamEvent:
    """Structured event yielded by ``SuperBrowser.act_stream()``.

    Frozen dataclass — the ``type`` field cannot be reassigned.
    The ``data`` dict payload should be treated as read-only by callers.
    """

    type: StepEvent
    data: dict[str, Any] = field(default_factory=dict)


class DelegationStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PluginSlotKey(StrEnum):
    MEMORY = "memory"
    CONTEXT_ENGINE = "context_engine"
    SKILL_PROVIDER = "skill_provider"
    VISION_PROVIDER = "vision_provider"
    CUSTOM = "custom"


@dataclass
class PlanItem:
    index: int
    description: str
    status: PlanStatus = PlanStatus.PENDING
    action_taken: Optional[str] = None
    result_summary: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return None


@dataclass
class LoopNudge:
    level: int
    message: str
    repetition_count: int
    repeated_action: str


@dataclass
class StepResult:
    step_number: int
    action_name: str
    action_params: dict[str, Any]
    action_result: Any
    duration_ms: float
    page_changed: bool = False
    error: Optional[str] = None


@dataclass
class LoopResult:
    instruction: str
    steps: list[StepResult] = field(default_factory=list)
    plan: list[PlanItem] = field(default_factory=list)
    completion_reason: str = ""
    total_duration_ms: float = 0.0
    total_steps: int = 0
    loop_detections: int = 0
    replan_count: int = 0


@dataclass
class DebugConfig:
    """Configuration for interactive debug mode on failures."""
    enabled: bool = False
    screenshot_dir: str = "./debug_artifacts"
    capture_dom: bool = True


@dataclass
class ActionTimeoutConfig:
    """Per-action timeout configuration for the agent loop.

    Attributes:
        default_action_timeout: Default timeout (seconds) for any action.
        navigation_timeout: Timeout (seconds) for navigation actions.
        per_action_overrides: Mapping of action name -> timeout override.
    """
    default_action_timeout: float = 30.0
    navigation_timeout: float = 60.0
    per_action_overrides: dict[str, float] = field(default_factory=dict)

    def timeout_for(self, action_name: str) -> float:
        """Return the configured timeout for *action_name*.

        Navigation actions use ``navigation_timeout`` unless explicitly
        overridden in ``per_action_overrides``.
        """
        if action_name in self.per_action_overrides:
            return self.per_action_overrides[action_name]
        if action_name in ("navigate", "goto", "go_to", "navigate_to"):
            return self.navigation_timeout
        return self.default_action_timeout


@dataclass
class RetryBudget:
    """Per-action retry limits."""
    click: int = 3
    type: int = 3
    navigate: int = 2
    scroll: int = 2
    extract: int = 1

    def can_retry(self, action_type: str, attempt: int) -> bool:
        """Return True if *attempt* (1-indexed) is within budget for *action_type*."""
        limit = getattr(self, action_type, None)
        if limit is None:
            return True
        return attempt <= limit


@dataclass
class ChildTask:
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str = ""
    status: DelegationStatus = DelegationStatus.PENDING
    result: Any = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return None


@dataclass
class DelegationResult:
    tasks: list[ChildTask]
    total_duration_ms: float
    completed_count: int
    failed_count: int
    cancelled_count: int

    @property
    def all_succeeded(self) -> bool:
        return self.failed_count == 0 and self.cancelled_count == 0
