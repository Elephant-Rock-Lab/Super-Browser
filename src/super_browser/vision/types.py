"""GAP-06 vision types — enums, dataclasses, and configuration."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Optional


class VisionTaskComplexity(StrEnum):
    SIMPLE = "simple"
    COMPLEX = "complex"
    AMBIGUOUS = "ambiguous"


class CaptchaType(StrEnum):
    TEXT_DISTORTED = "text_distorted"
    IMAGE_GRID = "image_grid"
    RECAPTCHA_V2 = "recaptcha_v2"
    HCAPTCHA = "hcaptcha"
    SLIDER = "slider"


class VisionProviderName(StrEnum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    UITARS = "uitars"


@dataclass(frozen=True)
class VisionLocation:
    x: float
    y: float
    width: Optional[float] = None
    height: Optional[float] = None
    confidence: float = 0.0


@dataclass(frozen=True)
class CaptchaSolution:
    solved: bool
    answer: Optional[str] = None
    grid_selections: Optional[list[int]] = None
    slider_position: Optional[float] = None
    provider: Optional[str] = None
    confidence: float = 0.0
    token_cost: float = 0.0
    duration_ms: float = 0.0


@dataclass(frozen=True)
class StateInference:
    answer: str
    labels: dict[str, bool] = field(default_factory=dict)
    confidence: float = 0.0
    model: Optional[str] = None
    token_cost: float = 0.0
    duration_ms: float = 0.0
    provider: Optional[str] = None


@dataclass(frozen=True)
class OCRWord:
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float


@dataclass
class CascadeConfig:
    simple_provider: VisionProviderName = VisionProviderName.UITARS
    simple_model: Optional[str] = None
    complex_provider: VisionProviderName = VisionProviderName.OPENAI
    complex_model: str = "gpt-4o-mini"
    ambiguous_provider: VisionProviderName = VisionProviderName.ANTHROPIC
    ambiguous_model: str = "claude-sonnet-4-20250514"
    confidence_threshold_for_escalation: float = 0.6
    max_escalations: int = 2


@dataclass
class VisionCacheEntry:
    key: str
    description: str
    response: Any
    image_dhash: int
    created_at: float = field(default_factory=time.monotonic)
    last_hit: float = field(default_factory=time.monotonic)
    hit_count: int = 0


@dataclass
class VisionCostTracker:
    _total_cost: float = 0.0
    _call_count: int = 0

    def record(self, cost: float) -> None:
        self._total_cost += cost
        self._call_count += 1

    @property
    def total_cost(self) -> float:
        return self._total_cost

    @property
    def call_count(self) -> int:
        return self._call_count
