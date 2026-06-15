"""Tests for the release artifact verification script.

Tests the guard logic without requiring a full venv install by testing
the metadata-parsing checks against the built wheel.
"""

from __future__ import annotations

import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "verify_release_artifact.py"
PROJECT_ROOT = SCRIPT.parent.parent


@pytest.fixture(scope="module")
def built_wheel() -> Path | None:
    """Build the wheel once for all tests in this module."""
    dist = PROJECT_ROOT / "dist"
    dist.mkdir(exist_ok=True)
    wheels = list(dist.glob("superbrowser_sdk-*.whl"))
    if not wheels:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--wheel", "--no-isolation"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"Build failed: {result.stderr[:200]}")
        wheels = list(dist.glob("superbrowser_sdk-*.whl"))
    return wheels[0] if wheels else None


def _read_wheel_metadata(wheel_path: Path) -> tuple[str, str, list[str], list[str]]:
    """Extract metadata, entry points, and file listing from a wheel."""
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()
        metadata_file = [n for n in names if n.endswith(".dist-info/METADATA")][0]
        metadata = zf.read(metadata_file).decode("utf-8")
        entry_files = [n for n in names if n.endswith(".dist-info/entry_points.txt")]
        entry_points = zf.read(entry_files[0]).decode("utf-8") if entry_files else ""
    return metadata, entry_points, names, names


class TestWheelMetadata:
    """Test wheel metadata assertions."""

    def test_distribution_name(self, built_wheel: Path) -> None:
        if built_wheel is None:
            pytest.skip("No wheel built")
        metadata, _, _, _ = _read_wheel_metadata(built_wheel)
        match = re.search(r"^Name:\s*(.+)$", metadata, re.MULTILINE)
        assert match is not None
        assert match.group(1).strip() == "superbrowser-sdk"

    def test_entry_point_registered(self, built_wheel: Path) -> None:
        if built_wheel is None:
            pytest.skip("No wheel built")
        _, entry_points, _, _ = _read_wheel_metadata(built_wheel)
        assert "superbrowser = super_browser.cli:main" in entry_points

    def test_no_cli_py_shadowing(self, built_wheel: Path) -> None:
        if built_wheel is None:
            pytest.skip("No wheel built")
        _, _, names, _ = _read_wheel_metadata(built_wheel)
        assert "super_browser/cli.py" not in names
        assert "super_browser/cli/__init__.py" in names


class TestExtrasIntegrity:
    """Test that extras don't have stale references."""

    def test_no_stale_super_browser_refs(self, built_wheel: Path) -> None:
        if built_wheel is None:
            pytest.skip("No wheel built")
        metadata, _, _, _ = _read_wheel_metadata(built_wheel)
        extra_lines = [
            line for line in metadata.splitlines()
            if line.startswith("Requires-Dist:") and "extra ==" in line
        ]
        stale = [line for line in extra_lines if "super-browser[" in line]
        assert not stale, f"Stale references found: {stale}"

    def test_all_extra_present(self, built_wheel: Path) -> None:
        if built_wheel is None:
            pytest.skip("No wheel built")
        metadata, _, _, _ = _read_wheel_metadata(built_wheel)
        extra_lines = [
            line for line in metadata.splitlines()
            if line.startswith("Requires-Dist:") and "extra ==" in line
        ]
        has_all = any(
            'extra == "all"' in line or "extra == 'all'" in line
            for line in extra_lines
        )
        assert has_all, "[all] extra not found in metadata"


class TestReadmeIntegrity:
    """Test README install command consistency."""

    def test_no_stale_install_commands(self) -> None:
        readme = PROJECT_ROOT / "README.md"
        content = readme.read_text(encoding="utf-8")
        stale = re.findall(r"pip install super-browser\[", content)
        assert not stale, f"Found {len(stale)} stale install commands"

    def test_has_correct_install_command(self) -> None:
        readme = PROJECT_ROOT / "README.md"
        content = readme.read_text(encoding="utf-8")
        assert "pip install superbrowser-sdk[" in content

    def test_pypi_badge_correct(self) -> None:
        readme = PROJECT_ROOT / "README.md"
        content = readme.read_text(encoding="utf-8")
        assert "pypi/v/superbrowser-sdk" in content


class TestScriptExists:
    """Test that the verification script exists and is runnable."""

    def test_script_exists(self) -> None:
        assert SCRIPT.exists(), f"Script not found: {SCRIPT}"

    def test_script_has_main(self) -> None:
        content = SCRIPT.read_text(encoding="utf-8")
        assert "def main()" in content
        assert "__name__" in content
