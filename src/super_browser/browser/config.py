"""Browser session configuration."""

from __future__ import annotations

import warnings
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional


class SessionMode(StrEnum):
    """How to obtain a browser session."""
    PATCHRIGHT_LAUNCH = "patchright_launch"
    PATCHRIGHT_ATTACH = "patchright_attach"
    DISCOVER = "discover"
    DAEMON = "daemon"


@dataclass(frozen=True)
class SessionConfig:
    """Immutable configuration for a browser session."""
    mode: SessionMode = SessionMode.PATCHRIGHT_LAUNCH
    headless: bool = False
    executable_path: Optional[str] = None
    chrome_args: tuple[str, ...] = ()
    user_data_dir: Optional[str] = None
    proxy: Optional[str] = None
    viewport: tuple[int, int] = (1280, 720)
    user_agent: Optional[str] = None
    default_timeout: float = 30.0
    navigation_timeout: float = 30.0
    discovery_timeout: float = 30.0
    discovery_interval: float = 0.5
    cdp_ws_url: Optional[str] = None
    daemon_socket_path: Optional[str] = None
    stale_recovery: bool = True
    event_buffer_size: int = 500
    shutdown_grace_period: float = 7.0

    def __post_init__(self) -> None:
        warnings.warn(
            "SessionConfig is deprecated. Use super_browser.Config instead.",
            DeprecationWarning,
            stacklevel=2,
        )
