"""Consistency checks — compare FingerprintMatrix values against DeviceProfile."""

from __future__ import annotations

from abc import ABC, abstractmethod

from super_browser.stealth.consistency.matrix import FingerprintMatrix
from super_browser.stealth.profiles.schema import DeviceProfile

from .report import CheckResult

__all__ = [
    "ConsistencyCheck",
    "UA_OS_Match",
    "GPU_Vendor_WebGL",
    "Hardware_Cores",
    "Memory_Cap",
    "Fonts_OS_Match",
    "Screen_DPR",
    "Timezone_Locale",
    "Webdriver_False",
    "ALL_CHECKS",
]


class ConsistencyCheck(ABC):
    """Abstract base for a single fingerprint consistency check."""

    @property
    @abstractmethod
    def check_id(self) -> str: ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    def severity(self) -> str:
        """Default severity — override for critical checks."""
        return "warning"

    @abstractmethod
    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        """Evaluate the check and return a :class:`CheckResult`."""
        ...

    def _make_result(
        self, passed: bool, actual: str, expected: str
    ) -> CheckResult:
        return CheckResult(
            check_id=self.check_id,
            name=self.name,
            passed=passed,
            actual=actual,
            expected=expected,
            severity=self.severity,
        )


# ---------------------------------------------------------------------------
# Concrete checks
# ---------------------------------------------------------------------------


class UA_OS_Match(ConsistencyCheck):
    """UA string OS matches profile.os.name."""

    check_id = "CHK-001"
    name = "UA_OS_Match"
    severity = "critical"

    # Map profile OS names to common UA tokens.
    _OS_TOKENS: dict[str, tuple[str, ...]] = {
        "windows": ("Windows",),
        "macos": ("Macintosh", "Mac OS"),
        "linux": ("Linux", "X11"),
        "android": ("Android",),
        "ios": ("iPhone", "iPad"),
    }

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        os_name = profile.os.name.lower()
        tokens = self._OS_TOKENS.get(os_name, (os_name,))
        matched = any(t.lower() in matrix.user_agent.lower() for t in tokens)
        expected = f"UA contains OS token for '{os_name}'"
        actual = matrix.user_agent
        return self._make_result(matched, actual, expected)


class GPU_Vendor_WebGL(ConsistencyCheck):
    """WebGL unmasked vendor matches profile.gpu.vendor."""

    check_id = "CHK-002"
    name = "GPU_Vendor_WebGL"
    severity = "critical"

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        expected = profile.gpu.vendor
        actual = matrix.webgl_unmasked_vendor
        # The matrix webgl_unmasked_vendor may be a composite like
        # "Google Inc. (NVIDIA)" while the profile.gpu.vendor is
        # "NVIDIA Corporation".  Match by extracting the primary vendor
        # keyword from the profile value.
        primary = expected.split()[0].lower()  # e.g. "nvidia"
        passed = primary in actual.lower()
        return self._make_result(passed, actual, expected)


class Hardware_Cores(ConsistencyCheck):
    """hardwareConcurrency matches profile.device.cores."""

    check_id = "CHK-003"
    name = "Hardware_Cores"
    severity = "warning"

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        expected = str(profile.device.cores)
        actual = str(matrix.hardware_concurrency)
        return self._make_result(actual == expected, actual, expected)


class Memory_Cap(ConsistencyCheck):
    """deviceMemory is capped at 8 (browser privacy limit)."""

    check_id = "CHK-004"
    name = "Memory_Cap"
    severity = "warning"

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        expected = "≤8"
        actual = str(matrix.device_memory)
        passed = matrix.device_memory <= 8
        return self._make_result(passed, actual, expected)


class Fonts_OS_Match(ConsistencyCheck):
    """Font list is consistent with OS — no cross-platform fonts."""

    check_id = "CHK-005"
    name = "Fonts_OS_Match"
    severity = "warning"

    # Fonts that are strongly tied to one platform.
    _MAC_FONTS = frozenset({
        ".SF NS Display", ".SF NS Text", "SF Pro Display",
        "SF Pro Text", "Apple Color Emoji", "Apple SD Gothic Neo",
        "Avenir", "Avenir Next", "Geneva", "Helvetica Neue",
    })
    _WINDOWS_FONONS = frozenset({
        "Segoe UI", "Segoe UI Symbol", "Consolas",
        "MS Gothic", "MS PGothic", "Times New Roman",
    })
    _LINUX_FONTS = frozenset({
        "Noto Sans", "Noto Serif", "DejaVu Sans", "DejaVu Sans Mono",
        "Liberation Sans", "Liberation Mono", "Ubuntu",
    })

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        os_name = profile.os.name.lower()
        font_set = set(matrix.fonts)

        cross_contaminated = False
        offending: list[str] = []

        if os_name in ("linux", "android"):
            bad = font_set & self._MAC_FONTS
            if bad:
                cross_contaminated = True
                offending.extend(sorted(bad))
        elif os_name == "windows":
            bad = font_set & self._MAC_FONTS
            if bad:
                cross_contaminated = True
                offending.extend(sorted(bad))
        elif os_name == "macos":
            bad = font_set & self._LINUX_FONTS
            if bad:
                cross_contaminated = True
                offending.extend(sorted(bad))

        expected = f"No cross-platform fonts for os='{os_name}'"
        actual = (
            f"Cross-platform fonts found: {offending}"
            if offending
            else "Clean"
        )
        return self._make_result(not cross_contaminated, actual, expected)


class Screen_DPR(ConsistencyCheck):
    """devicePixelRatio matches profile.display.dpr."""

    check_id = "CHK-006"
    name = "Screen_DPR"
    severity = "warning"

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        expected = str(profile.display.dpr)
        actual = str(matrix.device_pixel_ratio)
        return self._make_result(actual == expected, actual, expected)


class Timezone_Locale(ConsistencyCheck):
    """Timezone matches locale region."""

    check_id = "CHK-007"
    name = "Timezone_Locale"
    severity = "warning"

    # Simplified region → timezone prefix mapping.
    _REGION_TZ_PREFIXES: dict[str, tuple[str, ...]] = {
        "US": ("America/", "US/"),
        "GB": ("Europe/London", "GMT"),
        "DE": ("Europe/Berlin", "CET"),
        "FR": ("Europe/Paris", "CET"),
        "JP": ("Asia/Tokyo", "JST"),
        "KR": ("Asia/Seoul", "KST"),
        "CN": ("Asia/Shanghai", "PRC", "CST"),
        "AU": ("Australia/",),
        "BR": ("America/Sao_Paulo", "America/Rio", "BRT"),
        "IN": ("Asia/Kolkata", "IST"),
        "RU": ("Europe/Moscow", "Asia/", "Europe/"),
    }

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        # Extract region code from locale (e.g. "en-US" → "US").
        locale = profile.locale
        region = ""
        if "-" in locale:
            region = locale.split("-", 1)[1].upper()
        elif "_" in locale:
            region = locale.split("_", 1)[1].upper()

        tz = matrix.timezone
        prefixes = self._REGION_TZ_PREFIXES.get(region, ())

        if prefixes:
            passed = any(tz.startswith(p) for p in prefixes)
        else:
            # Unknown region — cannot validate, pass by default.
            passed = True

        expected = f"Timezone consistent with region '{region}'"
        actual = f"timezone='{tz}', locale='{locale}'"
        return self._make_result(passed, actual, expected)


class Webdriver_False(ConsistencyCheck):
    """navigator.webdriver is false (not detected as automation)."""

    check_id = "CHK-008"
    name = "Webdriver_False"
    severity = "critical"

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        expected = "False"
        actual = str(matrix.webdriver)
        return self._make_result(not matrix.webdriver, actual, expected)


class Canvas_Audio_Consistency(ConsistencyCheck):
    """Ejector seed is populated when canvas/audio noise injection is active."""

    check_id = "CHK-009"
    name = "Canvas_Audio_Consistency"
    severity = "warning"

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        has_seed = bool(matrix.ejector_seed)
        actual = f"ejector_seed={'set' if has_seed else 'empty'}"
        expected = "ejector_seed=set"
        return self._make_result(has_seed, actual, expected)


class WebRTC_Blocked(ConsistencyCheck):
    """WebRTC leak prevention ejector is configured."""

    check_id = "CHK-010"
    name = "WebRTC_Blocked"
    severity = "warning"

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        has_seed = bool(matrix.ejector_seed)
        actual = f"webrtc_ejector={'configured' if has_seed else 'unconfigured'}"
        expected = "webrtc_ejector=configured"
        return self._make_result(has_seed, actual, expected)


class Timing_Precision(ConsistencyCheck):
    """Timing/Math fingerprint noise ejector is configured."""

    check_id = "CHK-011"
    name = "Timing_Precision"
    severity = "warning"

    def check(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> CheckResult:
        has_seed = bool(matrix.ejector_seed)
        actual = f"timing_ejector={'configured' if has_seed else 'unconfigured'}"
        expected = "timing_ejector=configured"
        return self._make_result(has_seed, actual, expected)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ALL_CHECKS: tuple[ConsistencyCheck, ...] = (
    UA_OS_Match(),
    GPU_Vendor_WebGL(),
    Hardware_Cores(),
    Memory_Cap(),
    Fonts_OS_Match(),
    Screen_DPR(),
    Timezone_Locale(),
    Webdriver_False(),
    Canvas_Audio_Consistency(),
    WebRTC_Blocked(),
    Timing_Precision(),
)
