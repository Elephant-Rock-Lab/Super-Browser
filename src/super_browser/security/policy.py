"""ActionPolicyEngine — allow/deny/confirm rule evaluation."""

from __future__ import annotations

import json
import time
from fnmatch import fnmatch
from typing import Any, Optional

from super_browser.security.types import (
    PolicyDecision,
    PolicyRule,
    PolicyVerdict,
    SecurityConfig,
)


class ActionPolicyEngine:

    def __init__(self, config: SecurityConfig) -> None:
        self._rules: list[PolicyRule] = []
        self._confirm_callback = config.confirm_callback
        if config.policy_file:
            self.load_rules(config.policy_file)

    def load_rules(self, policy_file: str) -> None:
        with open(policy_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        for rule_data in data.get("rules", []):
            self._rules.append(PolicyRule(
                action=rule_data["action"],
                verdict=PolicyVerdict(rule_data["verdict"]),
                url_pattern=rule_data.get("url_pattern"),
                reason=rule_data.get("reason"),
            ))

    def evaluate(self, action: str, url: str = "") -> PolicyDecision:
        start = time.perf_counter()
        for rule in self._rules:
            if rule.action != action and rule.action != "*":
                continue
            if rule.url_pattern and url:
                from urllib.parse import urlparse
                hostname = urlparse(url).hostname or ""
                if not fnmatch(hostname, rule.url_pattern) and not fnmatch(url, rule.url_pattern):
                    continue
            elapsed = (time.perf_counter() - start) * 1000
            return PolicyDecision(
                verdict=rule.verdict,
                matched_rule=rule,
                reason=rule.reason,
                evaluation_time_ms=elapsed,
            )
        elapsed = (time.perf_counter() - start) * 1000
        return PolicyDecision(verdict=PolicyVerdict.ALLOW, evaluation_time_ms=elapsed)

    async def confirm_action(self, decision: PolicyDecision, action_details: dict) -> bool:
        if self._confirm_callback is None:
            return False
        result = self._confirm_callback(decision, action_details)
        if hasattr(result, '__await__'):
            result = await result
        return bool(result)

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    @property
    def rule_count(self) -> int:
        return len(self._rules)
