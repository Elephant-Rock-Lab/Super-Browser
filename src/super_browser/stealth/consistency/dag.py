"""DAG validation and topological ordering for the rule list.

* Acyclicity: DFS three-coloring (white → gray → black).  When DFS
  re-enters a gray node we have a cycle; the path-stack gives us the
  cycle for the error message.
* Topological sort: Kahn's algorithm seeded by all nodes with in-degree
  zero (typically the rules whose inputs are profile fields).

Both passes are O(V + E).
"""

from __future__ import annotations

from dataclasses import dataclass

from super_browser.stealth.consistency.errors import (
    DuplicateOutputError,
    RuleDagCycleError,
)
from super_browser.stealth.consistency.rule import Rule

__all__ = ["RulePlan", "validate_and_order"]

_WHITE = 0
_GRAY = 1
_BLACK = 2


@dataclass(frozen=True)
class RulePlan:
    """Pre-computed rule plan returned by :func:`validate_and_order`."""

    order: list[Rule]  # noqa: RUF012 — mutable list inside frozen dataclass by design
    producers: dict[str, str]  # noqa: RUF012


def validate_and_order(rules: list[Rule]) -> RulePlan:
    """Validate acyclicity and return topologically sorted rules.

    Raises
    ------
    DuplicateOutputError
        When two rules write the same output path.
    RuleDagCycleError
        When the rule graph is cyclic.
    """
    # 1. Build producer index (output path → rule id).
    producers: dict[str, str] = {}
    for rule in rules:
        existing = producers.get(rule.output)
        if existing is not None:
            raise DuplicateOutputError(rule.output, [existing, rule.id])
        producers[rule.output] = rule.id

    # 2. Build adjacency list and in-degree map.
    rule_by_id: dict[str, Rule] = {r.id: r for r in rules}
    decl_order: dict[str, int] = {r.id: i for i, r in enumerate(rules)}

    adj: dict[str, list[str]] = {r.id: [] for r in rules}
    in_degree: dict[str, int] = {r.id: 0 for r in rules}

    for rule in rules:
        for inp in rule.inputs:
            producer_id = producers.get(inp)
            if producer_id is None or producer_id == rule.id:
                continue
            adj[producer_id].append(rule.id)
            in_degree[rule.id] += 1

    # 3. Cycle detection via DFS three-coloring.
    _detect_cycle(rules, adj)

    # 4. Topo sort (Kahn's). Cycle check guarantees we drain all nodes.
    order: list[Rule] = []
    queue = sorted(
        [rid for rid, deg in in_degree.items() if deg == 0],
        key=lambda rid: decl_order.get(rid, 0),
    )

    while queue:
        rid = queue.pop(0)
        rule = rule_by_id[rid]
        order.append(rule)
        newly_ready: list[str] = []
        for downstream in adj[rid]:
            in_degree[downstream] -= 1
            if in_degree[downstream] == 0:
                newly_ready.append(downstream)
        if newly_ready:
            newly_ready.sort(key=lambda x: decl_order.get(x, 0))
            # Insert in sorted position (stable merge).
            queue = _merge_sorted(queue, newly_ready, decl_order)

    if len(order) != len(rules):
        raise RuleDagCycleError(["<unresolved>"])

    return RulePlan(order=order, producers=producers)


def _merge_sorted(
    a: list[str], b: list[str], key: dict[str, int]
) -> list[str]:
    """Merge two lists sorted by *key* into one sorted list."""
    result: list[str] = []
    i = j = 0
    while i < len(a) and j < len(b):
        if key.get(a[i], 0) <= key.get(b[j], 0):
            result.append(a[i])
            i += 1
        else:
            result.append(b[j])
            j += 1
    result.extend(a[i:])
    result.extend(b[j:])
    return result


def _detect_cycle(rules: list[Rule], adj: dict[str, list[str]]) -> None:
    """DFS three-coloring cycle detector.  Raises on cycle."""
    color: dict[str, int] = {r.id: _WHITE for r in rules}
    path: list[str] = []

    def visit(rid: str) -> None:
        color[rid] = _GRAY
        path.append(rid)
        for nxt in adj.get(rid, []):
            c = color.get(nxt, _WHITE)
            if c == _GRAY:
                idx = path.index(nxt) if nxt in path else -1
                if idx >= 0:
                    cycle = [*path[idx:], nxt]
                else:
                    cycle = [nxt, *path, nxt]
                raise RuleDagCycleError(cycle)
            if c == _WHITE:
                visit(nxt)
        color[rid] = _BLACK
        path.pop()

    for rule in rules:
        if color[rule.id] == _WHITE:
            visit(rule.id)
