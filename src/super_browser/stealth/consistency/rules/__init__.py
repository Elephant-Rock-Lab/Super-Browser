"""Rule registry — single source of truth for the consistency rule set.

Rule families:
  GPU_RULES          R-001..R-003, R-024, R-025
  USER_AGENT_RULES   R-004..R-007
  NAVIGATOR_RULES    R-008..R-010
  SCREEN_RULES       R-011..R-012b
  LOCALE_RULES       R-013, R-014, R-014b
  AUDIO_RULES        R-015, R-016, R-016b
  FONT_RULES         R-017
  BEHAVIOR_RULES     R-018
  EXTRAS_RULES       R-019..R-030

Total: 30 rules.
"""

from __future__ import annotations

from super_browser.stealth.consistency.rules.audio import AUDIO_RULES
from super_browser.stealth.consistency.rules.behavior import BEHAVIOR_RULES, EXTRAS_RULES
from super_browser.stealth.consistency.rules.fonts import FONT_RULES
from super_browser.stealth.consistency.rules.gpu import GPU_RULES
from super_browser.stealth.consistency.rules.locale import LOCALE_RULES
from super_browser.stealth.consistency.rules.navigator import NAVIGATOR_RULES
from super_browser.stealth.consistency.rules.screen import SCREEN_RULES
from super_browser.stealth.consistency.rules.user_agent import USER_AGENT_RULES

__all__ = ["ALL_RULES"]

ALL_RULES: list = [
    *GPU_RULES,
    *USER_AGENT_RULES,
    *NAVIGATOR_RULES,
    *SCREEN_RULES,
    *LOCALE_RULES,
    *AUDIO_RULES,
    *FONT_RULES,
    *BEHAVIOR_RULES,
    *EXTRAS_RULES,
]
