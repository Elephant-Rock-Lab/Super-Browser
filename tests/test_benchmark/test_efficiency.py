"""TEST-42-01-01 through TEST-42-01-06 — Agent Efficiency Benchmark tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Make scripts/ importable so we can import the benchmark module directly
_SCRIPTS_DIR = str(Path(__file__).resolve().parent.parent.parent / "scripts")
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

from agent_efficiency_benchmark import (  # noqa: E402
    MockAction,
    MockWorkflow,
    _build_workflows,
    build_report,
    compare_with_baseline,
    generate_markdown,
    measure_workflow,
)

# ---------------------------------------------------------------------------
# TEST-42-01-01: Benchmark produces JSON output with required keys
# ---------------------------------------------------------------------------


class TestBenchmarkJsonOutput:
    """AC-01-01: Benchmark produces valid JSON with required keys."""

    def test_json_output_has_required_keys(self) -> None:
        report = build_report(_build_workflows())
        # Top-level keys
        assert "timestamp" in report
        assert "version" in report
        assert "workflows" in report
        assert "aggregate" in report

        # Aggregate keys
        agg = report["aggregate"]
        assert "total_calls" in agg
        assert "total_output_bytes" in agg
        assert "overall_stale_ref_rate" in agg
        assert "category_coverage" in agg

    def test_json_output_is_serializable(self) -> None:
        report = build_report(_build_workflows())
        serialized = json.dumps(report)
        reloaded = json.loads(serialized)
        assert reloaded["version"] == report["version"]
        assert reloaded["aggregate"]["total_calls"] == report["aggregate"]["total_calls"]

    def test_json_output_contains_all_four_workflows(self) -> None:
        report = build_report(_build_workflows())
        wf_names = set(report["workflows"].keys())
        expected = {"navigate_and_extract", "form_fill", "qa_smoke", "error_recovery"}
        assert wf_names == expected


# ---------------------------------------------------------------------------
# TEST-42-01-02: Benchmark counts tool calls
# ---------------------------------------------------------------------------


class TestBenchmarkCallCount:
    """AC-01-02: call_count matches number of actions in each workflow."""

    def test_call_count_matches_actions(self) -> None:
        wf = MockWorkflow(
            name="five_step",
            actions=[
                MockAction("a", {}),
                MockAction("b", {}),
                MockAction("c", {}),
                MockAction("d", {}),
                MockAction("e", {}),
            ],
        )
        result = measure_workflow(wf)
        assert result["call_count"] == 5

    def test_aggregate_total_calls(self) -> None:
        report = build_report(_build_workflows())
        # 4 + 5 + 5 + 4 = 18 total actions across all workflows
        assert report["aggregate"]["total_calls"] == 18


# ---------------------------------------------------------------------------
# TEST-42-01-03: Benchmark measures output bytes
# ---------------------------------------------------------------------------


class TestBenchmarkOutputBytes:
    """AC-01-02: output_bytes matches sum of action output sizes."""

    def test_output_bytes_known_sizes(self) -> None:
        wf = MockWorkflow(
            name="byte_test",
            actions=[
                MockAction("x", {}, output_size_bytes=200),
                MockAction("y", {}, output_size_bytes=300),
                MockAction("z", {}, output_size_bytes=500),
            ],
        )
        result = measure_workflow(wf)
        assert result["output_bytes"] == 1000

    def test_aggregate_total_output_bytes(self) -> None:
        report = build_report(_build_workflows())
        # Verify aggregate is sum of individual workflow output_bytes
        total = sum(wf["output_bytes"] for wf in report["workflows"].values())
        assert report["aggregate"]["total_output_bytes"] == total


# ---------------------------------------------------------------------------
# TEST-42-01-04: Benchmark computes stale-ref rate
# ---------------------------------------------------------------------------


class TestBenchmarkStaleRefRate:
    """AC-01-03: stale_ref_rate is stale_ref_count / call_count."""

    def test_stale_ref_rate_two_of_ten(self) -> None:
        actions = [
            MockAction("click", {"selector": ".btn"}, ok=False,
                       failure_category="stale_ref", output_size_bytes=100),
            MockAction("retry", {}, ok=True, success_category="navigation",
                       output_size_bytes=100),
            MockAction("click", {"selector": ".btn"}, ok=False,
                       failure_category="stale_ref", output_size_bytes=100),
        ] + [MockAction(f"step_{i}", {}, ok=True, success_category="inspection",
                        output_size_bytes=50)
             for i in range(7)]

        wf = MockWorkflow(name="stale_test", actions=actions)
        result = measure_workflow(wf)
        assert result["stale_ref_count"] == 2
        assert result["call_count"] == 10
        assert result["stale_ref_rate"] == 0.2

    def test_stale_ref_rate_zero_when_none(self) -> None:
        wf = MockWorkflow(
            name="clean",
            actions=[
                MockAction("a", {}, ok=True, success_category="navigation"),
                MockAction("b", {}, ok=True, success_category="inspection"),
            ],
        )
        result = measure_workflow(wf)
        assert result["stale_ref_count"] == 0
        assert result["stale_ref_rate"] == 0.0


# ---------------------------------------------------------------------------
# TEST-42-01-05: --compare detects regression
# ---------------------------------------------------------------------------


class TestBenchmarkCompareRegression:
    """AC-01-04: --compare detects regression against baseline."""

    def test_regression_detected_on_higher_calls(self) -> None:
        """Baseline has lower call_count — current should flag regression."""
        report = build_report(_build_workflows())

        # Craft a baseline with a much lower call_count to trigger the 1.2x threshold
        baseline = {
            "version": "1.5.0",
            "aggregate": {
                "total_calls": 5,  # current is 18, 18 > 5 * 1.2 = 6
                "total_output_bytes": report["aggregate"]["total_output_bytes"],
                "overall_stale_ref_rate": report["aggregate"]["overall_stale_ref_rate"],
            },
        }

        comparison = compare_with_baseline(report, baseline)
        assert comparison["regression_detected"] is True
        assert any("call_count" in r for r in comparison["regressions"])

    def test_no_regression_when_comparable(self) -> None:
        """Same metrics should not trigger a regression."""
        report = build_report(_build_workflows())
        # Use the same report as baseline — no regression expected
        comparison = compare_with_baseline(report, report)
        assert comparison["regression_detected"] is False
        assert comparison["regressions"] == []


# ---------------------------------------------------------------------------
# TEST-42-01-06: Benchmark produces Markdown summary
# ---------------------------------------------------------------------------


class TestBenchmarkMarkdownOutput:
    """AC-01-05: Benchmark generates a Markdown summary table."""

    def test_markdown_contains_table_header(self) -> None:
        report = build_report(_build_workflows())
        md = generate_markdown(report)
        assert "| Workflow | Calls | Output (bytes) | Stale Refs | Categories |" in md
        assert "|:---------|:------|:---------------|:-----------|:-----------|" in md

    def test_markdown_contains_all_workflows(self) -> None:
        report = build_report(_build_workflows())
        md = generate_markdown(report)
        for name in ("navigate_and_extract", "form_fill", "qa_smoke", "error_recovery"):
            assert name in md

    def test_markdown_contains_aggregate_section(self) -> None:
        report = build_report(_build_workflows())
        md = generate_markdown(report)
        assert "## Aggregate" in md
        assert "Total calls:" in md
        assert "Category coverage:" in md
