"""Browser discovery via DevToolsActivePort scanning."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class DiscoveryResult:
    found: bool
    ws_url: Optional[str] = None
    profile_path: Optional[str] = None
    browser_pid: Optional[int] = None
    attempted_paths: int = 0
    discovery_time_ms: float = 0.0


# Common DevToolsActivePort locations across platforms
_PROFILE_PATHS: list[Path] = [
    # Windows
    Path(os.environ.get("LOCALAPPDATA", "")) / "Google/Chrome/User Data",
    Path(os.environ.get("PROGRAMFILES", "")) / "Google/Chrome/Application",
    Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Google/Chrome/Application",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Chromium/User Data",
    Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Edge/User Data",
    Path(os.environ.get("PROGRAMFILES", "")) / "BraveSoftware/Brave-Browser/Application",
    # macOS
    Path.home() / "Library/Application Support/Google/Chrome",
    Path.home() / "Library/Application Support/Chromium",
    Path.home() / "Library/Application Support/Microsoft Edge",
    Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser",
    # Linux
    Path.home() / ".config/google-chrome",
    Path.home() / ".config/chromium",
    Path.home() / ".config/microsoft-edge",
    Path.home() / ".config/BraveSoftware/Brave-Browser",
    # Snap/Flatpak
    Path.home() / ".snap/chromium/common/chromium",
    Path.home() / ".var/app/org.chromium.Chromium/config/chromium",
]


class BrowserDiscovery:
    """Discover running browser instances via DevToolsActivePort."""

    @classmethod
    def discover(
        cls,
        timeout: float = 30.0,
        interval: float = 0.5,
        ws_url_override: Optional[str] = None,
    ) -> DiscoveryResult:
        """Scan for a running Chrome-compatible browser with remote debugging.

        Checks ws_url_override (or SB_CDP_WS env var) first, then polls
        profile directories for DevToolsActivePort files.
        """
        start = time.monotonic()

        override = ws_url_override or os.environ.get("SB_CDP_WS")
        if override:
            return DiscoveryResult(
                found=True, ws_url=override,
                discovery_time_ms=(time.monotonic() - start) * 1000,
            )

        valid_paths = [p for p in _PROFILE_PATHS if p.exists()]
        deadline = start + timeout

        while time.monotonic() < deadline:
            for profile in valid_paths:
                port_file = profile / "DevToolsActivePort"
                if not port_file.exists():
                    continue
                try:
                    lines = port_file.read_text().strip().splitlines()
                    if len(lines) >= 2:
                        port = int(lines[0])
                        path = lines[1]
                        ws_url = f"ws://127.0.0.1:{port}{path}"
                        elapsed = (time.monotonic() - start) * 1000
                        return DiscoveryResult(
                            found=True, ws_url=ws_url,
                            profile_path=str(profile),
                            attempted_paths=len(valid_paths),
                            discovery_time_ms=elapsed,
                        )
                except (ValueError, OSError):
                    continue
            time.sleep(interval)

        elapsed = (time.monotonic() - start) * 1000
        return DiscoveryResult(
            found=False,
            attempted_paths=len(valid_paths),
            discovery_time_ms=elapsed,
        )
