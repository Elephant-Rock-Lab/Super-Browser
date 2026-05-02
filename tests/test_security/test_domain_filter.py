"""Tests for DomainFilter."""

from super_browser.security.domain_filter import DomainFilter
from super_browser.security.types import SecurityConfig


def _filter(**kwargs) -> DomainFilter:
    config = SecurityConfig(**kwargs)
    return DomainFilter(config)


class TestBlocklist:
    def test_blocked(self):
        f = _filter(domain_blocklist=("*.malware.com", "*.phishing.net"))
        v = f.check("https://evil.malware.com/page")
        assert v.allowed is False
        assert v.matched_pattern == "*.malware.com"

    def test_not_blocked(self):
        f = _filter(domain_blocklist=("*.malware.com",))
        v = f.check("https://safe.example.com")
        assert v.allowed is True


class TestAllowlist:
    def test_allowed(self):
        f = _filter(domain_allowlist=("*.example.com", "trusted.org"))
        v = f.check("https://sub.example.com/page")
        assert v.allowed is True

    def test_exact_match(self):
        f = _filter(domain_allowlist=("trusted.org",))
        v = f.check("https://trusted.org/page")
        assert v.allowed is True

    def test_not_in_allowlist(self):
        f = _filter(domain_allowlist=("*.example.com",))
        v = f.check("https://unknown.com")
        assert v.allowed is False


class TestEmptyLists:
    def test_empty_allows_all(self):
        f = _filter()
        v = f.check("https://anything.com/page")
        assert v.allowed is True


class TestPrecedence:
    def test_blocklist_over_allowlist(self):
        f = _filter(
            domain_allowlist=("*.example.com",),
            domain_blocklist=("evil.example.com",),
        )
        v = f.check("https://evil.example.com")
        assert v.allowed is False
        assert v.matched_pattern == "evil.example.com"


class TestEdgeCases:
    def test_no_hostname(self):
        f = _filter(domain_blocklist=("*.evil.com",))
        v = f.check("data:text/html,hello")
        assert v.allowed is True

    def test_invalid_url(self):
        f = _filter(domain_blocklist=("*.evil.com",))
        v = f.check("not-a-url")
        assert v.allowed is True  # no hostname to match

    def test_empty_url(self):
        f = _filter()
        v = f.check("")
        assert v.allowed is True


class TestCheckTime:
    def test_under_1ms(self):
        f = _filter(domain_blocklist=("*.malware.com",))
        v = f.check("https://safe.example.com")
        assert v.check_time_ms < 1.0
