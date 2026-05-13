"""Host OS auto-detection — select a device profile matching the current machine."""

from __future__ import annotations

import platform


def detect_host_profile() -> str:
    """Return the profile ID that best matches the current OS and architecture.

    Mapping
    -------
    - Linux  x86_64 → ``linux-chrome-stable``
    - Darwin arm64  → ``macos-m4-chrome-stable``
    - Darwin x86_64 → ``macos-chrome-stable``
    - Windows x86_64 → ``windows-chrome-stable``
    - Unknown → ``linux-chrome-stable`` (safe fallback)
    """
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Linux" and machine in ("x86_64", "amd64"):
        return "linux-chrome-stable"
    if system == "Darwin" and machine == "arm64":
        return "macos-m4-chrome-stable"
    if system == "Darwin" and machine in ("x86_64", "amd64"):
        return "macos-chrome-stable"
    if system == "Windows" and machine in ("x86_64", "amd64"):
        return "windows-chrome-stable"

    # Safe fallback — Linux profiles have the least platform-specific signals
    return "linux-chrome-stable"
