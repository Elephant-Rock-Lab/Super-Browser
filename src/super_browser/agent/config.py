"""Agent core configuration.

Composed into :class:`Config` as ``agent``.
Fields control the agent loop, LLM defaults, and feature flags.

.. deprecated:: 2.0
   :class:`SuperBrowserConfig` was removed in v2.0. All fields are now
   directly on :class:`AgentConfig`.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentConfig:
    """Agent sub-config — LLM client fields and feature flags.

    The top-level attributes (``llm_provider``, ``llm_model``, ``llm_api_key``)
    supply values needed by :func:`create_llm`.

    Feature flags (``enable_recovery``, ``enable_budget``, etc.) were previously
    on the removed :class:`SuperBrowserConfig`. They are now directly here.
    """

    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_api_key: str = ""
    # -- Agent loop --
    max_steps: int = 50
    loop_window_size: int = 20
    stagnation_threshold: int = 3
    nudge_levels: tuple[int, ...] = (5, 8, 12)
    max_delegation_concurrency: int = 4
    # -- LLM --
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096
    # -- Tracing (legacy, now in TracingConfig) --
    trace_enabled: bool = True
    trace_output_dir: str = ""
    # -- Feature flags --
    enable_recovery: bool = False
    enable_budget: bool = False
    enable_security: bool = False
    enable_vision: bool = False
    vision_cache_dir: str = ""
    enable_stealth: bool = False
    enable_skills: bool = False
    skills_dir: str = ""
    enable_verification: bool = False
