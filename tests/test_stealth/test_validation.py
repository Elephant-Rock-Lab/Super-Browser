"""Tests for BATCH-33/TASK-01 — Fingerprint Validation Suite.

TEST-33-01-01: Perfect matrix — all checks pass, score == 100
TEST-33-01-02: GPU mismatch — GPU_Vendor_WebGL detects inconsistency
TEST-33-01-03: Memory cap violation — deviceMemory > 8 flagged
TEST-33-01-04: Webdriver detection — webdriver=True is caught
TEST-33-01-05: Report immutability — frozen dataclass raises on mutation
TEST-33-01-06: Score calculation — partial pass yields correct percentage
"""

from __future__ import annotations

import dataclasses

import pytest
from super_browser.stealth.consistency.matrix import FingerprintMatrix
from super_browser.stealth.profiles.schema import (
    AudioInfo,
    BehaviorInfo,
    BrowserInfo,
    DeviceInfo,
    DeviceProfile,
    DisplayInfo,
    EntropyBudget,
    FontInfo,
    GPUInfo,
    OSInfo,
)
from super_browser.stealth.validation import (
    CheckResult,
    FingerprintValidationSuite,
    ValidationReport,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(**overrides) -> DeviceProfile:
    """Create a minimal valid DeviceProfile for tests."""
    defaults = dict(
        id="test-win-profile",
        version="1.0.0",
        engine="chromium",
        browser=BrowserInfo(
            name="chrome",
            channel="stable",
            min_version="131",
            max_version="131",
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        ),
        os=OSInfo(name="windows", version="10.0", arch="x86_64"),
        device=DeviceInfo(
            vendor="generic",
            model="PC",
            cpu_family="intel-core-i7",
            cores=8,
            memory_gb=16,
        ),
        display=DisplayInfo(
            width=1920, height=1080, dpr=1, color_depth=24, pixel_depth=24
        ),
        gpu=GPUInfo(
            vendor="NVIDIA Corporation",
            renderer="NVIDIA GeForce RTX 3070",
            webgl_unmasked_vendor="Google Inc. (NVIDIA)",
            webgl_unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3070, D3D11)",
            webgl_max_texture_size=16384,
            webgl_max_color_attachments=8,
        ),
        audio=AudioInfo(
            context_sample_rate=48000,
            audio_worklet_latency=0.04,
            destination_max_channel_count=2,
        ),
        fonts=FontInfo(family="win-pack", list=("Arial", "Consolas")),
        behavior=BehaviorInfo(
            hand="right", tremor=0.18, wpm=60, scroll_style="smooth"
        ),
        entropy_budget=EntropyBudget(),
        timezone="America/New_York",
        locale="en-US",
        languages=("en-US", "en"),
    )
    defaults.update(overrides)
    return DeviceProfile(**defaults)


def _make_matrix(**overrides) -> FingerprintMatrix:
    """Create a FingerprintMatrix that passes all checks for _make_profile()."""
    defaults = dict(
        profile_id="test-win-profile",
        seed="seed-abc-123",
        derived_at="2026-05-13T00:00:00+00:00",
        consistency_engine_version="0.1.0",
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
        platform="Win32",
        hardware_concurrency=8,
        device_memory=8,
        languages=("en-US", "en"),
        locale="en-US",
        timezone="America/New_York",
        webdriver=False,
        sec_ch_ua='"Chromium";v="131", "Not_A Brand";v="24"',
        sec_ch_ua_platform='"Windows"',
        sec_ch_ua_platform_version="15.0.0",
        sec_ch_ua_arch='"x86"',
        sec_ch_ua_bitness='"64"',
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
        webgl_unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3070, D3D11)",
        webgl_max_texture_size=16384,
        webgl_max_color_attachments=8,
        webgl_extensions=("EXT_color_buffer_float",),
        audio_context_sample_rate=48000,
        audio_worklet_latency=0.04,
        audio_destination_max_channel_count=2,
        fonts=("Arial", "Consolas"),
        behavior_hand="right",
        behavior_tremor=0.18,
        behavior_wpm=60,
        behavior_scroll_style="smooth",
        connection_effective_type="4g",
        connection_downlink=10.0,
        connection_rtt=50,
        connection_save_data=False,
        storage_quota=0,
        storage_usage=0,
        navigator_vendor="Google Inc.",
        navigator_app_version="",
        navigator_app_codename="Mozilla",
        navigator_product="Gecko",
        navigator_cookie_enabled=True,
        navigator_max_touch_points=0,
        ejector_seed="seed-abc-123",
    )
    defaults.update(overrides)
    return FingerprintMatrix(**defaults)


# ===================================================================
# TEST-33-01-01: Perfect matrix — all checks pass, score == 100
# ===================================================================


class TestPerfectMatrix:
    """All checks pass on a perfectly consistent matrix."""

    def test_all_pass_score_100(self) -> None:
        profile = _make_profile()
        matrix = _make_matrix()
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)

        assert report.passed is True
        assert report.score == 100.0
        assert len(report.checks) == 11
        assert all(r.passed for r in report.checks)


# ===================================================================
# TEST-33-01-02: GPU mismatch detected
# ===================================================================


class TestGPUMismatch:
    """GPU_Vendor_WebGL flags a vendor mismatch."""

    def test_gpu_vendor_mismatch(self) -> None:
        profile = _make_profile()
        matrix = _make_matrix(
            webgl_unmasked_vendor="Google Inc. (Intel)"
        )
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)

        gpu_check = next(r for r in report.checks if r.check_id == "CHK-002")
        assert gpu_check.passed is False
        assert report.passed is False
        assert report.score < 100.0


# ===================================================================
# TEST-33-01-03: Memory cap violation
# ===================================================================


class TestMemoryCapViolation:
    """deviceMemory > 8 is flagged by Memory_Cap check."""

    def test_memory_over_cap(self) -> None:
        profile = _make_profile()
        matrix = _make_matrix(device_memory=16)
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)

        mem_check = next(r for r in report.checks if r.check_id == "CHK-004")
        assert mem_check.passed is False
        assert mem_check.actual == "16"
        assert mem_check.expected == "≤8"


# ===================================================================
# TEST-33-01-04: Webdriver detection
# ===================================================================


class TestWebdriverDetection:
    """webdriver=True is caught as critical failure."""

    def test_webdriver_true_fails(self) -> None:
        profile = _make_profile()
        matrix = _make_matrix(webdriver=True)
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)

        wd_check = next(r for r in report.checks if r.check_id == "CHK-008")
        assert wd_check.passed is False
        assert wd_check.severity == "critical"


# ===================================================================
# TEST-33-01-05: Report immutability
# ===================================================================


class TestReportImmutability:
    """Frozen dataclasses raise FrozenInstanceError on mutation."""

    def test_check_result_frozen(self) -> None:
        result = CheckResult(
            check_id="T-001",
            name="Test",
            passed=True,
            actual="a",
            expected="b",
            severity="warning",
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            result.passed = False  # type: ignore[misc]

    def test_validation_report_frozen(self) -> None:
        report = ValidationReport(
            profile_id="p1",
            seed="s1",
            timestamp="2026-01-01T00:00:00+00:00",
            checks=(),
            passed=True,
            score=100.0,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            report.score = 50.0  # type: ignore[misc]


# ===================================================================
# TEST-33-01-06: Score calculation — partial pass
# ===================================================================


class TestScoreCalculation:
    """Partial pass yields correct percentage."""

    def test_partial_score(self) -> None:
        """3 of 9 checks fail → score = 66.7."""
        profile = _make_profile()
        # Break 3 checks: webdriver=True, device_memory=16, and
        # hardware_concurrency mismatch
        matrix = _make_matrix(webdriver=True, device_memory=16, hardware_concurrency=2)
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)

        failed = [r for r in report.checks if not r.passed]
        assert len(failed) == 3
        assert round(report.score, 2) == 72.73
        assert report.passed is False
