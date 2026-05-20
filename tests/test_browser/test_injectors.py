"""Tests for BATCH-49/TASK-02 — StealthInjector implementations.

TEST-49-02-01 through TEST-49-02-10 as specified in Blueprint v1.1.
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from super_browser.browser.engine import EngineCapabilities, InjectionTiming, StealthInjector
from super_browser.browser.injectors import (
    BiDiInjector,
    CDPInjector,
    PageScriptInjector,
    select_injector,
)

# ---------------------------------------------------------------------------
# TEST-49-02-01: CDPInjector implements StealthInjector
# ---------------------------------------------------------------------------


class TestCDPInjectorProtocol:
    """TEST-49-02-01 — CDPInjector satisfies StealthInjector protocol."""

    def test_isinstance_stealth_injector(self) -> None:
        """CDPInjector is recognised as a StealthInjector at runtime."""
        injector = CDPInjector()
        assert isinstance(injector, StealthInjector)

    def test_has_required_methods(self) -> None:
        """CDPInjector exposes inject_before_load, inject_after_load, injection_timing."""
        injector = CDPInjector()
        assert hasattr(injector, "inject_before_load")
        assert hasattr(injector, "inject_after_load")
        assert hasattr(injector, "injection_timing")


# ---------------------------------------------------------------------------
# TEST-49-02-02: PageScriptInjector implements StealthInjector
# ---------------------------------------------------------------------------


class TestPageScriptInjectorProtocol:
    """TEST-49-02-02 — PageScriptInjector satisfies StealthInjector protocol."""

    def test_isinstance_stealth_injector(self) -> None:
        """PageScriptInjector is recognised as a StealthInjector at runtime."""
        injector = PageScriptInjector()
        assert isinstance(injector, StealthInjector)

    def test_has_required_methods(self) -> None:
        """PageScriptInjector exposes all StealthInjector members."""
        injector = PageScriptInjector()
        assert hasattr(injector, "inject_before_load")
        assert hasattr(injector, "inject_after_load")
        assert hasattr(injector, "injection_timing")


# ---------------------------------------------------------------------------
# TEST-49-02-03: CDPInjector timing is BEFORE
# ---------------------------------------------------------------------------


class TestCDPInjectorTiming:
    """TEST-49-02-03 — CDPInjector.injection_timing == BEFORE."""

    def test_timing_is_before(self) -> None:
        injector = CDPInjector()
        assert injector.injection_timing == InjectionTiming.BEFORE


# ---------------------------------------------------------------------------
# TEST-49-02-04: PageScriptInjector timing is AFTER
# ---------------------------------------------------------------------------


class TestPageScriptInjectorTiming:
    """TEST-49-02-04 — PageScriptInjector.injection_timing == AFTER."""

    def test_timing_is_after(self) -> None:
        injector = PageScriptInjector()
        assert injector.injection_timing == InjectionTiming.AFTER


# ---------------------------------------------------------------------------
# TEST-49-02-05: select_injector CDP path
# ---------------------------------------------------------------------------


class TestSelectInjectorCDP:
    """TEST-49-02-05 — select_injector returns CDPInjector when CDP available."""

    def test_returns_cdp_injector(self) -> None:
        caps = EngineCapabilities(cdp=True)
        injector = select_injector(caps)
        assert isinstance(injector, CDPInjector)

    def test_cdp_preferred_over_bidi(self) -> None:
        """CDP takes precedence even when BiDi is also available."""
        caps = EngineCapabilities(cdp=True, bidi=True)
        injector = select_injector(caps)
        assert isinstance(injector, CDPInjector)


# ---------------------------------------------------------------------------
# TEST-49-02-06: select_injector fallback
# ---------------------------------------------------------------------------


class TestSelectInjectorFallback:
    """TEST-49-02-06 — select_injector returns PageScriptInjector as fallback."""

    def test_returns_page_injector_when_no_cdp(self) -> None:
        caps = EngineCapabilities(cdp=False, bidi=False)
        injector = select_injector(caps)
        assert isinstance(injector, PageScriptInjector)

    def test_bidi_returns_bidi_injector(self) -> None:
        """BiDi without CDP returns BiDiInjector (not page fallback)."""
        caps = EngineCapabilities(cdp=False, bidi=True)
        injector = select_injector(caps)
        assert isinstance(injector, BiDiInjector)


# ---------------------------------------------------------------------------
# TEST-49-02-07: BiDiInjector stub importable
# ---------------------------------------------------------------------------


class TestBiDiInjectorImport:
    """TEST-49-02-07 — BiDiInjector is importable and raises NotImplementedError."""

    def test_importable(self) -> None:
        injector = BiDiInjector()
        assert injector is not None

    @pytest.mark.asyncio
    async def test_before_raises(self) -> None:
        injector = BiDiInjector()
        with pytest.raises(NotImplementedError):
            await injector.inject_before_load("")

    @pytest.mark.asyncio
    async def test_after_raises(self) -> None:
        injector = BiDiInjector()
        with pytest.raises(NotImplementedError):
            await injector.inject_after_load("")

    def test_timing_is_both(self) -> None:
        injector = BiDiInjector()
        assert injector.injection_timing == InjectionTiming.BOTH


# ---------------------------------------------------------------------------
# TEST-49-02-08: select_injector None capabilities
# ---------------------------------------------------------------------------


class TestSelectInjectorNone:
    """TEST-49-02-08 — select_injector with None capabilities returns fallback."""

    def test_none_capabilities(self) -> None:
        injector = select_injector(None)
        assert isinstance(injector, PageScriptInjector)

    def test_default_capabilities(self) -> None:
        """Default EngineCapabilities (all False) → PageScriptInjector."""
        caps = EngineCapabilities()
        injector = select_injector(caps)
        assert isinstance(injector, PageScriptInjector)


# ---------------------------------------------------------------------------
# TEST-49-02-09: CDPInjector wraps InjectDelivery
# ---------------------------------------------------------------------------


class TestCDPInjectorDelegation:
    """TEST-49-02-09 — CDPInjector wraps InjectDelivery (delegates)."""

    @pytest.mark.asyncio
    async def test_creates_delivery_on_inject_before(self) -> None:
        """inject_before_load creates an InjectDelivery instance."""
        injector = CDPInjector()
        assert injector.delivery is None

        await injector.inject_before_load("window.foo = 1")

        assert injector.delivery is not None
        # The delivery object should be an InjectDelivery instance
        from super_browser.stealth.consistency.inject_delivery import InjectDelivery

        assert isinstance(injector.delivery, InjectDelivery)

    @pytest.mark.asyncio
    async def test_inject_after_delegates_to_delivery(self) -> None:
        """inject_after_load delegates to InjectDelivery._install_add_init_script."""
        injector = CDPInjector()
        await injector.inject_before_load("window.foo = 1")

        # Mock the delivery's _install_add_init_script to verify delegation
        injector._delivery._install_add_init_script = AsyncMock()

        await injector.inject_after_load("/* extra */")

        injector._delivery._install_add_init_script.assert_awaited_once()


# ---------------------------------------------------------------------------
# TEST-49-02-10: select_injector return type
# ---------------------------------------------------------------------------


class TestSelectInjectorReturnType:
    """TEST-49-02-10 — select_injector always returns a StealthInjector."""

    @pytest.mark.parametrize(
        "caps",
        [
            EngineCapabilities(cdp=True),
            EngineCapabilities(bidi=True),
            EngineCapabilities(cdp=False, bidi=False),
            None,
        ],
        ids=["cdp", "bidi", "fallback", "none"],
    )
    def test_all_paths_return_stealth_injector(self, caps) -> None:
        injector = select_injector(caps)
        assert isinstance(injector, StealthInjector)
