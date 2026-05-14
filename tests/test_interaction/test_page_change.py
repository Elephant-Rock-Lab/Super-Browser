"""BATCH-40/TASK-02 — Page Change Summary.

TEST-40-02-01 through TEST-40-02-08.
Validates PageChangeSummary, PageFingerprint, compute_page_change(),
and ActionResult integration.
"""

from super_browser.results import (
    ActionResult,
    PageChangeSummary,
    PageFingerprint,
    compute_page_change,
)
from super_browser.results.types import ResultMeta

# ── TEST-40-02-01: PageChangeSummary dataclass exists ──────────────────────

def test_40_02_01_page_change_summary_dataclass():
    """PageChangeSummary must be instantiable with change_type and summary."""
    pcs = PageChangeSummary(change_type="navigation", summary="Page changed")
    assert pcs.change_type == "navigation"
    assert pcs.summary == "Page changed"
    assert pcs.title is None
    assert pcs.url is None
    assert pcs.artifact_hint is None


# ── TEST-40-02-02: ActionResult has page_change_summary ────────────────────

def test_40_02_02_action_result_has_page_change_summary():
    """ActionResult can carry a PageChangeSummary instance."""
    pcs = PageChangeSummary(
        change_type="mutation",
        summary="DOM mutated",
        title="New Page",
        url="https://example.com/page",
    )
    r = ActionResult(
        ok=True,
        meta=ResultMeta(trace_id="t", duration_ms=0.0),
        page_change_summary=pcs,
    )
    assert r.page_change_summary is not None
    assert r.page_change_summary.change_type == "mutation"
    assert r.page_change_summary.title == "New Page"


# ── TEST-40-02-03: Navigation detected when URL changes ────────────────────

def test_40_02_03_navigation_detected_on_url_change():
    """compute_page_change must return 'navigation' when URL differs."""
    before = PageFingerprint(
        url="https://example.com/a",
        title="Page A",
        node_count=100,
        interactive_count=10,
    )
    after = PageFingerprint(
        url="https://example.com/b",
        title="Page B",
        node_count=100,
        interactive_count=10,
    )
    result = compute_page_change(before, after)
    assert result.change_type == "navigation"
    assert "example.com/b" in result.summary
    assert result.url == "https://example.com/b"
    assert result.title == "Page B"


# ── TEST-40-02-04: Mutation detected when node_count changes ───────────────

def test_40_02_04_mutation_detected_on_node_count_change():
    """compute_page_change must return 'mutation' when node_count differs."""
    before = PageFingerprint(
        url="https://example.com/a",
        title="Page A",
        node_count=100,
        interactive_count=10,
    )
    after = PageFingerprint(
        url="https://example.com/a",
        title="Page A",
        node_count=95,
        interactive_count=10,
    )
    result = compute_page_change(before, after)
    assert result.change_type == "mutation"
    assert result.summary == "DOM mutated"


# ── TEST-40-02-05: No change when fingerprint identical ────────────────────

def test_40_02_05_unchanged_when_fingerprint_identical():
    """compute_page_change must return 'unchanged' when fingerprints match."""
    before = PageFingerprint(
        url="https://example.com/a",
        title="Page A",
        node_count=100,
        interactive_count=10,
    )
    after = PageFingerprint(
        url="https://example.com/a",
        title="Page A",
        node_count=100,
        interactive_count=10,
    )
    result = compute_page_change(before, after)
    assert result.change_type == "unchanged"
    assert result.summary == "No observable change"


# ── TEST-40-02-06: Summary includes title and url ──────────────────────────

def test_40_02_06_summary_includes_title_and_url():
    """Navigation summary must populate title and url fields."""
    before = PageFingerprint(
        url="https://old.com",
        title="Old",
        node_count=50,
        interactive_count=5,
    )
    after = PageFingerprint(
        url="https://new.com",
        title="New Title",
        node_count=60,
        interactive_count=8,
    )
    result = compute_page_change(before, after)
    assert result.title == "New Title"
    assert result.url == "https://new.com"


# ── TEST-40-02-07: artifact_hint set on screenshot actions ─────────────────

def test_40_02_07_artifact_hint_set():
    """compute_page_change must pass through artifact_hint."""
    before = PageFingerprint(
        url="https://example.com",
        title="Page",
        node_count=100,
        interactive_count=10,
    )
    after = PageFingerprint(
        url="https://example.com",
        title="Page",
        node_count=100,
        interactive_count=10,
    )
    result = compute_page_change(before, after, artifact_hint="screenshot")
    assert result.artifact_hint == "screenshot"
    assert result.change_type == "unchanged"


# ── TEST-40-02-08: Summary is None when not computed ───────────────────────

def test_40_02_08_summary_is_none_by_default():
    """Default ActionResult must have page_change_summary set to None."""
    r = ActionResult(ok=True, meta=ResultMeta(trace_id="t", duration_ms=0.0))
    assert r.page_change_summary is None


# ── Round-trip: to_dict / from_dict preserves PageChangeSummary ────────────

def test_40_02_round_trip_page_change_summary():
    """to_dict/from_dict must preserve PageChangeSummary without data loss."""
    pcs = PageChangeSummary(
        change_type="navigation",
        summary="Navigated to https://example.com/b",
        title="Page B",
        url="https://example.com/b",
        artifact_hint=None,
    )
    original = ActionResult(
        ok=True,
        meta=ResultMeta(trace_id="rt-42", duration_ms=1.0),
        page_change_summary=pcs,
    )
    d = original.to_dict()
    assert d["page_change_summary"] is not None
    assert d["page_change_summary"]["change_type"] == "navigation"

    restored = ActionResult.from_dict(d)
    assert restored.page_change_summary is not None
    assert restored.page_change_summary.change_type == "navigation"
    assert restored.page_change_summary.url == "https://example.com/b"
    assert restored.page_change_summary.title == "Page B"
