#!/usr/bin/env python
"""Release artifact verification script.

Verifies a built wheel or sdist against release-quality criteria.

Wheel-only checks (entry points, module shadowing guard, extras):
  - run when the artifact is a ``.whl``
  - skipped for sdists (``.tar.gz``) which lack ``entry_points.txt`` and the
    flat package layout

Shared checks (run for both):
  - Distribution name is ``superbrowser-sdk``
  - Version is present in metadata
  - Package installs in a clean venv
  - ``import super_browser`` works and reports the version
  - ``superbrowser version`` CLI works
  - CLI ``--help`` lists all subcommands
  - README install commands use ``superbrowser-sdk``
  - No stale ``pip install super-browser[`` in user-facing docs

Usage::

    python scripts/verify_release_artifact.py dist/superbrowser_sdk-*.whl
    python scripts/verify_release_artifact.py dist/superbrowser_sdk-*.tar.gz

Exit code 0 = all checks passed, 1 = one or more checks failed.
"""

from __future__ import annotations

import re
import subprocess
import sys
import tarfile
import tempfile
import zipfile
from pathlib import Path
from typing import NamedTuple

# ANSI colors (optional, gracefully degrades)
GREEN = "\033[92m"
RED = "\033[91m"
BOLD = "\033[1m"
RESET = "\033[0m"


def _ok(msg: str) -> None:
    print(f"  {GREEN}✓{RESET} {msg}")


def _fail(msg: str) -> None:
    print(f"  {RED}✗{RESET} {msg}")


# ---------------------------------------------------------------------------
# Archive reading — dispatch by suffix
# ---------------------------------------------------------------------------


class ArchiveMeta(NamedTuple):
    """Metadata extracted from a wheel or sdist archive."""

    metadata: str           # METADATA (wheel) or PKG-INFO (sdist) content
    entry_points: str       # entry_points.txt content (wheel only; "" for sdist)
    names: list[str]        # member names
    is_wheel: bool          # True for .whl, False for .tar.gz


def _read_archive(artifact: Path) -> ArchiveMeta:
    """Read metadata + member list from a wheel or sdist.

    Raises ``ValueError`` for unsupported archive types.
    """
    name = artifact.name.lower()
    if name.endswith(".whl"):
        return _read_wheel(artifact)
    if name.endswith(".tar.gz"):
        return _read_sdist(artifact)
    raise ValueError(
        f"Unsupported archive type: {artifact.name}. "
        "Expected a .whl wheel or a .tar.gz sdist."
    )


def _read_wheel(wheel_path: Path) -> ArchiveMeta:
    with zipfile.ZipFile(wheel_path) as zf:
        names = zf.namelist()
        metadata_files = [n for n in names if n.endswith(".dist-info/METADATA")]
        if not metadata_files:
            raise ValueError("No METADATA file found in wheel")
        metadata = zf.read(metadata_files[0]).decode("utf-8")
        entry_files = [n for n in names if n.endswith(".dist-info/entry_points.txt")]
        entry_points = zf.read(entry_files[0]).decode("utf-8") if entry_files else ""
    return ArchiveMeta(metadata=metadata, entry_points=entry_points, names=names, is_wheel=True)


def _read_sdist(sdist_path: Path) -> ArchiveMeta:
    with tarfile.open(sdist_path, "r:gz") as tf:
        members = tf.getnames()
        # PKG-INFO lives at the archive root (e.g. "superbrowser_sdk-2.5.0/PKG-INFO")
        pkg_info_files = [n for n in members if n.endswith("PKG-INFO")]
        if not pkg_info_files:
            raise ValueError("No PKG-INFO file found in sdist")
        metadata = tf.extractfile(pkg_info_files[0]).read().decode("utf-8")
    # sdists have no entry_points.txt and no flat package layout
    return ArchiveMeta(metadata=metadata, entry_points="", names=members, is_wheel=False)


# ---------------------------------------------------------------------------
# Main verification flow
# ---------------------------------------------------------------------------


def main() -> int:
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <artifact-path> [README-path] [docs-dir]")
        print("\nExample:")
        print(f"  {sys.argv[0]} dist/superbrowser_sdk-2.0.2-py3-none-any.whl README.md docs/")
        print(f"  {sys.argv[0]} dist/superbrowser_sdk-2.0.2.tar.gz README.md docs/")
        return 1

    artifact_path = Path(sys.argv[1])
    readme_path = Path(sys.argv[2]) if len(sys.argv) >= 3 else Path("README.md")
    docs_dir = Path(sys.argv[3]) if len(sys.argv) >= 4 else Path("docs")

    if not artifact_path.exists():
        print(f"{RED}Error:{RESET} Artifact not found: {artifact_path}")
        return 1

    # Read archive — fail clearly on bad type
    try:
        archive = _read_archive(artifact_path)
    except ValueError as e:
        print(f"{RED}Error:{RESET} {e}")
        return 1

    failures: list[str] = []
    kind = "wheel" if archive.is_wheel else "sdist"

    print(f"\n{BOLD}Release Artifact Verification{RESET}")
    print(f"  {kind.capitalize()}: {artifact_path}")
    print()

    metadata = archive.metadata

    # ------------------------------------------------------------------
    # 1. Metadata (name + version)
    # ------------------------------------------------------------------
    print(f"{BOLD}1. {kind.capitalize()} metadata{RESET}")

    # Distribution name
    name_match = re.search(r"^Name:\s*(.+)$", metadata, re.MULTILINE)
    dist_name = name_match.group(1).strip() if name_match else ""
    if dist_name == "superbrowser-sdk":
        _ok(f"Distribution name: {dist_name}")
    else:
        _fail(f"Distribution name is '{dist_name}', expected 'superbrowser-sdk'")
        failures.append("distribution-name")

    # Version
    version_match = re.search(r"^Version:\s*(.+)$", metadata, re.MULTILINE)
    version = version_match.group(1).strip() if version_match else "unknown"
    if version != "unknown":
        _ok(f"Version: {version}")
    else:
        _fail("Version not found in metadata")
        failures.append("version-missing")

    # ------------------------------------------------------------------
    # 2. Console script entry point (wheel only)
    # ------------------------------------------------------------------
    entry_points = archive.entry_points

    if archive.is_wheel:
        print(f"\n{BOLD}2. Console scripts{RESET}")

        if "superbrowser = super_browser.cli:main" in entry_points:
            _ok("Entry point: superbrowser = super_browser.cli:main")
        else:
            _fail(f"Entry point missing or incorrect:\n  {entry_points}")
            failures.append("entry-point")

        if "superbrowser-mcp = super_browser.mcp_server:main" in entry_points:
            _ok("Entry point: superbrowser-mcp = super_browser.mcp_server:main")
        else:
            _fail("Entry point superbrowser-mcp missing or incorrect")
            failures.append("entry-point-mcp")
    else:
        print(f"\n{BOLD}2. Console scripts — skipped (sdist has no entry_points.txt){RESET}")

    # ------------------------------------------------------------------
    # 3. [all] extra self-reference (wheel only — sdists include metadata
    #    but entry-point/console checks are wheel-specific; extras ARE in
    #    the sdist PKG-INFO, so we check them for both)
    # ------------------------------------------------------------------
    print(f"\n{BOLD}3. Extras self-reference{RESET}")

    # Extract all Requires-Dist lines with extras
    extra_lines = [
        line for line in metadata.splitlines()
        if line.startswith("Requires-Dist:") and "extra ==" in line
    ]

    stale_refs = []
    for line in extra_lines:
        if "super-browser[" in line:
            stale_refs.append(line.strip())

    if not stale_refs:
        _ok("No stale 'super-browser[' references in extras")
    else:
        for ref in stale_refs:
            _fail(f"Stale reference: {ref}")
        failures.append("extras-stale-ref")

    # Check [all] specifically exists
    has_all = any('extra == "all"' in line or "extra == 'all'" in line for line in extra_lines)
    if has_all:
        _ok("[all] extra present")
    else:
        _fail("[all] extra not found")
        failures.append("extras-all-missing")

    # ------------------------------------------------------------------
    # 4. No cli.py shadowing (wheel only — sdist has source layout)
    # ------------------------------------------------------------------
    names = archive.names

    if archive.is_wheel:
        print(f"\n{BOLD}4. Module shadowing guard{RESET}")

        cli_py_files = [n for n in names if n == "super_browser/cli.py"]
        if not cli_py_files:
            _ok("No cli.py module in wheel (no shadowing)")
        else:
            _fail("cli.py found in wheel — will shadow cli/ package")
            failures.append("cli-shadowing")

        # Verify cli/__init__.py exists
        if "super_browser/cli/__init__.py" in names:
            _ok("cli/__init__.py present in wheel")
        else:
            _fail("cli/__init__.py missing from wheel")
            failures.append("cli-init-missing")
    else:
        print(f"\n{BOLD}4. Module shadowing guard — skipped (sdist){RESET}")

    # ------------------------------------------------------------------
    # 5. Install and runtime checks (both wheel + sdist)
    # ------------------------------------------------------------------
    print(f"\n{BOLD}5. Runtime verification (isolated venv){RESET}")

    with tempfile.TemporaryDirectory(prefix="sb-verify-") as venv_dir:
        venv_path = Path(venv_dir)
        pip = str(venv_path / "Scripts" / "pip") if sys.platform == "win32" else str(venv_path / "bin" / "pip")
        python = str(venv_path / "Scripts" / "python") if sys.platform == "win32" else str(venv_path / "bin" / "python")

        # Create venv
        result = subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            _fail(f"Failed to create venv: {result.stderr.strip()}")
            failures.append("venv-creation")
        else:
            # Install the artifact (pip handles both .whl and .tar.gz)
            result = subprocess.run(
                [pip, "install", "--quiet", str(artifact_path)],
                capture_output=True, text=True,
            )
            if result.returncode != 0:
                _fail(f"Failed to install {kind}: {result.stderr.strip()[:200]}")
                failures.append(f"{kind}-install")
            else:
                _ok(f"{kind.capitalize()} installs in clean venv")

                # Import check
                result = subprocess.run(
                    [python, "-c", "import super_browser; print(super_browser.__version__)"],
                    capture_output=True, text=True,
                )
                if result.returncode == 0 and version in result.stdout.strip():
                    _ok(f"import super_browser → {version}")
                else:
                    _fail(f"Import failed: {result.stderr.strip()[:200]}")
                    failures.append("import")

                # CLI version check
                cli_bin = str(venv_path / "Scripts" / "superbrowser") if sys.platform == "win32" else str(venv_path / "bin" / "superbrowser")
                result = subprocess.run(
                    [cli_bin, "version"],
                    capture_output=True, text=True,
                )
                if result.returncode == 0 and version in result.stdout:
                    _ok(f"superbrowser version → {result.stdout.strip()}")
                else:
                    _fail(f"CLI version failed (rc={result.returncode}): {result.stderr.strip()[:200]}")
                    failures.append("cli-version")

                # CLI help lists all commands
                result = subprocess.run(
                    [cli_bin, "--help"],
                    capture_output=True, text=True,
                )
                expected_commands = [
                    "version", "info", "run", "interactive", "script",
                    "replay", "act", "stealth-check", "stealth-validate",
                    "memory", "result-demo",
                ]
                missing = [c for c in expected_commands if c not in result.stdout]
                if not missing:
                    _ok("CLI --help lists all 11 subcommands")
                else:
                    _fail(f"Missing subcommands in help: {missing}")
                    failures.append("cli-help-commands")

    # ------------------------------------------------------------------
    # 6. README install commands
    # ------------------------------------------------------------------
    print(f"\n{BOLD}6. README install commands{RESET}")

    if readme_path.exists():
        readme_content = readme_path.read_text(encoding="utf-8")

        # Check badge
        if "pypi/v/superbrowser-sdk" in readme_content:
            _ok("PyPI badge: superbrowser-sdk")
        else:
            _fail("PyPI badge missing or wrong")
            failures.append("readme-badge")

        # Check no stale install commands
        stale_readme = re.findall(r"pip install super-browser\[", readme_content)
        if not stale_readme:
            _ok("No stale 'pip install super-browser[' in README")
        else:
            _fail(f"Found {len(stale_readme)} stale install commands in README")
            failures.append("readme-stale-install")

        # Verify at least one correct install command
        if "pip install superbrowser-sdk[" in readme_content:
            _ok("README has correct install command")
        else:
            _fail("README missing 'pip install superbrowser-sdk['")
            failures.append("readme-no-install")
    else:
        _fail(f"README not found: {readme_path}")
        failures.append("readme-missing")

    # ------------------------------------------------------------------
    # 7. User-facing docs scan
    # ------------------------------------------------------------------
    print(f"\n{BOLD}7. User-facing docs scan{RESET}")

    if docs_dir.exists():
        stale_docs = []
        for md_file in docs_dir.rglob("*.md"):
            # Skip docs/aiv/ — historical batch records, not user-facing
            if "docs/aiv/" in str(md_file).replace("\\", "/"):
                continue
            content = md_file.read_text(encoding="utf-8", errors="replace")
            matches = re.findall(r"pip install super-browser\[", content)
            if matches:
                stale_docs.append(f"{md_file}: {len(matches)} occurrence(s)")

        if not stale_docs:
            _ok("No stale install commands in user-facing docs")
        else:
            for doc in stale_docs:
                _fail(doc)
            failures.append("docs-stale-install")
    else:
        _ok(f"Docs dir not found ({docs_dir}), skipping")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print()
    if not failures:
        print(f"{GREEN}{BOLD}ALL CHECKS PASSED{RESET} — artifact is release-ready.\n")
        return 0
    else:
        print(f"{RED}{BOLD}{len(failures)} CHECK(S) FAILED:{RESET}")
        for f in failures:
            print(f"  {RED}•{RESET} {f}")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())
