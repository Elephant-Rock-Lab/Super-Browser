"""BATCH-03/TASK-01 — Unified Config tests (TEST-03-01-01 … TEST-03-01-07)."""

from __future__ import annotations

import os
from pathlib import Path
from unittest import mock

from super_browser.browser.config import SessionConfig
from super_browser.budget.types import BudgetConfig
from super_browser.config import AgentConfig, Config, TracingConfig
from super_browser.security.types import SecurityConfig
from super_browser.stealth.types import StealthConfig

# ── TEST-03-01-01: Config.from_env() reads SB_LLM_PROVIDER and SB_HEADLESS ──


class TestFromEnv:
    """TEST-03-01-01 — Config.from_env() reads SB_LLM_PROVIDER and SB_HEADLESS."""

    def test_llm_provider_from_env(self) -> None:
        env = {"SB_LLM_PROVIDER": "openai", "SB_LLM_MODEL": "gpt-4o", "SB_LLM_API_KEY": "sk-test"}
        with mock.patch.dict(os.environ, env, clear=False):
            cfg = Config.from_env()
        assert cfg.agent.llm_provider == "openai"
        assert cfg.agent.llm_model == "gpt-4o"
        assert cfg.agent.llm_api_key == "sk-test"

    def test_headless_from_env(self) -> None:
        with mock.patch.dict(os.environ, {"SB_HEADLESS": "true"}, clear=False):
            cfg = Config.from_env()
        assert cfg.browser.headless is True

    def test_headless_false_from_env(self) -> None:
        with mock.patch.dict(os.environ, {"SB_HEADLESS": "false"}, clear=False):
            cfg = Config.from_env()
        assert cfg.browser.headless is False

    def test_default_when_no_env(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            cfg = Config.from_env()
        # Defaults should match the original class defaults
        assert cfg.agent.llm_provider == "anthropic"
        assert cfg.browser.headless is False


# ── TEST-03-01-02: Config.from_dict() creates valid Config with all sub-configs ──


class TestFromDict:
    """TEST-03-01-02 — Config.from_dict() creates valid Config with all sub-configs."""

    def test_full_dict(self) -> None:
        d = {
            "browser": {"headless": True, "default_timeout": 60.0},
            "agent": {
                "llm_provider": "openai",
                "llm_model": "gpt-4o",
                "llm_api_key": "sk-key",
                "max_steps": 100,
                "default_model": "gpt-4o",
            },
            "stealth": {"proxy_url": "http://proxy:8080"},
            "budget": {"daily_cap_usd": 25.0},
            "security": {"injection_detection_enabled": False},
            "tracing": {"enabled": True, "sink_type": "file"},
        }
        cfg = Config.from_dict(d)

        assert isinstance(cfg.browser, SessionConfig)
        assert cfg.browser.headless is True
        assert cfg.browser.default_timeout == 60.0

        assert isinstance(cfg.agent, AgentConfig)
        assert cfg.agent.llm_provider == "openai"
        assert cfg.agent.llm_model == "gpt-4o"
        assert cfg.agent.llm_api_key == "sk-key"
        assert cfg.agent.max_steps == 100

        assert isinstance(cfg.stealth, StealthConfig)
        assert cfg.stealth.proxy_url == "http://proxy:8080"

        assert isinstance(cfg.budget, BudgetConfig)
        assert cfg.budget.daily_cap_usd == 25.0

        assert isinstance(cfg.security, SecurityConfig)
        assert cfg.security.injection_detection_enabled is False

        assert isinstance(cfg.tracing, TracingConfig)
        assert cfg.tracing.enabled is True
        assert cfg.tracing.sink_type == "file"

    def test_empty_dict_gives_defaults(self) -> None:
        cfg = Config.from_dict({})
        assert isinstance(cfg, Config)
        assert cfg.agent.llm_provider == "anthropic"
        assert cfg.browser.headless is False
        assert cfg.budget.daily_cap_usd == 10.0

    def test_unknown_keys_ignored(self) -> None:
        d = {
            "browser": {"headless": True, "unknown_key": 42},
            "agent": {"llm_provider": "anthropic", "bogus": True},
        }
        cfg = Config.from_dict(d)  # should not raise
        assert cfg.browser.headless is True

    def test_legacy_core_dict_merged(self) -> None:
        """v1.x dict with nested 'core' is merged into flat fields (backward compat)."""
        d = {
            "agent": {
                "llm_provider": "openai",
                "core": {"max_steps": 100},
            },
        }
        cfg = Config.from_dict(d)
        assert cfg.agent.max_steps == 100
        assert cfg.agent.llm_provider == "openai"


# ── TEST-03-01-03: Config.from_yaml() loads from YAML file ──


class TestFromYaml:
    """TEST-03-01-03 — Config.from_yaml() loads from YAML file."""

    def test_load_yaml(self, tmp_path: Path) -> None:
        yaml_content = (
            "browser:\n"
            "  headless: true\n"
            "agent:\n"
            "  llm_provider: openai\n"
            "  llm_model: gpt-4o\n"
            "  llm_api_key: sk-yaml\n"
            "budget:\n"
            "  daily_cap_usd: 42.0\n"
            "tracing:\n"
            "  enabled: true\n"
            "  sink_type: otlp\n"
        )
        yaml_file = tmp_path / "config.yaml"
        yaml_file.write_text(yaml_content, encoding="utf-8")

        cfg = Config.from_yaml(yaml_file)

        assert cfg.browser.headless is True
        assert cfg.agent.llm_provider == "openai"
        assert cfg.agent.llm_model == "gpt-4o"
        assert cfg.agent.llm_api_key == "sk-yaml"
        assert cfg.budget.daily_cap_usd == 42.0
        assert cfg.tracing.enabled is True
        assert cfg.tracing.sink_type == "otlp"

    def test_empty_yaml(self, tmp_path: Path) -> None:
        yaml_file = tmp_path / "empty.yaml"
        yaml_file.write_text("", encoding="utf-8")
        cfg = Config.from_yaml(yaml_file)
        assert cfg.agent.llm_provider == "anthropic"  # default


# ── TEST-03-01-04: Default Config has sensible values ──


class TestDefaults:
    """TEST-03-01-04 — Default Config has sensible values."""

    def test_default_construction(self) -> None:
        cfg = Config()
        assert cfg.browser.headless is False
        assert cfg.browser.viewport == (1280, 720)
        assert cfg.agent.llm_provider == "anthropic"
        assert cfg.agent.llm_model == "claude-sonnet-4-20250514"
        assert cfg.agent.llm_api_key == ""
        assert cfg.agent.max_steps == 50
        assert cfg.budget.daily_cap_usd == 10.0
        assert cfg.security.injection_detection_enabled is True
        assert cfg.stealth.headless is False
        assert cfg.tracing.enabled is False
        assert cfg.tracing.sink_type == "console"


# ── TEST-03-01-05: Config.validate() returns empty list for valid config ──


class TestValidateValid:
    """TEST-03-01-05 — Config.validate() returns empty list for valid config."""

    def test_valid_config_no_errors(self) -> None:
        cfg = Config(
            agent=AgentConfig(
                llm_provider="anthropic",
                llm_model="claude-sonnet-4-20250514",
                llm_api_key="sk-ant-valid-key",
            ),
        )
        errors = cfg.validate()
        assert errors == []

    def test_openai_valid(self) -> None:
        cfg = Config(
            agent=AgentConfig(
                llm_provider="openai",
                llm_api_key="sk-openai-key",
            ),
        )
        errors = cfg.validate()
        assert errors == []


# ── TEST-03-01-06: Config.validate() returns errors for invalid config ──


class TestValidateInvalid:
    """TEST-03-01-06 — Config.validate() returns errors for invalid config."""

    def test_invalid_provider(self) -> None:
        cfg = Config(agent=AgentConfig(llm_provider="bogus"))
        errors = cfg.validate()
        assert any("llm_provider" in e for e in errors)

    def test_missing_api_key(self) -> None:
        cfg = Config(agent=AgentConfig(llm_provider="anthropic", llm_api_key=""))
        errors = cfg.validate()
        assert any("llm_api_key" in e for e in errors)

    def test_negative_budget(self) -> None:
        cfg = Config(budget=BudgetConfig(daily_cap_usd=-5.0))
        errors = cfg.validate()
        assert any("daily_cap_usd" in e for e in errors)

    def test_invalid_tracing_sink(self) -> None:
        cfg = Config(tracing=TracingConfig(sink_type="invalid"))
        errors = cfg.validate()
        assert any("sink_type" in e for e in errors)


# ── TEST-03-01-07: Config.from_env() values compatible with create_llm() ──


class TestFromEnvLLMCompatibility:
    """TEST-03-01-07 — Config.from_env() values compatible with create_llm()."""

    def test_env_values_match_create_llm_signature(self) -> None:
        """Verify that Config.from_env() produces values that match
        the create_llm(provider, model, api_key) signature."""
        env = {
            "SB_LLM_PROVIDER": "anthropic",
            "SB_LLM_MODEL": "claude-sonnet-4-20250514",
            "SB_LLM_API_KEY": "sk-ant-test123",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            cfg = Config.from_env()

        # Values must be directly usable as create_llm() arguments
        assert isinstance(cfg.agent.llm_provider, str)
        assert isinstance(cfg.agent.llm_model, str)
        assert isinstance(cfg.agent.llm_api_key, str)
        assert cfg.agent.llm_provider in ("anthropic", "openai")
        assert len(cfg.agent.llm_api_key) > 0

    def test_openai_provider_from_env(self) -> None:
        env = {
            "SB_LLM_PROVIDER": "openai",
            "SB_LLM_MODEL": "gpt-4o",
            "SB_LLM_API_KEY": "sk-openai-test",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            cfg = Config.from_env()

        assert cfg.agent.llm_provider == "openai"
        assert cfg.agent.llm_model == "gpt-4o"
        assert cfg.agent.llm_api_key == "sk-openai-test"


# ── Package export test ──


class TestPackageExport:
    """Verify Config is accessible from the top-level package."""

    def test_import_from_package(self) -> None:
        import super_browser

        assert hasattr(super_browser, "Config")
        assert super_browser.Config is Config
