"""BATCH-03/TASK-02 — Deprecation warning tests (TEST-03-02-01 … TEST-03-02-04)."""

from __future__ import annotations

import warnings

import pytest
from super_browser.agent.config import SuperBrowserConfig
from super_browser.browser.config import SessionConfig
from super_browser.config import AgentConfig, Config

# ── TEST-03-02-01: Old SuperBrowserConfig() emits DeprecationWarning ──


class TestSuperBrowserConfigDeprecation:
    """TEST-03-02-01 — Old SuperBrowserConfig() emits DeprecationWarning."""

    def test_default_construction_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = SuperBrowserConfig()  # noqa: F841
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "SuperBrowserConfig is deprecated" in str(w[0].message)

    def test_custom_args_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = SuperBrowserConfig(max_steps=100, default_model="gpt-4o")
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert cfg.max_steps == 100
        assert cfg.default_model == "gpt-4o"


# ── TEST-03-02-02: Old SessionConfig() emits DeprecationWarning ──


class TestSessionConfigDeprecation:
    """TEST-03-02-02 — Old SessionConfig() emits DeprecationWarning."""

    def test_default_construction_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = SessionConfig()  # noqa: F841
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert "SessionConfig is deprecated" in str(w[0].message)

    def test_custom_args_warns(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = SessionConfig(headless=True, default_timeout=60.0)
        assert len(w) == 1
        assert issubclass(w[0].category, DeprecationWarning)
        assert cfg.headless is True
        assert cfg.default_timeout == 60.0


# ── TEST-03-02-03: All existing tests still pass ──
# This is verified by the full pytest run.  We provide a sanity check that
# the unified Config can still be constructed without emitting deprecation
# warnings (the internal suppression is working).


class TestUnifiedConfigNoLeakedWarnings:
    """TEST-03-02-03 — Unified Config does NOT leak deprecation warnings."""

    def test_config_default_no_warning(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            cfg = Config()
        deprecation_msgs = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_msgs) == 0, (
            f"Config() leaked {len(deprecation_msgs)} DeprecationWarning(s)"
        )
        assert cfg.browser.headless is False
        assert cfg.agent.core.max_steps == 50

    def test_agent_config_default_no_warning(self) -> None:
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ac = AgentConfig()
        deprecation_msgs = [x for x in w if issubclass(x.category, DeprecationWarning)]
        assert len(deprecation_msgs) == 0, (
            f"AgentConfig() leaked {len(deprecation_msgs)} DeprecationWarning(s)"
        )
        assert ac.core.max_steps == 50


# ── TEST-03-02-04: Old config objects are constructable (backward compat) ──


class TestBackwardCompat:
    """TEST-03-02-04 — Old config objects are still constructable."""

    def test_super_browser_config_attributes(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            cfg = SuperBrowserConfig(
                max_steps=200,
                loop_window_size=30,
                stagnation_threshold=5,
                default_model="gpt-4o",
                llm_temperature=0.7,
                llm_max_tokens=8192,
                trace_enabled=False,
                enable_recovery=True,
                enable_budget=True,
                enable_security=True,
                enable_vision=True,
                enable_stealth=True,
                enable_skills=True,
            )
        assert cfg.max_steps == 200
        assert cfg.loop_window_size == 30
        assert cfg.stagnation_threshold == 5
        assert cfg.default_model == "gpt-4o"
        assert cfg.llm_temperature == 0.7
        assert cfg.llm_max_tokens == 8192
        assert cfg.trace_enabled is False
        assert cfg.enable_recovery is True
        assert cfg.enable_budget is True
        assert cfg.enable_security is True
        assert cfg.enable_vision is True
        assert cfg.enable_stealth is True
        assert cfg.enable_skills is True

    def test_session_config_attributes(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            cfg = SessionConfig(
                headless=True,
                default_timeout=60.0,
                navigation_timeout=45.0,
                viewport=(1920, 1080),
            )
        assert cfg.headless is True
        assert cfg.default_timeout == 60.0
        assert cfg.navigation_timeout == 45.0
        assert cfg.viewport == (1920, 1080)

    def test_super_browser_config_frozen(self) -> None:
        """Old config remains immutable (frozen)."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            cfg = SuperBrowserConfig()
        with pytest.raises(AttributeError):
            cfg.max_steps = 999  # type: ignore[misc]

    def test_session_config_frozen(self) -> None:
        """Old config remains immutable (frozen)."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            cfg = SessionConfig()
        with pytest.raises(AttributeError):
            cfg.headless = True  # type: ignore[misc]
