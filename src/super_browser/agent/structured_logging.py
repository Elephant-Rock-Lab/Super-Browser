"""Structured JSON logging with correlation IDs for the agent loop.

Provides a ``StructuredFormatter`` that emits one JSON object per log line
and a convenience ``setup_structured_logging()`` function that wires it
into the root logger.
"""

from __future__ import annotations

import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Optional


class StructuredFormatter(logging.Formatter):
    """Formats every log record as a single JSON line.

    Fields emitted:
        timestamp   — ISO-8601 UTC
        level       — e.g. ``"WARNING"``
        correlation_id — propagated from the ``LogRecord``
        message     — the formatted message
        *(extra)    — any additional fields passed via ``extra={}``
    """

    def __init__(self, *, correlation_id: Optional[str] = None) -> None:
        super().__init__()
        self._correlation_id = correlation_id

    def format(self, record: logging.LogRecord) -> str:
        entry: dict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "correlation_id": getattr(record, "correlation_id", self._correlation_id or ""),
            "message": record.getMessage(),
        }

        # Merge in any extra fields the caller attached
        reserved = {
            "name", "msg", "args", "created", "relativeCreated",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "pathname", "filename", "module", "thread", "threadName",
            "process", "processName", "levelname", "levelno", "message",
            "msecs", "taskName",
        }
        for key, value in record.__dict__.items():
            if key not in reserved and key not in entry:
                try:
                    json.dumps(value)
                    entry[key] = value
                except (TypeError, ValueError):
                    entry[key] = str(value)

        return json.dumps(entry, default=str)


def setup_structured_logging(
    correlation_id: Optional[str] = None,
    *,
    level: int = logging.INFO,
    logger_name: Optional[str] = None,
) -> str:
    """Configure *logger_name* (or the root logger) with ``StructuredFormatter``.

    Returns the correlation_id used (generated if not supplied).
    """
    cid = correlation_id or str(uuid.uuid4())
    target = logging.getLogger(logger_name)
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(StructuredFormatter(correlation_id=cid))
    target.addHandler(handler)
    target.setLevel(level)
    return cid
