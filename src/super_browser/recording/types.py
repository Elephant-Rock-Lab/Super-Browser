"""Recording data types — ActionRecord and RecordingSession."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

SCHEMA_VERSION = "1.0"

# Keys that are stripped from params/context before recording to prevent
# credential leakage (HB-23-04).
_SENSITIVE_KEY_PATTERNS = frozenset({
    "api_key", "apikey", "token", "secret", "password", "credential",
    "authorization", "cookie", "session_id",
})


def _filter_sensitive(params: dict[str, Any]) -> dict[str, Any]:
    """Return a copy of *params* with sensitive keys redacted."""
    safe: dict[str, Any] = {}
    for key, value in params.items():
        if key.lower() in _SENSITIVE_KEY_PATTERNS:
            safe[key] = "[REDACTED]"
        else:
            safe[key] = value
    return safe


@dataclass
class ActionRecord:
    """A single recorded browser action."""

    index: int
    timestamp: float
    action: str
    params: dict[str, Any]
    url: str = ""
    title: str = ""
    screenshot_before: Optional[str] = None  # base64
    screenshot_after: Optional[str] = None  # base64
    ok: bool = True
    error: Optional[str] = None
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (JSON-friendly)."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "action": self.action,
            "params": self.params,
            "url": self.url,
            "title": self.title,
            "screenshot_before": self.screenshot_before,
            "screenshot_after": self.screenshot_after,
            "ok": self.ok,
            "error": self.error,
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ActionRecord:
        """Deserialize from a plain dict."""
        return cls(
            index=data["index"],
            timestamp=data["timestamp"],
            action=data["action"],
            params=data.get("params", {}),
            url=data.get("url", ""),
            title=data.get("title", ""),
            screenshot_before=data.get("screenshot_before"),
            screenshot_after=data.get("screenshot_after"),
            ok=data.get("ok", True),
            error=data.get("error"),
            duration_ms=data.get("duration_ms", 0.0),
        )


@dataclass
class RecordingSession:
    """Container for a complete recording session."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    started_at: float = field(default_factory=time.monotonic)
    actions: list[ActionRecord] = field(default_factory=list)
    schema_version: str = SCHEMA_VERSION

    @property
    def metadata(self) -> dict[str, Any]:
        """Computed metadata — action count, error count, duration."""
        error_count = sum(1 for a in self.actions if not a.ok)
        duration_ms = 0.0
        if self.actions:
            duration_ms = (self.actions[-1].timestamp - self.started_at) * 1000
        return {
            "action_count": len(self.actions),
            "error_count": error_count,
            "duration_ms": duration_ms,
            "schema_version": self.schema_version,
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "schema_version": self.schema_version,
            "actions": [a.to_dict() for a in self.actions],
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecordingSession:
        """Deserialize from a plain dict."""
        actions = [ActionRecord.from_dict(a) for a in data.get("actions", [])]
        session = cls(
            session_id=data.get("session_id", uuid.uuid4().hex),
            started_at=data.get("started_at", 0.0),
            schema_version=data.get("schema_version", SCHEMA_VERSION),
        )
        session.actions = actions
        return session
