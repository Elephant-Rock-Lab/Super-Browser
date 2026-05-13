"""Consistency engine error types."""

from __future__ import annotations


class RuleDagCycleError(Exception):
    """Raised when the rule DAG contains a cycle.

    The cycle path is included for triage.
    """

    def __init__(self, cycle: list[str]) -> None:
        self.cycle = cycle
        super().__init__(
            f"[consistency] rule DAG contains a cycle: {' -> '.join(cycle)}"
        )


class DuplicateOutputError(Exception):
    """Raised when two rules declare the same output path."""

    def __init__(self, path: str, rule_ids: list[str]) -> None:
        self.path = path
        self.rule_ids = rule_ids
        super().__init__(
            f"[consistency] output path '{path}' is produced by multiple rules: "
            f"{', '.join(rule_ids)}"
        )


class MissingInputError(Exception):
    """Raised when a rule's declared input is missing from the matrix."""

    def __init__(self, rule_id: str, path: str) -> None:
        self.rule_id = rule_id
        self.path = path
        super().__init__(
            f"[consistency] rule {rule_id} requires input '{path}' "
            f"but it is missing from the matrix-under-construction"
        )
