"""v1.9.2 feature tests — Docs-code alignment.

Verifies:
- All documented Config snippets are executable
- CompletionReason enum matches docs
- StaleRefDetector has 10 signatures
- Config composition root wires recovery/budget
- Version is correct
"""

from __future__ import annotations

from packaging.version import Version as _V

from super_browser import __version__
from super_browser.browser.config import SessionConfig
from super_browser.config import Config
from super_browser.results.types import CompletionReason


class TestV192DocsCodeAlignment:
    """Every documented snippet must be executable."""

    def test_version_is_192(self) -> None:
        assert _V(__version__) >= _V("1.9.2")

    # -- ITEM-1: Config examples are executable --

    def test_config_with_session_config_playwright(self) -> None:
        """README: Config(browser=SessionConfig(backend="playwright"))"""
        cfg = Config(browser=SessionConfig(backend="playwright"))
        assert cfg.browser.backend == "playwright"

    def test_config_with_session_config_cdp(self) -> None:
        """README: Config(browser=SessionConfig(backend="cdp", endpoint=...))"""
        cfg = Config(browser=SessionConfig(backend="cdp", endpoint="ws://chromium:9222"))
        assert cfg.browser.backend == "cdp"
        assert cfg.browser.endpoint == "ws://chromium:9222"

    def test_config_default_is_auto(self) -> None:
        cfg = Config()
        assert cfg.browser.backend == "auto"

    # -- ITEM-3: StaleRefDetector has 10 signatures --

    def test_stale_ref_detector_10_signatures(self) -> None:
        from super_browser.interaction.recovery import StaleRefDetector
        assert len(StaleRefDetector.STALE_SIGNATURES) == 10

    # -- ITEM-4: CompletionReason matches docs --

    def test_completion_reason_values(self) -> None:
        expected = {"success", "budget_exhausted", "error", "cancelled", "max_steps"}
        actual = {e.value for e in CompletionReason}
        assert actual == expected, f"Expected {expected}, got {actual}"

    def test_no_loop_detected(self) -> None:
        assert not hasattr(CompletionReason, "LOOP_DETECTED")

    def test_no_aborted(self) -> None:
        assert not hasattr(CompletionReason, "ABORTED")

    # -- ITEM-6: Config composition root wires recovery/budget --

    def test_config_agent_core_has_enable_recovery(self) -> None:
        cfg = Config()
        assert hasattr(cfg.agent, "enable_recovery")

    def test_config_agent_core_has_enable_budget(self) -> None:
        cfg = Config()
        assert hasattr(cfg.agent, "enable_budget")

    def test_config_recovery_defaults_false(self) -> None:
        cfg = Config()
        assert cfg.agent.enable_recovery is False

    def test_config_budget_defaults_false(self) -> None:
        cfg = Config()
        assert cfg.agent.enable_budget is False

    def test_config_recovery_can_enable(self) -> None:
        from super_browser.config import AgentConfig
        cfg = Config(agent=AgentConfig(enable_recovery=True))
        assert cfg.agent.enable_recovery is True
