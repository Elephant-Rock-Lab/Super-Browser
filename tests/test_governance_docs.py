"""Governance documentation integrity tests.

Prevents drift between contributor docs, operating doctrine, and repository state.
These tests are machine-checkable evidence that Wave 0 stays sealed.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CONTRIBUTING = REPO_ROOT / "CONTRIBUTING.md"
OPERATING_DOCTRINE = REPO_ROOT / "docs" / "operating-doctrine.md"
README = REPO_ROOT / "README.md"


def _read(path: Path) -> str:
    assert path.exists(), f"Required file missing: {path}"
    return path.read_text(encoding="utf-8")


class TestOperatingDoctrine:
    """docs/operating-doctrine.md exists and contains canonical terms."""

    def test_operating_doctrine_exists(self) -> None:
        assert OPERATING_DOCTRINE.exists(), "docs/operating-doctrine.md must exist"

    def test_operating_doctrine_contains_canonical_terms(self) -> None:
        text = _read(OPERATING_DOCTRINE)
        required_terms = [
            "Disk-Verified Large-Wave Execution",
            "Large-Wave Execution",
            "Disk-Verified Planning",
            "Scale by wave",
            "Ground by disk",
            "Accept by tests",
            "Seal by evidence",
        ]
        for term in required_terms:
            assert term in text, (
                f"Operating doctrine missing canonical term: {term!r}"
            )


class TestContributingDoc:
    """CONTRIBUTING.md must reflect current repository state."""

    def test_contributing_uses_main_not_master(self) -> None:
        text = _read(CONTRIBUTING)
        assert "master" not in text, (
            "CONTRIBUTING.md still references 'master' — should be 'main'"
        )

    def test_contributing_uses_valid_install_extra(self) -> None:
        text = _read(CONTRIBUTING)
        # [browser] was removed in v1.10.0 — must not appear
        assert ".[browser" not in text, (
            "CONTRIBUTING.md references removed [browser] extra "
            "— use [dev,all] or [patchright,anthropic,openai,dev]"
        )

    def test_contributing_requires_disk_verified_wave_execution(self) -> None:
        text = _read(CONTRIBUTING)
        # Must reference the operating doctrine
        assert "operating-doctrine" in text or "Disk-Verified" in text, (
            "CONTRIBUTING.md must reference the operating doctrine or disk verification"
        )


class TestReadmeLinks:
    """README.md must link to the operating doctrine."""

    def test_readme_links_to_operating_doctrine(self) -> None:
        text = _read(README)
        assert "operating-doctrine" in text, (
            "README.md must link to docs/operating-doctrine.md"
        )
