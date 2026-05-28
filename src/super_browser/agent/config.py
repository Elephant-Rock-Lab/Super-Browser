"""Agent core configuration.

Composed into :class:`Config` as ``agent.core``.
Fields control the agent loop, LLM defaults, and feature flags.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SuperBrowserConfig:
    max_steps: int = 50
    loop_window_size: int = 20
    stagnation_threshold: int = 3
    nudge_levels: tuple[int, ...] = (5, 8, 12)
    max_delegation_concurrency: int = 4
    default_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    trace_enabled: bool = True
    trace_output_dir: str = ""
    enable_recovery: bool = False
    enable_budget: bool = False
    enable_security: bool = False
    enable_vision: bool = False
    vision_cache_dir: str = ""
    enable_stealth: bool = False
    enable_skills: bool = False
    skills_dir: str = ""
    enable_verification: bool = False
