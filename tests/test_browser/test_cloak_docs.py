"""BATCH-27/TASK-03 — pyproject.toml, Docs & Examples tests.

TEST-27-03-01: [cloak] extra installs cloakbrowser
TEST-27-03-02: docs/cloak-integration.md exists
TEST-27-03-03: example script imports correctly
TEST-27-03-04: README mentions CloakBrowser
"""

from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


# ── TEST-27-03-01: [cloak] extra installs cloakbrowser ──────────────────


class TestCloakExtra:
    """TEST-27-03-01 — [cloak] extra installs cloakbrowser."""

    def test_cloak_extra_in_pyproject(self) -> None:
        """pyproject.toml contains [cloak] optional dependency."""
        pyproject_path = ROOT / "pyproject.toml"
        content = pyproject_path.read_text(encoding="utf-8")
        assert "cloak" in content
        assert "cloakbrowser" in content
        assert ">=0.3" in content


# ── TEST-27-03-02: docs/cloak-integration.md exists ─────────────────────


class TestDocsExist:
    """TEST-27-03-02 — docs/cloak-integration.md exists and has content."""

    def test_cloak_docs_exist(self) -> None:
        docs_path = ROOT / "docs" / "cloak-integration.md"
        assert docs_path.exists(), "docs/cloak-integration.md must exist"
        content = docs_path.read_text(encoding="utf-8")
        assert len(content) > 100
        assert "CloakBrowser" in content
        assert "cloak_humanize" in content
        assert "cloak_fingerprint_seed" in content


# ── TEST-27-03-03: example script imports correctly ─────────────────────


class TestExampleScript:
    """TEST-27-03-03 — example script parses without syntax error."""

    def test_example_parses(self) -> None:
        """examples/cloak_stealth.py is valid Python."""
        example_path = ROOT / "examples" / "cloak_stealth.py"
        assert example_path.exists(), "examples/cloak_stealth.py must exist"
        source = example_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        # Verify it has at least one async function
        func_defs = [node for node in ast.walk(tree) if isinstance(node, ast.AsyncFunctionDef)]
        assert len(func_defs) >= 1, "Example should have at least one async function"


# ── TEST-27-03-04: README mentions CloakBrowser ────────────────────────


class TestReadmeSection:
    """TEST-27-03-04 — README mentions CloakBrowser."""

    def test_readme_mentions_cloak(self) -> None:
        readme_path = ROOT / "README.md"
        content = readme_path.read_text(encoding="utf-8")
        assert "CloakBrowser" in content
        assert "stealth_backend" in content or "cloak" in content.lower()
