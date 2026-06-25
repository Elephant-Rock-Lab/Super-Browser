"""Tests for the release artifact verification script.

Tests the guard logic without requiring a full venv install by testing
the metadata-parsing checks against the built wheel and sdist.
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


@pytest.fixture(scope="module")
def built_sdist() -> Path | None:
    """Build the sdist once for all tests in this module."""
    dist = PROJECT_ROOT / "dist"
    dist.mkdir(exist_ok=True)
    sdists = list(dist.glob("superbrowser_sdk-*.tar.gz"))
    if not sdists:
        result = subprocess.run(
            [sys.executable, "-m", "build", "--sdist", "--no-isolation"],
            cwd=str(PROJECT_ROOT),
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            pytest.skip(f"Build failed: {result.stderr[:200]}")
        sdists = list(dist.glob("superbrowser_sdk-*.tar.gz"))
    return sdists[0] if sdists else None


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


# ---------------------------------------------------------------------------
# Sdist support (P2.2)
# ---------------------------------------------------------------------------


class TestSdistMetadata:
    """Test that the verifier can read sdist (.tar.gz) metadata."""

    def test_sdist_readable_via_dispatch(self, built_sdist: Path) -> None:
        """The _read_archive dispatch reads an sdist without error."""
        if built_sdist is None:
            pytest.skip("No sdist built")
        # Import the dispatch helper from the script.
        import importlib.util
        spec = importlib.util.spec_from_file_location("verify_release_artifact", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        archive = mod._read_archive(built_sdist)
        assert archive.is_wheel is False
        assert "superbrowser-sdk" in archive.metadata
        assert "Version:" in archive.metadata

    def test_sdist_distribution_name(self, built_sdist: Path) -> None:
        if built_sdist is None:
            pytest.skip("No sdist built")
        import importlib.util
        spec = importlib.util.spec_from_file_location("verify_release_artifact", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        archive = mod._read_archive(built_sdist)
        match = re.search(r"^Name:\s*(.+)$", archive.metadata, re.MULTILINE)
        assert match is not None
        assert match.group(1).strip() == "superbrowser-sdk"

    def test_sdist_version_matches_wheel(self, built_wheel: Path, built_sdist: Path) -> None:
        """Wheel and sdist must report the same version."""
        if built_wheel is None or built_sdist is None:
            pytest.skip("No wheel or sdist built")
        w_meta = _read_wheel_metadata(built_wheel)[0]
        import importlib.util
        spec = importlib.util.spec_from_file_location("verify_release_artifact", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        s_archive = mod._read_archive(built_sdist)
        w_ver = re.search(r"^Version:\s*(.+)$", w_meta, re.MULTILINE).group(1).strip()
        s_ver = re.search(r"^Version:\s*(.+)$", s_archive.metadata, re.MULTILINE).group(1).strip()
        assert w_ver == s_ver

    def test_sdist_has_pkg_info(self, built_sdist: Path) -> None:
        """The sdist must contain a PKG-INFO file."""
        if built_sdist is None:
            pytest.skip("No sdist built")
        import tarfile
        with tarfile.open(built_sdist, "r:gz") as tf:
            members = tf.getnames()
        assert any(m.endswith("PKG-INFO") for m in members)


class TestArchiveDispatch:
    """Test the archive-type dispatch and bad-input handling."""

    def test_bad_archive_type_raises(self, tmp_path: Path) -> None:
        """A non-.whl / non-.tar.gz file must raise ValueError."""
        import importlib.util
        spec = importlib.util.spec_from_file_location("verify_release_artifact", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        bad = tmp_path / "not-a-package.zip"
        bad.write_bytes(b"PK\x03\x04")  # zip magic, but wrong extension
        with pytest.raises(ValueError, match="Unsupported archive type"):
            mod._read_archive(bad)

    def test_wheel_dispatched_as_wheel(self, built_wheel: Path) -> None:
        if built_wheel is None:
            pytest.skip("No wheel built")
        import importlib.util
        spec = importlib.util.spec_from_file_location("verify_release_artifact", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        archive = mod._read_archive(built_wheel)
        assert archive.is_wheel is True
        assert archive.entry_points  # wheel has entry_points.txt

    def test_sdist_dispatched_as_sdist(self, built_sdist: Path) -> None:
        if built_sdist is None:
            pytest.skip("No sdist built")
        import importlib.util
        spec = importlib.util.spec_from_file_location("verify_release_artifact", SCRIPT)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        archive = mod._read_archive(built_sdist)
        assert archive.is_wheel is False
        assert archive.entry_points == ""  # sdist has no entry_points.txt
