"""GAP-04 recovery types — enums, error taxonomy, recovery hints, watchdog events."""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ErrorType(StrEnum):
    AUTH = "auth"
    BILLING = "billing"
    RATE_LIMIT = "rate_limit"
    OVERLOADED = "overloaded"
    CONTEXT_OVERFLOW = "context_overflow"
    TIMEOUT = "timeout"
    SELECTOR_NOT_FOUND = "selector_not_found"
    STALE_ELEMENT = "stale_element"
    NAVIGATION_FAILED = "navigation_failed"
    BROWSER_CRASH = "browser_crash"
    CDP_SESSION_STALE = "cdp_session_stale"
    CAPTCHA_BLOCKED = "captcha_blocked"
    NETWORK_ERROR = "network_error"
    FORMAT_ERROR = "format_error"
    PERMISSION_DENIED = "permission_denied"
    UNKNOWN = "unknown"


class RecoveryStrategy(StrEnum):
    RETRY = "retry"
    RETRY_DIFFERENT_TIER = "retry_different_tier"
    RETRY_SIMILAR_SELECTOR = "retry_similar_selector"
    REATTACH_SESSION = "reattach_session"
    RESPAWN_BROWSER = "respawn_browser"
    REPLAY_ACTION = "replay_action"
    RE_PROMPT_LLM = "re_prompt_llm"
    NUDGE_AGENT = "nudge_agent"
    ABORT = "abort"
    CHECKPOINT_ROLLBACK = "checkpoint_rollback"


class WatchdogEvent(StrEnum):
    CRASH_DETECTED = "crash_detected"
    STALE_ELEMENT = "stale_element"
    NAVIGATION_TIMEOUT = "navigation_timeout"
    LOOP_DETECTED = "loop_detected"
    SECURITY_VIOLATION = "security_violation"
    CAPTCHA_DETECTED = "captcha_detected"
    SESSION_STALE = "session_stale"
    RECOVERY_STARTED = "recovery_started"
    RECOVERY_COMPLETED = "recovery_completed"
    RECOVERY_FAILED = "recovery_failed"
    NUDGE_INJECT = "nudge_inject"


class ValidationLevel(StrEnum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"


class TrajectoryState(StrEnum):
    CYCLE = "cycle"
    PROGRESS = "progress"
    COMPLETED = "completed"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RecoveryHint:
    strategy: RecoveryStrategy
    retryable: bool
    max_attempts: int = 3
    should_rotate_credential: bool = False
    should_compress: bool = False
    should_fallback: bool = False
    suggested_tier: Optional[str] = None
    message: str = ""


@dataclass
class ClassifiedError:
    error_type: ErrorType
    hint: RecoveryHint
    original_error: Optional[Exception] = None
    original_result: Optional[Any] = None
    classified_at: float = field(default_factory=time.monotonic)
    classification_time_ms: float = 0.0


@dataclass
class WatchdogEventData:
    event_type: WatchdogEvent
    source: str
    detail: str
    severity: str = "warning"
    data: Optional[dict] = None
    timestamp: float = field(default_factory=time.monotonic)


@dataclass
class NudgePayload:
    level: int
    message: str
    repetition_count: int = 0
    action_hash: str = ""


@dataclass
class RecoveryEvent:
    error_type: ErrorType
    strategy: RecoveryStrategy
    attempt: int
    outcome: str
    detail: str
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.monotonic)


@dataclass(frozen=True)
class ActionFingerprint:
    action_type: str
    target: str
    value: str = ""

    def __post_init__(self) -> None:
        if not self.action_type and not self.target:
            return
        raw = f"{self.action_type}|{self.target}|{self.value}"
        h = hashlib.sha256(raw.encode()).hexdigest()[:16]
        object.__setattr__(self, "hash", h)

    hash: str = ""


@dataclass
class ValidationResult:
    valid: bool
    level: ValidationLevel
    errors: list[str] = field(default_factory=list)
    corrected_output: Optional[str] = None
    attempt: int = 1


@dataclass
class ReflectionResult:
    state: TrajectoryState
    reasoning: str
    step_number: int
    confidence: float = 0.0
    suggested_action: Optional[str] = None


@dataclass(frozen=True)
class Checkpoint:
    checkpoint_id: str
    message: str
    created_at: float
    file_count: int
    commit_hash: str


@dataclass
class ActionRecord:
    action_type: str
    target: str
    value: str = ""
    url: str = ""
    timestamp: float = field(default_factory=time.monotonic)
    succeeded: bool = True
    tier_used: str = "selector"
