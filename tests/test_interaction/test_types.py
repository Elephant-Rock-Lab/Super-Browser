"""Tests for interaction types."""

from super_browser.interaction.types import (
    AXNode,
    AXSnapshot,
    CascadeResult,
    Tier,
    TierAttempt,
    TierOutcome,
    VisionRequest,
    VisionResponse,
)


class TestTier:
    def test_ordering(self):
        assert Tier.SELECTOR < Tier.COORDINATE < Tier.VISION

    def test_values(self):
        assert Tier.SELECTOR == 1
        assert Tier.COORDINATE == 2
        assert Tier.VISION == 3

    def test_iteration(self):
        tiers = list(Tier)
        assert len(tiers) == 3


class TestTierOutcome:
    def test_values(self):
        assert TierOutcome.SUCCESS == "success"
        assert TierOutcome.FAILED == "failed"
        assert TierOutcome.SKIPPED == "skipped"
        assert TierOutcome.UNAVAILABLE == "unavailable"


class TestTierAttempt:
    def test_frozen(self):
        a = TierAttempt(Tier.SELECTOR, TierOutcome.SUCCESS, 10.0)
        assert a.tier == Tier.SELECTOR
        assert a.coordinates is None

    def test_with_coordinates(self):
        a = TierAttempt(Tier.COORDINATE, TierOutcome.SUCCESS, 5.0, coordinates=(100.0, 200.0))
        assert a.coordinates == (100.0, 200.0)


class TestCascadeResult:
    def test_all_failed(self):
        attempts = (
            TierAttempt(Tier.SELECTOR, TierOutcome.FAILED, 10.0, error="not found"),
            TierAttempt(Tier.COORDINATE, TierOutcome.FAILED, 5.0, error="no bbox"),
        )
        c = CascadeResult("click", "button", attempts)
        assert c.succeeded_tier is None
        assert len(c.attempts) == 2

    def test_success(self):
        attempts = (TierAttempt(Tier.SELECTOR, TierOutcome.SUCCESS, 5.0),)
        c = CascadeResult("click", "button", attempts, succeeded_tier=Tier.SELECTOR)
        assert c.succeeded_tier == Tier.SELECTOR


class TestAXNode:
    def test_center_with_bounds(self):
        node = AXNode(ref="@e0", role="button", name="OK", bounds=(10.0, 20.0, 100.0, 40.0))
        assert node.center == (60.0, 40.0)

    def test_center_without_bounds(self):
        node = AXNode(ref="@e1", role="button", name="OK")
        assert node.center is None

    def test_is_interactive(self):
        assert AXNode(ref="@e0", role="button", name="X").is_interactive
        assert AXNode(ref="@e0", role="link", name="X").is_interactive
        assert AXNode(ref="@e0", role="textbox", name="X").is_interactive
        assert not AXNode(ref="@e0", role="generic", name="X").is_interactive
        assert not AXNode(ref="@e0", role="heading", name="X").is_interactive


class TestAXSnapshot:
    def _make_snapshot(self):
        nodes = {
            "e0": AXNode(ref="@e0", role="button", name="Login"),
            "e1": AXNode(ref="@e1", role="link", name="Home", url="/"),
            "e2": AXNode(ref="@e2", role="textbox", name="Email", value=""),
            "e3": AXNode(ref="@e3", role="generic", name=""),
        }
        return AXSnapshot(url="https://example.com", title="Test", nodes=nodes)

    def test_resolve(self):
        snap = self._make_snapshot()
        assert snap.resolve("@e0") is not None
        assert snap.resolve("@e0").name == "Login"
        assert snap.resolve("e0").name == "Login"
        assert snap.resolve("@e99") is None

    def test_find_by_text(self):
        snap = self._make_snapshot()
        results = snap.find_by_text("login")
        assert len(results) == 1
        assert results[0].role == "button"

    def test_find_by_role(self):
        snap = self._make_snapshot()
        results = snap.find_by_role("link")
        assert len(results) == 1
        assert results[0].name == "Home"

    def test_to_compact_str(self):
        snap = self._make_snapshot()
        s = snap.to_compact_str()
        assert '[@e0] button "Login"' in s
        assert "url=/" in s
        assert "[@e2] textbox" in s


class TestVisionTypes:
    def test_request_frozen(self):
        req = VisionRequest(screenshot=b"png", element_description="button", page_url="https://x.com", viewport_size=(800, 600))
        assert req.viewport_size == (800, 600)

    def test_response_defaults(self):
        resp = VisionResponse(found=False)
        assert resp.x is None
        assert resp.confidence == 0.0
        assert resp.token_cost == 0.0

    def test_response_found(self):
        resp = VisionResponse(found=True, x=100.0, y=200.0, confidence=0.95, model="test")
        assert resp.x == 100.0
