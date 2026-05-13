"""Rule protocol — the unit of relational locking inside the consistency engine.

Each rule reads a tuple of dotted-path inputs from the matrix-under-
construction, runs its ``derive`` function (pure + deterministic given the
inputs and PRNG), and the engine writes the returned value to the rule's
``output`` path.  Rules are executed in topological order; the engine
verifies the DAG is acyclic before any rule runs.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Generic, TypeVar

from super_browser.stealth.consistency.prng import Xoshiro256PRNG

__all__ = ["Rule", "define_rule"]

T = TypeVar("T")


@dataclass(frozen=True)
class Rule(Generic[T]):
    """A single consistency rule.

    Parameters
    ----------
    id:
        Stable rule identifier, e.g. ``"R-001"``.
    description:
        Short human description of the lock the rule encodes.
    inputs:
        Dotted paths into the matrix-under-construction.  Empty for
        source rules.
    output:
        Dotted path the rule writes.  Must be unique across the rule
        list; the engine raises :class:`DuplicateOutputError` otherwise.
    derive:
        Compute the output.  Must be pure given (inputs, prng).
    """

    id: str
    description: str
    inputs: tuple[str, ...]
    output: str
    derive: Callable[[tuple[Any, ...], Xoshiro256PRNG], T]


def define_rule(
    id: str,
    description: str,
    inputs: tuple[str, ...],
    output: str,
    derive: Callable[[tuple[Any, ...], Xoshiro256PRNG], Any],
) -> Rule[Any]:
    """Factory for :class:`Rule` with erased generic for homogeneous lists."""
    return Rule(
        id=id,
        description=description,
        inputs=inputs,
        output=output,
        derive=derive,
    )
