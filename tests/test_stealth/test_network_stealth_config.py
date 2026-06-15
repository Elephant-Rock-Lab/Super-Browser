"""Tests for NetworkStealthConfig — Track B slice 2 (Wave 19).

Covers Config integration, from_dict, from_env, and defaults.
"""

from __future__ import annotations

import os

import pytest

from super_browser.config import Config, NetworkStealthConfig


class TestNetworkStealthConfig:
    def test_defaults(self) -> None:
        cfg = NetworkStealthConfig()
        assert cfg.proxy_rotation_strategy == "round_robin"
        assert cfg.proxy_health_check_url is None
        assert cfg.proxy_health_check_interval == 300.0
        assert cfg.proxy_max_failures == 3
        assert cfg.proxy_cooldown_seconds == 60.0
        assert cfg.proxy_sticky_ttl == 1800.0

        assert cfg.ip_reputation_provider_url is None
        assert cfg.ip_reputation_api_key is None
        assert cfg.ip_reputation_timeout == 10.0
        assert cfg.ip_reputation_cache_ttl == 3600.0

        assert cfg.tls_check_enabled is False
        assert cfg.tls_echo_url == "https://tls.peet.ws/api/all"

    def test_frozen(self) -> None:
        cfg = NetworkStealthConfig()
        with pytest.raises(AttributeError):
            cfg.proxy_max_failures = 99  # type: ignore[misc]


class TestConfigIntegration:
    def test_config_has_network_stealth(self) -> None:
        cfg = Config()
        assert isinstance(cfg.network_stealth, NetworkStealthConfig)

    def test_from_dict_network_stealth(self) -> None:
        cfg = Config.from_dict({
            "network_stealth": {
                "proxy_rotation_strategy": "weighted_random",
                "proxy_max_failures": 5,
                "ip_reputation_provider_url": "https://api.test/{ip}",
            },
        })
        assert cfg.network_stealth.proxy_rotation_strategy == "weighted_random"
        assert cfg.network_stealth.proxy_max_failures == 5
        assert cfg.network_stealth.ip_reputation_provider_url == "https://api.test/{ip}"

    def test_from_dict_ignores_unknown_keys(self) -> None:
        cfg = Config.from_dict({
            "network_stealth": {
                "proxy_max_failures": 7,
                "totally_unknown_field": "ignored",
            },
        })
        assert cfg.network_stealth.proxy_max_failures == 7

    def test_from_dict_empty_network_stealth(self) -> None:
        cfg = Config.from_dict({})
        assert isinstance(cfg.network_stealth, NetworkStealthConfig)
        assert cfg.network_stealth.proxy_rotation_strategy == "round_robin"

    def test_from_env_network_stealth(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("SB_PROXY_ROTATION_STRATEGY", "least_used")
        monkeypatch.setenv("SB_PROXY_MAX_FAILURES", "7")
        monkeypatch.setenv("SB_IP_REP_PROVIDER_URL", "https://rep.test/{ip}")
        monkeypatch.setenv("SB_IP_REP_TIMEOUT", "15.0")
        monkeypatch.setenv("SB_PROXY_COOLDOWN", "120.0")

        cfg = Config.from_env()
        assert cfg.network_stealth.proxy_rotation_strategy == "least_used"
        assert cfg.network_stealth.proxy_max_failures == 7
        assert cfg.network_stealth.ip_reputation_provider_url == "https://rep.test/{ip}"
        assert cfg.network_stealth.ip_reputation_timeout == 15.0
        assert cfg.network_stealth.proxy_cooldown_seconds == 120.0

    def test_from_env_unset_uses_defaults(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Clear all SB_NETWORK_STEALTH vars
        for key in list(os.environ):
            if key.startswith("SB_PROXY_") or key.startswith("SB_IP_REP_"):
                monkeypatch.delenv(key, raising=False)

        cfg = Config.from_env()
        assert cfg.network_stealth.proxy_rotation_strategy == "round_robin"
        assert cfg.network_stealth.ip_reputation_provider_url is None
