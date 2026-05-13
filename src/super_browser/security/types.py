"""GAP-10 security types — enums, dataclasses, and configuration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class RiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class InjectionPattern(StrEnum):
    SYSTEM_OVERRIDE = "system_override"
    ROLE_MANIPULATION = "role_manipulation"
    DATA_EXFILTRATION = "data_exfiltration"
    JAILBREAK = "jailbreak"
    INSTRUCTION_INJECTION = "instruction_injection"
    UNICODE_OBFUSCATION = "unicode_obfuscation"
    CONTEXT_POISONING = "context_poisoning"


class SecretType(StrEnum):
    ANTHROPIC_KEY = "anthropic_key"
    OPENROUTER_KEY = "openrouter_key"
    OPENAI_KEY = "openai_key"
    GITHUB_TOKEN = "github_token"
    AWS_ACCESS_KEY = "aws_access_key"
    AWS_SECRET_KEY = "aws_secret_key"
    GOOGLE_API_KEY = "google_api_key"
    SLACK_TOKEN = "slack_token"
    STRIPE_KEY = "stripe_key"
    PASSWORD = "password"
    PEM_KEY = "pem_key"
    JWT = "jwt"
    DATABASE_URL = "database_url"
    GENERIC_TOKEN = "generic_token"


class PolicyVerdict(StrEnum):
    ALLOW = "allow"
    DENY = "deny"
    CONFIRM = "confirm"


class CommandSafety(StrEnum):
    SAFE = "safe"
    DANGEROUS = "dangerous"
    AMBIGUOUS = "ambiguous"
    LLM_APPROVED = "llm_approved"
    LLM_DENIED = "llm_denied"


class SecurityLevel(StrEnum):
    SAFE = "safe"
    SENSITIVE = "sensitive"
    DANGEROUS = "dangerous"


class SecurityEventType(StrEnum):
    INJECTION_BLOCKED = "injection_blocked"
    SECRET_REDACTED = "secret_redacted"
    COMMAND_DENIED = "command_denied"
    COMMAND_APPROVED = "command_approved"
    ACTION_BLOCKED = "action_blocked"
    ACTION_CONFIRMED = "action_confirmed"
    DOMAIN_BLOCKED = "domain_blocked"
    SECURITY_CHECK_PASSED = "security_check_passed"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SecurityConfig:
    injection_detection_enabled: bool = True
    unicode_detection_enabled: bool = True
    redaction_enabled: bool = True
    redaction_log_path: Optional[str] = None
    custom_secret_patterns: tuple[tuple[str, str], ...] = ()
    command_approval_enabled: bool = True
    llm_auto_approve_enabled: bool = False
    llm_auto_approve_client: Any = None
    llm_auto_approve_model: str = "claude-sonnet-4-20250514"
    llm_auto_approve_timeout: float = 2.0
    policy_file: Optional[str] = None
    confirm_callback: Optional[Callable] = None
    domain_filter_enabled: bool = True
    domain_allowlist: tuple[str, ...] = ()
    domain_blocklist: tuple[str, ...] = ()
    event_callback: Optional[Callable] = None


# ---------------------------------------------------------------------------
# Injection Detection
# ---------------------------------------------------------------------------

@dataclass
class InjectionMatch:
    pattern: InjectionPattern
    pattern_name: str
    matched_text: str
    position: int
    risk_level: RiskLevel


@dataclass
class InjectionVerdict:
    blocked: bool
    matches: list[InjectionMatch] = field(default_factory=list)
    sanitized_text: str = ""
    risk_level: RiskLevel = RiskLevel.LOW
    scan_time_ms: float = 0.0

    @property
    def match_count(self) -> int:
        return len(self.matches)


# ---------------------------------------------------------------------------
# Secret Redaction
# ---------------------------------------------------------------------------

@dataclass
class RedactionEntry:
    secret_type: SecretType
    original_start: int
    original_end: int
    placeholder: str
    sha256_hash6: str


@dataclass
class RedactionResult:
    was_redacted: bool
    redacted_text: str
    entries: list[RedactionEntry] = field(default_factory=list)
    scan_time_ms: float = 0.0

    @property
    def redaction_count(self) -> int:
        return len(self.entries)


# ---------------------------------------------------------------------------
# Command Approval
# ---------------------------------------------------------------------------

@dataclass
class CommandVerdict:
    safety: CommandSafety
    matched_pattern: Optional[str] = None
    reason: Optional[str] = None
    classification_time_ms: float = 0.0

    @property
    def is_approved(self) -> bool:
        return self.safety in (CommandSafety.SAFE, CommandSafety.LLM_APPROVED)


# ---------------------------------------------------------------------------
# Action Policy
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PolicyRule:
    action: str
    verdict: PolicyVerdict
    url_pattern: Optional[str] = None
    reason: Optional[str] = None


@dataclass
class PolicyDecision:
    verdict: PolicyVerdict
    matched_rule: Optional[PolicyRule] = None
    reason: Optional[str] = None
    evaluation_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Domain Filtering
# ---------------------------------------------------------------------------

@dataclass
class DomainVerdict:
    allowed: bool
    matched_pattern: Optional[str] = None
    reason: Optional[str] = None
    check_time_ms: float = 0.0


# ---------------------------------------------------------------------------
# Aggregate Result
# ---------------------------------------------------------------------------

@dataclass
class SecurityCheckResult:
    passed: bool
    injection_verdict: Optional[InjectionVerdict] = None
    redaction_result: Optional[RedactionResult] = None
    command_verdict: Optional[CommandVerdict] = None
    policy_decision: Optional[PolicyDecision] = None
    domain_verdict: Optional[DomainVerdict] = None
    total_check_time_ms: float = 0.0
    blocked_by: Optional[str] = None
