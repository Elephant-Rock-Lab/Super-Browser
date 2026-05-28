"""Tests for security types — enums, dataclasses, SecurityConfig."""

import pytest

from super_browser.security.types import (
    CommandSafety,
    CommandVerdict,
    InjectionMatch,
    InjectionPattern,
    InjectionVerdict,
    PolicyRule,
    PolicyVerdict,
    RedactionEntry,
    RedactionResult,
    RiskLevel,
    SecretType,
    SecurityCheckResult,
    SecurityConfig,
    SecurityEventType,
    SecurityLevel,
)


class TestRiskLevel:
    def test_values(self):
        assert RiskLevel.LOW == "low"
        assert RiskLevel.CRITICAL == "critical"
        assert len(RiskLevel) == 4


class TestInjectionPattern:
    def test_values(self):
        assert InjectionPattern.SYSTEM_OVERRIDE == "system_override"
        assert len(InjectionPattern) == 7


class TestSecretType:
    def test_values(self):
        assert SecretType.ANTHROPIC_KEY == "anthropic_key"
        assert len(SecretType) == 14


class TestPolicyVerdict:
    def test_values(self):
        assert PolicyVerdict.ALLOW == "allow"
        assert PolicyVerdict.DENY == "deny"
        assert PolicyVerdict.CONFIRM == "confirm"


class TestCommandSafety:
    def test_values(self):
        assert CommandSafety.SAFE == "safe"
        assert CommandSafety.DANGEROUS == "dangerous"
        assert len(CommandSafety) == 5


class TestSecurityLevel:
    def test_values(self):
        assert SecurityLevel.SAFE == "safe"
        assert SecurityLevel.SENSITIVE == "sensitive"
        assert SecurityLevel.DANGEROUS == "dangerous"


class TestSecurityEventType:
    def test_values(self):
        assert SecurityEventType.INJECTION_BLOCKED == "injection_blocked"
        assert len(SecurityEventType) == 8


class TestSecurityConfig:
    def test_defaults(self):
        config = SecurityConfig()
        assert config.injection_detection_enabled is True
        assert config.redaction_enabled is True
        assert config.domain_filter_enabled is True
        assert config.command_approval_enabled is True
        assert config.llm_auto_approve_enabled is False

    def test_frozen(self):
        config = SecurityConfig()
        with pytest.raises(AttributeError):
            config.injection_detection_enabled = False

    def test_custom_patterns(self):
        config = SecurityConfig(custom_secret_patterns=[("test", r"TEST_\w+")])
        assert len(config.custom_secret_patterns) == 1


class TestInjectionVerdict:
    def test_match_count(self):
        v = InjectionVerdict(blocked=True, matches=[
            InjectionMatch(InjectionPattern.SYSTEM_OVERRIDE, "n", "t", 0, RiskLevel.HIGH),
            InjectionMatch(InjectionPattern.JAILBREAK, "n2", "t2", 5, RiskLevel.CRITICAL),
        ])
        assert v.match_count == 2

    def test_default_empty(self):
        v = InjectionVerdict(blocked=False)
        assert v.match_count == 0


class TestRedactionResult:
    def test_redaction_count(self):
        r = RedactionResult(was_redacted=True, redacted_text="safe", entries=[
            RedactionEntry(SecretType.ANTHROPIC_KEY, 0, 10, "[R]", "abc123"),
        ])
        assert r.redaction_count == 1


class TestCommandVerdict:
    def test_is_approved_safe(self):
        v = CommandVerdict(safety=CommandSafety.SAFE)
        assert v.is_approved is True

    def test_is_approved_dangerous(self):
        v = CommandVerdict(safety=CommandSafety.DANGEROUS)
        assert v.is_approved is False

    def test_is_approved_llm_approved(self):
        v = CommandVerdict(safety=CommandSafety.LLM_APPROVED)
        assert v.is_approved is True

    def test_is_approved_llm_denied(self):
        v = CommandVerdict(safety=CommandSafety.LLM_DENIED)
        assert v.is_approved is False


class TestPolicyRule:
    def test_frozen(self):
        rule = PolicyRule(action="click", verdict=PolicyVerdict.ALLOW)
        with pytest.raises(AttributeError):
            rule.action = "other"

    def test_optional_fields(self):
        rule = PolicyRule(action="click", verdict=PolicyVerdict.ALLOW)
        assert rule.url_pattern is None
        assert rule.reason is None


class TestSecurityCheckResult:
    def test_passed(self):
        r = SecurityCheckResult(passed=True, total_check_time_ms=1.0)
        assert r.passed is True
        assert r.blocked_by is None

    def test_blocked(self):
        r = SecurityCheckResult(passed=False, blocked_by="domain_filter")
        assert r.passed is False
        assert r.blocked_by == "domain_filter"
