"""Test that user-facing docs and source code don't have stale naming.

Catches future drift of distribution name, CLI command, and install
commands. Explicitly allows historical docs (docs/aiv/, RFCs, gap
analysis, migration guides) and filesystem paths.
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


# Files/dirs exempt from stale-reference checks
HISTORICAL_PATTERNS = {
    "docs/aiv/",
    "docs/gap-analysis",
    "docs/rfcs/v2-decomposition",
    "CHANGELOG.md",
    "docs/migration/",
}


def _is_historical(path: Path) -> bool:
    """Check if a file is historical (exempt from checks)."""
    rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    return any(pattern in rel for pattern in HISTORICAL_PATTERNS)


def _is_filesystem_path(line: str) -> bool:
    """Check if a 'super-browser' reference is a filesystem path (exempt)."""
    return any(p in line for p in [
        "~/.config/super-browser",
        ".super-browser",
        ".config/super-browser",
        "config/super-browser",
    ])


def _scan_files(root: Path, patterns: list[str], suffix: str = "*.py") -> list[tuple[str, str]]:
    """Scan files for stale patterns. Returns list of (file, line)."""
    hits: list[tuple[str, str]] = []
    for f in root.rglob(suffix):
        if _is_historical(f):
            continue
        content = f.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(content.splitlines(), 1):
            for pattern in patterns:
                if re.search(pattern, line) and not _is_filesystem_path(line):
                    hits.append((f"{f}:{i}", line.strip()))
    return hits


class TestNoStaleCLINaming:
    """Ensure no stale 'super-browser' CLI command references."""

    def test_no_stale_cli_in_source(self) -> None:
        """Source files should not reference 'super-browser' as a CLI command."""
        src = PROJECT_ROOT / "src"
        hits = _scan_files(src, [r"super-browser (stealth|memory|version|info|run|interactive|act)"])
        assert not hits, "Stale CLI references found:\n" + "\n".join(f"  {f}: {line}" for f, line in hits)

    def test_no_stale_cli_in_user_docs(self) -> None:
        """User-facing docs should not reference 'super-browser' as a CLI command."""
        docs = PROJECT_ROOT / "docs"
        hits = _scan_files(docs, [r"^super-browser (stealth|memory|version|info|run|interactive|act)"], suffix="*.md")
        # Filter out historical files that passed the pattern but are in subdirs
        hits = [(f, line) for f, line in hits if not _is_historical(Path(f.rsplit(":", 1)[0]))]
        assert not hits, "Stale CLI references in docs:\n" + "\n".join(f"  {f}: {line}" for f, line in hits)


class TestNoStaleInstallCommands:
    """Ensure no stale 'pip install super-browser[' in user-facing content."""

    def test_no_stale_install_in_user_docs(self) -> None:
        """User-facing docs should use 'superbrowser-sdk' not 'super-browser'."""
        docs = PROJECT_ROOT / "docs"
        hits = _scan_files(docs, [r"pip install super-browser\["], suffix="*.md")
        hits = [(f, line) for f, line in hits if not _is_historical(Path(f.rsplit(":", 1)[0]))]
        assert not hits, "Stale install commands:\n" + "\n".join(f"  {f}: {line}" for f, line in hits)

    def test_no_stale_install_in_source(self) -> None:
        """Source code should use 'superbrowser-sdk' in install hints."""
        src = PROJECT_ROOT / "src"
        hits = _scan_files(src, [r"pip install super-browser\["])
        assert not hits, "Stale install commands in source:\n" + "\n".join(f"  {f}: {line}" for f, line in hits)

    def test_no_stale_install_in_readme(self) -> None:
        """README should use 'superbrowser-sdk'."""
        readme = PROJECT_ROOT / "README.md"
        content = readme.read_text(encoding="utf-8")
        hits = re.findall(r"pip install super-browser\[", content)
        assert not hits, f"Found {len(hits)} stale install commands in README"


class TestFilesystemPathsPreserved:
    """Ensure filesystem paths still use 'super-browser' (backward compat)."""

    def test_config_paths_use_super_browser(self) -> None:
        """Filesystem paths like ~/.config/super-browser/ must NOT be renamed."""
        src = PROJECT_ROOT / "src"
        py_files = list(src.rglob("*.py"))
        assert len(py_files) > 0
        # At least some files should reference the config path
        total_refs = 0
        for f in py_files:
            content = f.read_text(encoding="utf-8", errors="replace")
            total_refs += len(re.findall(r"super-browser", content))
        # We expect many references (filesystem paths)
        assert total_refs > 5, "Expected filesystem path references to 'super-browser'"
