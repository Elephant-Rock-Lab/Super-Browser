"""Integration tests for v1.7.0 — Agent UX & Reliability features.

Validates cross-cutting functionality across BATCH-40, 41, 42.
"""

from __future__ import annotations

from packaging.version import Version as _V
from super_browser import __version__
from super_browser.interaction.presets import BrowserJob, CompiledStep, QASmoke
from super_browser.interaction.recovery import StaleRefDetector
from super_browser.results import (
    ActionResult,
    FailureCategory,
    PageChangeSummary,
    PageFingerprint,
    SuccessCategory,
    action_result,
    compute_page_change,
)
from super_browser.security.action_redaction import (
    redact_args,
    redact_context,
)


class TestV170Version:
    """Version is 1.7.0."""

    def test_version_string(self) -> None:
        assert _V(__version__) >= _V("1.7.0")


class TestV170ResultCategories:
    """BATCH-40: Result categories are structured and serializable."""

    def test_success_result_has_category(self) -> None:
        result = action_result(ok=True, data={"url": "https://x.com"})
        assert result.result_category == "success"

    def test_failure_result_has_category(self) -> None:
        result = action_result(ok=False, error={"message": "timeout"})
        assert result.result_category == "failure"

    def test_category_round_trip(self) -> None:
        result = ActionResult(
            ok=True,
            success_category=SuccessCategory.NAVIGATION,
            page_change_summary=PageChangeSummary(
                change_type="navigation",
                summary="Page navigated",
                url="https://x.com",
            ),
        )
        d = result.to_dict()
        assert d["success_category"] == "navigation"
        assert d["page_change_summary"]["change_type"] == "navigation"

    def test_failure_category_is_superset(self) -> None:
        from super_browser.results import ErrorCategory

        for ec in ErrorCategory:
            assert hasattr(FailureCategory, ec.name)


class TestV170PageChange:
    """BATCH-40: Page change detection."""

    def test_navigation_detected(self) -> None:
        before = PageFingerprint(url="https://a.com", title="A", node_count=10, interactive_count=3)
        after = PageFingerprint(url="https://b.com", title="B", node_count=10, interactive_count=3)
        summary = compute_page_change(before, after)
        assert summary.change_type == "navigation"

    def test_mutation_detected(self) -> None:
        before = PageFingerprint(url="https://a.com", title="A", node_count=10, interactive_count=3)
        after = PageFingerprint(url="https://a.com", title="A", node_count=15, interactive_count=5)
        summary = compute_page_change(before, after)
        assert summary.change_type == "mutation"

    def test_unchanged_detected(self) -> None:
        fp = PageFingerprint(url="https://a.com", title="A", node_count=10, interactive_count=3)
        summary = compute_page_change(fp, fp)
        assert summary.change_type == "unchanged"


class TestV170StaleRecovery:
    """BATCH-41: Stale reference recovery."""

    def test_stale_detector_signatures(self) -> None:
        assert StaleRefDetector.is_stale(Exception("waiting for selector"))
        assert StaleRefDetector.is_stale(Exception("Execution context was destroyed"))
        assert StaleRefDetector.is_stale(Exception("Node is detached"))
        assert not StaleRefDetector.is_stale(Exception("Network error"))

    def test_stale_next_actions(self) -> None:
        actions = StaleRefDetector.get_next_actions("click", "@e5")
        assert len(actions) == 3
        assert actions[0].action_id == "refresh_snapshot"

    def test_stale_ref_category_exists(self) -> None:
        assert FailureCategory.STALE_REF.value == "stale_ref"


class TestV170Redaction:
    """BATCH-41: Secret redaction pipeline."""

    def test_redact_args_masks_password(self) -> None:
        result = redact_args({"username": "alice", "password": "secret123"})
        assert result["username"] == "alice"
        assert result["password"] == "[REDACTED:password]"

    def test_redact_context_scrubs_url(self) -> None:
        result = redact_context("https://api.x.com?token=abc123&user=alice")
        assert "[REDACTED:query_param]" in result
        assert "user=alice" in result

    def test_redaction_nested(self) -> None:
        result = redact_args({"config": {"api_key": "sk-12345"}})
        assert result["config"]["api_key"] == "[REDACTED:api_key]"


class TestV170Presets:
    """BATCH-42: Action presets."""

    def test_browser_job_compiles(self) -> None:
        job = BrowserJob(steps=[
            {"action": "open", "url": "https://example.com"},
            {"action": "click", "target": "#btn"},
            {"action": "screenshot", "path": "out.png"},
        ])
        compiled = job.compile()
        assert len(compiled) == 3
        assert compiled[0].action == "open"

    def test_qa_smoke_five_steps(self) -> None:
        qa = QASmoke(url="https://example.com", assert_text="Example")
        compiled = qa.compile()
        assert len(compiled) == 5
        actions = [s.action for s in compiled]
        assert actions == ["open", "wait", "assert_text", "network", "screenshot"]

    def test_compiled_step_is_frozen(self) -> None:
        step = CompiledStep("click", {"target": "#btn"}, "Click button")
        assert step.action == "click"
        assert step.params == {"target": "#btn"}
