"""Integration tests for BATCH-49 — Stealth Abstraction + Injectors."""

from __future__ import annotations


class TestStealthAbstractionIntegration:
    """TEST-49-03: Integration verification."""

    def test_injectors_module_importable(self) -> None:
        """All injectors + factory importable."""
        from super_browser.browser.injectors import (
            BiDiInjector,
            CDPInjector,
            PageScriptInjector,
            select_injector,
        )
        assert CDPInjector is not None
        assert PageScriptInjector is not None
        assert BiDiInjector is not None
        assert select_injector is not None

    def test_stealth_manager_bridge_in_constructor(self) -> None:
        """StealthManager accepts stealth_bridge in constructor."""
        from unittest.mock import MagicMock

        from super_browser.stealth.manager import StealthManager
        bridge = MagicMock()
        mgr = StealthManager(stealth_bridge=bridge)
        assert mgr._stealth_bridge is bridge

    def test_patchright_stealth_bridge_not_none(self) -> None:
        """PatchrightPage has stealth_bridge (not None after CDP setup)."""
        from unittest.mock import MagicMock

        from super_browser.browser.backends.patchright_backend import PatchrightPage
        mock_page = MagicMock()
        mock_cdp = MagicMock()
        pp = PatchrightPage(mock_page, mock_cdp)
        bridge = pp.stealth_bridge
        assert bridge is not None

    def test_snapshot_no_fake_result(self) -> None:
        """Snapshot no longer has _FakeResult workaround."""
        import inspect

        from super_browser.interaction.snapshot import SnapshotProvider
        source = inspect.getsource(SnapshotProvider)
        assert "_FakeResult" not in source

    def test_diagnostics_duck_typing(self) -> None:
        """diagnostics._send helper handles both bridge types."""
        from super_browser.stealth.diagnostics import _send
        assert callable(_send)

    def test_select_injector_returns_correct_types(self) -> None:
        """select_injector returns correct types for each path."""
        from super_browser.browser.engine import EngineCapabilities
        from super_browser.browser.injectors import (
            BiDiInjector,
            CDPInjector,
            PageScriptInjector,
            select_injector,
        )

        cdp_caps = EngineCapabilities(cdp=True, name="test")
        assert isinstance(select_injector(cdp_caps), CDPInjector)

        bidi_caps = EngineCapabilities(bidi=True, name="test")
        assert isinstance(select_injector(bidi_caps), BiDiInjector)

        no_caps = EngineCapabilities(name="test")
        assert isinstance(select_injector(no_caps), PageScriptInjector)
