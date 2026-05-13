"""Tests for ActionLoopDetector."""

from super_browser.agent.loop_detector import ActionLoopDetector


class TestActionLoopDetector:
    def test_no_nudge_on_different_actions(self):
        det = ActionLoopDetector()
        for i in range(10):
            result = det.record_and_check({"action": f"click-{i}", "target": f"#btn-{i}"})
            assert result is None

    def test_soft_nudge_at_5(self):
        det = ActionLoopDetector()
        action = {"action": "click", "target": "#btn"}
        for _ in range(4):
            det.record_and_check(action)
        nudge = det.record_and_check(action)
        assert nudge is not None
        assert nudge.level == 1
        assert nudge.repetition_count >= 5

    def test_strong_nudge_at_8(self):
        det = ActionLoopDetector()
        action = {"action": "click", "target": "#btn"}
        for _ in range(8):
            det.record_and_check(action)
        nudge = det.record_and_check(action)
        assert nudge is not None
        assert nudge.level == 2

    def test_critical_nudge_at_12(self):
        det = ActionLoopDetector()
        action = {"action": "click", "target": "#btn"}
        for _ in range(12):
            det.record_and_check(action)
        nudge = det.record_and_check(action)
        assert nudge is not None
        assert nudge.level == 3

    def test_normalize_strips_volatile_keys(self):
        det = ActionLoopDetector()
        a1 = {"action": "click", "target": "#btn", "trace_id": "abc"}
        a2 = {"action": "click", "target": "#btn", "trace_id": "xyz"}
        assert det.compute_hash(a1) == det.compute_hash(a2)

    def test_reset_clears_window(self):
        det = ActionLoopDetector()
        for _ in range(5):
            det.record_and_check({"action": "click", "target": "#btn"})
        det.reset()
        nudge = det.record_and_check({"action": "click", "target": "#btn"})
        assert nudge is None  # count is 1 after reset

    def test_window_size_bounds(self):
        det = ActionLoopDetector(window_size=5)
        for i in range(10):
            det.record_and_check({"action": "click", "target": f"#btn-{i}"})
        assert len(det._recent_hashes) == 5
