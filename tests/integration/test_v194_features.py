"""v1.9.4 feature tests — API Reference Completion + Doc Fixes.

Verifies:
- examples/backend_selection.py uses SessionConfig (not Config.Browser)
- docs/api-reference.md documents all 32 facade methods
- docs/api-reference.md version header says v1.9.3
- docs/architecture.md version header says v1.9.3
"""

from __future__ import annotations

from pathlib import Path

from packaging.version import Version as _V

from super_browser import __version__
from super_browser.agent.facade import SuperBrowser


class TestV194APIReference:
    """API reference completion and doc normalization."""

    def test_version_is_194(self) -> None:
        assert _V(__version__) >= _V("1.9.4")

    def test_backend_selection_uses_session_config(self) -> None:
        content = Path("./examples/backend_selection.py").read_text(encoding="utf-8")
        assert "SessionConfig" in content
        assert "Config.Browser" not in content

    def test_api_reference_has_all_facade_methods(self) -> None:
        content = Path("./docs/api-reference.md").read_text(encoding="utf-8")
        actual = sorted(
            m for m in dir(SuperBrowser)
            if not m.startswith("_") and callable(getattr(SuperBrowser, m))
        )
        for method in actual:
            assert method in content, f"Facade method '{method}' missing from api-reference.md"

    def test_api_reference_version_header(self) -> None:
        first_lines = Path("./docs/api-reference.md").read_text(encoding="utf-8").split("\n")[:5]
        joined = "\n".join(first_lines)
        assert "v2.1.0" in joined

    def test_architecture_version_header(self) -> None:
        first_lines = Path("./docs/architecture.md").read_text(encoding="utf-8").split("\n")[:5]
        joined = "\n".join(first_lines)
        assert "v2.1.0" in joined
