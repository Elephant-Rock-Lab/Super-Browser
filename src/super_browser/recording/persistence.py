"""Persistence — save/load RecordingSession as JSON files.

HB-23-03: JSON files include schema_version.
HB-23-04: Sensitive values are already filtered at record time.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Union

from super_browser.recording.types import RecordingSession

logger = logging.getLogger(__name__)


def save(recording: RecordingSession, path: Union[str, Path]) -> None:
    """Write *recording* to a JSON file at *path*.

    Creates parent directories if they don't exist.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    data = recording.to_dict()
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Recording saved to %s (%d actions)", path, len(recording.actions))


def load(path: Union[str, Path]) -> RecordingSession:
    """Load a RecordingSession from a JSON file at *path*.

    Raises FileNotFoundError if the file doesn't exist.
    Raises ValueError if the file is not valid recording JSON.
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Recording file not found: {path}")

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    if "actions" not in data:
        raise ValueError(f"Invalid recording file (missing 'actions'): {path}")

    session = RecordingSession.from_dict(data)
    logger.info("Recording loaded from %s (%d actions)", path, len(session.actions))
    return session
