"""StealthActionPolicy — allow/deny/confirm rules for dangerous browser actions."""

from __future__ import annotations

import json
import logging
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import Optional

from super_browser.security.types import PolicyDecision, PolicyRule, PolicyVerdict

logger = logging.getLogger(__name__)

_DEFAULT_RULES = [
    PolicyRule(action="navigate", verdict=PolicyVerdict.ALLOW),
    PolicyRule(action="click", verdict=PolicyVerdict.ALLOW),
    PolicyRule(action="fill", verdict=PolicyVerdict.ALLOW),
    PolicyRule(action="observe", verdict=PolicyVerdict.ALLOW),
    PolicyRule(action="file_upload", verdict=PolicyVerdict.CONFIRM, reason="File uploads require user approval"),
    PolicyRule(action="form_submit", verdict=PolicyVerdict.CONFIRM, reason="Form submissions require user approval"),
]


class StealthActionPolicy:
    """Loads and evaluates action policy rules for stealth-gated actions."""

    def __init__(self, policy_file: Optional[str] = None, confirm_callback=None) -> None:
        self._rules: list[PolicyRule] = list(_DEFAULT_RULES)
        self._confirm_callback = confirm_callback
        if policy_file:
            self.load_rules(policy_file)

    def load_rules(self, policy_file: str) -> None:
        path = Path(policy_file)
        try:
            text = path.read_text(encoding="utf-8")
            data = json.loads(text)
            raw_rules = data.get("rules", [])
            self._rules = [
                PolicyRule(
                    action=r["action"],
                    verdict=PolicyVerdict(r["verdict"]),
                    url_pattern=r.get("url_pattern"),
                    reason=r.get("reason"),
                )
                for r in raw_rules
            ]
        except (OSError, json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Failed to load policy file %s: %s", policy_file, exc)

    def evaluate(self, action: str, url: str = "") -> PolicyDecision:
        start = time.monotonic()
        for rule in self._rules:
            if rule.action != action:
                continue
            if rule.url_pattern and url and not fnmatch(url, rule.url_pattern):
                continue
            eval_ms = (time.monotonic() - start) * 1000
            return PolicyDecision(
                verdict=rule.verdict,
                matched_rule=rule,
                reason=rule.reason,
                evaluation_time_ms=eval_ms,
            )
        return PolicyDecision(
            verdict=PolicyVerdict.ALLOW,
            evaluation_time_ms=(time.monotonic() - start) * 1000,
        )

    async def confirm_action(self, decision: PolicyDecision, action_details: dict = None) -> bool:
        if decision.verdict != PolicyVerdict.CONFIRM:
            return decision.verdict == PolicyVerdict.ALLOW
        if self._confirm_callback is None:
            return False
        import asyncio
        result = self._confirm_callback(decision, action_details or {})
        if asyncio.iscoroutine(result):
            result = await result
        return bool(result)

    def add_rule(self, rule: PolicyRule) -> None:
        self._rules.append(rule)

    @property
    def rule_count(self) -> int:
        return len(self._rules)
