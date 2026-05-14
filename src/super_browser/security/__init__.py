"""GAP-10 Security Envelope — unified security for browser automation."""

from super_browser.security.action_redaction import (
    configure_redaction,
    is_redaction_configured,
    redact_args,
    redact_context,
    redact_result_dict,
)
from super_browser.security.approval import CommandApprover
from super_browser.security.domain_filter import DomainFilter
from super_browser.security.injection import PromptInjectionDetector
from super_browser.security.manager import SecurityManager
from super_browser.security.policy import ActionPolicyEngine
from super_browser.security.redactor import SecretRedactor
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


# CredentialVault requires cryptography — lazy import to avoid
# ImportError when [security] extras are not installed.
def __getattr__(name):
    if name == "CredentialVault":
        from super_browser.security.credential_vault import CredentialVault
        return CredentialVault
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "configure_redaction",
    "is_redaction_configured",
    "redact_args",
    "redact_context",
    "redact_result_dict",
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
