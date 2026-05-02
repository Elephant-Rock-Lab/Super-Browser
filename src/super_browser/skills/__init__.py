"""GAP-05 Domain Skill Registry — public API."""

from super_browser.skills.activation import compute_activation
from super_browser.skills.markdown import parse_markdown_skills
from super_browser.skills.registry import SkillRegistry
from super_browser.skills.types import (
    ActivationConfig,
    DomainSkill,
    InvalidSkillFormat,
    SelectorConflictWarning,
    SkillImportError,
    SkillProvenance,
    SkillQuery,
    SkillSizeExceeded,
    SkillStatus,
)

__all__ = [
    "ActivationConfig",
    "DomainSkill",
    "InvalidSkillFormat",
    "SelectorConflictWarning",
    "SkillImportError",
    "SkillProvenance",
    "SkillQuery",
    "SkillRegistry",
    "SkillSizeExceeded",
    "SkillStatus",
    "compute_activation",
    "parse_markdown_skills",
]
