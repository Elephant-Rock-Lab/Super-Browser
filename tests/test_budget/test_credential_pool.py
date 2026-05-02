"""Tests for CredentialPool."""

import json
import time
from pathlib import Path

from super_browser.budget.credential_pool import CredentialPool
from super_browser.budget.types import CredentialRotated, SelectionStrategy


class TestCredentialPoolRegister:
    def test_register_and_select(self):
        pool = CredentialPool()
        pool.register("anthropic", "key-1", "sk-test-1")
        entry = pool.select("anthropic")
        assert entry is not None
        assert entry.credential_id == "key-1"

    def test_register_multiple(self):
        pool = CredentialPool()
        pool.register("anthropic", "key-1", "sk-1")
        pool.register("anthropic", "key-2", "sk-2")
        pool.register("anthropic", "key-3", "sk-3")
        assert pool.active_count("anthropic") == 3

    def test_register_same_id_updates(self):
        pool = CredentialPool()
        pool.register("anthropic", "key-1", "sk-old")
        pool.register("anthropic", "key-1", "sk-new")
        entry = pool.select("anthropic")
        assert entry.api_key == "sk-new"

    def test_remove(self):
        pool = CredentialPool()
        pool.register("anthropic", "key-1", "sk-1")
        pool.register("anthropic", "key-2", "sk-2")
        pool.remove("anthropic", "key-1")
        assert pool.active_count("anthropic") == 1


class TestRoundRobinSelection:
    def test_cycles_through(self):
        pool = CredentialPool(strategy=SelectionStrategy.ROUND_ROBIN)
        pool.register("anthropic", "A", "sk-a")
        pool.register("anthropic", "B", "sk-b")
        pool.register("anthropic", "C", "sk-c")

        ids = [pool.select("anthropic").credential_id for _ in range(6)]
        assert ids == ["A", "B", "C", "A", "B", "C"]


class TestRandomSelection:
    def test_selects_from_pool(self):
        pool = CredentialPool(strategy=SelectionStrategy.RANDOM)
        pool.register("anthropic", "A", "sk-a")
        pool.register("anthropic", "B", "sk-b")

        selected = set()
        for _ in range(20):
            entry = pool.select("anthropic")
            selected.add(entry.credential_id)
        assert len(selected) >= 1


class TestLRUSelection:
    def test_selects_least_recently_used(self):
        pool = CredentialPool(strategy=SelectionStrategy.LEAST_RECENTLY_USED)
        pool.register("anthropic", "A", "sk-a")
        pool.register("anthropic", "B", "sk-b")
        pool.register("anthropic", "C", "sk-c")

        entry1 = pool.select("anthropic")
        assert entry1.credential_id == "A"
        entry2 = pool.select("anthropic")
        assert entry2.credential_id == "B"


class TestCostOptimizedSelection:
    def test_selects_lowest_spend(self):
        pool = CredentialPool(strategy=SelectionStrategy.COST_OPTIMIZED)
        pool.register("anthropic", "A", "sk-a")
        pool.register("anthropic", "B", "sk-b")
        pool.register("anthropic", "C", "sk-c")

        pool._find_entry("A").cumulative_spend_usd = 0.30
        pool._find_entry("B").cumulative_spend_usd = 0.05
        pool._find_entry("C").cumulative_spend_usd = 0.10

        entry = pool.select("anthropic")
        assert entry.credential_id == "B"


class TestCooldownAndFailure:
    def test_429_cooldown(self):
        pool = CredentialPool()
        pool.register("anthropic", "A", "sk-a")
        pool.register("anthropic", "B", "sk-b")

        rotated = pool.report_failure("A", 429)
        assert rotated is not None
        assert rotated.previous_credential_id == "A"
        assert rotated.new_credential_id == "B"
        assert rotated.reason == "429_rate_limit"

        entry_a = pool._find_entry("A")
        assert entry_a.is_on_cooldown

    def test_402_longer_cooldown(self):
        pool = CredentialPool()
        pool.register("anthropic", "A", "sk-a")
        pool.register("anthropic", "B", "sk-b")

        rotated = pool.report_failure("A", 402)
        assert rotated is not None
        assert rotated.cooldown_seconds == 300.0

    def test_all_on_cooldown_returns_none(self):
        pool = CredentialPool()
        pool.register("anthropic", "A", "sk-a")
        pool.report_failure("A", 429)
        assert pool.select("anthropic") is None

    def test_report_success_resets_failures(self):
        pool = CredentialPool()
        pool.register("anthropic", "A", "sk-a")
        pool._find_entry("A").consecutive_failures = 3
        pool.report_success("A")
        assert pool._find_entry("A").consecutive_failures == 0


class TestRotationCallback:
    def test_callback_invoked(self):
        rotations = []
        pool = CredentialPool(on_rotate=lambda r: rotations.append(r))
        pool.register("anthropic", "A", "sk-a")
        pool.register("anthropic", "B", "sk-b")
        pool.report_failure("A", 429)
        assert len(rotations) == 1
        assert rotations[0].reason == "429_rate_limit"


class TestProviders:
    def test_providers_list(self):
        pool = CredentialPool()
        pool.register("anthropic", "key-1", "sk-1")
        pool.register("openai", "key-2", "sk-2")
        assert set(pool.providers) == {"anthropic", "openai"}


class TestCredentialPoolPersistence:
    def test_save_and_load(self, tmp_path):
        state_dir = tmp_path / "creds"
        pool = CredentialPool(state_dir=state_dir)
        pool.register("anthropic", "key-1", "sk-1")
        pool.report_failure("key-1", 429)

        pool2 = CredentialPool(state_dir=state_dir)
        entry = pool2._find_entry("key-1")
        assert entry is not None
        assert entry.is_on_cooldown

    def test_no_state_dir(self):
        pool = CredentialPool()
        pool.register("anthropic", "key-1", "sk-1")
        assert pool.select("anthropic") is not None

    def test_select_unknown_provider(self):
        pool = CredentialPool()
        assert pool.select("nonexistent") is None

    def test_report_failure_unknown_credential(self):
        pool = CredentialPool()
        result = pool.report_failure("nonexistent", 429)
        assert result is None
