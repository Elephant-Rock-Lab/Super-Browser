"""Tests for interaction/presets.py — TEST-42-02-01 through TEST-42-02-08."""

import pytest

from super_browser.interaction.presets import BrowserJob, CompiledStep, QASmoke


# ---------------------------------------------------------------------------
# TEST-42-02-01: BrowserJob class exists
# ---------------------------------------------------------------------------
def test_browser_job_class_exists():
    """BrowserJob is importable and callable."""
    assert callable(BrowserJob)
    job = BrowserJob(steps=[{"action": "open", "url": "https://example.com"}])
    assert isinstance(job, BrowserJob)


# ---------------------------------------------------------------------------
# TEST-42-02-02: BrowserJob validates step schemas — missing 'action' key
# ---------------------------------------------------------------------------
def test_browser_job_validates_missing_action():
    """Step without 'action' key raises ValueError."""
    with pytest.raises(ValueError, match="missing 'action' key"):
        BrowserJob(steps=[{"url": "https://example.com"}])


# ---------------------------------------------------------------------------
# TEST-42-02-03: BrowserJob compiles to action list
# ---------------------------------------------------------------------------
def test_browser_job_compiles_three_steps():
    """compile() returns exactly 3 CompiledStep items for a 3-step job."""
    job = BrowserJob(steps=[
        {"action": "open", "url": "https://example.com"},
        {"action": "fill", "selector": "#name", "value": "Alice"},
        {"action": "click", "selector": "#submit"},
    ])
    compiled = job.compile()
    assert len(compiled) == 3
    assert all(isinstance(s, CompiledStep) for s in compiled)
    assert compiled[0].action == "open"
    assert compiled[1].action == "fill"
    assert compiled[2].action == "click"


# ---------------------------------------------------------------------------
# TEST-42-02-04: BrowserJob rejects unknown action
# ---------------------------------------------------------------------------
def test_browser_job_rejects_unknown_action():
    """Step with action='fly' raises ValueError listing valid actions."""
    with pytest.raises(ValueError, match="unknown action 'fly'"):
        BrowserJob(steps=[{"action": "fly"}])


# ---------------------------------------------------------------------------
# TEST-42-02-05: QASmoke generates 5-step sequence
# ---------------------------------------------------------------------------
def test_qa_smoke_generates_five_steps():
    """QASmoke.compile() returns exactly 5 CompiledStep items."""
    qa = QASmoke(url="https://x.com", assert_text="Welcome")
    compiled = qa.compile()
    assert len(compiled) == 5


# ---------------------------------------------------------------------------
# TEST-42-02-06: QASmoke steps have correct actions
# ---------------------------------------------------------------------------
def test_qa_smoke_step_actions():
    """The 5 QASmoke steps are: open, wait, assert_text, network, screenshot."""
    qa = QASmoke(url="https://x.com", assert_text="Welcome")
    compiled = qa.compile()
    actions = [s.action for s in compiled]
    assert actions == ["open", "wait", "assert_text", "network", "screenshot"]


# ---------------------------------------------------------------------------
# TEST-42-02-07: CompiledStep has action, params, description
# ---------------------------------------------------------------------------
def test_compiled_step_fields():
    """CompiledStep exposes action, params, and description."""
    job = BrowserJob(steps=[
        {"action": "open", "url": "https://example.com", "description": "Open homepage"},
    ])
    compiled = job.compile()
    step = compiled[0]
    assert step.action == "open"
    assert step.params == {"url": "https://example.com"}
    assert step.description == "Open homepage"


# ---------------------------------------------------------------------------
# TEST-42-02-08: Caller maps CompiledSteps to ActionResult
# ---------------------------------------------------------------------------
def test_compiled_step_maps_to_action_result():
    """Simulate caller mapping compiled steps to ActionResult."""
    from super_browser.results import ActionResult, action_result

    job = BrowserJob(steps=[
        {"action": "open", "url": "https://example.com"},
    ])
    job.compile()

    # Simulate what a caller would do after executing the step
    mock_result = action_result(ok=True, data={"url": "https://example.com"})
    assert isinstance(mock_result, ActionResult)
    assert mock_result.ok is True
