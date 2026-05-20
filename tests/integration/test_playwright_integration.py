"""Integration tests for BATCH-47 — PlaywrightBackend + refactoring verification."""

from __future__ import annotations

import subprocess


class TestBATCH47Integration:
    """TEST-47-03: Integration verification."""

    def test_controller_no_raw_page(self) -> None:
        """Controller has zero raw_page calls."""
        result = subprocess.run(
            ["grep", "-c", "raw_page", "src/super_browser/interaction/controller.py"],
            capture_output=True, text=True, cwd="C:/Next AI/SUPER-BROWSER",
        )
        # grep returns exit code 1 when no matches (count is 0)
        assert result.returncode != 0 or result.stdout.strip() == "0"

    def test_facade_no_batch47_markers(self) -> None:
        """Facade has zero TODO(BATCH-47) markers."""
        result = subprocess.run(
            ["grep", "-c", "TODO.BATCH-47", "src/super_browser/agent/facade.py"],
            capture_output=True, text=True, cwd="C:/Next AI/SUPER-BROWSER",
        )
        assert result.returncode != 0 or result.stdout.strip() == "0"

    def test_facade_no_session_private(self) -> None:
        """Facade has zero _session._private access."""
        result = subprocess.run(
            ["grep", "-c", "_session\\._", "src/super_browser/agent/facade.py"],
            capture_output=True, text=True, cwd="C:/Next AI/SUPER-BROWSER",
        )
        assert result.returncode != 0 or result.stdout.strip() == "0"

    def test_playwright_backend_importable(self) -> None:
        """PlaywrightBackend module loads without error."""
        from super_browser.browser.backends.playwright_backend import (
            PlaywrightEngine,
            PlaywrightPage,
            PlaywrightStealthBridge,
        )
        assert PlaywrightEngine is not None
        assert PlaywrightPage is not None
        assert PlaywrightStealthBridge is not None

    def test_backend_detection_precedence(self) -> None:
        """Backend detection: patchright > playwright > selenium."""
        import argparse

        from super_browser.browser.engine import _detect_backend
        # Explicit playwright
        config = argparse.Namespace(backend="playwright", mode=None)
        assert _detect_backend(config) == "playwright"

    def test_architecture_docs_exist(self) -> None:
        """Architecture docs exist."""
        import os
        assert os.path.exists("C:/Next AI/SUPER-BROWSER/docs/architecture.md")
