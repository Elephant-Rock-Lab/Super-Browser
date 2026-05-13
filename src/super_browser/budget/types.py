"""Token budget types — enums and dataclasses for GAP-09."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class BudgetScope(StrEnum):
    DAILY = "daily"
    PER_ACTION = "per_action"
    PER_TURN = "per_turn"


class AlertLevel(StrEnum):
    WARNING = "warning"
    CRITICAL = "critical"
    EXHAUSTED = "exhausted"


class CostTier(StrEnum):
    TIER_1 = "tier_1"
    TIER_2 = "tier_2"
    TIER_3_MINI = "tier_3_mini"
    TIER_3_SONNET = "tier_3_sonnet"
    TIER_3_OPUS = "tier_3_opus"


class SelectionStrategy(StrEnum):
    ROUND_ROBIN = "round_robin"
    RANDOM = "random"
    LEAST_RECENTLY_USED = "lru"
    COST_OPTIMIZED = "cost_optimized"


class CompressionStrategy(StrEnum):
    TOOL_OUTPUT_PRUNE = "tool_output_prune"
    TURN_SUMMARIZE = "turn_summarize"
    HEAD_TAIL_PROTECT = "head_tail_protect"


# ---------------------------------------------------------------------------
# Budget Alerts
# ---------------------------------------------------------------------------

@dataclass
class BudgetAlert:
    level: AlertLevel
    scope: BudgetScope
    current_spend: float
    cap: float
    remaining: float
    timestamp: float = field(default_factory=time.time)

    @property
    def usage_pct(self) -> float:
        return (self.current_spend / self.cap) * 100 if self.cap > 0 else 0.0


@dataclass
class BudgetBlock:
    exhausted_scope: BudgetScope
    current_spend: float
    cap: float
    alert: BudgetAlert


# ---------------------------------------------------------------------------
# Token Usage Record
# ---------------------------------------------------------------------------

@dataclass
class TokenUsageRecord:
    record_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: float = field(default_factory=time.time)
    model: str = ""
    provider: str = ""
    credential_id: str = ""
    cost_tier: CostTier = CostTier.TIER_1
    input_tokens: int = 0
    output_tokens: int = 0
    estimated_cost_usd: float = 0.0
    action_name: str = ""
    trace_id: str = ""

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "timestamp": self.timestamp,
            "model": self.model,
            "provider": self.provider,
            "credential_id": self.credential_id,
            "cost_tier": str(self.cost_tier),
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "estimated_cost_usd": self.estimated_cost_usd,
            "action_name": self.action_name,
            "trace_id": self.trace_id,
        }


# ---------------------------------------------------------------------------
# Cost Estimator
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ModelPricing:
    model: str
    provider: str
    input_cost_per_1m: float
    output_cost_per_1m: float
    context_window: int


# ---------------------------------------------------------------------------
# Budget Config & State
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class BudgetConfig:
    daily_cap_usd: float = 10.0
    per_action_cap_usd: float = 0.50
    per_turn_token_limit: int = 100_000
    warning_threshold: float = 0.80
    critical_threshold: float = 0.95
    context_compress_threshold: float = 0.75


@dataclass
class BudgetState:
    daily_spend_usd: float = 0.0
    daily_reset_timestamp: float = field(default_factory=time.time)
    turn_tokens_used: int = 0
    action_spend_usd: float = 0.0


# ---------------------------------------------------------------------------
# Model Cascade
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CascadeTier:
    tier: CostTier
    model: str
    provider: str
    cost_multiplier: float
    max_escalations: int = 3


@dataclass(frozen=True)
class CascadeConfig:
    tiers: tuple[CascadeTier, ...] = ()
    default_tier: CostTier = CostTier.TIER_1
    max_total_escalations: int = 3


@dataclass
class CascadeResult:
    selected_tier: CascadeTier
    model: str
    provider: str
    escalated_from: Optional[CostTier] = None
    escalation_count: int = 0
    estimated_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Context Compressor
# ---------------------------------------------------------------------------

@dataclass
class CompressionResult:
    original_tokens: int
    compressed_tokens: int
    compression_ratio: float
    strategies_applied: list[CompressionStrategy]
    duration_ms: float
    handoff_frame_applied: bool = True


# ---------------------------------------------------------------------------
# Credential Pool
# ---------------------------------------------------------------------------

@dataclass
class CredentialEntry:
    credential_id: str
    provider: str
    api_key: str
    is_active: bool = True
    last_used: float = 0.0
    cumulative_spend_usd: float = 0.0
    cooldown_until: float = 0.0
    consecutive_failures: int = 0

    @property
    def is_on_cooldown(self) -> bool:
        return self.cooldown_until > time.time()


@dataclass
class CredentialRotated:
    previous_credential_id: str
    new_credential_id: str
    provider: str
    reason: str
    cooldown_seconds: float
    timestamp: float = field(default_factory=time.time)


# ---------------------------------------------------------------------------
# Circuit Breaker
# ---------------------------------------------------------------------------

@dataclass
class CircuitState:
    provider: str
    consecutive_failures: int = 0
    last_failure_time: float = 0.0
    is_open: bool = False
    cooldown_seconds: float = 120.0
