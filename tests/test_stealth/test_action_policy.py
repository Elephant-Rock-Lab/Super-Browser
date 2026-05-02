"""Tests for StealthActionPolicy — rule loading, evaluation, confirmation."""

import json
import tempfile
from pathlib import Path

import pytest

from super_browser.security.types import PolicyDecision, PolicyRule, PolicyVerdict
from super_browser.stealth.action_policy import StealthActionPolicy


class TestDefaultRules:
    def test_default_rule_count(self):
        policy = StealthActionPolicy()
        assert policy.rule_count == 6

    def test_navigate_allowed(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("navigate")
        assert d.verdict == PolicyVerdict.ALLOW

    def test_click_allowed(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("click")
        assert d.verdict == PolicyVerdict.ALLOW

    def test_fill_allowed(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("fill")
        assert d.verdict == PolicyVerdict.ALLOW

    def test_observe_allowed(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("observe")
        assert d.verdict == PolicyVerdict.ALLOW

    def test_file_upload_needs_confirm(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("file_upload")
        assert d.verdict == PolicyVerdict.CONFIRM

    def test_form_submit_needs_confirm(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("form_submit")
        assert d.verdict == PolicyVerdict.CONFIRM

    def test_unknown_action_allowed(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("unknown_action")
        assert d.verdict == PolicyVerdict.ALLOW


class TestLoadJsonRules:
    def test_load_valid_file(self):
        rules = {
            "rules": [
                {"action": "navigate", "verdict": "allow"},
                {"action": "click", "verdict": "deny", "reason": "no clicking"},
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rules, f)
            f.flush()
            policy = StealthActionPolicy(policy_file=f.name)
            assert policy.rule_count == 2
            assert policy.evaluate("click").verdict == PolicyVerdict.DENY

    def test_load_invalid_file_keeps_defaults(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("not json")
            f.flush()
            policy = StealthActionPolicy(policy_file=f.name)
            assert policy.rule_count == 6

    def test_missing_file_keeps_defaults(self):
        policy = StealthActionPolicy(policy_file="/nonexistent/path.json")
        assert policy.rule_count == 6

    def test_url_pattern_matching(self):
        rules = {
            "rules": [
                {"action": "navigate", "verdict": "deny", "url_pattern": "https://evil.com/*"},
                {"action": "navigate", "verdict": "allow"},
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rules, f)
            f.flush()
            policy = StealthActionPolicy(policy_file=f.name)
            d = policy.evaluate("navigate", "https://evil.com/page")
            assert d.verdict == PolicyVerdict.DENY
            d2 = policy.evaluate("navigate", "https://good.com/page")
            assert d2.verdict == PolicyVerdict.ALLOW

    def test_first_match_wins(self):
        rules = {
            "rules": [
                {"action": "click", "verdict": "deny"},
                {"action": "click", "verdict": "allow"},
            ]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rules, f)
            f.flush()
            policy = StealthActionPolicy(policy_file=f.name)
            assert policy.evaluate("click").verdict == PolicyVerdict.DENY


class TestEvaluation:
    def test_evaluation_time_ms(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("navigate")
        assert d.evaluation_time_ms >= 0

    def test_matched_rule_set(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("file_upload")
        assert d.matched_rule is not None
        assert d.matched_rule.action == "file_upload"
        assert d.reason is not None

    def test_no_match_no_rule(self):
        policy = StealthActionPolicy()
        d = policy.evaluate("nonexistent")
        assert d.matched_rule is None


class TestAddRule:
    def test_add_rule(self):
        policy = StealthActionPolicy()
        initial = policy.rule_count
        policy.add_rule(PolicyRule(action="custom", verdict=PolicyVerdict.DENY))
        assert policy.rule_count == initial + 1
        assert policy.evaluate("custom").verdict == PolicyVerdict.DENY


class TestConfirmAction:
    def test_confirm_with_callback(self):
        cb = lambda decision, details: True
        policy = StealthActionPolicy(confirm_callback=cb)
        d = PolicyDecision(verdict=PolicyVerdict.CONFIRM, matched_rule=PolicyRule(action="test", verdict=PolicyVerdict.CONFIRM))

        async def _test():
            result = await policy.confirm_action(d)
            assert result is True

        import asyncio
        asyncio.run(_test())

    def test_confirm_without_callback(self):
        policy = StealthActionPolicy()
        d = PolicyDecision(verdict=PolicyVerdict.CONFIRM)

        async def _test():
            result = await policy.confirm_action(d)
            assert result is False

        import asyncio
        asyncio.run(_test())

    def test_allow_passes_through(self):
        policy = StealthActionPolicy()
        d = PolicyDecision(verdict=PolicyVerdict.ALLOW)

        async def _test():
            result = await policy.confirm_action(d)
            assert result is True

        import asyncio
        asyncio.run(_test())

    def test_deny_returns_false(self):
        policy = StealthActionPolicy()
        d = PolicyDecision(verdict=PolicyVerdict.DENY)

        async def _test():
            result = await policy.confirm_action(d)
            assert result is False

        import asyncio
        asyncio.run(_test())
