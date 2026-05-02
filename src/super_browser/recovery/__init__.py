"""GAP-04 Self-Healing & Session Recovery — error classification, recovery strategies, watchdogs."""

from super_browser.recovery.checkpoint import CheckpointManager
from super_browser.recovery.classifier import ErrorClassifier
from super_browser.recovery.coordinator import RecoveryCoordinator
from super_browser.recovery.event_bus import WatchdogEventBus
from super_browser.recovery.format_validator import FormatValidator
from super_browser.recovery.reflection import ReflectionAgent
from super_browser.recovery.retry_tracker import RetryTracker
from super_browser.recovery.session_recovery import SessionRecovery
from super_browser.recovery.types import (
    ActionFingerprint,
    ActionRecord,
    ClassifiedError,
    Checkpoint,
    ErrorType,
    NudgePayload,
    RecoveryEvent,
    RecoveryHint,
    RecoveryStrategy,
    ReflectionResult,
    TrajectoryState,
    ValidationLevel,
    ValidationResult,
    WatchdogEvent,
    WatchdogEventData,
)
from super_browser.recovery.watchdogs import (
    BaseWatchdog,
    CrashWatchdog,
    LoopWatchdog,
    NavigationWatchdog,
    SecurityWatchdog,
    StaleElementWatchdog,
)

__all__ = [
    "ActionFingerprint",
    "ActionRecord",
    "BaseWatchdog",
    "Checkpoint",
    "CheckpointManager",
    "ClassifiedError",
    "CrashWatchdog",
    "ErrorClassifier",
    "ErrorType",
    "FormatValidator",
    "LoopWatchdog",
    "NavigationWatchdog",
    "NudgePayload",
    "RecoveryCoordinator",
    "RecoveryEvent",
    "RecoveryHint",
    "RecoveryStrategy",
    "ReflectionAgent",
    "ReflectionResult",
    "RetryTracker",
    "SecurityWatchdog",
    "SessionRecovery",
    "StaleElementWatchdog",
    "TrajectoryState",
    "ValidationLevel",
    "ValidationResult",
    "WatchdogEvent",
    "WatchdogEventData",
    "WatchdogEventBus",
]
