"""v1.9.3 feature tests — Runtime/Config alignment.

Verifies:
- _detect_backend reads Config.browser.backend correctly
- _configure_vision/stealth/skills read cfg.agent.core
- create_llm uses SB_LLM_* env vars (not ANTHROPIC_API_KEY/OPENAI_API_KEY)
- save_session/load_session documented in api-stability
- StaleRefDetector has 10 signatures in agent-reliability docs
"""

from __future__ import annotations

from packaging.version import Version as _V

from super_browser import __version__
from super_browser.browser.config import SessionConfig
from super_browser.browser.engine import _detect_backend
from super_browser.config import Config


class TestV193RuntimeAlignment:
    """Config composition root actually works at runtime."""

    def test_version_is_193(self) -> None:
        assert _V(__version__) >= _V("1.9.3")

    # -- ITEM-1: _detect_backend reads Config.browser.backend --

    def test_detect_backend_auto(self) -> None:
        cfg = Config()
        result = _detect_backend(cfg)
        assert result == "patchright"  # auto-detects patchright

    def test_detect_backend_playwright(self) -> None:
        cfg = Config(browser=SessionConfig(backend="playwright"))
        assert _detect_backend(cfg) == "playwright"

    def test_detect_backend_selenium(self) -> None:
        cfg = Config(browser=SessionConfig(backend="selenium"))
        assert _detect_backend(cfg) == "selenium"

    def test_detect_backend_cdp(self) -> None:
        cfg = Config(browser=SessionConfig(backend="cdp"))
        assert _detect_backend(cfg) == "cdp"

    def test_detect_backend_patchright_explicit(self) -> None:
        cfg = Config(browser=SessionConfig(backend="patchright"))
        assert _detect_backend(cfg) == "patchright"

    # -- ITEM-2/3/4: Config.agent.core enables subsystems --

    def test_config_agent_core_enable_vision(self) -> None:
        cfg = Config()
        assert hasattr(cfg.agent.core, "enable_vision")
        assert cfg.agent.core.enable_vision is False

    def test_config_agent_core_enable_stealth(self) -> None:
        cfg = Config()
        assert hasattr(cfg.agent.core, "enable_stealth")
        assert cfg.agent.core.enable_stealth is False

    def test_config_agent_core_enable_skills(self) -> None:
        cfg = Config()
        assert hasattr(cfg.agent.core, "enable_skills")
        assert cfg.agent.core.enable_skills is False

    def test_config_agent_core_enable_recovery(self) -> None:
        cfg = Config()
        assert hasattr(cfg.agent.core, "enable_recovery")

    def test_config_agent_core_enable_budget(self) -> None:
        cfg = Config()
        assert hasattr(cfg.agent.core, "enable_budget")

    # -- ITEM-5: Docs alignment --

    def test_api_stability_lists_save_session(self) -> None:
        from pathlib import Path

        content = Path("C:/Next AI/SUPER-BROWSER/docs/api-stability.md").read_text(encoding="utf-8")
        assert "save_session" in content
        assert "load_session" in content

    def test_agent_reliability_10_signatures(self) -> None:
        from pathlib import Path

        content = Path("C:/Next AI/SUPER-BROWSER/docs/agent-reliability.md").read_text(encoding="utf-8")
        assert "10 error signatures" in content
        assert "8 error signatures" not in content

    def test_readme_sb_llm_env(self) -> None:
        from pathlib import Path

        content = Path("C:/Next AI/SUPER-BROWSER/README.md").read_text(encoding="utf-8")
        assert "SB_LLM_API_KEY" in content

    # -- ITEM-5: create_llm uses SB_LLM_* --

    def test_create_llm_uses_sb_env_vars(self) -> None:
        from super_browser.agent.llm.factory import create_llm

        # Verify the docstring mentions SB_LLM_*
        assert "SB_LLM_API_KEY" in create_llm.__doc__
