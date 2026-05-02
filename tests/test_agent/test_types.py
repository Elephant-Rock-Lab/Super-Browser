"""Tests for agent types."""

from super_browser.agent.types import (
    ChildTask,
    DelegationResult,
    DelegationStatus,
    LoopNudge,
    LoopResult,
    PlanItem,
    PlanStatus,
    StepEvent,
    StepResult,
)


class TestPlanStatus:
    def test_values(self):
        assert PlanStatus.PENDING == "pending"
        assert PlanStatus.DONE == "done"
        assert PlanStatus.FAILED == "failed"


class TestStepEvent:
    def test_values(self):
        assert StepEvent.STEP_START == "step_start"
        assert StepEvent.LOOP_DETECTED == "loop_detected"
        assert StepEvent.ABORT == "abort"


class TestPlanItem:
    def test_duration_ms(self):
        item = PlanItem(index=0, description="test", started_at=100.0, completed_at=101.5)
        assert item.duration_ms == 1500.0

    def test_no_duration(self):
        item = PlanItem(index=0, description="test")
        assert item.duration_ms is None


class TestLoopNudge:
    def test_fields(self):
        nudge = LoopNudge(level=2, message="try again", repetition_count=8, repeated_action="click")
        assert nudge.level == 2
        assert nudge.repeated_action == "click"


class TestStepResult:
    def test_defaults(self):
        sr = StepResult(step_number=1, action_name="click", action_params={}, action_result=None, duration_ms=50.0)
        assert sr.page_changed is False
        assert sr.error is None


class TestLoopResult:
    def test_defaults(self):
        lr = LoopResult(instruction="test")
        assert lr.steps == []
        assert lr.total_steps == 0
        assert lr.loop_detections == 0


class TestChildTask:
    def test_auto_uuid(self):
        t1 = ChildTask(instruction="a")
        t2 = ChildTask(instruction="b")
        assert t1.task_id != t2.task_id

    def test_duration(self):
        t = ChildTask(instruction="x", started_at=10.0, completed_at=12.0)
        assert t.duration_ms == 2000.0


class TestDelegationResult:
    def test_all_succeeded(self):
        r = DelegationResult(tasks=[], total_duration_ms=100.0, completed_count=3, failed_count=0, cancelled_count=0)
        assert r.all_succeeded

    def test_has_failures(self):
        r = DelegationResult(tasks=[], total_duration_ms=100.0, completed_count=2, failed_count=1, cancelled_count=0)
        assert not r.all_succeeded
