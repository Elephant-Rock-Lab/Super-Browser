"""Session recording subsystem — capture, persist, and replay browser sessions."""

from super_browser.recording.recorder import SessionRecorder
from super_browser.recording.replayer import MismatchRecord, RecordingReplayer, ReplayReport
from super_browser.recording.types import (
    SCHEMA_VERSION,
    ActionRecord,
    RecordingSession,
)

__all__ = [
    "ActionRecord",
    "MismatchRecord",
    "RecordingReplayer",
    "RecordingSession",
    "ReplayReport",
    "SCHEMA_VERSION",
    "SessionRecorder",
]
