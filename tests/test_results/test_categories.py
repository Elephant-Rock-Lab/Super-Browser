"""BATCH-40/TASK-01 — Result Category Taxonomy.

TEST-40-01-01 through TEST-40-01-12.
Validates SuccessCategory, FailureCategory, NextAction,
and ActionResult extensions.
"""

from super_browser.results import (
    ActionResult,
    ErrorCategory,
    FailureCategory,
    NextAction,
    SuccessCategory,
    action_result,
)
from super_browser.results.types import ResultMeta

# ── TEST-40-01-01: SuccessCategory enum has 5 values ──────────────────────

def test_40_01_01_success_category_values():
    """SuccessCategory must contain exactly the 5 specified members."""
    members = list(SuccessCategory)
    assert len(members) == 5
    assert SuccessCategory.NAVIGATION == "navigation"
    assert SuccessCategory.MUTATION == "mutation"
    assert SuccessCategory.INSPECTION == "inspection"
    assert SuccessCategory.ARTIFACT == "artifact"
    assert SuccessCategory.UNCHANGED == "unchanged"


# ── TEST-40-01-02: FailureCategory is superset of ErrorCategory ────────────

def test_40_01_02_failure_category_superset_of_error_category():
    """All 8 ErrorCategory values must be present in FailureCategory by name."""
    error_values = {ec.value for ec in ErrorCategory}
    failure_values = {fc.value for fc in FailureCategory}
    assert error_values.issubset(failure_values), (
        f"Missing: {error_values - failure_values}"
    )
    assert len(list(ErrorCategory)) == 8  # sanity: 8 originals


# ── TEST-40-01-03: FailureCategory has STALE_REF ───────────────────────────

def test_40_01_03_failure_category_stale_ref():
    """FailureCategory must include STALE_REF with value 'stale_ref'."""
    assert hasattr(FailureCategory, "STALE_REF")
    assert FailureCategory.STALE_REF == "stale_ref"


# ── TEST-40-01-04: FailureCategory has ELEMENT_OBSCURED ────────────────────

def test_40_01_04_failure_category_element_obscured():
    """FailureCategory must include ELEMENT_OBSCURED with value 'element_obscured'."""
    assert hasattr(FailureCategory, "ELEMENT_OBSCURED")
    assert FailureCategory.ELEMENT_OBSCURED == "element_obscured"


# ── TEST-40-01-05: ActionResult has result_category field ──────────────────

def test_40_01_05_action_result_has_result_category():
    """ActionResult(ok=True) via factory must set result_category to 'success'."""
    r = action_result(ok=True)
    assert hasattr(r, "result_category")
    assert r.result_category == "success"


# ── TEST-40-01-06: ActionResult ok=True has success_category ───────────────

def test_40_01_06_success_category_on_ok_result():
    """ActionResult with ok=True can carry a success_category."""
    r = ActionResult(
        ok=True,
        meta=ResultMeta(trace_id="t", duration_ms=0.0),
        success_category=SuccessCategory.NAVIGATION,
    )
    assert r.success_category == SuccessCategory.NAVIGATION


# ── TEST-40-01-07: ActionResult ok=False has failure_category ──────────────

def test_40_01_07_failure_category_on_error_result():
    """ActionResult with ok=False can carry a failure_category."""
    r = action_result(ok=False)
    r.failure_category = FailureCategory.STALE_REF
    assert r.failure_category == FailureCategory.STALE_REF


# ── TEST-40-01-08: NextAction dataclass has required fields ────────────────

def test_40_01_08_next_action_fields():
    """NextAction must have action_id and description fields."""
    na = NextAction(action_id="refresh_snapshot", description="Re-snapshot the page")
    assert na.action_id == "refresh_snapshot"
    assert na.description == "Re-snapshot the page"
    assert na.compiled_args is None


# ── TEST-40-01-09: ActionResult has next_actions field ─────────────────────

def test_40_01_09_next_actions_on_result():
    """ActionResult can carry a list of NextAction suggestions."""
    actions = [
        NextAction(action_id="retry", description="Retry the action"),
        NextAction(action_id="fallback", description="Use coordinate tier",
                   compiled_args={"x": 100, "y": 200}),
    ]
    r = ActionResult(
        ok=False,
        meta=ResultMeta(trace_id="t", duration_ms=0.0),
        next_actions=actions,
    )
    assert r.next_actions is not None
    assert len(r.next_actions) == 2
    assert r.next_actions[1].compiled_args == {"x": 100, "y": 200}


# ── TEST-40-01-10: to_dict includes all new fields ─────────────────────────

def test_40_01_10_to_dict_includes_new_fields():
    """to_dict() must serialize all new BATCH-40 fields."""
    r = ActionResult(
        ok=True,
        meta=ResultMeta(trace_id="t", duration_ms=0.0),
        result_category="success",
        success_category=SuccessCategory.INSPECTION,
        next_actions=[NextAction(action_id="none", description="N/A")],
    )
    d = r.to_dict()
    assert "result_category" in d
    assert d["result_category"] == "success"
    assert "success_category" in d
    assert d["success_category"] == "inspection"
    assert "failure_category" in d
    assert d["failure_category"] is None
    assert "next_actions" in d
    assert len(d["next_actions"]) == 1
    assert d["next_actions"][0]["action_id"] == "none"
    assert "page_change_summary" in d
    assert d["page_change_summary"] is None


# ── TEST-40-01-11: from_dict round-trips all new fields ────────────────────

def test_40_01_11_from_dict_round_trip():
    """from_dict(to_dict()) must preserve all new fields."""
    original = ActionResult(
        ok=False,
        meta=ResultMeta(trace_id="trace-42", duration_ms=1.5),
        result_category="failure",
        failure_category=FailureCategory.RATE_LIMITED,
        next_actions=[
            NextAction(action_id="backoff", description="Wait and retry",
                       compiled_args={"delay_s": 5}),
        ],
    )
    d = original.to_dict()
    restored = ActionResult.from_dict(d)

    assert restored.result_category == "failure"
    assert restored.failure_category == FailureCategory.RATE_LIMITED
    assert restored.success_category is None
    assert restored.next_actions is not None
    assert len(restored.next_actions) == 1
    assert restored.next_actions[0].action_id == "backoff"
    assert restored.next_actions[0].compiled_args == {"delay_s": 5}
    assert restored.page_change_summary is None


# ── TEST-40-01-12: Backward compat — old dict still works ──────────────────

def test_40_01_12_backward_compat_old_dict():
    """An old-style dict without new keys must deserialize without error."""
    old = {
        "ok": True,
        "data": None,
        "error": None,
        "meta": {
            "trace_id": "legacy",
            "duration_ms": 0.0,
            "method": None,
            "screenshot_hash": None,
            "token_cost": 0.0,
            "timestamp": 1000000.0,
        },
    }
    r = ActionResult.from_dict(old)
    assert r.ok is True
    assert r.result_category is None
    assert r.success_category is None
    assert r.failure_category is None
    assert r.next_actions is None
    assert r.page_change_summary is None
