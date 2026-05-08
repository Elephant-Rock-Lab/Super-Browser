"""Session recording subsystem — capture, persist, and replay browser sessions."""

from super_browser.recording.recorder import SessionRecorder
from super_browser.recording.replayer import MismatchRecord, RecordingReplayer, ReplayReport
from super_browser.recording.types import (
    ActionRecord,
    RecordingSession,
    SCHEMA_VERSION,
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
