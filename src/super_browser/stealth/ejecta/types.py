"""Ejecta types — result container for generated ejector payloads."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["EjectorResult"]


@dataclass(frozen=True)
class EjectorResult:
    """Immutable result from a single ejector's payload generation.

    Parameters
    ----------
    ejector_id:
        Unique identifier for the ejector that produced this payload
        (e.g. ``"canvas"``, ``"audio"``).
    js_payload:
        The complete JavaScript IIFE string to inject into the page.
    inject_order:
        Execution priority — lower values are injected first.
    size_bytes:
        Length of ``js_payload`` in bytes (UTF-8).
    """

    ejector_id: str
    js_payload: str
    inject_order: int
    size_bytes: int
