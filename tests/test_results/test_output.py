"""Tests for OutputDefender and OutputBudgetConfig."""

import json
import threading
from pathlib import Path

from super_browser.results import (
    OutputBudgetConfig,
    OutputDefender,
    SpilledResult,
    action_result,
)


class TestOutputBudgetConfig:
    def test_defaults(self):
        cfg = OutputBudgetConfig()
        assert cfg.spill_threshold == 50_000
        assert cfg.turn_budget == 200_000
        assert cfg.preview_length == 500

    def test_frozen(self):
        cfg = OutputBudgetConfig()
        try:
            cfg.turn_budget = 999  # type: ignore
            assert False, "should raise"
        except AttributeError:
            pass

    def test_resolve_threshold(self):
        cfg = OutputBudgetConfig(per_tool_overrides={"extract": 100_000})
        assert cfg.resolve_threshold("extract") == 100_000
        assert cfg.resolve_threshold("click") == 50_000


class TestOutputDefender:
    def test_small_result_passes_through(self, tmp_path):
        od = OutputDefender(spill_dir=tmp_path)
        r = action_result(ok=True, data={"msg": "hi"})
        defended = od.defend(r, max_chars=50_000)
        assert defended.ok is True
        assert not isinstance(defended.data, SpilledResult)

    def test_level2_spill_to_disk(self, tmp_path):
        od = OutputDefender(spill_dir=tmp_path, spill_threshold=100)
        big_data = {"content": "x" * 200}
        r = action_result(ok=True, data=big_data)
        defended = od.defend(r, max_chars=50_000)
        assert isinstance(defended.data, SpilledResult)
        assert Path(defended.data.file_path).exists()
        assert len(defended.data.preview) <= 500
        spilled_file = Path(defended.data.file_path)
        content = spilled_file.read_text(encoding="utf-8")
        json.loads(content)  # valid JSON

    def test_level3_turn_budget(self, tmp_path):
        od = OutputDefender(spill_dir=tmp_path, spill_threshold=1_000_000, turn_budget=500)
        for i in range(5):
            r = action_result(ok=True, data={"idx": i, "pad": "x" * 80})
            od.defend(r, max_chars=50_000)
        assert od.turn_used <= 500

    def test_new_turn_reset(self, tmp_path):
        od = OutputDefender(spill_dir=tmp_path, turn_budget=1_000_000)
        r = action_result(ok=True, data={"k": "v"})
        od.defend(r, max_chars=50_000)
        assert od.turn_used > 0
        od.new_turn()
        assert od.turn_used == 0

    def test_turn_remaining(self, tmp_path):
        od = OutputDefender(spill_dir=tmp_path, turn_budget=1_000_000)
        assert od.turn_remaining == 1_000_000
        r = action_result(ok=True, data={"x": "y"})
        od.defend(r, max_chars=50_000)
        assert od.turn_remaining < 1_000_000

    def test_concurrent_defend_thread_safety(self, tmp_path):
        od = OutputDefender(spill_dir=tmp_path, spill_threshold=1_000_000, turn_budget=10_000_000)
        results = []
        errors = []

        def worker():
            try:
                for _ in range(20):
                    r = action_result(ok=True, data={"val": "x" * 50})
                    defended = od.defend(r, max_chars=50_000)
                    results.append(defended)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert len(results) == 200
        assert od.turn_used > 0

    def test_custom_budget_config(self, tmp_path):
        cfg = OutputBudgetConfig(turn_budget=1000, spill_threshold=1_000_000)
        od = OutputDefender(config=cfg, spill_dir=tmp_path)
        for _ in range(10):
            r = action_result(ok=True, data={"pad": "x" * 100})
            od.defend(r, max_chars=50_000)
        assert od.turn_used <= 1000

    # -- C3: Level 3 must actually spill to disk --

    def test_level3_actually_spills_to_disk(self, tmp_path):
        """C3: Level 3 must write large results to disk, not just decrement the counter."""
        od = OutputDefender(
            spill_dir=tmp_path,
            spill_threshold=1_000_000,   # high so Level 2 doesn't trigger first
            turn_budget=5_000,            # triggers after a few large results
        )
        results = []
        for i in range(5):
            r = action_result(ok=True, data={"idx": i, "content": "x" * 2000})
            defended = od.defend(r, max_chars=50_000)
            results.append(defended)

        # At least some results should have been spilled to disk by Level 3
        spilled = [r for r in results if isinstance(r.data, SpilledResult)]
        assert len(spilled) >= 1, f"Level 3 should spill large results to disk. turn_used={od.turn_used}, spilled_count={len(spilled)}"

        # Spilled files must exist on disk
        for r in spilled:
            assert Path(r.data.file_path).exists(), f"Spilled file missing: {r.data.file_path}"

        # Budget should be respected
        assert od.turn_used <= 5_000

    def test_level3_preserves_ok_status(self, tmp_path):
        """C3: Spilled results should still carry ok=True."""
        od = OutputDefender(
            spill_dir=tmp_path,
            spill_threshold=1_000_000,
            turn_budget=5_000,
        )
        results = []
        for i in range(5):
            r = action_result(ok=True, data={"big": "x" * 2000})
            defended = od.defend(r, max_chars=50_000)
            results.append(defended)

        for r in results:
            assert r.ok is True
