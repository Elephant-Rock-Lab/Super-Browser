"""Tests for SnapshotProvider."""

import asyncio
from unittest.mock import AsyncMock

from super_browser.browser.cdp import CDPResult
from super_browser.interaction.snapshot import SnapshotProvider
from super_browser.interaction.types import AXNode, AXSnapshot


def _make_cdp_with_ax_tree(nodes=None):
    """Create a mock CDP that returns AX tree data."""
    if nodes is None:
        nodes = [
            {
                "nodeId": "1",
                "role": {"type": "role", "value": "button"},
                "name": {"type": "string", "value": "Login"},
                "properties": [
                    {"name": "bounds", "value": {"type": "object", "value": [
                        {"name": "x", "value": {"type": "number", "value": 10}},
                        {"name": "y", "value": {"type": "number", "value": 20}},
                        {"name": "width", "value": {"type": "number", "value": 100}},
                        {"name": "height", "value": {"type": "number", "value": 40}},
                    ]}},
                    {"name": "focused", "value": {"type": "boolean", "value": "false"}},
                ],
            },
            {
                "nodeId": "2",
                "role": {"type": "role", "value": "link"},
                "name": {"type": "string", "value": "Home"},
                "properties": [
                    {"name": "url", "value": {"type": "string", "value": "/"}},
                ],
            },
            {
                "nodeId": "3",
                "role": {"type": "role", "value": "generic"},
                "name": {"type": "string", "value": "div"},
            },
            {
                "nodeId": "4",
                "role": {"type": "role", "value": "textbox"},
                "name": {"type": "string", "value": "Email"},
                "value": {"type": "string", "value": ""},
                "properties": [
                    {"name": "description", "value": {"type": "string", "value": "Enter your email"}},
                    {"name": "disabled", "value": {"type": "boolean", "value": "true"}},
                ],
            },
        ]

    cdp = AsyncMock()
    cdp.send = AsyncMock(return_value=CDPResult(
        ok=True, data={"nodes": nodes}, error=None, method="Accessibility.getFullAXTree", duration_ms=10.0,
    ))
    return cdp


class TestCaptureAXOnly:
    def test_basic_capture(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://example.com", "Test")
            assert snap.url == "https://example.com"
            assert snap.title == "Test"
            assert len(snap.nodes) == 3  # button, link, textbox (generic excluded)
        asyncio.run(_test())

    def test_interactive_nodes_only(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://x.com", "X")
            roles = {n.role for n in snap.nodes.values()}
            assert "generic" not in roles
            assert "button" in roles
            assert "link" in roles
        asyncio.run(_test())

    def test_ref_ids_sequential(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://x.com", "X")
            refs = sorted(snap.nodes.keys(), key=lambda x: int(x[1:]))
            assert refs == ["e0", "e1", "e2"]
        asyncio.run(_test())

    def test_bounds_parsing(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://x.com", "X")
            btn = snap.nodes["e0"]
            assert btn.bounds == (10.0, 20.0, 100.0, 40.0)
            assert btn.center == (60.0, 40.0)
        asyncio.run(_test())

    def test_properties_extracted(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://x.com", "X")
            link = snap.nodes["e1"]
            assert link.url == "/"
            textbox = snap.nodes["e2"]
            assert textbox.description == "Enter your email"
            assert textbox.disabled is True
        asyncio.run(_test())

    def test_empty_tree(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree(nodes=[])
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://x.com", "X")
            assert len(snap.nodes) == 0
            assert snap.token_count == 0
        asyncio.run(_test())

    def test_token_count_estimation(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://x.com", "X")
            assert snap.token_count == 30  # 3 nodes * 10
        asyncio.run(_test())

    def test_find_by_text_after_capture(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://x.com", "X")
            results = snap.find_by_text("login")
            assert len(results) == 1
            assert results[0].ref == "@e0"
        asyncio.run(_test())

    def test_to_compact_str(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_ax_only("https://x.com", "X")
            s = snap.to_compact_str()
            assert '[@e0] button "Login"' in s
            assert "[disabled]" in s  # textbox has disabled=True
        asyncio.run(_test())


class TestCaptureHybrid:
    def test_returns_ax_snapshot(self):
        async def _test():
            cdp = _make_cdp_with_ax_tree()
            provider = SnapshotProvider(cdp)
            snap = await provider.capture_hybrid("https://x.com", "X")
            assert isinstance(snap, AXSnapshot)
            assert snap.url == "https://x.com"
        asyncio.run(_test())
