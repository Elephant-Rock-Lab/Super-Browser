"""Tests for BATCH-33/TASK-02 — Stealth Regression Harness + CLI.

Test IDs: TEST-33-02-01 through TEST-33-02-04
"""

import json
import sys
from unittest.mock import patch

import pytest

from super_browser.cli import main
from super_browser.stealth.consistency.matrix import FingerprintMatrix
from super_browser.stealth.profiles.schema import DeviceProfile
from super_browser.stealth.validation.harness import (
    BaselineResult,
    StealthRegressionHarness,
)
from super_browser.stealth.validation.report import CheckResult, ValidationReport
from super_browser.stealth.validation.suite import FingerprintValidationSuite

# Shared fixtures
# ---------------------------------------------------------------------------


def _make_profile() -> DeviceProfile:
    """Build a minimal valid DeviceProfile for testing."""
    from super_browser.stealth.profiles.schema import (
        AudioInfo,
        BehaviorInfo,
        BrowserInfo,
        DeviceInfo,
        DisplayInfo,
        EntropyBudget,
        FontInfo,
        GPUInfo,
        OSInfo,
    )

    return DeviceProfile(
        id="test-profile",
        version="1.0",
        engine="test",
        browser=BrowserInfo(
            name="Chrome",
            channel="stable",
            min_version="120",
            max_version="130",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
        ),
        os=OSInfo(name="windows", version="11", arch="x64"),
        device=DeviceInfo(
            vendor="Dell", model="XPS", cpu_family="x86", cores=8, memory_gb=16
        ),
        display=DisplayInfo(
            width=1920, height=1080, dpr=1, color_depth=24, pixel_depth=24
        ),
        gpu=GPUInfo(
            vendor="NVIDIA Corporation",
            renderer="RTX 3080",
            webgl_unmasked_vendor="Google Inc. (NVIDIA)",
            webgl_unmasked_renderer="ANGLE (NVIDIA, RTX 3080)",
            webgl_max_texture_size=16384,
            webgl_max_color_attachments=8,
        ),
        audio=AudioInfo(
            context_sample_rate=48000,
            audio_worklet_latency=0.005,
            destination_max_channel_count=2,
        ),
        fonts=FontInfo(family="windows", list=("Arial", "Segoe UI", "Consolas")),
        behavior=BehaviorInfo(hand="right", tremor=0.5, wpm=80, scroll_style="smooth"),
        entropy_budget=EntropyBudget(),
        timezone="America/New_York",
        locale="en-US",
        languages=("en-US", "en"),
    )


def _make_matrix() -> FingerprintMatrix:
    """Build a minimal FingerprintMatrix for testing."""
    return FingerprintMatrix(
        profile_id="test-profile",
        seed="default",
        derived_at="2026-05-13T14:00:00Z",
        consistency_engine_version="0.1.0",
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
        platform="Win32",
        hardware_concurrency=8,
        device_memory=8,
        languages=("en-US", "en"),
        locale="en-US",
        timezone="America/New_York",
        webdriver=False,
        sec_ch_ua='"Chromium";v="125"',
        sec_ch_ua_platform="Windows",
        sec_ch_ua_platform_version="15.0.0",
        sec_ch_ua_arch="x86",
        sec_ch_ua_bitness="64",
        sec_ch_ua_mobile="?0",
        sec_ch_ua_model="",
        screen_width=1920,
        screen_height=1080,
        screen_avail_width=1920,
        screen_avail_height=1040,
        color_depth=24,
        pixel_depth=24,
        device_pixel_ratio=1,
        viewport_inner_width=1920,
        viewport_inner_height=969,
        viewport_outer_width=1920,
        viewport_outer_height=1040,
        screen_orientation_type="landscape-primary",
        screen_orientation_angle=0,
        webgl_unmasked_vendor="Google Inc. (NVIDIA)",
        webgl_unmasked_renderer="ANGLE (NVIDIA, RTX 3080)",
        webgl_max_texture_size=16384,
        webgl_max_color_attachments=8,
        webgl_extensions=("WEBGL_debug_renderer_info",),
        audio_context_sample_rate=48000,
        audio_worklet_latency=0.005,
        audio_destination_max_channel_count=2,
        fonts=("Arial", "Segoe UI", "Consolas"),
        behavior_hand="right",
        behavior_tremor=0.5,
        behavior_wpm=80,
        behavior_scroll_style="smooth",
        connection_effective_type="4g",
        connection_downlink=10.0,
        connection_rtt=50,
        connection_save_data=False,
        storage_quota=1000000000,
        storage_usage=50000000,
        navigator_vendor="Google Inc.",
        navigator_app_version="5.0 (Windows NT 10.0; Win64; x64) Chrome/125.0",
        navigator_app_codename="Mozilla",
        navigator_product="Gecko",
        navigator_cookie_enabled=True,
        navigator_max_touch_points=0,
        ejector_seed="default",
    )


def _make_check_result(check_id: str, name: str, passed: bool) -> CheckResult:
    return CheckResult(
        check_id=check_id,
        name=name,
        passed=passed,
        actual="ok" if passed else "bad",
        expected="ok",
        severity="warning",
    )


def _make_report(checks: tuple[CheckResult, ...]) -> ValidationReport:
    passed_count = sum(1 for c in checks if c.passed)
    return ValidationReport(
        profile_id="test-profile",
        seed="default",
        timestamp="2026-05-13T14:00:00Z",
        checks=checks,
        passed=passed_count == len(checks),
        score=(passed_count / len(checks)) * 100 if checks else 0.0,
    )


# ---------------------------------------------------------------------------
# TEST-33-02-01: capture_baseline writes JSON, load_baseline reads it back
# ---------------------------------------------------------------------------


class TestBaselineCaptureAndLoad:
    """TEST-33-02-01: Baseline round-trip (capture → disk → load)."""

    def test_capture_and_load_roundtrip(self, tmp_path):
        profile = _make_profile()
        matrix = _make_matrix()
        checks = (
            _make_check_result("CHK-001", "UA_OS_Match", True),
            _make_check_result("CHK-002", "GPU_Vendor_WebGL", True),
        )
        report = _make_report(checks)
        harness = StealthRegressionHarness(baseline_dir=tmp_path)

        baseline = harness.capture_baseline(profile, "default", matrix, report)

        # Verify returned BaselineResult
        assert baseline.profile_id == "test-profile"
        assert baseline.seed == "default"
        assert baseline.matrix_hash
        assert len(baseline.check_results) == 2

        # Verify file written
        baseline_file = tmp_path / "test-profile.json"
        assert baseline_file.is_file()

        # Load it back
        loaded = harness.load_baseline("test-profile")
        assert loaded.profile_id == baseline.profile_id
        assert loaded.seed == baseline.seed
        assert loaded.matrix_hash == baseline.matrix_hash
        assert len(loaded.check_results) == len(baseline.check_results)
        for original, restored in zip(baseline.check_results, loaded.check_results):
            assert original.check_id == restored.check_id
            assert original.passed == restored.passed

    def test_load_missing_raises(self, tmp_path):
        harness = StealthRegressionHarness(baseline_dir=tmp_path)
        with pytest.raises(FileNotFoundError, match="No baseline found"):
            harness.load_baseline("nonexistent")


# ---------------------------------------------------------------------------
# TEST-33-02-02: detect_regression flags regressed checks
# ---------------------------------------------------------------------------


class TestDetectRegression:
    """TEST-33-02-02: detect_regression identifies newly-failing checks."""

    def test_no_regression_when_identical(self, tmp_path):
        checks = (
            _make_check_result("CHK-001", "UA_OS_Match", True),
            _make_check_result("CHK-008", "Webdriver_False", True),
        )
        report = _make_report(checks)
        baseline = BaselineResult(
            profile_id="test-profile",
            seed="default",
            captured_at="2026-05-13T14:00:00Z",
            matrix_hash="abc123",
            check_results=checks,
        )
        harness = StealthRegressionHarness(baseline_dir=tmp_path)
        regressed = harness.detect_regression(report, baseline)
        assert regressed == []

    def test_regression_detected(self, tmp_path):
        baseline_checks = (
            _make_check_result("CHK-001", "UA_OS_Match", True),
            _make_check_result("CHK-003", "Hardware_Cores", True),
            _make_check_result("CHK-008", "Webdriver_False", True),
        )
        baseline = BaselineResult(
            profile_id="test-profile",
            seed="default",
            captured_at="2026-05-13T14:00:00Z",
            matrix_hash="abc123",
            check_results=baseline_checks,
        )

        # Current: CHK-003 regressed (was pass, now fail)
        current_checks = (
            _make_check_result("CHK-001", "UA_OS_Match", True),
            _make_check_result("CHK-003", "Hardware_Cores", False),
            _make_check_result("CHK-008", "Webdriver_False", True),
        )
        report = _make_report(current_checks)

        harness = StealthRegressionHarness(baseline_dir=tmp_path)
        regressed = harness.detect_regression(report, baseline)

        assert len(regressed) == 1
        assert regressed[0].check_id == "CHK-003"
        assert regressed[0].name == "Hardware_Cores"

    def test_was_failing_still_failing_not_regression(self, tmp_path):
        """A check that was already failing in baseline is NOT a regression."""
        baseline_checks = (
            _make_check_result("CHK-001", "UA_OS_Match", True),
            _make_check_result("CHK-003", "Hardware_Cores", False),  # already failing
        )
        baseline = BaselineResult(
            profile_id="test-profile",
            seed="default",
            captured_at="2026-05-13T14:00:00Z",
            matrix_hash="abc123",
            check_results=baseline_checks,
        )
        current_checks = (
            _make_check_result("CHK-001", "UA_OS_Match", True),
            _make_check_result("CHK-003", "Hardware_Cores", False),  # still failing
        )
        report = _make_report(current_checks)

        harness = StealthRegressionHarness(baseline_dir=tmp_path)
        regressed = harness.detect_regression(report, baseline)
        assert len(regressed) == 0


# ---------------------------------------------------------------------------
# TEST-33-02-03: CLI --capture-baseline writes baseline file
# ---------------------------------------------------------------------------


class TestCLICaptureBaseline:
    """TEST-33-02-03: ``stealth-validate --capture-baseline`` writes baseline."""

    def test_capture_baseline_writes_file(self, tmp_path, monkeypatch):
        profile = _make_profile()
        matrix = _make_matrix()
        # main is imported at module level

        with (
            patch("super_browser.stealth.profiles.load_profile", return_value=profile),
            patch(
                "super_browser.stealth.consistency.derive.derive_matrix",
                return_value=matrix,
            ),
        ):
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "superbrowser",
                    "stealth-validate",
                    "--profile",
                    "test-profile",
                    "--seed",
                    "default",
                    "--capture-baseline",
                    "--baseline-dir",
                    str(tmp_path),
                ],
            )
            main()

        baseline_file = tmp_path / "test-profile.json"
        assert baseline_file.is_file()

        data = json.loads(baseline_file.read_text(encoding="utf-8"))
        assert data["profile_id"] == "test-profile"
        assert data["seed"] == "default"
        assert "matrix_hash" in data
        assert len(data["check_results"]) > 0


# ---------------------------------------------------------------------------
# TEST-33-02-04: CLI --ci exits 1 on regression
# ---------------------------------------------------------------------------


class TestCLICIMode:
    """TEST-33-02-04: ``stealth-validate --ci`` exits 1 on regression."""

    def test_ci_passes_with_no_regression(self, tmp_path, monkeypatch):
        # main is imported at module level
        profile = _make_profile()
        matrix = _make_matrix()

        # Capture a baseline first (all passing)
        all_pass_checks = tuple(
            _make_check_result(f"CHK-{i:03d}", f"Check_{i}", True)
            for i in range(1, 9)
        )
        harness = StealthRegressionHarness(baseline_dir=tmp_path)
        baseline_report = _make_report(all_pass_checks)
        harness.capture_baseline(profile, "default", matrix, baseline_report)

        with (
            patch("super_browser.stealth.profiles.load_profile", return_value=profile),
            patch(
                "super_browser.stealth.consistency.derive.derive_matrix",
                return_value=matrix,
            ),
        ):
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "superbrowser",
                    "stealth-validate",
                    "--profile",
                    "test-profile",
                    "--seed",
                    "default",
                    "--ci",
                    "--baseline-dir",
                    str(tmp_path),
                ],
            )
            # Should NOT raise SystemExit (exit 0)
            main()

    def test_ci_exits_1_on_regression(self, tmp_path, monkeypatch):
        # main is imported at module level
        profile = _make_profile()
        matrix = _make_matrix()

        # Capture baseline with all passing
        all_pass_checks = tuple(
            _make_check_result(f"CHK-{i:03d}", f"Check_{i}", True)
            for i in range(1, 9)
        )
        harness = StealthRegressionHarness(baseline_dir=tmp_path)
        baseline_report = _make_report(all_pass_checks)
        harness.capture_baseline(profile, "default", matrix, baseline_report)

        # Now mock the suite to return a regressed report
        regressed_checks = list(all_pass_checks)
        regressed_checks[2] = _make_check_result("CHK-003", "Hardware_Cores", False)

        with (
            patch("super_browser.stealth.profiles.load_profile", return_value=profile),
            patch(
                "super_browser.stealth.consistency.derive.derive_matrix",
                return_value=matrix,
            ),
            patch.object(
                FingerprintValidationSuite,
                "run",
                return_value=_make_report(tuple(regressed_checks)),
            ),
        ):
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "superbrowser",
                    "stealth-validate",
                    "--profile",
                    "test-profile",
                    "--seed",
                    "default",
                    "--ci",
                    "--baseline-dir",
                    str(tmp_path),
                ],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1

    def test_ci_exits_1_when_no_baseline(self, tmp_path, monkeypatch):
        # main is imported at module level
        profile = _make_profile()
        matrix = _make_matrix()

        with (
            patch("super_browser.stealth.profiles.load_profile", return_value=profile),
            patch(
                "super_browser.stealth.consistency.derive.derive_matrix",
                return_value=matrix,
            ),
        ):
            monkeypatch.setattr(
                sys,
                "argv",
                [
                    "superbrowser",
                    "stealth-validate",
                    "--profile",
                    "test-profile",
                    "--ci",
                    "--baseline-dir",
                    str(tmp_path),
                ],
            )
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 1
