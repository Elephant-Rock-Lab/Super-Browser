"""Tests for device profile schema, loading, and host detection.

TEST-30-01-01: Schema validation — missing required field raises ValueError
TEST-30-01-02: JSON loading round-trip — loaded profile matches JSON
TEST-30-01-03: Host OS detection returns valid profile ID
TEST-30-01-04: Non-existent profile ID raises ProfileNotFoundError
TEST-30-01-05: DeviceProfile immutability — setattr raises FrozenInstanceError
TEST-30-01-06: All 4 profiles load without error
"""

from __future__ import annotations

import json
import platform
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from super_browser.stealth.profiles import (
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
    ProfileNotFoundError,
    list_profiles,
    load_profile,
)
from super_browser.stealth.profiles.host_detect import detect_host_profile

# ---------------------------------------------------------------------------
# TEST-30-01-01: Schema validation — missing required field raises ValueError
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    """Validate that DeviceProfile.validate() rejects empty / zero fields."""

    def _make_valid_profile(self, **overrides) -> DeviceProfile:
        """Create a valid baseline profile; override specific fields."""
        base = dict(
            id="test-profile",
            version="1.0.0",
            engine="chromium",
            browser=BrowserInfo(
                name="chrome",
                channel="stable",
                min_version="131",
                max_version="131",
                user_agent="Mozilla/5.0 Test",
            ),
            os=OSInfo(name="linux", version="22.04", arch="x86_64"),
            device=DeviceInfo(
                vendor="generic",
                model="PC",
                cpu_family="intel-core-i5",
                cores=4,
                memory_gb=8,
            ),
            display=DisplayInfo(
                width=1920, height=1080, dpr=1, color_depth=24, pixel_depth=24
            ),
            gpu=GPUInfo(
                vendor="Mesa",
                renderer="Mesa Intel",
                webgl_unmasked_vendor="Google Inc.",
                webgl_unmasked_renderer="ANGLE (Intel)",
                webgl_max_texture_size=16384,
                webgl_max_color_attachments=8,
            ),
            audio=AudioInfo(
                context_sample_rate=44100,
                audio_worklet_latency=0.01,
                destination_max_channel_count=2,
            ),
            fonts=FontInfo(family="linux-system-pack"),
            behavior=BehaviorInfo(hand="right", tremor=0.18, wpm=60, scroll_style="smooth"),
            entropy_budget=EntropyBudget(),
            timezone="UTC",
            locale="en-US",
            languages=("en-US",),
        )
        base.update(overrides)
        return DeviceProfile(**base)

    def test_valid_profile_passes(self):
        profile = self._make_valid_profile()
        profile.validate()  # should not raise

    def test_empty_id_raises(self):
        profile = self._make_valid_profile(id="")
        with pytest.raises(ValueError, match="DeviceProfile.id"):
            profile.validate()

    def test_empty_engine_raises(self):
        profile = self._make_valid_profile(engine="")
        with pytest.raises(ValueError, match="DeviceProfile.engine"):
            profile.validate()

    def test_empty_browser_name_raises(self):
        browser = BrowserInfo(name="", channel="stable", min_version="131", max_version="131", user_agent="UA")
        profile = self._make_valid_profile(browser=browser)
        with pytest.raises(ValueError, match="BrowserInfo.name"):
            profile.validate()

    def test_empty_browser_user_agent_raises(self):
        browser = BrowserInfo(name="chrome", channel="stable", min_version="131", max_version="131", user_agent="")
        profile = self._make_valid_profile(browser=browser)
        with pytest.raises(ValueError, match="BrowserInfo.user_agent"):
            profile.validate()

    def test_zero_cores_raises(self):
        device = DeviceInfo(vendor="generic", model="PC", cpu_family="intel", cores=0, memory_gb=8)
        profile = self._make_valid_profile(device=device)
        with pytest.raises(ValueError, match="DeviceInfo.cores"):
            profile.validate()

    def test_zero_memory_raises(self):
        device = DeviceInfo(vendor="generic", model="PC", cpu_family="intel", cores=4, memory_gb=0)
        profile = self._make_valid_profile(device=device)
        with pytest.raises(ValueError, match="DeviceInfo.memory_gb"):
            profile.validate()

    def test_zero_display_width_raises(self):
        display = DisplayInfo(width=0, height=1080, dpr=1, color_depth=24, pixel_depth=24)
        profile = self._make_valid_profile(display=display)
        with pytest.raises(ValueError, match="DisplayInfo.width"):
            profile.validate()

    def test_empty_gpu_vendor_raises(self):
        gpu = GPUInfo(
            vendor="",
            renderer="Mesa Intel",
            webgl_unmasked_vendor="Google Inc.",
            webgl_unmasked_renderer="ANGLE (Intel)",
            webgl_max_texture_size=16384,
            webgl_max_color_attachments=8,
        )
        profile = self._make_valid_profile(gpu=gpu)
        with pytest.raises(ValueError, match="GPUInfo.vendor"):
            profile.validate()

    def test_zero_audio_sample_rate_raises(self):
        audio = AudioInfo(context_sample_rate=0, audio_worklet_latency=0.01, destination_max_channel_count=2)
        profile = self._make_valid_profile(audio=audio)
        with pytest.raises(ValueError, match="AudioInfo.context_sample_rate"):
            profile.validate()

    def test_empty_font_family_raises(self):
        fonts = FontInfo(family="")
        profile = self._make_valid_profile(fonts=fonts)
        with pytest.raises(ValueError, match="FontInfo.family"):
            profile.validate()

    def test_zero_wpm_raises(self):
        behavior = BehaviorInfo(hand="right", tremor=0.18, wpm=0, scroll_style="smooth")
        profile = self._make_valid_profile(behavior=behavior)
        with pytest.raises(ValueError, match="BehaviorInfo.wpm"):
            profile.validate()

    def test_empty_timezone_raises(self):
        profile = self._make_valid_profile(timezone="")
        with pytest.raises(ValueError, match="DeviceProfile.timezone"):
            profile.validate()

    def test_empty_locale_raises(self):
        profile = self._make_valid_profile(locale="")
        with pytest.raises(ValueError, match="DeviceProfile.locale"):
            profile.validate()


# ---------------------------------------------------------------------------
# TEST-30-01-02: JSON loading round-trip — loaded profile matches JSON
# ---------------------------------------------------------------------------


class TestJsonRoundTrip:
    """Verify that loaded profiles faithfully reproduce the JSON source."""

    @pytest.fixture()
    def _profile_id(self) -> str:
        return "linux-chrome-stable"

    def test_round_trip_fields(self):
        profile = load_profile("linux-chrome-stable")
        data_dir = Path(__file__).parent.parent.parent / "src" / "super_browser" / "stealth" / "profiles" / "data"
        raw = json.loads((data_dir / "linux-chrome-stable.json").read_text(encoding="utf-8"))

        assert profile.id == raw["id"]
        assert profile.version == raw["version"]
        assert profile.engine == raw["engine"]
        assert profile.browser.name == raw["browser"]["name"]
        assert profile.browser.channel == raw["browser"]["channel"]
        assert profile.browser.min_version == raw["browser"]["min_version"]
        assert profile.browser.max_version == raw["browser"]["max_version"]
        assert profile.browser.user_agent == raw["browser"]["user_agent"]
        assert profile.os.name == raw["os"]["name"]
        assert profile.os.version == raw["os"]["version"]
        assert profile.os.arch == raw["os"]["arch"]
        assert profile.device.vendor == raw["device"]["vendor"]
        assert profile.device.cores == raw["device"]["cores"]
        assert profile.device.memory_gb == raw["device"]["memory_gb"]
        assert profile.display.width == raw["display"]["width"]
        assert profile.display.height == raw["display"]["height"]
        assert profile.gpu.vendor == raw["gpu"]["vendor"]
        assert profile.gpu.webgl_extensions == tuple(raw["gpu"]["webgl_extensions"])
        assert profile.fonts.list == tuple(raw["fonts"]["list"])
        assert profile.languages == tuple(raw["languages"])
        assert profile.timezone == raw["timezone"]
        assert profile.locale == raw["locale"]


# ---------------------------------------------------------------------------
# TEST-30-01-03: Host OS detection returns valid profile ID
# ---------------------------------------------------------------------------


class TestHostDetection:
    """detect_host_profile() must return a loadable profile ID."""

    def test_returns_valid_profile(self):
        profile_id = detect_host_profile()
        available = list_profiles()
        assert profile_id in available, (
            f"detect_host_profile() returned '{profile_id}' "
            f"which is not in available profiles: {available}"
        )

    def test_returns_string(self):
        result = detect_host_profile()
        assert isinstance(result, str)

    def test_linux_mapping(self):
        """Verify Linux x86_64 logic when platform matches."""
        system = platform.system()
        machine = platform.machine().lower()
        if system == "Linux" and machine in ("x86_64", "amd64"):
            assert detect_host_profile() == "linux-chrome-stable"

    def test_macos_arm_mapping(self):
        """Verify Darwin arm64 logic when platform matches."""
        if platform.system() == "Darwin" and platform.machine().lower() == "arm64":
            assert detect_host_profile() == "macos-m4-chrome-stable"

    def test_macos_x86_mapping(self):
        """Verify Darwin x86_64 logic when platform matches."""
        if platform.system() == "Darwin" and platform.machine().lower() in ("x86_64", "amd64"):
            assert detect_host_profile() == "macos-chrome-stable"

    def test_windows_mapping(self):
        """Verify Windows x86_64 logic when platform matches."""
        if platform.system() == "Windows" and platform.machine().lower() in ("x86_64", "amd64"):
            assert detect_host_profile() == "windows-chrome-stable"


# ---------------------------------------------------------------------------
# TEST-30-01-04: Non-existent profile ID raises ProfileNotFoundError
# ---------------------------------------------------------------------------


class TestProfileNotFound:
    def test_nonexistent_raises(self):
        with pytest.raises(ProfileNotFoundError, match="does-not-exist"):
            load_profile("does-not-exist")

    def test_empty_raises(self):
        with pytest.raises(ProfileNotFoundError):
            load_profile("")

    def test_is_exception(self):
        assert issubclass(ProfileNotFoundError, Exception)


# ---------------------------------------------------------------------------
# TEST-30-01-05: DeviceProfile immutability — setattr raises FrozenInstanceError
# ---------------------------------------------------------------------------


class TestImmutability:
    def test_frozen_device_profile(self):
        profile = load_profile("linux-chrome-stable")
        with pytest.raises(FrozenInstanceError):
            profile.id = "modified"  # type: ignore[misc]

    def test_frozen_browser_info(self):
        profile = load_profile("linux-chrome-stable")
        with pytest.raises(FrozenInstanceError):
            profile.browser.name = "modified"  # type: ignore[misc]

    def test_frozen_gpu_info(self):
        profile = load_profile("linux-chrome-stable")
        with pytest.raises(FrozenInstanceError):
            profile.gpu.vendor = "modified"  # type: ignore[misc]

    def test_frozen_os_info(self):
        profile = load_profile("linux-chrome-stable")
        with pytest.raises(FrozenInstanceError):
            profile.os.name = "modified"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# TEST-30-01-06: All 4 profiles load without error
# ---------------------------------------------------------------------------


class TestAllProfilesLoad:
    EXPECTED_PROFILES = [
        "linux-chrome-stable",
        "macos-chrome-stable",
        "macos-m4-chrome-stable",
        "windows-chrome-stable",
    ]

    def test_list_profiles_returns_expected(self):
        available = list_profiles()
        for pid in self.EXPECTED_PROFILES:
            assert pid in available, f"Missing profile: {pid}"

    def test_list_profiles_count(self):
        available = list_profiles()
        assert len(available) == 4

    @pytest.mark.parametrize("profile_id", EXPECTED_PROFILES)
    def test_load_each_profile(self, profile_id: str):
        profile = load_profile(profile_id)
        assert profile.id == profile_id
        profile.validate()  # must not raise

    @pytest.mark.parametrize("profile_id", EXPECTED_PROFILES)
    def test_each_profile_has_user_agent(self, profile_id: str):
        profile = load_profile(profile_id)
        assert "Chrome" in profile.browser.user_agent

    @pytest.mark.parametrize("profile_id", EXPECTED_PROFILES)
    def test_each_profile_has_extensions(self, profile_id: str):
        profile = load_profile(profile_id)
        assert len(profile.gpu.webgl_extensions) > 0

    @pytest.mark.parametrize("profile_id", EXPECTED_PROFILES)
    def test_each_profile_has_fonts(self, profile_id: str):
        profile = load_profile(profile_id)
        assert len(profile.fonts.list) > 0
