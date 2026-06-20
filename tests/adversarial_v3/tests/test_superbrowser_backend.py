"""Real-backend smoke tests for SuperBrowserBackend.

These tests instantiate the *real* SuperBrowserBackend against the SDK
checked out in this repository (not the stub, not a published package).
They are the merge gate for PR #172: every advertised backend path must
be exercised at least once so that constructor mismatches, wrong
lifecycle methods, and missing evaluation surfaces fail loudly here
rather than silently certifying a broken manual CI run.

Gating:
    Skipped unless SB_AD3_SMOKE=1 is set, because they launch a real
    browser (Patchright/Chromium). Run locally with:

        SB_AD3_SMOKE=1 PYTHONPATH=src python -m pytest \
            tests/adversarial_v3/tests/test_superbrowser_backend.py

    The offline CI lane does not set this var, so these tests are
    inert there. They exist to be run before merge and on the manual
    real-browser workflow.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from adversarial3.backends import SuperBrowserBackend
from adversarial3.core import BrowserBackend, Page

# Skip the whole module unless explicitly opted in. We do NOT auto-skip
# on import failure of super_browser: an ImportError here is itself a
# signal worth surfacing, not hiding.
_SMOKE_ON = os.environ.get("SB_AD3_SMOKE", "") == "1"
pytestmark = pytest.mark.skipif(
    not _SMOKE_ON,
    reason="Real-browser smoke test; set SB_AD3_SMOKE=1 to run",
)


class TestSuperBrowserBackendConstruction:
    """Construction + protocol compliance — no browser launched yet."""

    def test_is_browser_backend(self):
        backend = SuperBrowserBackend()
        assert isinstance(backend, BrowserBackend)

    def test_is_superbrowser_not_stub(self):
        from adversarial3.backends import StubBackend

        backend = SuperBrowserBackend()
        assert not isinstance(backend, StubBackend)
        assert backend.__class__.__name__ == "SuperBrowserBackend"


class TestSuperBrowserBackendLifecycle:
    """Exercises __aenter__/__aexit__ — the path that calls the SDK.

    This is where PR #172 fails today: the backend builds
    ``Config(session=...)`` but the SDK's ``Config`` has no ``session``
    field (it is ``browser=``), so ``__aenter__`` raises ``TypeError``
    before any browser launches. The assertions below pin that
    contract: if the constructor shape drifts again, this test breaks
    before the manual workflow can certify a broken run.
    """

    @pytest.mark.asyncio
    async def test_enter_exit_roundtrip(self):
        backend = SuperBrowserBackend(headless=True)
        async with backend:
            # If __aenter__ succeeded, the SDK accepted the config.
            assert backend._sb is not None
        # __aexit__ must tear down without raising. If the backend
        # calls a non-existent facade method (e.g. close() instead of
        # stop()), the context-manager exit raises here.
        assert backend._sb is None

    @pytest.mark.asyncio
    async def test_enter_is_idempotent_safe(self):
        # Entering, exiting, then the object going out of scope must
        # not raise. Guards against double-stop / use-after-stop bugs
        # in the lifecycle wiring.
        async with SuperBrowserBackend(headless=True):
            pass


class TestSuperBrowserBackendPage:
    """Exercises new_page / goto / evaluate against a live browser.

    These are the highest-value assertions in the suite: they prove the
    page adapter actually talks to a real page. PR #172's adapter calls
    ``sb.evaluate(expr)`` which does not exist on the facade, and passes
    ``wait_until=`` to ``navigate()`` which the facade does not accept
    as a keyword — both surface here.
    """

    @pytest.mark.asyncio
    async def test_new_page_is_page(self):
        async with SuperBrowserBackend(headless=True) as backend:
            page = await backend.new_page()
            assert isinstance(page, Page)

    @pytest.mark.asyncio
    async def test_goto_sets_url(self):
        async with SuperBrowserBackend(headless=True) as backend:
            page = await backend.new_page()
            await page.goto("https://example.com", wait_until="domcontentloaded")
            assert page.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_evaluate_returns_real_value(self):
        # The decisive evaluation test. A working adapter returns the
        # actual JS value; a broken one raises AttributeError or returns
        # a result wrapper instead of a primitive.
        async with SuperBrowserBackend(headless=True) as backend:
            page = await backend.new_page()
            await page.goto("https://example.com", wait_until="domcontentloaded")
            result: Any = await page.evaluate("1 + 1")
            assert result == 2

    @pytest.mark.asyncio
    async def test_evaluate_reads_navigator(self):
        # Proves the adapter reads a real browser property, not a stub
        # value. navigator.userAgent is always a non-empty string in a
        # real Chromium.
        async with SuperBrowserBackend(headless=True) as backend:
            page = await backend.new_page()
            await page.goto("https://example.com", wait_until="domcontentloaded")
            ua = await page.evaluate("navigator.userAgent")
            assert isinstance(ua, str) and len(ua) > 0
