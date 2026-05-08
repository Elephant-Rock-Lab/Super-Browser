"""Session recording subsystem — capture, persist, and replay browser sessions."""

from super_browser.recording.recorder import SessionRecorder
from super_browser.recording.types import (
    ActionRecord,
    RecordingSession,
    SCHEMA_VERSION,
)

__all__ = [
    "ActionRecord",
    "RecordingSession",
    "SCHEMA_VERSION",
    "SessionRecorder",
]
