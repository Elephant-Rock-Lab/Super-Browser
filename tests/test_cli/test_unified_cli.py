"""Tests for the unified CLI entry point (issue #148 fix).

Verifies that all subcommands are accessible via the single ``main()``
function in ``super_browser.cli.__init__``, resolving the module
shadowing bug where ``cli.py`` commands were inaccessible.
"""

from __future__ import annotations

import sys
from unittest.mock import patch

import pytest

from super_browser import __version__
from super_browser.cli import main


class TestCLIVersion:
    """Test ``superbrowser version`` subcommand."""

    def test_version_prints(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``superbrowser version`` prints the package version."""
        with patch.object(sys, "argv", ["superbrowser", "version"]):
            main()

        captured = capsys.readouterr()
        assert __version__ in captured.out
        assert "superbrowser" in captured.out

    def test_no_command_prints_version(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``superbrowser`` with no subcommand defaults to version."""
        with patch.object(sys, "argv", ["superbrowser"]):
            main()

        captured = capsys.readouterr()
        assert __version__ in captured.out


class TestCLIHelp:
    """Test that all subcommands are registered."""

    def test_help_lists_all_commands(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``superbrowser --help`` lists all subcommands."""
        with pytest.raises(SystemExit) as exc_info:
            with patch.object(sys, "argv", ["superbrowser", "--help"]):
                main()

        assert exc_info.value.code == 0

        captured = capsys.readouterr()
        # Commands from former cli.py
        for cmd in ["version", "info", "run", "interactive", "script", "replay", "act", "stealth-check"]:
            assert cmd in captured.out, f"Missing subcommand '{cmd}' in help output"

        # Commands from former cli/__init__.py
        for cmd in ["memory", "stealth-validate", "result-demo"]:
            assert cmd in captured.out, f"Missing subcommand '{cmd}' in help output"


class TestCLIMemory:
    """Test memory subcommand (smoke — no real data)."""

    def test_memory_list_no_data(self, capsys: pytest.CaptureFixture[str], tmp_path) -> None:
        """``superbrowser memory list`` with empty dir prints gracefully."""
        with patch.object(sys, "argv", [
            "superbrowser", "memory", "list", "--dir", str(tmp_path),
        ]):
            main()

        captured = capsys.readouterr()
        assert "No domains" in captured.out


class TestCLIResultDemo:
    """Test result-demo subcommand."""

    def test_result_demo_success(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``superbrowser result-demo`` prints success result."""
        with patch.object(sys, "argv", ["superbrowser", "result-demo"]):
            main()

        captured = capsys.readouterr()
        assert "OK" in captured.out

    def test_result_demo_json(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``superbrowser result-demo --json`` outputs JSON."""
        with patch.object(sys, "argv", ["superbrowser", "result-demo", "--json"]):
            main()

        captured = capsys.readouterr()
        import json
        data = json.loads(captured.out)
        assert data["ok"] is True

    def test_result_demo_failure(self, capsys: pytest.CaptureFixture[str]) -> None:
        """``superbrowser result-demo --fail`` prints failure result."""
        with patch.object(sys, "argv", ["superbrowser", "result-demo", "--fail"]):
            main()

        captured = capsys.readouterr()
        assert "FAIL" in captured.out


class TestCLIEntryPoint:
    """Test that the entry point target is importable and callable."""

    def test_entry_point_importable(self) -> None:
        """The ``super_browser.cli:main`` entry point resolves correctly."""
        from super_browser.cli import main as entry_main

        assert callable(entry_main)

    def test_no_shadowing(self) -> None:
        """``super_browser.cli`` resolves to the package, not a stale module."""
        import super_browser.cli as cli

        # The package __file__ should point to __init__.py, not cli.py
        assert cli.__file__.endswith("__init__.py")
        assert "cli.py" not in cli.__file__
