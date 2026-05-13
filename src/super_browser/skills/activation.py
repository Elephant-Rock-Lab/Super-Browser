"""ACT-R activation scoring for domain skills."""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from typing import Optional

from super_browser.skills.types import ActivationConfig, DomainSkill, SkillStatus


def compute_activation(
    skill: DomainSkill,
    current_task: str = "",
    config: ActivationConfig = ActivationConfig(),
    *,
    similarity_fn: Optional[Callable[[str, str], float]] = None,
) -> float:
    base_level = config.base_level_weight * math.log(skill.access_count + 1)

    if skill.last_used > 0:
        hours_since = (time.monotonic() - skill.last_used) / 3600.0
        recency_bonus = config.recency_weight * (config.decay_factor ** hours_since)
    else:
        recency_bonus = 0.0

    context_boost = 0.0
    if current_task and similarity_fn and skill.description:
        similarity = similarity_fn(current_task, skill.description)
        context_boost = min(
            config.context_weight * similarity,
            config.max_context_boost,
        )

    stale_penalty = config.stale_penalty if skill.status == SkillStatus.STALE else 0.0

    return base_level + recency_bonus + context_boost + stale_penalty
