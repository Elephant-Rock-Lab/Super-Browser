"""Tests for typed result payloads."""

from dataclasses import asdict

from super_browser.results import (
    ActionMethod,
    ClickResult,
    CompletionReason,
    DelegatedResult,
    FillResult,
    JSEvalResult,
    NavigateResult,
    ScreenshotResult,
    SelectResult,
    SpilledResult,
    action_result,
)


class TestClickResult:
    def test_serialization(self):
        cr = ClickResult(target="#btn", method=ActionMethod.SELECTOR, coordinates=(100.0, 200.0))
        d = asdict(cr)
        assert d["target"] == "#btn"
        assert d["method"] == ActionMethod.SELECTOR
        assert d["coordinates"] == (100.0, 200.0)

    def test_in_action_result(self):
        cr = ClickResult(target="a", method=ActionMethod.COORDINATE)
        r = action_result(ok=True, data=cr, method=ActionMethod.COORDINATE)
        d = r.to_dict()
        assert d["data"]["target"] == "a"
        assert d["data"]["method"] == "coordinate"


class TestNavigateResult:
    def test_redirect_chain(self):
        nr = NavigateResult(
            url="http://a.com", final_url="https://b.com",
            redirect_chain=["http://a.com", "https://b.com"],
        )
        d = asdict(nr)
        assert len(d["redirect_chain"]) == 2


class TestFillResult:
    def test_method_field(self):
        fr = FillResult(selector="#email", value_entered="test@test.com", method=ActionMethod.VISION)
        assert fr.method == ActionMethod.VISION


class TestJSEvalResult:
    def test_complex_types(self):
        jr = JSEvalResult(expression="1+1", result_type="number", result=2, console_errors=["warn"])
        d = asdict(jr)
        assert d["result"] == 2
        assert d["console_errors"] == ["warn"]


class TestDelegatedResult:
    def test_completion_reason(self):
        dr = DelegatedResult(
            instruction="search", completion_reason=CompletionReason.BUDGET_EXHAUSTED,
            summary="ran out", steps_executed=5, budget_remaining=0.0,
        )
        d = asdict(dr)
        assert d["completion_reason"] == "budget_exhausted"


class TestSpilledResult:
    def test_fields(self):
        sr = SpilledResult(preview="abc", file_path="/tmp/x.json", original_type="ExtractResult", original_size_chars=1000)
        assert sr.preview == "abc"
        assert sr.original_size_chars == 1000


class TestSelectResult:
    def test_fields(self):
        sr = SelectResult(selector="#sel", option="Option A", method=ActionMethod.SELECTOR, by="text")
        d = asdict(sr)
        assert d["by"] == "text"


class TestScreenshotResult:
    def test_hash_format(self):
        sr = ScreenshotResult(image_hash="a" * 64, width=1280, height=720)
        assert len(sr.image_hash) == 64
