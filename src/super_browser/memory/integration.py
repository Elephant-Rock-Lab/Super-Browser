"""Memory integration — wires MemoryStore into the agent loop and facade."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

from super_browser.memory.store import MemoryStore

logger = logging.getLogger(__name__)


def create_memory_store(
    *,
    memory_enabled: bool = False,
    memory_dir: str = "~/.config/super-browser/memory",
    ttl_days: int = 30,
) -> Optional[MemoryStore]:
    """Create a :class:`MemoryStore` if memory is enabled, else return None.

    This is the single factory used by :class:`SuperBrowser` to decide
    whether memory subsystem is active (HB-25-01: opt-in).
    """
    if not memory_enabled:
        return None
    resolved = Path(memory_dir).expanduser()
    return MemoryStore(resolved, ttl_days=ttl_days)


def extract_domain_from_url(url: str) -> str:
    """Extract a domain key from a URL for memory lookups.

    Returns ``"unknown"`` if the URL cannot be parsed.
    """
    try:
        parsed = urlparse(url)
        return parsed.hostname or "unknown"
    except Exception:
        return "unknown"


def build_memory_context(
    store: Optional[MemoryStore],
    url: str,
) -> str:
    """Build the memory context string to inject into an LLM prompt.

    Returns an empty string if the store is None or there is no data.
    """
    if store is None:
        return ""
    domain = extract_domain_from_url(url)
    return store.get_context_for_prompt(domain)


def record_task_result(
    store: Optional[MemoryStore],
    url: str,
    task: str,
    actions: list[dict],
    success: bool,
) -> None:
    """Record a task result to memory if the store is active.

    Only records successful sequences (per authority rules).
    """
    if store is None:
        return
    domain = extract_domain_from_url(url)
    store.record_sequence(domain, task, actions, success)


def record_selector_result(
    store: Optional[MemoryStore],
    url: str,
    element: str,
    selector: str,
) -> None:
    """Record a working selector to memory if the store is active."""
    if store is None:
        return
    domain = extract_domain_from_url(url)
    store.record_selector(domain, element, selector)
