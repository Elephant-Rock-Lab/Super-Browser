"""Tests for CircuitBreaker."""

import time

from super_browser.budget.credential_pool import CircuitBreaker
from super_browser.budget.types import CircuitState


class TestCircuitBreaker:
    def test_initially_closed(self):
        cb = CircuitBreaker()
        assert not cb.is_open("anthropic")

    def test_opens_at_threshold(self):
        cb = CircuitBreaker()
        for _ in range(4):
            just_opened = cb.record_failure("anthropic")
            assert not just_opened
        just_opened = cb.record_failure("anthropic")
        assert just_opened
        assert cb.is_open("anthropic")

    def test_stays_open(self):
        cb = CircuitBreaker()
        for _ in range(5):
            cb.record_failure("anthropic")
        assert cb.is_open("anthropic")

    def test_success_resets(self):
        cb = CircuitBreaker()
        for _ in range(5):
            cb.record_failure("anthropic")
        assert cb.is_open("anthropic")
        cb.record_success("anthropic")
        assert not cb.is_open("anthropic")

    def test_auto_close_after_cooldown(self):
        cb = CircuitBreaker(cooldown_seconds=0.01)
        for _ in range(5):
            cb.record_failure("anthropic")
        assert cb.is_open("anthropic")
        time.sleep(0.02)
        assert not cb.is_open("anthropic")

    def test_time_until_reset(self):
        cb = CircuitBreaker(cooldown_seconds=120.0)
        for _ in range(5):
            cb.record_failure("anthropic")
        remaining = cb.time_until_reset("anthropic")
        assert remaining > 0
        assert remaining <= 120.0

    def test_time_until_reset_closed(self):
        cb = CircuitBreaker()
        assert cb.time_until_reset("anthropic") == 0.0

    def test_time_until_reset_unknown_provider(self):
        cb = CircuitBreaker()
        assert cb.time_until_reset("nonexistent") == 0.0

    def test_on_circuit_open_callback(self):
        opened = []
        cb = CircuitBreaker(on_circuit_open=lambda p: opened.append(p))
        for _ in range(5):
            cb.record_failure("anthropic")
        assert opened == ["anthropic"]

    def test_callback_only_on_open(self):
        opened = []
        cb = CircuitBreaker(on_circuit_open=lambda p: opened.append(p))
        cb.record_failure("anthropic")
        assert opened == []

    def test_multiple_providers_independent(self):
        cb = CircuitBreaker()
        for _ in range(5):
            cb.record_failure("anthropic")
        assert cb.is_open("anthropic")
        assert not cb.is_open("openai")

    def test_failure_count_resets_on_success(self):
        cb = CircuitBreaker()
        cb.record_failure("anthropic")
        cb.record_failure("anthropic")
        cb.record_success("anthropic")
        cb.record_failure("anthropic")
        cb.record_failure("anthropic")
        cb.record_failure("anthropic")
        just_opened = cb.record_failure("anthropic")
        assert not just_opened
        assert not cb.is_open("anthropic")
