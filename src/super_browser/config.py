"""Unified configuration for Super Browser.

Composes all existing sub-configs into a single :class:`Config` dataclass
with construction helpers for env vars, YAML files, and plain dicts.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# AgentConfig is defined in this module (no import from agent.config)
from super_browser.browser.config import SessionConfig
from super_browser.budget.types import BudgetConfig
from super_browser.security.types import SecurityConfig
from super_browser.stealth.types import ProxyTier, StealthConfig

# ---------------------------------------------------------------------------
# New sub-configs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConsistencyConfig:
    """Configuration for the consistency fingerprint engine.

    When ``enabled`` is *True* (default), StealthManager will load a device
    profile, derive a deterministic FingerprintMatrix, and inject JavaScript
    overrides via the inject pipeline instead of the legacy UA-pool approach.

    When *False*, the legacy ``UserAgentPool`` + ``custom_init_scripts``
    path is used (backward compatible).
    """

    enabled: bool = True
    profile_id: Optional[str] = None  # None = auto-detect host OS
    seed: str = "default"


@dataclass(frozen=True)
class CloakConfig:
    """Configuration for the optional CloakBrowser stealth backend.

    When ``cloak_enabled`` is *True* (default) and ``cloakbrowser`` is
    installed, BrowserSession will use CloakBrowser's patched Chromium
    binary instead of vanilla Patchright.  If ``cloakbrowser`` is not
    installed the session silently falls back to Patchright.
    """

    cloak_enabled: bool = True
    cloak_fingerprint_seed: Optional[int] = None
    cloak_humanize: bool = False
    cloak_humanize_preset: str = "default"
    cloak_geoip: bool = False
    cloak_platform: Optional[str] = None


@dataclass(frozen=True)
class TracingConfig:
    """Tracing / observability sub-config (new in unified Config)."""

    enabled: bool = False
    sink_type: str = "console"  # "console" | "file" | "otlp"
    output_dir: str = ""  # Directory for FileSink trace output


@dataclass(frozen=True)
class NetworkConfig:
    """Configuration for Chromium-native networking."""

    browser_fetch: bool = True            # Enable session.fetch()
    llm_via_browser: bool = False          # Route LLM calls through browser (opt-in)


@dataclass(frozen=True)
class MemoryConfig:
    """Memory sub-config — per-domain agent memory."""

    memory_enabled: bool = False
    memory_dir: str = "~/.config/super-browser/memory"
    memory_ttl_days: int = 30


@dataclass(frozen=True)
class AgentConfig:
    """Agent sub-config: LLM settings and feature flags.

    All former ``SuperBrowserConfig`` fields are flattened here as
    top-level attributes. The ``core`` nested wrapper is removed in v2.0.
    """

    # -- LLM client --
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-20250514"
    llm_api_key: str = ""

    # -- Agent loop (formerly SuperBrowserConfig) --
    max_steps: int = 50
    loop_window_size: int = 20
    stagnation_threshold: int = 3
    nudge_levels: tuple[int, ...] = (5, 8, 12)
    max_delegation_concurrency: int = 4
    default_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # -- Feature flags (formerly SuperBrowserConfig) --
    enable_recovery: bool = False
    enable_budget: bool = False
    enable_security: bool = False
    enable_vision: bool = False
    vision_cache_dir: str = ""
    enable_stealth: bool = False
    enable_skills: bool = False
    skills_dir: str = ""
    enable_verification: bool = False

    # -- Tracing (formerly SuperBrowserConfig) --
    trace_enabled: bool = True
    trace_output_dir: str = ""


# ---------------------------------------------------------------------------
# Unified Config
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Config:
    """Top-level configuration that composes all sub-configs.

    Construction helpers:
        * :meth:`from_env`  — reads ``SB_*`` environment variables
        * :meth:`from_yaml` — loads from a YAML file
        * :meth:`from_dict` — creates from a plain dict
    """

    browser: SessionConfig = field(default_factory=SessionConfig)
    agent: AgentConfig = field(default_factory=AgentConfig)
    stealth: StealthConfig = field(default_factory=StealthConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    security: SecurityConfig = field(default_factory=SecurityConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    memory: MemoryConfig = field(default_factory=MemoryConfig)
    cloak: CloakConfig = field(default_factory=CloakConfig)
    consistency: ConsistencyConfig = field(default_factory=ConsistencyConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)

    # ------------------------------------------------------------------
    # from_env
    # ------------------------------------------------------------------

    @classmethod
    def from_env(cls) -> Config:
        """Build a :class:`Config` from ``SB_*`` environment variables.

        Supported variables:

        ================ ==========================
        Env var          Target field
        ================ ==========================
        SB_LLM_PROVIDER  agent.llm_provider
        SB_LLM_MODEL     agent.llm_model
        SB_LLM_API_KEY   agent.llm_api_key
        SB_HEADLESS      browser.headless
        SB_PROXY_URL     stealth.proxy_url
        SB_DAILY_BUDGET  budget.daily_cap_usd
        SB_STEALTH_TIER  stealth.proxy_tier
        SB_TRACING_ENABLED tracing.enabled
        SB_TRACING_SINK  tracing.sink_type
        ================ ==========================
        """
        # -- Agent --------------------------------------------------
        agent_kw: dict = {}
        _env_str(agent_kw, "SB_LLM_PROVIDER", "llm_provider")
        _env_str(agent_kw, "SB_LLM_MODEL", "llm_model")
        _env_str(agent_kw, "SB_LLM_API_KEY", "llm_api_key")

        # -- Browser ------------------------------------------------
        browser_kw: dict = {}
        _env_bool(browser_kw, "SB_HEADLESS", "headless")

        # -- Stealth ------------------------------------------------
        stealth_kw: dict = {}
        _env_str(stealth_kw, "SB_PROXY_URL", "proxy_url")
        if "SB_STEALTH_TIER" in os.environ:
            stealth_kw["proxy_tier"] = ProxyTier(os.environ["SB_STEALTH_TIER"])

        # -- Budget -------------------------------------------------
        budget_kw: dict = {}
        _env_float(budget_kw, "SB_DAILY_BUDGET", "daily_cap_usd")

        # -- Tracing ------------------------------------------------
        tracing_kw: dict = {}
        _env_bool(tracing_kw, "SB_TRACING_ENABLED", "enabled")
        _env_str(tracing_kw, "SB_TRACING_SINK", "sink_type")
        _env_str(tracing_kw, "SB_TRACING_OUTPUT_DIR", "output_dir")

        # -- Memory -------------------------------------------------
        memory_kw: dict = {}
        _env_bool(memory_kw, "SB_MEMORY_ENABLED", "memory_enabled")
        _env_str(memory_kw, "SB_MEMORY_DIR", "memory_dir")
        _env_int(memory_kw, "SB_MEMORY_TTL_DAYS", "memory_ttl_days")

        # -- Cloak ---------------------------------------------------
        cloak_kw: dict = {}
        _env_bool(cloak_kw, "SB_CLOAK_ENABLED", "cloak_enabled")
        _env_int(cloak_kw, "SB_CLOAK_FINGERPRINT_SEED", "cloak_fingerprint_seed")
        _env_bool(cloak_kw, "SB_CLOAK_HUMANIZE", "cloak_humanize")
        _env_str(cloak_kw, "SB_CLOAK_HUMANIZE_PRESET", "cloak_humanize_preset")
        _env_bool(cloak_kw, "SB_CLOAK_GEOIP", "cloak_geoip")
        _env_str(cloak_kw, "SB_CLOAK_PLATFORM", "cloak_platform")

        # -- Consistency -------------------------------------------
        consistency_kw: dict = {}
        _env_bool(consistency_kw, "SB_CONSISTENCY_ENABLED", "enabled")
        _env_str(consistency_kw, "SB_CONSISTENCY_PROFILE_ID", "profile_id")
        _env_str(consistency_kw, "SB_CONSISTENCY_SEED", "seed")

        # -- Network -----------------------------------------------
        network_kw: dict = {}
        _env_bool(network_kw, "SB_BROWSER_FETCH", "browser_fetch")
        _env_bool(network_kw, "SB_LLM_VIA_BROWSER", "llm_via_browser")

        return cls(
            browser=SessionConfig(**browser_kw),
            agent=AgentConfig(**agent_kw),
            stealth=StealthConfig(**stealth_kw),
            budget=BudgetConfig(**budget_kw),
            security=SecurityConfig(),
            tracing=TracingConfig(**tracing_kw),
            memory=MemoryConfig(**memory_kw),
            cloak=CloakConfig(**cloak_kw),
            consistency=ConsistencyConfig(**consistency_kw),
            network=NetworkConfig(**network_kw),
        )

    # ------------------------------------------------------------------
    # from_yaml
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, path: str | Path) -> Config:
        """Load a :class:`Config` from a YAML file.

        The YAML structure mirrors the sub-config names::

            browser:
              headless: true
            agent:
              llm_provider: anthropic
            stealth:
              proxy_url: "http://proxy:8080"
            budget:
              daily_cap_usd: 15.0
            tracing:
              enabled: true
              sink_type: file
        """
        try:
            import yaml  # type: ignore[import-untyped]
        except ImportError as exc:
            raise ImportError(
                "PyYAML is required for Config.from_yaml(). "
                "Install it with: pip install pyyaml"
            ) from exc

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(
                f"Config file not found: {path}. "
                "Create one with Config.from_dict() first or check the path."
            )
        with path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}

        return cls.from_dict(data)

    # ------------------------------------------------------------------
    # from_dict
    # ------------------------------------------------------------------

    @classmethod
    def from_dict(cls, d: dict) -> Config:
        """Build a :class:`Config` from a nested dictionary.

        Unrecognised keys inside each sub-dict are silently ignored so that
        YAML files can contain extra metadata without breaking construction.
        """
        return cls(
            browser=_build_sub(SessionConfig, d.get("browser", {})),
            agent=_build_agent(d.get("agent", {})),
            stealth=_build_sub(StealthConfig, d.get("stealth", {})),
            budget=_build_sub(BudgetConfig, d.get("budget", {})),
            security=_build_sub(SecurityConfig, d.get("security", {})),
            tracing=_build_sub(TracingConfig, d.get("tracing", {})),
            memory=_build_sub(MemoryConfig, d.get("memory", {})),
            cloak=_build_sub(CloakConfig, d.get("cloak", {})),
            consistency=_build_sub(ConsistencyConfig, d.get("consistency", {})),
            network=_build_sub(NetworkConfig, d.get("network", {})),
        )

    # ------------------------------------------------------------------
    # validate
    # ------------------------------------------------------------------

    def validate(self) -> list[str]:
        """Return a list of validation error strings (empty == valid)."""
        errors: list[str] = []

        # Agent checks
        valid_providers = ("anthropic", "openai")
        if self.agent.llm_provider not in valid_providers:
            errors.append(
                f"agent.llm_provider must be one of {valid_providers}, "
                f"got {self.agent.llm_provider!r}"
            )
        if not self.agent.llm_api_key:
            errors.append("agent.llm_api_key is required for LLM access")

        # Budget checks
        if self.budget.daily_cap_usd <= 0:
            errors.append(
                f"budget.daily_cap_usd must be > 0, "
                f"got {self.budget.daily_cap_usd}"
            )

        # Browser checks
        vp = self.browser.viewport
        if vp[0] <= 0 or vp[1] <= 0:
            errors.append(
                f"browser.viewport dimensions must be positive, got {vp}"
            )

        # Tracing checks
        valid_sinks = ("console", "file", "otlp")
        if self.tracing.sink_type not in valid_sinks:
            errors.append(
                f"tracing.sink_type must be one of {valid_sinks}, "
                f"got {self.tracing.sink_type!r}"
            )

        return errors


# ======================================================================
# Private helpers
# ======================================================================





def _env_str(target: dict, env_key: str, field_name: str) -> None:
    val = os.environ.get(env_key)
    if val is not None:
        target[field_name] = val


def _env_bool(target: dict, env_key: str, field_name: str) -> None:
    val = os.environ.get(env_key)
    if val is not None:
        target[field_name] = val.lower() in ("true", "1", "yes")


def _env_float(target: dict, env_key: str, field_name: str) -> None:
    val = os.environ.get(env_key)
    if val is not None:
        target[field_name] = float(val)


def _env_int(target: dict, env_key: str, field_name: str) -> None:
    val = os.environ.get(env_key)
    if val is not None:
        target[field_name] = int(val)


def _build_sub(cls_type: type, data: dict) -> object:
    """Construct *cls_type* from *data*, ignoring unknown keys."""
    if not isinstance(data, dict):
        return cls_type()
    valid_fields = {f.name for f in cls_type.__dataclass_fields__.values()}
    filtered = {k: v for k, v in data.items() if k in valid_fields}
    return cls_type(**filtered)


def _build_agent(data: dict) -> AgentConfig:
    """Build an :class:`AgentConfig` from a dict.

    In v2.0, all fields are top-level on AgentConfig (no nested 'core').
    For backward compatibility, if a 'core' sub-dict is present, its fields
    are merged into the top-level before construction.
    """
    if not isinstance(data, dict):
        return AgentConfig()

    # Merge legacy 'core' sub-dict into top-level for v1.x compat
    merged = dict(data)
    core_data = merged.pop("core", {})
    if isinstance(core_data, dict):
        for k, v in core_data.items():
            if k not in merged:
                merged[k] = v

    valid_fields = {f.name for f in AgentConfig.__dataclass_fields__.values()}
    filtered = {k: v for k, v in merged.items() if k in valid_fields}
    return AgentConfig(**filtered)
