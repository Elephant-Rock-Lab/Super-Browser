"""GAP-10 Security Envelope — unified security for browser automation."""

from super_browser.security.types import (
    CommandSafety,
    CommandVerdict,
    DomainVerdict,
    InjectionMatch,
    InjectionPattern,
    InjectionVerdict,
    PolicyDecision,
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
from super_browser.security.injection import PromptInjectionDetector
from super_browser.security.redactor import SecretRedactor
from super_browser.security.approval import CommandApprover
from super_browser.security.policy import ActionPolicyEngine
from super_browser.security.domain_filter import DomainFilter
from super_browser.security.credential_vault import CredentialVault
from super_browser.security.manager import SecurityManager

__all__ = [
    "CommandSafety",
    "CommandVerdict",
    "DomainVerdict",
    "InjectionMatch",
    "InjectionPattern",
    "InjectionVerdict",
    "PolicyDecision",
    "PolicyRule",
    "PolicyVerdict",
    "RedactionEntry",
    "RedactionResult",
    "RiskLevel",
    "SecretType",
    "SecurityCheckResult",
    "SecurityConfig",
    "SecurityEventType",
    "SecurityLevel",
    "PromptInjectionDetector",
    "SecretRedactor",
    "CommandApprover",
    "ActionPolicyEngine",
    "DomainFilter",
    "SecurityManager",
    "CredentialVault",
]
