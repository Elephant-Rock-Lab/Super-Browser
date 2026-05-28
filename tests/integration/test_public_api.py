"""Gate 2 tests — Public API smoke test (v1.11.0).

Verifies every import and facade method documented in api-stability.md
actually exists in the source.
"""

from __future__ import annotations


class TestTopLevelImports:
    """All Tier 1 top-level imports from api-stability.md resolve."""

    def test_super_browser(self) -> None:
        from super_browser import SuperBrowser
        assert SuperBrowser is not None

    def test_config(self) -> None:
        from super_browser import Config
        assert Config is not None

    def test_action_result(self) -> None:
        from super_browser import ActionResult
        assert ActionResult is not None

    def test_create_llm(self) -> None:
        from super_browser import create_llm
        assert callable(create_llm)

    def test_mock_llm_client(self) -> None:
        from super_browser.testing import MockLLMClient
        assert MockLLMClient is not None


class TestResultTypes:
    """All result types from api-stability.md resolve."""

    def test_success_category(self) -> None:
        from super_browser.results.types import SuccessCategory
        assert SuccessCategory is not None

    def test_failure_category(self) -> None:
        from super_browser.results.types import FailureCategory
        assert FailureCategory is not None

    def test_error_category(self) -> None:
        from super_browser.results.types import ErrorCategory
        assert ErrorCategory is not None

    def test_next_action(self) -> None:
        from super_browser.results.types import NextAction
        assert NextAction is not None

    def test_page_change_summary(self) -> None:
        from super_browser.results.types import PageChangeSummary
        assert PageChangeSummary is not None

    def test_page_fingerprint(self) -> None:
        from super_browser.results.types import PageFingerprint
        assert PageFingerprint is not None


class TestTier2Protocols:
    """All Tier 2 protocols from api-stability.md resolve."""

    def test_browser_engine(self) -> None:
        from super_browser.browser.engine import BrowserEngine
        assert BrowserEngine is not None

    def test_engine_page(self) -> None:
        from super_browser.browser.engine import EnginePage
        assert EnginePage is not None

    def test_stealth_bridge(self) -> None:
        from super_browser.browser.engine import StealthBridge
        assert StealthBridge is not None

    def test_stealth_injector(self) -> None:
        from super_browser.browser.engine import StealthInjector
        assert StealthInjector is not None

    def test_engine_capabilities(self) -> None:
        from super_browser.browser.engine import EngineCapabilities
        assert EngineCapabilities is not None

    def test_backend_type(self) -> None:
        from super_browser.browser.engine import BackendType
        assert BackendType is not None


class TestConfigChildren:
    """All Config sub-configs from api-stability.md resolve."""

    def test_session_config(self) -> None:
        from super_browser.browser.config import SessionConfig
        assert SessionConfig is not None

    def test_agent_config(self) -> None:
        from super_browser.config import AgentConfig
        assert AgentConfig is not None

    def test_budget_config(self) -> None:
        from super_browser.config import BudgetConfig
        assert BudgetConfig is not None

    def test_security_config(self) -> None:
        from super_browser.config import SecurityConfig
        assert SecurityConfig is not None

    def test_stealth_config(self) -> None:
        from super_browser.config import StealthConfig
        assert StealthConfig is not None

    def test_tracing_config(self) -> None:
        from super_browser.config import TracingConfig
        assert TracingConfig is not None

    def test_network_config(self) -> None:
        from super_browser.config import NetworkConfig
        assert NetworkConfig is not None

    def test_memory_config(self) -> None:
        from super_browser.config import MemoryConfig
        assert MemoryConfig is not None

    def test_consistency_config(self) -> None:
        from super_browser.config import ConsistencyConfig
        assert ConsistencyConfig is not None

    def test_cloak_config(self) -> None:
        from super_browser.config import CloakConfig
        assert CloakConfig is not None


class TestFacadeMethods:
    """All documented facade methods from api-stability.md exist on SuperBrowser."""

    @classmethod
    def _get_methods(cls) -> set[str]:
        from super_browser.agent.facade import SuperBrowser
        return {m for m in dir(SuperBrowser) if not m.startswith("_") and callable(getattr(SuperBrowser, m))}

    def test_start(self) -> None:
        assert "start" in self._get_methods()

    def test_stop(self) -> None:
        assert "stop" in self._get_methods()

    def test_navigate(self) -> None:
        assert "navigate" in self._get_methods()

    def test_click(self) -> None:
        assert "click" in self._get_methods()

    def test_fill(self) -> None:
        assert "fill" in self._get_methods()

    def test_extract(self) -> None:
        assert "extract" in self._get_methods()

    def test_observe(self) -> None:
        assert "observe" in self._get_methods()

    def test_act(self) -> None:
        assert "act" in self._get_methods()

    def test_open_tab(self) -> None:
        assert "open_tab" in self._get_methods()

    def test_switch_tab(self) -> None:
        assert "switch_tab" in self._get_methods()

    def test_close_tab(self) -> None:
        assert "close_tab" in self._get_methods()

    def test_list_tabs(self) -> None:
        assert "list_tabs" in self._get_methods()

    def test_upload_file(self) -> None:
        assert "upload_file" in self._get_methods()

    def test_download(self) -> None:
        assert "download" in self._get_methods()

    def test_enter_frame(self) -> None:
        assert "enter_frame" in self._get_methods()

    def test_exit_frame(self) -> None:
        assert "exit_frame" in self._get_methods()

    def test_query_shadow(self) -> None:
        assert "query_shadow" in self._get_methods()

    def test_intercept_requests(self) -> None:
        assert "intercept_requests" in self._get_methods()

    def test_block_requests(self) -> None:
        assert "block_requests" in self._get_methods()

    def test_mock_response(self) -> None:
        assert "mock_response" in self._get_methods()

    def test_clear_interceptions(self) -> None:
        assert "clear_interceptions" in self._get_methods()

    def test_delegate(self) -> None:
        assert "delegate" in self._get_methods()

    def test_register_tool(self) -> None:
        assert "register_tool" in self._get_methods()

    def test_abort(self) -> None:
        assert "abort" in self._get_methods()

    def test_configure_verification(self) -> None:
        assert "configure_verification" in self._get_methods()

    def test_enable_recording(self) -> None:
        assert "enable_recording" in self._get_methods()

    def test_replay(self) -> None:
        assert "replay" in self._get_methods()

    def test_enable_memory(self) -> None:
        assert "enable_memory" in self._get_methods()

    def test_learn_from_trajectory(self) -> None:
        assert "learn_from_trajectory" in self._get_methods()

    def test_save_session(self) -> None:
        assert "save_session" in self._get_methods()

    def test_load_session(self) -> None:
        assert "load_session" in self._get_methods()

    def test_tools(self) -> None:
        assert "tools" in self._get_methods()


class TestFacadeProperties:
    """All documented properties from api-stability.md exist on SuperBrowser."""

    @classmethod
    def _get_properties(cls) -> set[str]:
        from super_browser.agent.facade import SuperBrowser
        return {m for m in dir(SuperBrowser) if not m.startswith("_") and not callable(getattr(SuperBrowser, m))}

    def test_recording(self) -> None:
        assert "recording" in self._get_properties()

    def test_memory(self) -> None:
        assert "memory" in self._get_properties()

    def test_is_running(self) -> None:
        assert "is_running" in self._get_properties()

    def test_stealth_backend(self) -> None:
        assert "stealth_backend" in self._get_properties()
