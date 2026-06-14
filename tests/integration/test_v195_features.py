"""v1.9.5 feature tests — Doc Version Normalization + Example Fix.

Verifies:
- docs/api-stability.md version header updated to v2.0.0a1
- docs/error-catalog.md version header updated to v2.0.0a1
- examples/stealth_mode.py uses StealthConfig (not Config.Stealth)
- No Config.Browser/Config.Agent/Config.Budget in any example
- No Config.Stealth in any example
"""

from __future__ import annotations

from pathlib import Path

from packaging.version import Version as _V

from super_browser import __version__

EXAMPLES_DIR = Path("./examples")
DOCS_DIR = Path("./docs")


class TestV195DocNormalization:
    """Doc version normalization and example correctness."""

    def test_version_is_195(self) -> None:
        assert _V(__version__) >= _V("1.9.5")

    def test_api_stability_version_header(self) -> None:
        header = (DOCS_DIR / "api-stability.md").read_text(encoding="utf-8").split("\n")[:5]
        assert "v2.0.0a1" in "\n".join(header)

    def test_error_catalog_version_header(self) -> None:
        header = (DOCS_DIR / "error-catalog.md").read_text(encoding="utf-8").split("\n")[:5]
        assert "v2.0.0a1" in "\n".join(header)

    def test_no_config_browser_alias_in_examples(self) -> None:
        for f in EXAMPLES_DIR.glob("*.py"):
            content = f.read_text(encoding="utf-8")
            assert "Config.Browser" not in content, f"{f.name}: Config.Browser found"
            assert "Config.Agent" not in content, f"{f.name}: Config.Agent found"
            assert "Config.Budget" not in content, f"{f.name}: Config.Budget found"
            assert "Config.Stealth" not in content, f"{f.name}: Config.Stealth found"

    def test_stealth_mode_uses_stealth_config(self) -> None:
        content = (EXAMPLES_DIR / "stealth_mode.py").read_text(encoding="utf-8")
        assert "StealthConfig" in content
        assert "Config.Stealth" not in content

    def test_all_doc_headers_current(self) -> None:
        """All user-facing doc headers should not reference stale versions."""
        stale_patterns = ["v1.9.0 —", "v1.9.1 —", "v1.9.2 —", "v1.9.3 —", "v1.10.0 —"]
        for doc in DOCS_DIR.rglob("*.md"):
            if "aiv" in str(doc) or "discovery" in str(doc):
                continue
            content = doc.read_text(encoding="utf-8")
            for pat in stale_patterns:
                assert pat not in content, f"{doc.name}: stale version ref '{pat}' found"
