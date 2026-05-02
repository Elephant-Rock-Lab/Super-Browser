"""TokenBudgetGovernor — 3-scope budget enforcement (daily, per-action, per-turn)."""

from __future__ import annotations

import json
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from super_browser.budget.cost_estimator import CostEstimator
from super_browser.budget.types import (
    AlertLevel,
    BudgetAlert,
    BudgetBlock,
    BudgetConfig,
    BudgetScope,
    BudgetState,
    TokenUsageRecord,
)

_SECONDS_PER_DAY = 86_400


class TokenBudgetGovernor:

    def __init__(
        self,
        config: BudgetConfig = BudgetConfig(),
        cost_estimator: Optional[CostEstimator] = None,
        state_dir: Optional[Path] = None,
        alert_callback: Optional[Callable[[BudgetAlert], None]] = None,
    ) -> None:
        self._config = config
        self._estimator = cost_estimator or CostEstimator()
        self._state_dir = state_dir
        self._alert_callback = alert_callback
        self._state = BudgetState()
        self._lock = threading.Lock()
        self._records: list[TokenUsageRecord] = []
        self._load_state()

    # -- Budget Checks -------------------------------------------------------

    def check_budget(
        self,
        scope: BudgetScope,
        estimated_cost_usd: float = 0.0,
        estimated_tokens: int = 0,
    ) -> Optional[BudgetBlock]:
        with self._lock:
            self._auto_reset_daily()
            if scope == BudgetScope.DAILY:
                return self._check_daily(estimated_cost_usd)
            elif scope == BudgetScope.PER_ACTION:
                return self._check_action(estimated_cost_usd)
            else:
                return self._check_turn(estimated_tokens)

    def record_usage(self, record: TokenUsageRecord) -> Optional[BudgetAlert]:
        with self._lock:
            self._auto_reset_daily()
            self._state.daily_spend_usd += record.estimated_cost_usd
            self._state.action_spend_usd += record.estimated_cost_usd
            self._state.turn_tokens_used += record.input_tokens + record.output_tokens
            self._records.append(record)
            self._save_state()

            alert = self._check_thresholds(
                record.estimated_cost_usd,
                record.input_tokens + record.output_tokens,
            )
            if alert and self._alert_callback:
                self._alert_callback(alert)
            return alert

    def new_action(self) -> None:
        with self._lock:
            self._state.action_spend_usd = 0.0

    def new_turn(self) -> None:
        with self._lock:
            self._state.turn_tokens_used = 0

    def reset_daily(self) -> None:
        with self._lock:
            self._state.daily_spend_usd = 0.0
            self._state.daily_reset_timestamp = time.time()
            self._records.clear()
            self._save_state()

    # -- Properties ----------------------------------------------------------

    @property
    def daily_spend(self) -> float:
        with self._lock:
            self._auto_reset_daily()
            return self._state.daily_spend_usd

    @property
    def daily_remaining(self) -> float:
        with self._lock:
            self._auto_reset_daily()
            return max(0.0, self._config.daily_cap_usd - self._state.daily_spend_usd)

    @property
    def turn_tokens_used(self) -> int:
        with self._lock:
            return self._state.turn_tokens_used

    @property
    def turn_tokens_remaining(self) -> int:
        with self._lock:
            return max(0, self._config.per_turn_token_limit - self._state.turn_tokens_used)

    @property
    def action_spend(self) -> float:
        with self._lock:
            return self._state.action_spend_usd

    @property
    def records(self) -> list[TokenUsageRecord]:
        with self._lock:
            return list(self._records)

    # -- Internal ------------------------------------------------------------

    def _check_daily(self, estimated: float) -> Optional[BudgetBlock]:
        projected = self._state.daily_spend_usd + estimated
        if projected > self._config.daily_cap_usd:
            alert = BudgetAlert(
                level=AlertLevel.EXHAUSTED,
                scope=BudgetScope.DAILY,
                current_spend=self._state.daily_spend_usd,
                cap=self._config.daily_cap_usd,
                remaining=max(0.0, self._config.daily_cap_usd - self._state.daily_spend_usd),
            )
            return BudgetBlock(
                exhausted_scope=BudgetScope.DAILY,
                current_spend=self._state.daily_spend_usd,
                cap=self._config.daily_cap_usd,
                alert=alert,
            )
        return None

    def _check_action(self, estimated: float) -> Optional[BudgetBlock]:
        projected = self._state.action_spend_usd + estimated
        if projected > self._config.per_action_cap_usd:
            alert = BudgetAlert(
                level=AlertLevel.EXHAUSTED,
                scope=BudgetScope.PER_ACTION,
                current_spend=self._state.action_spend_usd,
                cap=self._config.per_action_cap_usd,
                remaining=max(0.0, self._config.per_action_cap_usd - self._state.action_spend_usd),
            )
            return BudgetBlock(
                exhausted_scope=BudgetScope.PER_ACTION,
                current_spend=self._state.action_spend_usd,
                cap=self._config.per_action_cap_usd,
                alert=alert,
            )
        return None

    def _check_turn(self, estimated: int) -> Optional[BudgetBlock]:
        projected = self._state.turn_tokens_used + estimated
        if projected > self._config.per_turn_token_limit:
            alert = BudgetAlert(
                level=AlertLevel.EXHAUSTED,
                scope=BudgetScope.PER_TURN,
                current_spend=float(self._state.turn_tokens_used),
                cap=float(self._config.per_turn_token_limit),
                remaining=float(max(0, self._config.per_turn_token_limit - self._state.turn_tokens_used)),
            )
            return BudgetBlock(
                exhausted_scope=BudgetScope.PER_TURN,
                current_spend=float(self._state.turn_tokens_used),
                cap=float(self._config.per_turn_token_limit),
                alert=alert,
            )
        return None

    def _check_thresholds(
        self, cost_usd: float, tokens: int
    ) -> Optional[BudgetAlert]:
        daily_pct = self._state.daily_spend_usd / self._config.daily_cap_usd if self._config.daily_cap_usd > 0 else 0.0
        if daily_pct >= 1.0:
            return BudgetAlert(
                level=AlertLevel.EXHAUSTED, scope=BudgetScope.DAILY,
                current_spend=self._state.daily_spend_usd, cap=self._config.daily_cap_usd,
                remaining=max(0.0, self._config.daily_cap_usd - self._state.daily_spend_usd),
            )
        if daily_pct >= self._config.critical_threshold:
            return BudgetAlert(
                level=AlertLevel.CRITICAL, scope=BudgetScope.DAILY,
                current_spend=self._state.daily_spend_usd, cap=self._config.daily_cap_usd,
                remaining=max(0.0, self._config.daily_cap_usd - self._state.daily_spend_usd),
            )
        if daily_pct >= self._config.warning_threshold:
            return BudgetAlert(
                level=AlertLevel.WARNING, scope=BudgetScope.DAILY,
                current_spend=self._state.daily_spend_usd, cap=self._config.daily_cap_usd,
                remaining=max(0.0, self._config.daily_cap_usd - self._state.daily_spend_usd),
            )

        action_pct = self._state.action_spend_usd / self._config.per_action_cap_usd if self._config.per_action_cap_usd > 0 else 0.0
        if action_pct >= 1.0:
            return BudgetAlert(
                level=AlertLevel.EXHAUSTED, scope=BudgetScope.PER_ACTION,
                current_spend=self._state.action_spend_usd, cap=self._config.per_action_cap_usd,
                remaining=max(0.0, self._config.per_action_cap_usd - self._state.action_spend_usd),
            )
        if action_pct >= self._config.critical_threshold:
            return BudgetAlert(
                level=AlertLevel.CRITICAL, scope=BudgetScope.PER_ACTION,
                current_spend=self._state.action_spend_usd, cap=self._config.per_action_cap_usd,
                remaining=max(0.0, self._config.per_action_cap_usd - self._state.action_spend_usd),
            )

        turn_pct = self._state.turn_tokens_used / self._config.per_turn_token_limit if self._config.per_turn_token_limit > 0 else 0.0
        if turn_pct >= 1.0:
            return BudgetAlert(
                level=AlertLevel.EXHAUSTED, scope=BudgetScope.PER_TURN,
                current_spend=float(self._state.turn_tokens_used), cap=float(self._config.per_turn_token_limit),
                remaining=float(max(0, self._config.per_turn_token_limit - self._state.turn_tokens_used)),
            )

        return None

    def _auto_reset_daily(self) -> None:
        if time.time() - self._state.daily_reset_timestamp > _SECONDS_PER_DAY:
            self._state.daily_spend_usd = 0.0
            self._state.daily_reset_timestamp = time.time()
            self._records.clear()

    # -- Persistence ---------------------------------------------------------

    def _load_state(self) -> None:
        if self._state_dir is None:
            return
        state_file = self._state_dir / "daily.json"
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            self._state.daily_spend_usd = data.get("daily_spend_usd", 0.0)
            self._state.daily_reset_timestamp = data.get("daily_reset_timestamp", time.time())
            self._state.turn_tokens_used = data.get("turn_tokens_used", 0)
            self._state.action_spend_usd = data.get("action_spend_usd", 0.0)
        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            pass

    def _save_state(self) -> None:
        if self._state_dir is None:
            return
        try:
            self._state_dir.mkdir(parents=True, exist_ok=True)
            state_file = self._state_dir / "daily.json"
            data = {
                "daily_spend_usd": self._state.daily_spend_usd,
                "daily_reset_timestamp": self._state.daily_reset_timestamp,
                "turn_tokens_used": self._state.turn_tokens_used,
                "action_spend_usd": self._state.action_spend_usd,
            }
            state_file.write_text(json.dumps(data), encoding="utf-8")
        except OSError:
            pass
