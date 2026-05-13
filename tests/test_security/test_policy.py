"""Tests for ActionPolicyEngine."""

import json

from super_browser.security.policy import ActionPolicyEngine
from super_browser.security.types import PolicyDecision, PolicyRule, PolicyVerdict, SecurityConfig


def _engine(**kwargs) -> ActionPolicyEngine:
    config = SecurityConfig(**kwargs)
    return ActionPolicyEngine(config)


class TestDefaultAllow:
    def test_no_rules_allows(self):
        e = _engine()
        d = e.evaluate("click", "https://example.com")
        assert d.verdict == PolicyVerdict.ALLOW

    def test_unknown_action_allowed(self):
        e = _engine()
        d = e.evaluate("scroll", "https://example.com")
        assert d.verdict == PolicyVerdict.ALLOW


class TestPolicyFile:
    def test_load_json(self, tmp_path):
        policy = {
            "rules": [
                {"action": "click", "verdict": "allow"},
                {"action": "form_submit", "verdict": "deny", "url_pattern": "*.bank.com",
                 "reason": "No form submissions on banking sites"},
                {"action": "file_upload", "verdict": "confirm", "reason": "Needs approval"},
            ]
        }
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        e = _engine(policy_file=str(path))
        assert e.rule_count == 3

    def test_allow_rule(self, tmp_path):
        policy = {"rules": [{"action": "click", "verdict": "allow"}]}
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        e = _engine(policy_file=str(path))
        d = e.evaluate("click", "https://example.com")
        assert d.verdict == PolicyVerdict.ALLOW
        assert d.matched_rule is not None

    def test_deny_rule(self, tmp_path):
        policy = {"rules": [
            {"action": "form_submit", "verdict": "deny", "url_pattern": "*.bank.com"},
        ]}
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        e = _engine(policy_file=str(path))
        d = e.evaluate("form_submit", "https://secure.bank.com")
        assert d.verdict == PolicyVerdict.DENY
        assert d.matched_rule.url_pattern == "*.bank.com"

    def test_confirm_rule(self, tmp_path):
        policy = {"rules": [{"action": "file_upload", "verdict": "confirm"}]}
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        e = _engine(policy_file=str(path))
        d = e.evaluate("file_upload", "https://docs.example.com")
        assert d.verdict == PolicyVerdict.CONFIRM

    def test_url_pattern_mismatch(self, tmp_path):
        policy = {"rules": [
            {"action": "form_submit", "verdict": "deny", "url_pattern": "*.bank.com"},
        ]}
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        e = _engine(policy_file=str(path))
        d = e.evaluate("form_submit", "https://safe.example.com")
        assert d.verdict == PolicyVerdict.ALLOW

    def test_first_match_wins(self, tmp_path):
        policy = {"rules": [
            {"action": "click", "verdict": "allow"},
            {"action": "click", "verdict": "deny"},
        ]}
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        e = _engine(policy_file=str(path))
        d = e.evaluate("click")
        assert d.verdict == PolicyVerdict.ALLOW


class TestWildcardAction:
    def test_wildcard_matches_all(self, tmp_path):
        policy = {"rules": [
            {"action": "*", "verdict": "deny"},
        ]}
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        e = _engine(policy_file=str(path))
        d = e.evaluate("anything")
        assert d.verdict == PolicyVerdict.DENY


class TestConfirmCallback:
    def test_callback_approved(self):
        async def on_confirm(decision, details):
            return True

        e = _engine(confirm_callback=on_confirm)
        approved = asyncio.run(e.confirm_action(
            PolicyDecision(verdict=PolicyVerdict.CONFIRM),
            {"action": "test"},
        ))
        assert approved is True

    def test_callback_denied(self):
        async def on_confirm(decision, details):
            return False

        e = _engine(confirm_callback=on_confirm)
        approved = asyncio.run(e.confirm_action(
            PolicyDecision(verdict=PolicyVerdict.CONFIRM),
            {"action": "test"},
        ))
        assert approved is False

    def test_no_callback_returns_false(self):
        e = _engine()
        approved = asyncio.run(e.confirm_action(
            PolicyDecision(verdict=PolicyVerdict.CONFIRM),
            {"action": "test"},
        ))
        assert approved is False


class TestAddRule:
    def test_add_rule(self):
        e = _engine()
        assert e.rule_count == 0
        e.add_rule(PolicyRule(action="click", verdict=PolicyVerdict.ALLOW))
        assert e.rule_count == 1
        d = e.evaluate("click")
        assert d.verdict == PolicyVerdict.ALLOW


class TestEvaluationTime:
    def test_under_5ms(self, tmp_path):
        policy = {"rules": [{"action": "click", "verdict": "allow"}]}
        path = tmp_path / "policy.json"
        path.write_text(json.dumps(policy), encoding="utf-8")
        e = _engine(policy_file=str(path))
        d = e.evaluate("click")
        assert d.evaluation_time_ms < 5.0


import asyncio  # noqa: E402
