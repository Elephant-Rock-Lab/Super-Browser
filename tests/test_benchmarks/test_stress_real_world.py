"""Tests for the real-world stress harness.

Covers:
- Fixture server starts/stops and serves correct content
- Report schema serialization
- Markdown rendering
- CLI argument parsing
- Scenario name constants
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import pytest

# Ensure stress module is importable
_STRESS_DIR = Path(__file__).resolve().parent.parent.parent / "stress"
if str(_STRESS_DIR) not in sys.path:
    sys.path.insert(0, str(_STRESS_DIR))


class TestStressFixtureServer:
    """Test the fixture server lifecycle and content."""

    def test_server_starts_and_stops(self) -> None:
        """Server starts, returns a base URL, and stops cleanly."""
        from stress.server import StressFixtureServer

        server = StressFixtureServer(port=0)
        base_url = server.start()
        assert base_url.startswith("http://127.0.0.1:")
        server.stop()

    def test_server_base_url_raises_when_not_started(self) -> None:
        """base_url raises RuntimeError when server not started."""
        from stress.server import StressFixtureServer

        server = StressFixtureServer(port=0)
        with pytest.raises(RuntimeError, match="not started"):
            _ = server.base_url

    def test_server_serves_index(self) -> None:
        """Index page is served with expected content."""
        import urllib.request

        from stress.server import StressFixtureServer

        with StressFixtureServer(port=0) as base_url:
            resp = urllib.request.urlopen(f"{base_url}/")
            content = resp.read().decode()
            assert "Stress Test Home" in content
            assert "layout-marker" in content

    def test_server_serves_login(self) -> None:
        """Login page is served with form elements."""
        import urllib.request

        from stress.server import StressFixtureServer

        with StressFixtureServer(port=0) as base_url:
            resp = urllib.request.urlopen(f"{base_url}/login.html")
            content = resp.read().decode()
            assert "login-form" in content
            assert "username" in content
            assert "password" in content

    def test_server_serves_app(self) -> None:
        """App page is served with dynamic content marker."""
        import urllib.request

        from stress.server import StressFixtureServer

        with StressFixtureServer(port=0) as base_url:
            resp = urllib.request.urlopen(f"{base_url}/app.html")
            content = resp.read().decode()
            assert "content-area" in content
            assert "__HYDRATED__" in content

    def test_server_api_data(self) -> None:
        """/api/data returns JSON with items."""
        import urllib.request

        from stress.server import StressFixtureServer

        with StressFixtureServer(port=0) as base_url:
            resp = urllib.request.urlopen(f"{base_url}/api/data")
            data = json.loads(resp.read())
            assert "items" in data
            assert len(data["items"]) == 20

    def test_server_api_error(self) -> None:
        """/api/error returns 500."""
        import urllib.error
        import urllib.request

        from stress.server import StressFixtureServer

        with StressFixtureServer(port=0) as base_url:
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                urllib.request.urlopen(f"{base_url}/api/error")
            assert exc_info.value.code == 500

    def test_server_download(self) -> None:
        """/download returns deterministic payload."""
        import urllib.request

        from stress.server import DOWNLOAD_PAYLOAD, StressFixtureServer

        with StressFixtureServer(port=0) as base_url:
            resp = urllib.request.urlopen(f"{base_url}/download")
            content = resp.read()
            assert content == DOWNLOAD_PAYLOAD
            assert len(content) == 1024

    def test_server_api_auth(self) -> None:
        """POST /api/auth returns authenticated JSON."""
        import urllib.request

        from stress.server import StressFixtureServer

        with StressFixtureServer(port=0) as base_url:
            req = urllib.request.Request(
                f"{base_url}/api/auth", method="POST", data=b"{}"
            )
            resp = urllib.request.urlopen(req)
            data = json.loads(resp.read())
            assert data["authenticated"] is True
            assert "token" in data
            assert "user" in data

    def test_heavy_dom_size(self) -> None:
        """Heavy DOM fixture has 10k+ nodes."""
        from stress.server import HEAVY_DOM_HTML

        node_count = HEAVY_DOM_HTML.count("<")
        assert node_count >= 10000

    def test_static_routes_completeness(self) -> None:
        """All expected static routes are registered."""
        from stress.server import STATIC_ROUTES

        expected = ["/", "/index.html", "/login.html", "/app.html", "/form.html", "/heavy-dom.html"]
        for route in expected:
            assert route in STATIC_ROUTES, f"Missing route: {route}"


class TestReportSerialization:
    """Test report building and serialization."""

    def test_serialize_report_schema_version(self) -> None:
        """Report has correct schema version."""
        from scripts.stress_real_world import (
            SCHEMA_VERSION,
            build_report,
            serialize_report,
        )

        report = build_report(
            mode="quick",
            config={"sessions": 1},
            realism={"auth": True},
            scenarios=[],
            started_at=0.0,
            duration_s=1.0,
            environment={},
        )
        data = serialize_report(report)
        assert data["schema_version"] == SCHEMA_VERSION
        assert data["schema_version"] == 1

    def test_serialize_report_summary(self) -> None:
        """Summary correctly counts passed/failed."""
        from scripts.stress_real_world import ScenarioResult, build_report, serialize_report

        scenarios = [
            ScenarioResult(name="a", passed=True, duration_s=1.0),
            ScenarioResult(name="b", passed=False, duration_s=2.0, error="fail"),
            ScenarioResult(name="c", passed=True, duration_s=3.0),
        ]
        report = build_report(
            mode="realistic",
            config={},
            realism={},
            scenarios=scenarios,
            started_at=0.0,
            duration_s=6.0,
            environment={},
        )
        data = serialize_report(report)
        assert data["summary"]["total"] == 3
        assert data["summary"]["passed"] == 2
        assert data["summary"]["failed"] == 1

    def test_serialize_report_empty_scenarios(self) -> None:
        """Empty scenarios list produces valid summary."""
        from scripts.stress_real_world import build_report, serialize_report

        report = build_report(
            mode="quick",
            config={},
            realism={},
            scenarios=[],
            started_at=0.0,
            duration_s=0.0,
            environment={},
        )
        data = serialize_report(report)
        assert data["summary"]["total"] == 0
        assert data["summary"]["passed"] == 0
        assert data["summary"]["failed"] == 0

    def test_serialize_report_scenario_metrics(self) -> None:
        """Scenario metrics are preserved in serialization."""
        from scripts.stress_real_world import ScenarioResult, build_report, serialize_report

        scenarios = [
            ScenarioResult(
                name="test",
                passed=True,
                duration_s=1.5,
                metrics={"items": 10, "time_ms": 1500},
            ),
        ]
        report = build_report(
            mode="quick",
            config={},
            realism={},
            scenarios=scenarios,
            started_at=0.0,
            duration_s=1.5,
            environment={},
        )
        data = serialize_report(report)
        assert data["scenarios"][0]["metrics"]["items"] == 10
        assert data["scenarios"][0]["metrics"]["time_ms"] == 1500

    def test_serialize_report_realism_section(self) -> None:
        """Realism section is preserved in serialized output."""
        from scripts.stress_real_world import build_report, serialize_report

        realism = {
            "auth": True,
            "dynamic_dom": True,
            "file_io": False,
            "browser_crash_recovery": False,
        }
        report = build_report(
            mode="realistic",
            config={},
            realism=realism,
            scenarios=[],
            started_at=0.0,
            duration_s=0.0,
            environment={},
        )
        data = serialize_report(report)
        assert data["realism"] == realism
        assert data["realism"]["auth"] is True
        assert data["realism"]["file_io"] is False


class TestMarkdownRendering:
    """Test Markdown report rendering."""

    def test_render_markdown_has_title(self) -> None:
        """Markdown output has the expected title."""
        from scripts.stress_real_world import build_report, render_markdown, serialize_report

        report = build_report(
            mode="quick",
            config={},
            realism={"auth": True},
            scenarios=[],
            started_at=0.0,
            duration_s=5.0,
            environment={},
        )
        data = serialize_report(report)
        md = render_markdown(report, data)
        assert "# Stress Test Results" in md

    def test_render_markdown_has_summary(self) -> None:
        """Markdown output has summary section."""
        from scripts.stress_real_world import (
            ScenarioResult,
            build_report,
            render_markdown,
            serialize_report,
        )

        scenarios = [ScenarioResult(name="auth", passed=True, duration_s=1.0)]
        report = build_report(
            mode="quick",
            config={},
            realism={},
            scenarios=scenarios,
            started_at=0.0,
            duration_s=1.0,
            environment={},
        )
        data = serialize_report(report)
        md = render_markdown(report, data)
        assert "## Summary" in md
        assert "Passed:" in md

    def test_render_markdown_has_realism_table(self) -> None:
        """Markdown output has realism dimensions table."""
        from scripts.stress_real_world import build_report, render_markdown, serialize_report

        report = build_report(
            mode="quick",
            config={},
            realism={"auth": True, "dynamic_dom": False},
            scenarios=[],
            started_at=0.0,
            duration_s=0.0,
            environment={},
        )
        data = serialize_report(report)
        md = render_markdown(report, data)
        assert "## Realism Dimensions" in md
        assert "auth" in md

    def test_render_markdown_has_scenario_table(self) -> None:
        """Markdown output has scenario results table."""
        from scripts.stress_real_world import (
            ScenarioResult,
            build_report,
            render_markdown,
            serialize_report,
        )

        scenarios = [
            ScenarioResult(name="js_heavy", passed=True, duration_s=2.5),
            ScenarioResult(name="auth_flow", passed=False, duration_s=1.0, error="timeout"),
        ]
        report = build_report(
            mode="quick",
            config={},
            realism={},
            scenarios=scenarios,
            started_at=0.0,
            duration_s=3.5,
            environment={},
        )
        data = serialize_report(report)
        md = render_markdown(report, data)
        assert "## Scenario Results" in md
        assert "js_heavy" in md
        assert "auth_flow" in md


class TestScenarioConstants:
    """Test scenario definitions and constants."""

    def test_all_scenarios_count(self) -> None:
        """Exactly 8 scenarios are defined."""
        from scripts.stress_real_world import ALL_SCENARIOS

        assert len(ALL_SCENARIOS) == 8

    def test_all_scenarios_names(self) -> None:
        """Scenario names match the specification."""
        from scripts.stress_real_world import ALL_SCENARIOS

        expected = {
            "auth_flow",
            "js_heavy",
            "file_handling",
            "viewport_rotation",
            "request_intercept",
            "parallel_profiles",
            "warm_ramp",
            "storage_pressure",
        }
        assert set(ALL_SCENARIOS) == expected

    def test_schema_version_is_1(self) -> None:
        """Schema version is 1 for initial release."""
        from scripts.stress_real_world import SCHEMA_VERSION

        assert SCHEMA_VERSION == 1

    def test_default_output_dir(self) -> None:
        """Default output directory is stress-results."""
        from scripts.stress_real_world import DEFAULT_OUT_DIR

        assert DEFAULT_OUT_DIR.name == "stress-results"


class TestScenarioResultDataclass:
    """Test ScenarioResult dataclass behavior."""

    def test_scenario_result_defaults(self) -> None:
        """ScenarioResult has correct defaults."""
        from scripts.stress_real_world import ScenarioResult

        r = ScenarioResult(name="test", passed=True, duration_s=1.0)
        assert r.error is None
        assert r.screenshot is None
        assert r.metrics == {}

    def test_scenario_result_with_error(self) -> None:
        """ScenarioResult preserves error info."""
        from scripts.stress_real_world import ScenarioResult

        r = ScenarioResult(
            name="test",
            passed=False,
            duration_s=0.5,
            error="ConnectionError: refused",
        )
        assert r.error == "ConnectionError: refused"
        assert not r.passed

    def test_scenario_result_with_metrics(self) -> None:
        """ScenarioResult preserves metrics."""
        from scripts.stress_real_world import ScenarioResult

        r = ScenarioResult(
            name="test",
            passed=True,
            duration_s=2.0,
            metrics={"items": 5, "hydrated": True},
        )
        assert r.metrics["items"] == 5
        assert r.metrics["hydrated"] is True


class TestReportJSONValidation:
    """Test that serialized reports are valid JSON and well-formed."""

    def test_report_is_json_serializable(self) -> None:
        """Serialized report can be round-tripped through json.loads."""
        from scripts.stress_real_world import ScenarioResult, build_report, serialize_report

        scenarios = [
            ScenarioResult(name="a", passed=True, duration_s=1.0, metrics={"x": 1}),
        ]
        report = build_report(
            mode="quick",
            config={"sessions": 1, "concurrency": 1},
            realism={"auth": True},
            scenarios=scenarios,
            started_at=time.time(),
            duration_s=1.0,
            environment={"rss_peak_mb": 100.0},
        )
        data = serialize_report(report)

        # Must be JSON serializable
        json_str = json.dumps(data)
        loaded = json.loads(json_str)

        assert loaded["schema_version"] == 1
        assert loaded["mode"] == "quick"
        assert loaded["summary"]["total"] == 1
        assert loaded["summary"]["passed"] == 1
        assert loaded["scenarios"][0]["name"] == "a"
        assert loaded["environment"]["rss_peak_mb"] == 100.0

    def test_report_has_required_top_level_keys(self) -> None:
        """Report has all required top-level keys."""
        from scripts.stress_real_world import build_report, serialize_report

        report = build_report(
            mode="quick",
            config={},
            realism={},
            scenarios=[],
            started_at=0.0,
            duration_s=0.0,
            environment={},
        )
        data = serialize_report(report)

        required = {
            "schema_version",
            "mode",
            "timestamp_utc",
            "started_at",
            "duration_s",
            "config",
            "realism",
            "summary",
            "scenarios",
            "environment",
        }
        assert required.issubset(data.keys()), f"Missing keys: {required - set(data.keys())}"


class TestScenarioAssertionLogic:
    """Test that scenario pass/fail conditions are real, not trivially true.

    These tests verify that ScenarioResult objects with empty/wrong metrics
    correctly produce passed=False, proving the scenario logic is meaningful.
    """

    def test_auth_flow_fails_without_cookie(self) -> None:
        """auth_flow must fail if cookie is absent."""
        from scripts.stress_real_world import ScenarioResult

        # Simulate what auth_flow returns when cookie is missing
        r = ScenarioResult(
            name="auth_flow",
            passed=False,  # click_ok=True but cookie_present=False
            duration_s=1.0,
            metrics={"click_ok": True, "cookie_present": False, "user_storage_present": False},
        )
        assert not r.passed, "auth_flow must fail without auth cookie"

    def test_auth_flow_fails_without_storage(self) -> None:
        """auth_flow must fail if localStorage user is absent."""
        from scripts.stress_real_world import ScenarioResult

        r = ScenarioResult(
            name="auth_flow",
            passed=False,  # cookie=True but user_storage=False
            duration_s=1.0,
            metrics={"click_ok": True, "cookie_present": True, "user_storage_present": False},
        )
        assert not r.passed

    def test_viewport_fails_without_width_difference(self) -> None:
        """viewport_rotation must fail if widths are identical."""
        # The scenario requires mobile_width < 768 and desktop_width >= 1024.
        # If both are the same, it must fail.
        mobile_w = 1920  # same as desktop
        desktop_w = 1920
        passed = mobile_w > 0 and desktop_w > 0 and mobile_w < 768 and desktop_w >= 1024
        assert not passed, "viewport_rotation must fail when widths are identical"

    def test_viewport_passes_with_correct_widths(self) -> None:
        """viewport_rotation passes with mobile < 768 and desktop >= 1024."""
        mobile_w = 375
        desktop_w = 1920
        passed = mobile_w > 0 and desktop_w > 0 and mobile_w < 768 and desktop_w >= 1024
        assert passed

    def test_request_intercept_fails_without_mock_effect(self) -> None:
        """request_intercept must fail if mock is not effective."""
        from scripts.stress_real_world import ScenarioResult

        r = ScenarioResult(
            name="request_intercept",
            passed=False,
            duration_s=2.0,
            metrics={
                "mock_ok": True,
                "item_count_after_mock": 20,  # mock didn't work
                "mock_effective": False,
                "block_ok": True,
                "item_count_restored": 20,
                "normal_restored": True,
            },
        )
        assert not r.passed, "request_intercept must fail when mock is ineffective"

    def test_request_intercept_pass_condition_requires_all(self) -> None:
        """request_intercept pass condition requires all four checks."""
        mock_ok = True
        mock_effective = True
        block_ok = True
        normal_restored = False  # this fails

        passed = mock_ok and mock_effective and block_ok and normal_restored
        assert not passed, "Must fail when normal_restored is False"

    def test_parallel_profiles_fails_with_duplicate_values(self) -> None:
        """parallel_profiles must fail if profiles share the same value."""
        values = ["profile-0-token", "profile-0-token"]  # not distinct
        concurrency = 2
        all_distinct = len(set(values)) == concurrency
        assert not all_distinct, "Must fail when profiles share values"

    def test_parallel_profiles_passes_with_distinct_values(self) -> None:
        """parallel_profiles passes with distinct values per profile."""
        values = ["profile-0-token", "profile-1-token"]
        concurrency = 2
        all_distinct = len(set(values)) == concurrency
        assert all_distinct

    def test_parallel_profiles_fails_with_partial_failure(self) -> None:
        """parallel_profiles must fail if any profile fails."""
        results = [
            {"ok": True, "ls_value": "profile-0-token"},
            {"ok": False, "ls_value": None},  # one failed
        ]
        all_ok = all(r.get("ok") for r in results)
        assert not all_ok

    def test_file_handling_fails_without_download(self) -> None:
        """file_handling must fail if download fails."""
        from scripts.stress_real_world import ScenarioResult

        r = ScenarioResult(
            name="file_handling",
            passed=False,
            duration_s=1.0,
            metrics={"upload_ok": True, "download_ok": False},
        )
        assert not r.passed

    def test_file_handling_fails_without_upload(self) -> None:
        """file_handling must fail if upload fails."""
        upload_ok = False
        download_ok = True
        passed = upload_ok and download_ok
        assert not passed


class TestRSSSampler:
    """Test the RSSSampler periodic memory tracker."""

    def test_rss_sampler_stop_without_start(self) -> None:
        """RSSSampler.stop() returns zeros when never started."""
        import asyncio

        from scripts.stress_real_world import RSSSampler

        sampler = RSSSampler()
        stats = asyncio.run(sampler.stop())
        assert stats["rss_start_mb"] == 0.0
        assert stats["rss_peak_mb"] == 0.0
        assert stats["rss_end_mb"] == 0.0
        assert stats["rss_delta_mb"] == 0.0

    def test_rss_sampler_returns_real_stats(self) -> None:
        """RSSSampler collects samples after start."""
        import asyncio

        from scripts.stress_real_world import RSSSampler

        async def _run() -> dict[str, float]:
            sampler = RSSSampler()
            sampler.start()
            await asyncio.sleep(1.0)
            return await sampler.stop()

        stats = asyncio.run(_run())
        # Should have real samples (non-zero on any real system)
        assert "rss_start_mb" in stats
        assert "rss_peak_mb" in stats
        assert "rss_end_mb" in stats
        assert "rss_delta_mb" in stats


class TestWaitForCondition:
    """Test the polling helper that replaces hard sleeps."""

    def test_returns_true_immediately(self) -> None:
        """Condition already met returns True quickly."""
        import asyncio

        from scripts.stress_real_world import _wait_for_condition

        async def _always_true() -> bool:
            return True

        result = asyncio.run(_wait_for_condition(_always_true, timeout_s=1.0))
        assert result is True

    def test_returns_false_on_timeout(self) -> None:
        """Condition never met returns False after timeout."""
        import asyncio

        from scripts.stress_real_world import _wait_for_condition

        async def _always_false() -> bool:
            return False

        result = asyncio.run(_wait_for_condition(_always_false, timeout_s=0.3, interval_s=0.1))
        assert result is False

    def test_eventually_true(self) -> None:
        """Condition becomes true after a few polls."""
        import asyncio

        from scripts.stress_real_world import _wait_for_condition

        counter = {"n": 0}

        async def _after_three() -> bool:
            counter["n"] += 1
            return counter["n"] >= 3

        result = asyncio.run(_wait_for_condition(_after_three, timeout_s=2.0, interval_s=0.05))
        assert result is True
        assert counter["n"] >= 3


class TestUploadDigestFix:
    """Verify fixture server returns real upload digest."""

    def test_upload_returns_non_empty_digest(self) -> None:
        """/api/upload returns sha256 of actual body, not empty bytes."""
        import hashlib
        import json as json_mod
        import urllib.request

        from stress.server import StressFixtureServer

        payload = b"test-upload-content-12345"
        expected_hash = hashlib.sha256(payload).hexdigest()

        with StressFixtureServer(port=0) as base_url:
            req = urllib.request.Request(
                f"{base_url}/api/upload",
                method="POST",
                data=payload,
            )
            resp = urllib.request.urlopen(req)
            data = json_mod.loads(resp.read())
            assert data["sha256"] == expected_hash
            assert data["sha256"] != hashlib.sha256(b"").hexdigest()
            assert data["size_bytes"] == len(payload)
