"""Tests for ChallengeConfig wiring — Track D slice 1 (Wave 25).

Covers config defaults, from_dict, from_env, and integration with Config.
"""

from __future__ import annotations

import pytest

from super_browser.config import ChallengeConfig, Config


class TestChallengeConfig:
    def test_defaults(self) -> None:
        cfg = ChallengeConfig()
        assert cfg.turnstile_detect_enabled is True
        assert cfg.kasada_detect_enabled is True
        assert cfg.token_cache_ttl_s == 1800.0
        assert cfg.token_cache_max_entries == 100

    def test_custom_values(self) -> None:
        cfg = ChallengeConfig(
            turnstile_detect_enabled=False,
            kasada_detect_enabled=False,
            token_cache_ttl_s=600.0,
            token_cache_max_entries=50,
        )
        assert cfg.turnstile_detect_enabled is False
        assert cfg.kasada_detect_enabled is False
        assert cfg.token_cache_ttl_s == 600.0
        assert cfg.token_cache_max_entries == 50

    def test_frozen(self) -> None:
        cfg = ChallengeConfig()
        with pytest.raises(AttributeError):
            cfg.turnstile_detect_enabled = False  # type: ignore[misc]


class TestConfigIntegration:
    def test_config_has_challenges(self) -> None:
        cfg = Config()
        assert isinstance(cfg.challenges, ChallengeConfig)
        assert cfg.challenges.turnstile_detect_enabled is True

    def test_from_dict_challenges(self) -> None:
        cfg = Config.from_dict({
            "challenges": {
                "turnstile_detect_enabled": False,
                "kasada_detect_enabled": True,
                "token_cache_ttl_s": 300.0,
                "token_cache_max_entries": 25,
            },
        })
        assert cfg.challenges.turnstile_detect_enabled is False
        assert cfg.challenges.kasada_detect_enabled is True
        assert cfg.challenges.token_cache_ttl_s == 300.0
        assert cfg.challenges.token_cache_max_entries == 25

    def test_from_dict_challenges_empty(self) -> None:
        """Missing challenges key → defaults."""
        cfg = Config.from_dict({})
        assert cfg.challenges.turnstile_detect_enabled is True

    def test_from_env_challenges(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SB_TURNSTILE_DETECT", "false")
        monkeypatch.setenv("SB_KASADA_DETECT", "false")
        monkeypatch.setenv("SB_TOKEN_CACHE_TTL", "600")
        monkeypatch.setenv("SB_TOKEN_CACHE_MAX", "50")
        cfg = Config.from_env()
        assert cfg.challenges.turnstile_detect_enabled is False
        assert cfg.challenges.kasada_detect_enabled is False
        assert cfg.challenges.token_cache_ttl_s == 600.0
        assert cfg.challenges.token_cache_max_entries == 50

    def test_from_env_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Clear challenge env vars
        for key in ("SB_TURNSTILE_DETECT", "SB_KASADA_DETECT",
                     "SB_TOKEN_CACHE_TTL", "SB_TOKEN_CACHE_MAX"):
            monkeypatch.delenv(key, raising=False)
        cfg = Config.from_env()
        assert cfg.challenges.turnstile_detect_enabled is True
        assert cfg.challenges.kasada_detect_enabled is True
