"""TEST-25-03-*: Memory CLI & Config tests."""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from super_browser.config import Config, MemoryConfig
from super_browser.memory.store import MemoryStore
from super_browser.memory.types import ActionSequence, DomainMemory


# ---------------------------------------------------------------------------
# TEST-25-03-01: "memory list" shows domains
# ---------------------------------------------------------------------------

class TestMemoryCLIList:
    def test_memory_list_shows_domains(self, tmp_path, capsys):
        """TEST-25-03-01: 'memory list' shows domains."""
        store = MemoryStore(tmp_path / "mem")
        mem = DomainMemory(domain="shop.example.com")
        mem.sequences.append(ActionSequence(task="buy", actions=[{"action": "click"}]))
        store.save("shop.example.com", mem)

        # Simulate CLI list command
        domains = store.list_domains()
        assert "shop.example.com" in domains

    def test_memory_list_empty(self, tmp_path):
        """Empty memory dir returns no domains."""
        store = MemoryStore(tmp_path / "empty_mem")
        assert store.list_domains() == []


# ---------------------------------------------------------------------------
# TEST-25-03-02: "memory clear" deletes domain file
# ---------------------------------------------------------------------------

class TestMemoryCLIClear:
    def test_memory_clear_deletes_file(self, tmp_path):
        """TEST-25-03-02: 'memory clear' deletes domain file."""
        store = MemoryStore(tmp_path / "mem")
        mem = DomainMemory(domain="rm.example.com")
        mem.sequences.append(ActionSequence(task="x", actions=[{"action": "y"}]))
        store.save("rm.example.com", mem)
        assert store._domain_path("rm.example.com").exists()

        store.clear("rm.example.com")
        assert not store._domain_path("rm.example.com").exists()


# ---------------------------------------------------------------------------
# TEST-25-03-03: Config.memory_enabled defaults to False
# ---------------------------------------------------------------------------

class TestMemoryConfig:
    def test_memory_enabled_defaults_false(self):
        """TEST-25-03-03: Config.memory.memory_enabled defaults to False."""
        config = Config()
        assert config.memory.memory_enabled is False

    def test_memory_config_defaults(self):
        """MemoryConfig has correct defaults."""
        mc = MemoryConfig()
        assert mc.memory_enabled is False
        assert mc.memory_dir == "~/.config/super-browser/memory"
        assert mc.memory_ttl_days == 30

    def test_memory_config_from_dict(self):
        """Config.from_dict parses memory section."""
        config = Config.from_dict({
            "memory": {
                "memory_enabled": True,
                "memory_dir": "/tmp/test-mem",
                "memory_ttl_days": 14,
            }
        })
        assert config.memory.memory_enabled is True
        assert config.memory.memory_dir == "/tmp/test-mem"
        assert config.memory.memory_ttl_days == 14

    def test_memory_config_from_dict_partial(self):
        """Partial memory config uses defaults for missing fields."""
        config = Config.from_dict({
            "memory": {
                "memory_enabled": True,
            }
        })
        assert config.memory.memory_enabled is True
        assert config.memory.memory_dir == "~/.config/super-browser/memory"

    def test_memory_config_from_env(self):
        """Config.from_env reads SB_MEMORY_* variables."""
        env = {
            "SB_MEMORY_ENABLED": "true",
            "SB_MEMORY_DIR": "/custom/mem",
            "SB_MEMORY_TTL_DAYS": "7",
        }
        with patch.dict(os.environ, env, clear=False):
            config = Config.from_env()
        assert config.memory.memory_enabled is True
        assert config.memory.memory_dir == "/custom/mem"
        assert config.memory.memory_ttl_days == 7


# ---------------------------------------------------------------------------
# TEST-25-03-04: Credentials not stored in memory
# ---------------------------------------------------------------------------

class TestCredentialFilteringInCLI:
    def test_credentials_not_in_memory_json(self, tmp_path):
        """TEST-25-03-04: Credentials are filtered from memory files."""
        store = MemoryStore(tmp_path / "mem")
        store.record_sequence(
            "api.example.com",
            "authenticate",
            [
                {"action": "fill", "username": "user@example.com"},
                {"action": "fill", "password": "s3cret!"},
                {"action": "fill", "api_key": "sk-ABCDEF"},
                {"action": "click", "target": "#submit"},
            ],
            success=True,
        )

        # Read raw file
        path = store._domain_path("api.example.com")
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)

        # Password and api_key values must be redacted
        assert "s3cret!" not in raw
        assert "sk-ABCDEF" not in raw
        assert "***REDACTED***" in raw

        # Non-credential values should be intact
        assert "user@example.com" in raw
        assert "#submit" in raw

    def test_token_redacted(self, tmp_path):
        """Token values are redacted."""
        store = MemoryStore(tmp_path / "mem")
        store.record_sequence(
            "auth.example.com",
            "login",
            [{"action": "store", "token": "jwt-xyz-123", "secret": "supersecret"}],
            success=True,
        )
        raw = store._domain_path("auth.example.com").read_text(encoding="utf-8")
        assert "jwt-xyz-123" not in raw
        assert "supersecret" not in raw
        assert "***REDACTED***" in raw


# ---------------------------------------------------------------------------
# CLI _memory function integration tests
# ---------------------------------------------------------------------------

class TestCLIMemoryFunction:
    def test_cli_list_no_domains(self, tmp_path, capsys):
        """CLI list command with no domains prints message."""
        import argparse
        from super_browser.cli import memory_handler

        args = argparse.Namespace(
            command="memory",
            memory_command="list",
            dir=str(tmp_path / "mem"),
        )
        memory_handler(args)
        captured = capsys.readouterr()
        assert "No domains" in captured.out

    def test_cli_show_empty_domain(self, tmp_path, capsys):
        """CLI show command for nonexistent domain."""
        import argparse
        from super_browser.cli import memory_handler

        args = argparse.Namespace(
            command="memory",
            memory_command="show",
            domain="nothing.example.com",
            dir=str(tmp_path / "mem"),
        )
        memory_handler(args)
        captured = capsys.readouterr()
        assert "No memory" in captured.out

    def test_cli_clear(self, tmp_path, capsys):
        """CLI clear command removes domain file."""
        import argparse
        from super_browser.cli import memory_handler

        store = MemoryStore(tmp_path / "mem")
        mem = DomainMemory(domain="del.example.com")
        mem.sequences.append(ActionSequence(task="x", actions=[{"action": "y"}]))
        store.save("del.example.com", mem)

        args = argparse.Namespace(
            command="memory",
            memory_command="clear",
            domain="del.example.com",
            dir=str(tmp_path / "mem"),
        )
        memory_handler(args)
        captured = capsys.readouterr()
        assert "Cleared" in captured.out
        assert not store._domain_path("del.example.com").exists()

    def test_cli_prune(self, tmp_path, capsys):
        """CLI prune command runs."""
        import argparse
        from super_browser.cli import memory_handler

        args = argparse.Namespace(
            command="memory",
            memory_command="prune",
            dir=str(tmp_path / "mem"),
            ttl=30,
        )
        memory_handler(args)
        captured = capsys.readouterr()
        assert "Pruned" in captured.out

    def test_cli_show_with_data(self, tmp_path, capsys):
        """CLI show command displays memory contents."""
        import argparse
        from super_browser.cli import memory_handler

        store = MemoryStore(tmp_path / "mem")
        store.record_sequence("show.example.com", "buy item", [{"action": "click"}], success=True)
        store.record_selector("show.example.com", "cart_button", "#cart")

        args = argparse.Namespace(
            command="memory",
            memory_command="show",
            domain="show.example.com",
            dir=str(tmp_path / "mem"),
        )
        memory_handler(args)
        captured = capsys.readouterr()
        assert "buy item" in captured.out
        assert "#cart" in captured.out
