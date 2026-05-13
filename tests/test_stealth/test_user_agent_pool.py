"""Tests for UserAgentPool (BATCH-12 / TASK-02).

Test IDs:
    TEST-12-02-03 — UAPool returns realistic Chrome UA strings
    TEST-12-02-04 — UAPool rotation does not repeat within min_rotation gap
    TEST-12-02-05 — UAPool respects configured OS distribution
"""

import re

from super_browser.stealth.user_agent_pool import UserAgentPool

# Regex to validate a realistic Chrome UA string
_UA_RE = re.compile(
    r"Mozilla/5\.0 \(.+\) AppleWebKit/537\.36 \(KHTML, like Gecko\) Chrome/\d+\.\d+\.\d+\.\d+ Safari/537\.36"
)


class TestRealisticChromeUAStrings:
    """TEST-12-02-03: UAPool returns realistic Chrome UA strings."""

    def test_all_pool_entries_match_chrome_pattern(self):
        pool = UserAgentPool(seed=42)
        for _ in range(pool.pool_size):
            ua = pool.get_next()
            assert _UA_RE.match(ua), f"UA does not match Chrome pattern: {ua!r}"

    def test_pool_has_at_least_15_entries(self):
        pool = UserAgentPool()
        assert pool.pool_size >= 15, f"Pool size {pool.pool_size} < 15"

    def test_chrome_versions_in_expected_range(self):
        pool = UserAgentPool()
        versions = pool.chrome_versions
        assert min(versions) >= 130, f"Min version {min(versions)} < 130"
        assert max(versions) <= 140, f"Max version {max(versions)} > 140"

    def test_get_random_also_returns_valid_ua(self):
        pool = UserAgentPool(seed=42)
        for _ in range(50):
            ua = pool.get_random()
            assert _UA_RE.match(ua), f"Random UA does not match pattern: {ua!r}"


class TestRotationNoRepeat:
    """TEST-12-02-04: UAPool rotation does not repeat within min_rotation gap."""

    def test_no_immediate_repeat_with_gap_3(self):
        pool = UserAgentPool(min_rotation_gap=3, seed=42)
        history: list[str] = []
        for _ in range(20):
            ua = pool.get_next()
            # The UA should not appear in the last `min_rotation_gap` entries
            recent = history[-3:] if len(history) >= 3 else history
            assert ua not in recent, (
                f"UA {ua!r} repeated within gap of 3. "
                f"Recent: {recent}"
            )
            history.append(ua)

    def test_no_immediate_repeat_with_gap_1(self):
        pool = UserAgentPool(min_rotation_gap=1, seed=42)
        prev = None
        for _ in range(20):
            ua = pool.get_next()
            if prev is not None:
                assert ua != prev, "UA repeated immediately with gap=1"
            prev = ua

    def test_rotation_covers_multiple_uas(self):
        pool = UserAgentPool(min_rotation_gap=2, seed=42)
        uas = {pool.get_next() for _ in range(10)}
        assert len(uas) > 1, "Rotation should return multiple distinct UAs"


class TestOSDistribution:
    """TEST-12-02-05: UAPool respects configured OS distribution."""

    def test_pool_contains_multiple_os_labels(self):
        pool = UserAgentPool()
        os_labels = pool.os_labels
        assert len(os_labels) >= 3, f"Expected ≥3 OS labels, got: {os_labels}"

    def test_pool_contains_windows_entries(self):
        pool = UserAgentPool()
        os_labels = pool.os_labels
        assert any("Windows" in label for label in os_labels), (
            f"Expected Windows in OS labels: {os_labels}"
        )

    def test_pool_contains_macos_entries(self):
        pool = UserAgentPool()
        os_labels = pool.os_labels
        assert any("macOS" in label for label in os_labels), (
            f"Expected macOS in OS labels: {os_labels}"
        )

    def test_pool_contains_linux_entries(self):
        pool = UserAgentPool()
        os_labels = pool.os_labels
        assert any("Linux" in label for label in os_labels), (
            f"Expected Linux in OS labels: {os_labels}"
        )

    def test_all_entries_have_known_os(self):
        """Every UA in the pool should be categorised under a known OS."""
        pool = UserAgentPool()
        known = {"Windows 10", "Windows 11", "macOS 13", "macOS 14", "Linux"}
        from super_browser.stealth.user_agent_pool import _CHROME_VERSIONS, _UA_TEMPLATES
        for template in _UA_TEMPLATES:
            for ver in _CHROME_VERSIONS:
                ua = template.format(ver=ver)  # noqa: F841
                os_label = pool._extract_os_label(template)
                assert os_label in known, f"Unknown OS label: {os_label!r} for template"
