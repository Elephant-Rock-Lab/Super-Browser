"""MemoryStore — per-domain JSON persistence with TTL pruning and credential filtering."""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path

from super_browser.memory.types import ActionSequence, DomainMemory

logger = logging.getLogger(__name__)

# Fields that look like credentials — never persist values under these keys.
_CREDENTIAL_PATTERNS = re.compile(
    r"(api_key|apikey|password|passwd|secret|token|auth|credential|private_key)",
    re.IGNORECASE,
)


def _sanitize_dict(data: dict) -> dict:
    """Return a copy of *data* with credential-like field values redacted."""
    clean: dict = {}
    for key, value in data.items():
        if isinstance(key, str) and _CREDENTIAL_PATTERNS.search(key):
            clean[key] = "***REDACTED***"
        elif isinstance(value, dict):
            clean[key] = _sanitize_dict(value)
        elif isinstance(value, list):
            clean[key] = [
                _sanitize_dict(item) if isinstance(item, dict) else item
                for item in value
            ]
        else:
            clean[key] = value
    return clean


def _is_empty(memory: DomainMemory) -> bool:
    """Return True if a DomainMemory has no useful data."""
    return (
        not memory.sequences
        and not memory.selectors
        and not memory.preferences
    )


class MemoryStore:
    """Per-domain JSON memory store with TTL-based pruning.

    Memory files are stored as ``<memory_dir>/<domain>.json``.
    If a file is corrupted (invalid JSON), ``load()`` returns an empty
    :class:`DomainMemory` without crashing.
    """

    def __init__(self, memory_dir: Path, ttl_days: int = 30) -> None:
        self._dir = Path(memory_dir)
        self._ttl_days = ttl_days
        self._ttl_seconds = ttl_days * 86400

    # -- Core persistence --------------------------------------------------

    def save(self, domain: str, memory: DomainMemory) -> None:
        """Persist *memory* to a domain JSON file."""
        if _is_empty(memory):
            # Don't write empty stores to disk.
            return
        self._dir.mkdir(parents=True, exist_ok=True)
        path = self._domain_path(domain)
        data = memory.to_dict()
        # Final credential sweep across the entire payload.
        data = _sanitize_dict(data)
        data["updated_at"] = time.time()
        tmp_path = path.with_suffix(".tmp")
        try:
            tmp_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
            tmp_path.replace(path)
        except OSError:
            logger.exception("Failed to save memory for domain %s", domain)
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def load(self, domain: str) -> DomainMemory:
        """Load domain memory from disk.

        Returns an empty :class:`DomainMemory` if the file does not exist
        or is corrupted.
        """
        path = self._domain_path(domain)
        if not path.exists():
            return DomainMemory(domain=domain)
        try:
            raw = path.read_text(encoding="utf-8")
            data = json.loads(raw)
            return DomainMemory.from_dict(data)
        except (json.JSONDecodeError, ValueError, KeyError, TypeError) as exc:
            logger.warning(
                "Corrupted memory file for domain %s, returning empty store: %s",
                domain,
                exc,
            )
            return DomainMemory(domain=domain)
        except OSError as exc:
            logger.warning(
                "Cannot read memory file for domain %s: %s",
                domain,
                exc,
            )
            return DomainMemory(domain=domain)

    # -- Listing / clearing ------------------------------------------------

    def list_domains(self) -> list[str]:
        """Return domain names that have memory files on disk."""
        if not self._dir.exists():
            return []
        return sorted(
            p.stem for p in self._dir.glob("*.json")
        )

    def clear(self, domain: str) -> None:
        """Delete the memory file for *domain*."""
        path = self._domain_path(domain)
        try:
            path.unlink(missing_ok=True)
        except OSError:
            logger.exception("Failed to clear memory for domain %s", domain)

    # -- TTL pruning -------------------------------------------------------

    def prune(self) -> int:
        """Remove entries older than TTL.

        For each domain file, removes expired action sequences and deletes
        the file entirely if nothing remains.

        Returns the number of entries (sequences) removed.
        """
        removed = 0
        now = time.time()
        for domain in self.list_domains():
            memory = self.load(domain)
            before = len(memory.sequences)
            memory.sequences = [
                seq for seq in memory.sequences
                if (now - seq.created_at) < self._ttl_seconds
            ]
            removed += before - len(memory.sequences)
            if _is_empty(memory):
                self.clear(domain)
            elif removed > 0:
                memory.updated_at = now
                self.save(domain, memory)
        return removed

    # -- High-level record helpers -----------------------------------------

    def record_sequence(
        self,
        domain: str,
        task: str,
        actions: list[dict],
        success: bool,
    ) -> None:
        """Record an action sequence for *domain*.

        Only records if *success* is True (per blueprint authority rules).
        """
        if not success:
            return

        memory = self.load(domain)
        # Sanitize actions before storage.
        safe_actions = [_sanitize_dict(a) if isinstance(a, dict) else a for a in actions]
        memory.sequences.append(
            ActionSequence(
                task=task,
                actions=safe_actions,
                success=True,
                created_at=time.time(),
                used_count=0,
            )
        )
        memory.updated_at = time.time()
        self.save(domain, memory)

    def record_selector(self, domain: str, element: str, selector: str) -> None:
        """Record a working CSS selector for *element* on *domain*."""
        memory = self.load(domain)
        memory.selectors[element] = selector
        memory.updated_at = time.time()
        self.save(domain, memory)

    # -- Prompt context ----------------------------------------------------

    def get_context_for_prompt(self, domain: str) -> str:
        """Generate advisory text from domain memory for LLM prompt injection.

        Returns an empty string if there is nothing useful to inject.
        """
        memory = self.load(domain)
        parts: list[str] = []

        # Successful sequences
        successful = [s for s in memory.sequences if s.success]
        if successful:
            lines = ["Previous successful action sequences on this domain:"]
            for seq in successful[-5:]:  # Limit to recent 5
                action_desc = ", ".join(
                    a.get("action", str(a)) if isinstance(a, dict) else str(a)
                    for a in seq.actions[:10]
                )
                lines.append(f"  - Task: {seq.task} | Actions: {action_desc}")
            parts.append("\n".join(lines))

        # Working selectors
        if memory.selectors:
            lines = ["Working CSS selectors on this domain:"]
            for element, selector in list(memory.selectors.items())[-10:]:
                lines.append(f"  - {element}: {selector}")
            parts.append("\n".join(lines))

        # Preferences
        if memory.preferences:
            lines = ["Known preferences for this domain:"]
            for key, value in list(memory.preferences.items())[-5:]:
                lines.append(f"  - {key}: {value}")
            parts.append("\n".join(lines))

        return "\n\n".join(parts)

    # -- Internal ----------------------------------------------------------

    def _domain_path(self, domain: str) -> Path:
        """Return the file path for a domain's memory file."""
        # Sanitize domain for use as a filename.
        safe_name = re.sub(r"[^\w.\-]", "_", domain)
        return self._dir / f"{safe_name}.json"
