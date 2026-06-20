"""Core types and abstractions for the adversarial assessment framework.

This module defines the fundamental data structures and protocols that
everything else builds upon. It is intentionally dependency-free.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Protocol,
    TypeVar,
    runtime_checkable,
)

# ============================================================================
# Exceptions
# ============================================================================

class JSUnsupportedError(Exception):
    """Raised when a backend cannot evaluate JavaScript.

    StubBackend raises this for any expression not explicitly configured
    via ``set_js_response()``. Vectors and the harness use this to
    return INCONCLUSIVE rather than interpreting ``None`` as a real
    browser observation.
    """


# ============================================================================
# Enums
# ============================================================================

class Verdict(Enum):
    """Outcome of evaluating a single vector or target."""
    CLEAN = "clean"
    CHALLENGED = "challenged"
    FLAGGED = "flagged"
    INCONCLUSIVE = "inconclusive"
    SKIPPED = "skipped"

    def __str__(self) -> str:
        return self.value


class Severity(Enum):
    """How serious a vector failure is."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"

    def __str__(self) -> str:
        return self.value


class Tier(Enum):
    """Classification of detection sophistication."""
    FINGERPRINT = "fingerprint"
    AUTOMATION = "automation"
    EJECTOR = "ejector"
    BEHAVIORAL = "behavioral"
    NETWORK = "network"
    EXTERNAL_SCANNER = "external_scanner"
    EXTERNAL_VENDOR = "external_vendor"
    CONTROLLED = "controlled"

    def __str__(self) -> str:
        return self.value


# ============================================================================
# Result types
# ============================================================================

@dataclass(frozen=True)
class VectorResult:
    """Result of evaluating a single detection vector."""
    vector_id: str
    tier: Tier
    name: str
    verdict: Verdict
    score: float  # 0.0-1.0
    details: dict[str, Any] = field(default_factory=dict)
    severity: Severity = Severity.INFO
    duration_ms: float = 0.0
    error: str | None = None

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            object.__setattr__(
                self, "score", max(0.0, min(1.0, self.score))
            )

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tier"] = str(self.tier)
        d["verdict"] = str(self.verdict)
        d["severity"] = str(self.severity)
        return d


@dataclass(frozen=True)
class TierSummary:
    """Aggregated results for a single tier."""
    tier: Tier
    score: float  # 0.0-1.0
    vector_count: int
    passed: int
    failed: int
    skipped: int
    inconclusive: int
    avg_duration_ms: float
    critical_failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tier"] = str(self.tier)
        return d


@dataclass(frozen=True)
class AssessmentReport:
    """Complete assessment report."""
    run_id: str
    timestamp: str
    overall_score: float
    tier_summaries: list[TierSummary]
    results: list[VectorResult]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "timestamp": self.timestamp,
            "overall_score": round(self.overall_score, 4),
            "tier_summaries": [ts.to_dict() for ts in self.tier_summaries],
            "results": [r.to_dict() for r in self.results],
            "metadata": self.metadata,
        }

    @property
    def total_targets(self) -> int:
        return len(self.results)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, default=str)


# ============================================================================
# Protocols (structural subtyping — no inheritance required)
# ============================================================================

T = TypeVar("T")


@runtime_checkable
class BrowserBackend(Protocol):
    """Protocol for browser automation backends.

    Implementations: PlaywrightBackend, PatchrightBackend, SuperBrowserBackend,
    StubBackend (for testing).
    """

    async def new_page(self) -> Page:
        ...

    async def close(self) -> None:
        ...

    async def __aenter__(self) -> BrowserBackend:
        ...

    async def __aexit__(self, *exc: object) -> None:
        ...


@runtime_checkable
class Page(Protocol):
    """Protocol for a browser page/tab."""

    async def goto(self, url: str, *, wait_until: str = "networkidle", timeout: int = 30000) -> None:
        ...

    async def evaluate(self, expression: str) -> Any:
        ...

    async def screenshot(self, *, path: str | None = None, full_page: bool = False) -> bytes | None:
        ...

    async def close(self) -> None:
        ...

    @property
    def url(self) -> str | None:
        ...


@runtime_checkable
class Vector(Protocol):
    """Protocol for a detection vector.

    A vector is the atomic unit of detection. It can be:
    - A JS payload evaluated in the browser (client-side)
    - A server-side check against request headers
    - A behavioral analysis requiring interaction recording
    - A composite of multiple signals
    """

    @property
    def vector_id(self) -> str:
        ...

    @property
    def tier(self) -> Tier:
        ...

    @property
    def name(self) -> str:
        ...

    @property
    def description(self) -> str:
        ...

    @property
    def severity(self) -> Severity:
        ...

    @property
    def requires_browser(self) -> bool:
        """True if this vector needs a live browser to evaluate."""
        ...

    @property
    def requires_interaction(self) -> bool:
        """True if this vector needs human-like interaction."""
        ...

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        """Evaluate this vector and return a result."""
        ...


@dataclass(frozen=True)
class EvaluationContext:
    """Context passed to vector evaluation."""
    page: Page | None = None
    browser: BrowserBackend | None = None
    server_url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# Abstract base classes (for implementations that prefer inheritance)
# ============================================================================

class BaseVector(ABC):
    """Base class for vector implementations."""

    def __init__(
        self,
        vector_id: str,
        tier: Tier,
        name: str,
        description: str,
        severity: Severity = Severity.INFO,
    ) -> None:
        self._vector_id = vector_id
        self._tier = tier
        self._name = name
        self._description = description
        self._severity = severity

    @property
    def vector_id(self) -> str: return self._vector_id
    @property
    def tier(self) -> Tier: return self._tier
    @property
    def name(self) -> str: return self._name
    @property
    def description(self) -> str: return self._description
    @property
    def severity(self) -> Severity: return self._severity

    @property
    def requires_browser(self) -> bool:
        return True

    @property
    def requires_interaction(self) -> bool:
        return False

    @abstractmethod
    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        ...


class BaseReporter(ABC):
    """Base class for report formatters."""

    @abstractmethod
    def render(self, report: AssessmentReport) -> str:
        ...

    @abstractmethod
    def extension(self) -> str:
        ...

    def write(self, report: AssessmentReport, path: Path) -> None:
        path.write_text(self.render(report), encoding="utf-8")


class BaseEngine(ABC):
    """Base class for scoring engines."""

    @abstractmethod
    def compute(self, results: list[VectorResult]) -> AssessmentReport:
        ...


# ============================================================================
# Utilities
# ============================================================================

def now_utc() -> str:
    """ISO 8601 timestamp in UTC."""
    return datetime.now(timezone.utc).isoformat()


def verdict_emoji(verdict: Verdict) -> str:
    return {
        Verdict.CLEAN: "✅",
        Verdict.CHALLENGED: "⚠️",
        Verdict.FLAGGED: "🚫",
        Verdict.INCONCLUSIVE: "❓",
        Verdict.SKIPPED: "⏭️",
    }.get(verdict, "❓")


def severity_emoji(severity: Severity) -> str:
    return {
        Severity.CRITICAL: "🔴",
        Severity.WARNING: "🟡",
        Severity.INFO: "🔵",
    }.get(severity, "⚪")
