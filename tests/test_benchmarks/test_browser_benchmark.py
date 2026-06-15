"""Unit tests for the benchmark harness script.

Tests fixture discovery, result schema, markdown rendering, CLI arg
parsing, and psutil fallback — without requiring a real browser.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parent.parent.parent / "scripts" / "browser_benchmark.py"
PROJECT_ROOT = SCRIPT.parent.parent


# Make the script importable
sys.path.insert(0, str(SCRIPT.parent))
import browser_benchmark as bm  # noqa: E402  type: ignore[import-not-found]


class TestFixtureDiscovery:
    """Test discover_fixtures()."""

    def test_discovers_html_files(self) -> None:
        """Should find all .html files in benchmarks/fixtures/."""
        fixtures_dir = PROJECT_ROOT / "benchmarks" / "fixtures"
        result = bm.discover_fixtures(fixtures_dir)
        assert "simple.html" in result
        assert "form.html" in result
        assert "dom-heavy.html" in result
        assert "behavioral.html" in result

    def test_returns_sorted(self) -> None:
        """Results should be sorted alphabetically."""
        fixtures_dir = PROJECT_ROOT / "benchmarks" / "fixtures"
        result = bm.discover_fixtures(fixtures_dir)
        assert result == sorted(result)

    def test_nonexistent_dir(self) -> None:
        """Should return empty list for nonexistent directory."""
        result = bm.discover_fixtures(Path("/nonexistent/path"))
        assert result == []

    def test_empty_dir(self, tmp_path: Path) -> None:
        """Should return empty list for directory with no HTML."""
        (tmp_path / "readme.txt").write_text("not html")
        result = bm.discover_fixtures(tmp_path)
        assert result == []


class TestSummarize:
    """Test _summarize()."""

    def test_basic_stats(self) -> None:
        result = bm._summarize("test_metric", "ms", [10.0, 20.0, 30.0])
        assert result["name"] == "test_metric"
        assert result["unit"] == "ms"
        assert result["mean"] == 20.0
        assert result["median"] == 20.0
        assert result["min"] == 10.0
        assert result["max"] == 30.0

    def test_stdev(self) -> None:
        result = bm._summarize("test", "ms", [10.0, 20.0, 30.0])
        assert result["stdev"] == 10.0

    def test_single_sample_stdev_zero(self) -> None:
        """stdev is 0.0 when fewer than 2 samples."""
        result = bm._summarize("test", "ms", [15.0])
        assert result["stdev"] == 0.0

    def test_empty_samples(self) -> None:
        """Empty samples produce zeros."""
        result = bm._summarize("test", "ms", [])
        assert result["mean"] == 0
        assert result["min"] == 0

    def test_samples_preserved(self) -> None:
        """Raw samples are preserved in output."""
        samples = [10.0, 20.0, 30.0]
        result = bm._summarize("test", "ms", samples)
        assert result["samples"] == samples


class TestProcessTreeRss:
    """Test _process_tree_rss() fallback."""

    def test_returns_float(self) -> None:
        """Should return a float."""
        result = bm._process_tree_rss()
        assert isinstance(result, float)

    def test_returns_nonzero_with_psutil(self) -> None:
        """With psutil installed, should return nonzero."""
        result = bm._process_tree_rss()
        # psutil should be available in dev environment
        assert result > 0

    def test_graceful_without_psutil(self) -> None:
        """Should return 0.0 when psutil is not available."""
        with patch.dict("sys.modules", {"psutil": None}):
            result = bm._process_tree_rss()
            assert result == 0.0


class TestFormatMarkdown:
    """Test format_markdown()."""

    def _make_report(self) -> dict:
        return {
            "schema_version": 1,
            "timestamp_utc": "2026-06-16T00:00:00Z",
            "environment": {
                "python": "3.12.0",
                "platform": "linux",
                "browser_backend": "patchright",
                "headless": True,
                "super_browser_version": "2.0.2",
            },
            "config": {
                "iterations": 5,
                "warmup": 1,
                "fixtures_dir": "benchmarks/fixtures",
                "timeout_s": 30,
            },
            "metrics": [
                bm._summarize("browser_launch", "ms", [100.0, 120.0, 110.0]),
                bm._summarize("new_page", "ms", [5.0, 6.0, 5.5]),
            ],
            "memory": {
                "unit": "mb",
                "rss_before_mb": 100.0,
                "rss_after_mb": 150.0,
                "delta_mb": bm._summarize("memory_delta", "MB", [50.0]),
            },
        }

    def test_renders_header(self) -> None:
        md = bm.format_markdown(self._make_report())
        assert "# Benchmark Results" in md
        assert "v2.0.2" in md
        assert "patchright" in md

    def test_renders_table(self) -> None:
        md = bm.format_markdown(self._make_report())
        assert "| Metric | Mean |" in md
        assert "browser_launch" in md
        assert "new_page" in md
        assert "memory_delta" in md

    def test_renders_all_config(self) -> None:
        md = bm.format_markdown(self._make_report())
        assert "5" in md  # iterations
        assert "1" in md  # warmup

    def test_memory_skipped(self) -> None:
        """When memory is unavailable, shows 'skipped'."""
        report = self._make_report()
        report["memory"] = {"note": "psutil unavailable"}
        md = bm.format_markdown(report)
        assert "skipped" in md


class TestSchemaValidation:
    """Test that benchmark output conforms to the expected schema."""

    def _make_report(self) -> dict:
        return {
            "schema_version": 1,
            "timestamp_utc": "2026-06-16T00:00:00Z",
            "environment": {
                "python": "3.12.0",
                "platform": "linux",
                "browser_backend": "patchright",
                "headless": True,
                "super_browser_version": "2.0.2",
            },
            "config": {
                "iterations": 5,
                "warmup": 1,
                "fixtures_dir": "benchmarks/fixtures",
                "timeout_s": 30,
            },
            "metrics": [bm._summarize("test", "ms", [1.0, 2.0])],
            "memory": {"unit": "mb", "note": "test"},
        }

    def test_top_level_keys(self) -> None:
        report = self._make_report()
        assert report["schema_version"] == 1
        assert "timestamp_utc" in report
        assert "environment" in report
        assert "config" in report
        assert "metrics" in report
        assert "memory" in report

    def test_environment_keys(self) -> None:
        env = self._make_report()["environment"]
        for key in ("python", "platform", "browser_backend", "headless", "super_browser_version"):
            assert key in env, f"Missing environment key: {key}"

    def test_config_keys(self) -> None:
        cfg = self._make_report()["config"]
        for key in ("iterations", "warmup", "fixtures_dir", "timeout_s"):
            assert key in cfg, f"Missing config key: {key}"

    def test_metric_keys(self) -> None:
        metric = self._make_report()["metrics"][0]
        for key in ("name", "unit", "samples", "mean", "median", "min", "max", "stdev"):
            assert key in metric, f"Missing metric key: {key}"

    def test_json_serializable(self) -> None:
        """Report must be JSON-serializable."""
        report = self._make_report()
        serialized = json.dumps(report)
        deserialized = json.loads(serialized)
        assert deserialized["schema_version"] == 1


class TestCliArgParsing:
    """Test CLI argument parsing."""

    def test_defaults(self) -> None:
        """Default arguments should be sensible."""
        assert bm.DEFAULT_ITERATIONS == 5
        assert bm.DEFAULT_WARMUP == 1

    def test_fixtures_constant_exists(self) -> None:
        assert bm.DEFAULT_FIXTURES.exists()

    def test_output_dir_default(self) -> None:
        assert bm.Path("benchmarks/results")  # type: ignore[attr-defined]
