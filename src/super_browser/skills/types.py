"""GAP-05 skills types — enums, dataclasses, and error hierarchy."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from fnmatch import fnmatch
from typing import Any, Optional


class SkillProvenance(StrEnum):
    DISCOVERED = "discovered"
    LEARNED = "learned"
    MANUAL = "manual"


class SkillStatus(StrEnum):
    ACTIVE = "active"
    STALE = "stale"
    ARCHIVED = "archived"


@dataclass
class DomainSkill:
    skill_id: str
    domain: str
    name: str
    description: str = ""
    selectors: dict[str, str] = field(default_factory=dict)
    actions: dict[str, Any] = field(default_factory=dict)
    quirks: list[str] = field(default_factory=list)
    wait_strategy: dict[str, Any] = field(default_factory=dict)
    preferred_tier: dict[str, str] = field(default_factory=dict)
    url_patterns: list[str] = field(default_factory=list)
    provenance: SkillProvenance = SkillProvenance.LEARNED
    status: SkillStatus = SkillStatus.ACTIVE
    access_count: int = 0
    last_used: float = 0.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    version: int = 1

    def touch(self) -> None:
        self.access_count += 1
        self.last_used = time.monotonic()
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        return {
            "skill_id": self.skill_id,
            "domain": self.domain,
            "name": self.name,
            "description": self.description,
            "selectors": self.selectors,
            "actions": self.actions,
            "quirks": self.quirks,
            "wait_strategy": self.wait_strategy,
            "preferred_tier": self.preferred_tier,
            "url_patterns": self.url_patterns,
            "provenance": self.provenance.value,
            "status": self.status.value,
            "access_count": self.access_count,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainSkill:
        data = dict(data)
        data["provenance"] = SkillProvenance(data["provenance"])
        data["status"] = SkillStatus(data.get("status", "active"))
        valid_fields = {k for k in cls.__dataclass_fields__ if k != "_activation_score"}
        return cls(**{k: v for k, v in data.items() if k in valid_fields})

    def size_bytes(self) -> int:
        return len(json.dumps(self.to_dict()).encode("utf-8"))

    def matches_url(self, url: str) -> bool:
        if not self.url_patterns:
            return True
        return any(fnmatch(url, pattern) for pattern in self.url_patterns)


@dataclass(frozen=True)
class ActivationConfig:
    decay_factor: float = 0.5
    activation_threshold: float = 1.0
    base_level_weight: float = 1.0
    recency_weight: float = 1.0
    context_weight: float = 0.5
    stale_penalty: float = -2.0
    max_context_boost: float = 2.0


@dataclass
class SkillQuery:
    domain: Optional[str] = None
    provenance: Optional[SkillProvenance] = None
    status: Optional[SkillStatus] = None
    name_contains: Optional[str] = None
    min_access_count: int = 0


# -- Error hierarchy --

class SkillImportError(Exception):
    pass


class InvalidSkillFormat(SkillImportError):
    pass


class SelectorConflictWarning(SkillImportError):
    pass


class SkillSizeExceeded(SkillImportError):
    pass
