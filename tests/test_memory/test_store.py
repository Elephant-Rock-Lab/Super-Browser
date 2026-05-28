"""TEST-25-01-*: MemoryStore unit tests — persistence, TTL, corruption, context."""

from __future__ import annotations

import time

import pytest

from super_browser.memory.store import MemoryStore, _sanitize_dict
from super_browser.memory.types import ActionSequence, DomainMemory

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def store(tmp_path):
    """Return a MemoryStore backed by a temp directory."""
    return MemoryStore(tmp_path / "memory", ttl_days=30)


@pytest.fixture()
def store_short_ttl(tmp_path):
    """Return a MemoryStore with 0-day TTL (immediate expiry)."""
    return MemoryStore(tmp_path / "memory", ttl_days=0)


# ---------------------------------------------------------------------------
# TEST-25-01-01: save() writes domain file
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def test_save_creates_file(self, store):
        """TEST-25-01-01: store.save() writes domain file to disk."""
        mem = DomainMemory(domain="example.com")
        mem.sequences.append(ActionSequence(task="login", actions=[{"action": "click"}]))
        store.save("example.com", mem)
        assert store._domain_path("example.com").exists()

    # -----------------------------------------------------------------------
    # TEST-25-01-02: load() reads domain file
    # -----------------------------------------------------------------------

    def test_load_reconstructs_memory(self, store):
        """TEST-25-01-02: store.load() reconstructs full memory from file."""
        mem = DomainMemory(domain="example.com")
        mem.sequences.append(
            ActionSequence(task="login", actions=[{"action": "click", "target": "#btn"}])
        )
        mem.selectors["login_button"] = "#btn"
        store.save("example.com", mem)

        loaded = store.load("example.com")
        assert loaded.domain == "example.com"
        assert len(loaded.sequences) == 1
        assert loaded.sequences[0].task == "login"
        assert loaded.sequences[0].actions == [{"action": "click", "target": "#btn"}]
        assert loaded.selectors["login_button"] == "#btn"

    def test_load_nonexistent_returns_empty(self, store):
        """Loading a domain that has no file returns empty DomainMemory."""
        loaded = store.load("missing.com")
        assert loaded.domain == "missing.com"
        assert loaded.sequences == []
        assert loaded.selectors == {}


# ---------------------------------------------------------------------------
# TEST-25-01-03: get_context_for_prompt() returns advisory text
# ---------------------------------------------------------------------------

class TestContextForPrompt:
    def test_context_contains_successful(self, store):
        """TEST-25-01-03: get_context_for_prompt() returns prompt text."""
        mem = DomainMemory(domain="shop.example.com")
        mem.sequences.append(
            ActionSequence(
                task="add to cart",
                actions=[{"action": "click"}, {"action": "fill"}],
                success=True,
            )
        )
        store.save("shop.example.com", mem)
        ctx = store.get_context_for_prompt("shop.example.com")
        assert "Previous successful" in ctx
        assert "add to cart" in ctx

    def test_context_empty_for_empty_domain(self, store):
        """Context is empty string when no data exists."""
        ctx = store.get_context_for_prompt("empty.com")
        assert ctx == ""


# ---------------------------------------------------------------------------
# TEST-25-01-04: prune() removes expired entries
# ---------------------------------------------------------------------------

class TestPrune:
    def test_prune_removes_old_entries(self, store_short_ttl):
        """TEST-25-01-04: prune() removes entries older than TTL."""
        mem = DomainMemory(domain="old.example.com")
        # created_at in the distant past
        mem.sequences.append(
            ActionSequence(
                task="old task",
                actions=[{"action": "click"}],
                success=True,
                created_at=time.time() - 999999,
            )
        )
        store_short_ttl.save("old.example.com", mem)

        removed = store_short_ttl.prune()
        assert removed >= 1
        # After pruning the empty domain file should be deleted
        assert "old.example.com" not in store_short_ttl.list_domains()

    def test_prune_keeps_fresh_entries(self, store):
        """Fresh entries survive pruning."""
        mem = DomainMemory(domain="fresh.example.com")
        mem.sequences.append(
            ActionSequence(task="fresh task", actions=[{"action": "click"}], success=True)
        )
        store.save("fresh.example.com", mem)

        removed = store.prune()
        assert removed == 0
        loaded = store.load("fresh.example.com")
        assert len(loaded.sequences) == 1


# ---------------------------------------------------------------------------
# TEST-25-01-05: Corrupted JSON returns empty store
# ---------------------------------------------------------------------------

class TestCorruptedFiles:
    def test_corrupted_json_returns_empty(self, store):
        """TEST-25-01-05: Corrupted JSON returns empty store without crash."""
        store._dir.mkdir(parents=True, exist_ok=True)
        path = store._domain_path("bad.example.com")
        path.write_text("{ this is not valid JSON !!!", encoding="utf-8")

        loaded = store.load("bad.example.com")
        assert loaded.domain == "bad.example.com"
        assert loaded.sequences == []

    def test_empty_file_returns_empty(self, store):
        """Empty file also returns empty store."""
        store._dir.mkdir(parents=True, exist_ok=True)
        path = store._domain_path("empty.example.com")
        path.write_text("", encoding="utf-8")

        loaded = store.load("empty.example.com")
        assert loaded.sequences == []


# ---------------------------------------------------------------------------
# TEST-25-01-06: Entries have timestamps > 0
# ---------------------------------------------------------------------------

class TestTimestamps:
    def test_entries_have_timestamps(self, store):
        """TEST-25-01-06: All entries have created_at > 0."""
        mem = DomainMemory(domain="ts.example.com")
        seq = ActionSequence(task="ts task", actions=[{"action": "click"}])
        assert seq.created_at > 0
        mem.sequences.append(seq)
        store.save("ts.example.com", mem)

        loaded = store.load("ts.example.com")
        assert all(s.created_at > 0 for s in loaded.sequences)


# ---------------------------------------------------------------------------
# Credential filtering (HB-25-03)
# ---------------------------------------------------------------------------

class TestCredentialFiltering:
    def test_sanitize_redacts_api_key(self):
        """Credential fields are redacted during sanitization."""
        data = {"api_key": "sk-12345", "name": "test"}
        clean = _sanitize_dict(data)
        assert clean["api_key"] == "***REDACTED***"
        assert clean["name"] == "test"

    def test_sanitize_redacts_nested_credentials(self):
        """Nested credential fields are also redacted."""
        data = {"config": {"password": "hunter2", "host": "localhost"}}
        clean = _sanitize_dict(data)
        assert clean["config"]["password"] == "***REDACTED***"
        assert clean["config"]["host"] == "localhost"

    def test_saved_memory_has_no_credentials(self, store):
        """Credentials are not stored in memory files (HB-25-03)."""
        mem = DomainMemory(domain="creds.example.com")
        mem.sequences.append(
            ActionSequence(
                task="login",
                actions=[{"action": "fill", "api_key": "sk-SECRET", "field": "email"}],
            )
        )
        store.save("creds.example.com", mem)

        # Read raw file and check
        raw = store._domain_path("creds.example.com").read_text(encoding="utf-8")
        assert "sk-SECRET" not in raw
        assert "***REDACTED***" in raw

    def test_record_sequence_filters_credentials(self, store):
        """record_sequence sanitizes action dicts."""
        store.record_sequence(
            "login.example.com",
            "login",
            [{"action": "fill", "token": "abc123"}],
            success=True,
        )
        loaded = store.load("login.example.com")
        assert loaded.sequences[0].actions[0]["token"] == "***REDACTED***"

    def test_failed_sequence_not_recorded(self, store):
        """Failed sequences are NOT saved (authority rules)."""
        store.record_sequence(
            "fail.example.com",
            "broken login",
            [{"action": "click"}],
            success=False,
        )
        loaded = store.load("fail.example.com")
        assert len(loaded.sequences) == 0


# ---------------------------------------------------------------------------
# list_domains / clear
# ---------------------------------------------------------------------------

class TestListAndClear:
    def test_list_domains(self, store):
        """list_domains returns saved domain names."""
        mem = DomainMemory(domain="a.com")
        mem.sequences.append(ActionSequence(task="x", actions=[{"action": "y"}]))
        store.save("a.com", mem)

        mem2 = DomainMemory(domain="b.com")
        mem2.sequences.append(ActionSequence(task="z", actions=[{"action": "w"}]))
        store.save("b.com", mem2)

        domains = store.list_domains()
        assert "a.com" in domains
        assert "b.com" in domains

    def test_clear_deletes_file(self, store):
        """clear() deletes the domain file."""
        mem = DomainMemory(domain="rm.example.com")
        mem.sequences.append(ActionSequence(task="x", actions=[{"action": "y"}]))
        store.save("rm.example.com", mem)
        assert store._domain_path("rm.example.com").exists()

        store.clear("rm.example.com")
        assert not store._domain_path("rm.example.com").exists()


# ---------------------------------------------------------------------------
# record_selector
# ---------------------------------------------------------------------------

class TestRecordSelector:
    def test_record_selector(self, store):
        """Working selectors are recorded to domain memory."""
        store.record_selector("sel.example.com", "login_button", "#login-btn")
        loaded = store.load("sel.example.com")
        assert loaded.selectors["login_button"] == "#login-btn"
