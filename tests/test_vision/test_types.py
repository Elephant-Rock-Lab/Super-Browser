"""Tests for vision types — enums, dataclasses, configuration."""

from super_browser.vision.types import (
    CaptchaSolution,
    CaptchaType,
    CascadeConfig,
    OCRWord,
    StateInference,
    VisionCacheEntry,
    VisionCostTracker,
    VisionLocation,
    VisionProviderName,
    VisionTaskComplexity,
)


class TestVisionTaskComplexity:
    def test_values(self):
        assert VisionTaskComplexity.SIMPLE == "simple"
        assert VisionTaskComplexity.COMPLEX == "complex"
        assert VisionTaskComplexity.AMBIGUOUS == "ambiguous"
        assert len(VisionTaskComplexity) == 3


class TestCaptchaType:
    def test_values(self):
        assert CaptchaType.TEXT_DISTORTED == "text_distorted"
        assert CaptchaType.IMAGE_GRID == "image_grid"
        assert CaptchaType.RECAPTCHA_V2 == "recaptcha_v2"
        assert CaptchaType.HCAPTCHA == "hcaptcha"
        assert CaptchaType.SLIDER == "slider"
        assert len(CaptchaType) == 5


class TestVisionProviderName:
    def test_values(self):
        assert VisionProviderName.ANTHROPIC == "anthropic"
        assert VisionProviderName.OPENAI == "openai"
        assert VisionProviderName.UITARS == "uitars"
        assert len(VisionProviderName) == 3


class TestVisionLocation:
    def test_construction(self):
        loc = VisionLocation(x=100.0, y=200.0)
        assert loc.x == 100.0
        assert loc.y == 200.0
        assert loc.width is None
        assert loc.confidence == 0.0

    def test_with_bbox(self):
        loc = VisionLocation(x=150.0, y=250.0, width=100, height=40, confidence=0.9)
        assert loc.width == 100
        assert loc.confidence == 0.9

    def test_frozen(self):
        loc = VisionLocation(x=1, y=2)
        try:
            loc.x = 99  # type: ignore
            assert False
        except AttributeError:
            pass


class TestCaptchaSolution:
    def test_basic(self):
        sol = CaptchaSolution(solved=True, answer="ABC123")
        assert sol.solved
        assert sol.answer == "ABC123"
        assert sol.grid_selections is None

    def test_grid(self):
        sol = CaptchaSolution(solved=True, grid_selections=[0, 3, 6])
        assert sol.grid_selections == [0, 3, 6]


class TestStateInference:
    def test_basic(self):
        si = StateInference(answer="There is an error", labels={"has_error": True}, confidence=0.85)
        assert si.labels["has_error"]
        assert si.confidence == 0.85


class TestOCRWord:
    def test_construction(self):
        w = OCRWord(text="Submit", x=10, y=20, width=80, height=30, confidence=0.95)
        assert w.text == "Submit"
        assert w.confidence == 0.95


class TestCascadeConfig:
    def test_defaults(self):
        c = CascadeConfig()
        assert c.simple_provider == VisionProviderName.UITARS
        assert c.complex_provider == VisionProviderName.OPENAI
        assert c.ambiguous_provider == VisionProviderName.ANTHROPIC
        assert c.confidence_threshold_for_escalation == 0.6
        assert c.max_escalations == 2

    def test_custom(self):
        c = CascadeConfig(simple_provider=VisionProviderName.OPENAI, complex_model="gpt-4o")
        assert c.simple_provider == VisionProviderName.OPENAI
        assert c.complex_model == "gpt-4o"


class TestVisionCacheEntry:
    def test_construction(self):
        e = VisionCacheEntry(key="abc", description="button", response=None, image_dhash=123)
        assert e.key == "abc"
        assert e.hit_count == 0
        assert e.image_dhash == 123


class TestVisionCostTracker:
    def test_accumulation(self):
        t = VisionCostTracker()
        t.record(0.01)
        t.record(0.02)
        assert t.total_cost == 0.03
        assert t.call_count == 2

    def test_initial(self):
        t = VisionCostTracker()
        assert t.total_cost == 0.0
        assert t.call_count == 0
