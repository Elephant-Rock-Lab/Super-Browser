"""CredentialPool and CircuitBreaker — multi-credential failover."""

from __future__ import annotations

import json
import random
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Optional

from super_browser.budget.types import (
    CircuitState,
    CredentialEntry,
    CredentialRotated,
    SelectionStrategy,
)


class CircuitBreaker:
    FAILURE_THRESHOLD: int = 5

    def __init__(
        self,
        cooldown_seconds: float = 120.0,
        on_circuit_open: Optional[Callable[[str], None]] = None,
    ) -> None:
        self._cooldown_seconds = cooldown_seconds
        self._on_circuit_open = on_circuit_open
        self._circuits: dict[str, CircuitState] = {}

    def record_failure(self, provider: str) -> bool:
        circuit = self._circuits.setdefault(
            provider, CircuitState(provider=provider, cooldown_seconds=self._cooldown_seconds)
        )
        circuit.consecutive_failures += 1
        circuit.last_failure_time = time.time()

        if circuit.consecutive_failures >= self.FAILURE_THRESHOLD and not circuit.is_open:
            circuit.is_open = True
            if self._on_circuit_open:
                self._on_circuit_open(provider)
            return True
        return False

    def record_success(self, provider: str) -> None:
        circuit = self._circuits.get(provider)
        if circuit:
            circuit.consecutive_failures = 0
            circuit.is_open = False

    def is_open(self, provider: str) -> bool:
        circuit = self._circuits.get(provider)
        if circuit is None:
            return False
        if not circuit.is_open:
            return False
        elapsed = time.time() - circuit.last_failure_time
        if elapsed >= circuit.cooldown_seconds:
            circuit.is_open = False
            circuit.consecutive_failures = 0
            return False
        return True

    def time_until_reset(self, provider: str) -> float:
        circuit = self._circuits.get(provider)
        if circuit is None or not circuit.is_open:
            return 0.0
        remaining = circuit.cooldown_seconds - (time.time() - circuit.last_failure_time)
        return max(0.0, remaining)


class CredentialPool:
    COOLDOWN_429_SECONDS: float = 60.0
    COOLDOWN_402_SECONDS: float = 300.0
    MAX_CONSECUTIVE_FAILURES: int = 5

    def __init__(
        self,
        state_dir: Optional[Path] = None,
        strategy: SelectionStrategy = SelectionStrategy.ROUND_ROBIN,
        on_rotate: Optional[Callable[[CredentialRotated], None]] = None,
    ) -> None:
        self._state_dir = state_dir
        self._strategy = strategy
        self._on_rotate = on_rotate
        self._pool: dict[str, list[CredentialEntry]] = {}
        self._rr_index: dict[str, int] = {}
        self._lock = threading.Lock()
        self._load_state()

    # -- Registration --------------------------------------------------------

    def register(self, provider: str, credential_id: str, api_key: str) -> None:
        with self._lock:
            entries = self._pool.setdefault(provider, [])
            for e in entries:
                if e.credential_id == credential_id:
                    e.api_key = api_key
                    e.is_active = True
                    return
            entries.append(CredentialEntry(
                credential_id=credential_id, provider=provider, api_key=api_key,
            ))
            self._save_state(provider)

    def remove(self, provider: str, credential_id: str) -> None:
        with self._lock:
            entries = self._pool.get(provider, [])
            self._pool[provider] = [e for e in entries if e.credential_id != credential_id]
            self._save_state(provider)

    # -- Selection -----------------------------------------------------------

    def select(
        self,
        provider: str,
        strategy: Optional[SelectionStrategy] = None,
    ) -> Optional[CredentialEntry]:
        with self._lock:
            entries = self._pool.get(provider, [])
            active = [e for e in entries if e.is_active and not e.is_on_cooldown]
            if not active:
                return None

            strat = strategy or self._strategy
            if strat == SelectionStrategy.ROUND_ROBIN:
                entry = self._select_round_robin(provider, active)
            elif strat == SelectionStrategy.RANDOM:
                entry = self._select_random(active)
            elif strat == SelectionStrategy.LEAST_RECENTLY_USED:
                entry = self._select_lru(active)
            elif strat == SelectionStrategy.COST_OPTIMIZED:
                entry = self._select_cost_optimized(active)
            else:
                entry = active[0]

            if entry:
                entry.last_used = time.time()
            return entry

    def _select_round_robin(self, provider: str, entries: list[CredentialEntry]) -> CredentialEntry:
        idx = self._rr_index.get(provider, 0) % len(entries)
        self._rr_index[provider] = idx + 1
        return entries[idx]

    def _select_random(self, entries: list[CredentialEntry]) -> CredentialEntry:
        return random.choice(entries)

    def _select_lru(self, entries: list[CredentialEntry]) -> CredentialEntry:
        return min(entries, key=lambda e: e.last_used)

    def _select_cost_optimized(self, entries: list[CredentialEntry]) -> CredentialEntry:
        return min(entries, key=lambda e: e.cumulative_spend_usd)

    # -- Failure Handling ----------------------------------------------------

    def report_failure(
        self,
        credential_id: str,
        status_code: int,
    ) -> Optional[CredentialRotated]:
        with self._lock:
            entry = self._find_entry(credential_id)
            if entry is None:
                return None

            entry.consecutive_failures += 1

            if status_code == 429:
                cooldown = self.COOLDOWN_429_SECONDS
                reason = "429_rate_limit"
            elif status_code == 402:
                cooldown = self.COOLDOWN_402_SECONDS
                reason = "402_billing"
            else:
                cooldown = 0.0
                reason = "consecutive_failure"

            if cooldown > 0:
                entry.cooldown_until = time.time() + cooldown

            provider = entry.provider
            active = [e for e in self._pool.get(provider, []) if e.is_active and not e.is_on_cooldown and e.credential_id != credential_id]

            if not active:
                self._save_state(provider)
                return None

            next_entry = active[0]
            rotated = CredentialRotated(
                previous_credential_id=credential_id,
                new_credential_id=next_entry.credential_id,
                provider=provider,
                reason=reason,
                cooldown_seconds=cooldown,
            )

            if self._on_rotate:
                self._on_rotate(rotated)

            self._save_state(provider)
            return rotated

    def report_success(self, credential_id: str) -> None:
        with self._lock:
            entry = self._find_entry(credential_id)
            if entry:
                entry.consecutive_failures = 0

    # -- Properties ----------------------------------------------------------

    def active_count(self, provider: str) -> int:
        with self._lock:
            entries = self._pool.get(provider, [])
            return sum(1 for e in entries if e.is_active and not e.is_on_cooldown)

    @property
    def providers(self) -> list[str]:
        with self._lock:
            return list(self._pool.keys())

    # -- Internal ------------------------------------------------------------

    def _find_entry(self, credential_id: str) -> Optional[CredentialEntry]:
        for entries in self._pool.values():
            for e in entries:
                if e.credential_id == credential_id:
                    return e
        return None

    # -- Persistence ---------------------------------------------------------

    def _load_state(self) -> None:
        if self._state_dir is None:
            return
        try:
            if not self._state_dir.exists():
                return
            for provider_file in self._state_dir.glob("*.json"):
                provider = provider_file.stem
                data = json.loads(provider_file.read_text(encoding="utf-8"))
                entries = []
                for d in data.get("credentials", []):
                    entries.append(CredentialEntry(
                        credential_id=d["credential_id"],
                        provider=provider,
                        api_key=d.get("api_key", ""),
                        is_active=d.get("is_active", True),
                        last_used=d.get("last_used", 0.0),
                        cumulative_spend_usd=d.get("cumulative_spend_usd", 0.0),
                        cooldown_until=d.get("cooldown_until", 0.0),
                        consecutive_failures=d.get("consecutive_failures", 0),
                    ))
                self._pool[provider] = entries
        except (json.JSONDecodeError, KeyError, OSError):
            pass

    def _save_state(self, provider: str) -> None:
        if self._state_dir is None:
            return
        try:
            self._state_dir.mkdir(parents=True, exist_ok=True)
            entries = self._pool.get(provider, [])
            data = {
                "credentials": [
                    {
                        "credential_id": e.credential_id,
                        "api_key": e.api_key,
                        "is_active": e.is_active,
                        "last_used": e.last_used,
                        "cumulative_spend_usd": e.cumulative_spend_usd,
                        "cooldown_until": e.cooldown_until,
                        "consecutive_failures": e.consecutive_failures,
                    }
                    for e in entries
                ]
            }
            (self._state_dir / f"{provider}.json").write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass
