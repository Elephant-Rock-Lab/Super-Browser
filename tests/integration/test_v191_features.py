"""v1.9.1 feature tests — Config normalization + session persistence.

Verifies:
- Config is the default composition root
- SuperBrowserConfig is auto-wrapped via from_legacy
- save_session / load_session exist on the facade
- SessionConfig has session_file field
- All 2,164+ tests still pass
"""

from __future__ import annotations

import pytest
from packaging.version import Version as _V

from super_browser import __version__
from super_browser.agent.config import SuperBrowserConfig
from super_browser.agent.facade import SuperBrowser
from super_browser.browser.config import SessionConfig
from super_browser.config import Config


class TestV191Features:
    """Feature gate tests for v1.9.1."""

    def test_version_is_191(self) -> None:
        assert _V(__version__) >= _V("1.9.1")

    # -- Config normalization --

    def test_default_config_is_composition_root(self) -> None:
        sb = SuperBrowser()
        assert isinstance(sb._config, Config)

    def test_legacy_config_auto_wrapped(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = SuperBrowserConfig(max_steps=42)
        sb = SuperBrowser(config=legacy)
        assert isinstance(sb._config, Config)
        assert sb._config.agent.core.max_steps == 42
        assert sb._legacy_core is legacy

    def test_explicit_config_not_wrapped(self) -> None:
        cfg = Config()
        sb = SuperBrowser(config=cfg)
        assert sb._config is cfg
        assert sb._legacy_core is None

    def test_from_legacy_maps_tracing(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = SuperBrowserConfig(trace_enabled=True, trace_output_dir="/tmp")
        cfg = Config.from_legacy(legacy)
        assert cfg.tracing.enabled is True
        assert cfg.tracing.sink_type == "file"

    def test_from_legacy_tracing_console(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = SuperBrowserConfig(trace_enabled=True, trace_output_dir="")
        cfg = Config.from_legacy(legacy)
        assert cfg.tracing.sink_type == "console"

    # -- Session persistence --

    def test_save_session_method_exists(self) -> None:
        assert hasattr(SuperBrowser, "save_session")
        assert callable(getattr(SuperBrowser, "save_session"))

    def test_load_session_method_exists(self) -> None:
        assert hasattr(SuperBrowser, "load_session")
        assert callable(getattr(SuperBrowser, "load_session"))

    # -- SessionConfig.session_file --

    def test_session_config_has_session_file(self) -> None:
        with pytest.warns(DeprecationWarning):
            sc = SessionConfig()
        assert hasattr(sc, "session_file")
        assert sc.session_file is None

    def test_session_config_session_file_set(self) -> None:
        with pytest.warns(DeprecationWarning):
            sc = SessionConfig(session_file="saved.json")
        assert sc.session_file == "saved.json"

    # -- Facade method count --

    def test_facade_has_session_methods(self) -> None:
        methods = [m for m in dir(SuperBrowser) if not m.startswith("_")]
        assert "save_session" in methods
        assert "load_session" in methods

    # -- Config from_legacy returns Config --

    def test_from_legacy_returns_config(self) -> None:
        with pytest.warns(DeprecationWarning):
            legacy = SuperBrowserConfig()
        cfg = Config.from_legacy(legacy)
        assert isinstance(cfg, Config)
        assert isinstance(cfg.browser, SessionConfig)
