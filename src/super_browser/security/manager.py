"""SecurityManager — orchestrator for the full security check pipeline."""

from __future__ import annotations

import time
from typing import Any, Optional

from super_browser.security.approval import CommandApprover
from super_browser.security.domain_filter import DomainFilter
from super_browser.security.injection import PromptInjectionDetector
from super_browser.security.policy import ActionPolicyEngine
from super_browser.security.redactor import SecretRedactor
from super_browser.security.types import (
    CommandVerdict,
    DomainVerdict,
    InjectionVerdict,
    PolicyDecision,
    RedactionResult,
    SecurityCheckResult,
    SecurityConfig,
    SecurityEventType,
    SecurityLevel,
)


class SecurityManager:

    def __init__(self, config: SecurityConfig) -> None:
        self._config = config
        self._injection_detector = PromptInjectionDetector(config)
        self._secret_redactor = SecretRedactor(config)
        self._command_approver = CommandApprover(config)
        self._action_policy = ActionPolicyEngine(config)
        self._domain_filter = DomainFilter(config)
        self._event_callback = config.event_callback

    async def check_action(
        self,
        action: str,
        params: dict[str, Any],
        url: str = "",
        security_level: SecurityLevel = SecurityLevel.SENSITIVE,
    ) -> SecurityCheckResult:
        start = time.perf_counter()
        inj_verdict: Optional[InjectionVerdict] = None
        red_result: Optional[RedactionResult] = None
        cmd_verdict: Optional[CommandVerdict] = None
        pol_decision: Optional[PolicyDecision] = None
        dom_verdict: Optional[DomainVerdict] = None

        # 1. Domain filter
        if url and self._config.domain_filter_enabled:
            dom_verdict = self._domain_filter.check(url)
            if not dom_verdict.allowed:
                await self._emit_event(SecurityEventType.DOMAIN_BLOCKED, {
                    "action": action, "url": url, "pattern": dom_verdict.matched_pattern,
                })
                elapsed = (time.perf_counter() - start) * 1000
                return SecurityCheckResult(
                    passed=False, domain_verdict=dom_verdict,
                    total_check_time_ms=elapsed, blocked_by="domain_filter",
                )

        # 2. Action policy
        pol_decision = self._action_policy.evaluate(action, url)
        if pol_decision.verdict == "deny":
            await self._emit_event(SecurityEventType.ACTION_BLOCKED, {
                "action": action, "url": url, "reason": pol_decision.reason,
            })
            elapsed = (time.perf_counter() - start) * 1000
            return SecurityCheckResult(
                passed=False, policy_decision=pol_decision,
                total_check_time_ms=elapsed, blocked_by="action_policy",
            )
        if pol_decision.verdict == "confirm":
            approved = await self._action_policy.confirm_action(pol_decision, {
                "action": action, "params": params, "url": url,
            })
            if not approved:
                await self._emit_event(SecurityEventType.ACTION_BLOCKED, {
                    "action": action, "url": url, "reason": "User denied confirmation",
                })
                elapsed = (time.perf_counter() - start) * 1000
                return SecurityCheckResult(
                    passed=False, policy_decision=pol_decision,
                    total_check_time_ms=elapsed, blocked_by="action_policy_confirm",
                )
            await self._emit_event(SecurityEventType.ACTION_CONFIRMED, {
                "action": action, "url": url,
            })

        # Checks below only for SENSITIVE and DANGEROUS
        if security_level in (SecurityLevel.SENSITIVE, SecurityLevel.DANGEROUS):
            # 3. Injection detection
            if self._config.injection_detection_enabled:
                for key, value in params.items():
                    if isinstance(value, str):
                        inj_verdict = self._injection_detector.scan(value)
                        if inj_verdict.blocked:
                            await self._emit_event(SecurityEventType.INJECTION_BLOCKED, {
                                "action": action, "param": key,
                                "risk_level": inj_verdict.risk_level.value,
                            })
                            elapsed = (time.perf_counter() - start) * 1000
                            return SecurityCheckResult(
                                passed=False, injection_verdict=inj_verdict,
                                total_check_time_ms=elapsed, blocked_by="injection_detector",
                            )

            # 4. Secret redaction
            if self._config.redaction_enabled:
                for key, value in list(params.items()):
                    if isinstance(value, str):
                        red_result = self._secret_redactor.redact(value)
                        if red_result.was_redacted:
                            params[key] = red_result.redacted_text
                            await self._emit_event(SecurityEventType.SECRET_REDACTED, {
                                "action": action, "param": key,
                                "count": red_result.redaction_count,
                            })

        # 5. Command approval (DANGEROUS only)
        if security_level == SecurityLevel.DANGEROUS and self._config.command_approval_enabled:
            cmd_str = f"{action} {' '.join(str(v) for v in params.values())}"
            cmd_verdict = await self._command_approver.evaluate(cmd_str)
            if not cmd_verdict.is_approved:
                await self._emit_event(SecurityEventType.COMMAND_DENIED, {
                    "action": action, "safety": cmd_verdict.safety.value,
                    "pattern": cmd_verdict.matched_pattern,
                })
                elapsed = (time.perf_counter() - start) * 1000
                return SecurityCheckResult(
                    passed=False, command_verdict=cmd_verdict,
                    total_check_time_ms=elapsed, blocked_by="command_approver",
                )

        await self._emit_event(SecurityEventType.SECURITY_CHECK_PASSED, {
            "action": action, "security_level": security_level.value,
        })
        elapsed = (time.perf_counter() - start) * 1000
        return SecurityCheckResult(
            passed=True,
            injection_verdict=inj_verdict,
            redaction_result=red_result,
            command_verdict=cmd_verdict,
            policy_decision=pol_decision,
            domain_verdict=dom_verdict,
            total_check_time_ms=elapsed,
        )

    def scan_injection(self, text: str) -> InjectionVerdict:
        return self._injection_detector.scan(text)

    def redact_secrets(self, text: str) -> RedactionResult:
        return self._secret_redactor.redact(text)

    async def approve_command(self, command: str, context: str = "") -> CommandVerdict:
        return await self._command_approver.evaluate(command, context)

    def evaluate_policy(self, action: str, url: str = "") -> PolicyDecision:
        return self._action_policy.evaluate(action, url)

    def check_domain(self, url: str) -> DomainVerdict:
        return self._domain_filter.check(url)

    async def _emit_event(self, event_type: SecurityEventType, details: dict) -> None:
        if self._event_callback:
            try:
                result = self._event_callback(event_type, details)
                if hasattr(result, '__await__'):
                    await result
            except Exception:
                pass

    @property
    def injection_pattern_count(self) -> int:
        return self._injection_detector.pattern_count

    @property
    def secret_pattern_count(self) -> int:
        return self._secret_redactor.pattern_count

    @property
    def policy_rule_count(self) -> int:
        return self._action_policy.rule_count
