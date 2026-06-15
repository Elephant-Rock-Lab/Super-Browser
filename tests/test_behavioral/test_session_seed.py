"""Tests for SessionSeed — Track C slice 1 (Wave 22).

Covers derivation, determinism, independence, and edge cases.
"""

from __future__ import annotations

import random

from super_browser.behavioral.session_seed import SessionSeed


class TestSessionSeedBasics:
    def test_empty_seed_is_nondeterministic(self) -> None:
        session = SessionSeed()
        assert not session.is_deterministic
        assert session.base == ""

    def test_set_seed_is_deterministic(self) -> None:
        session = SessionSeed("repro-001")
        assert session.is_deterministic
        assert session.base == "repro-001"


class TestDerive:
    def test_derive_with_target(self) -> None:
        session = SessionSeed("test-session")
        seed = session.derive("click", "#submit-btn")
        assert seed == "test-session:click:#submit-btn"

    def test_derive_without_target(self) -> None:
        session = SessionSeed("test-session")
        seed = session.derive("navigate")
        assert seed == "test-session:navigate"

    def test_derive_different_actions_different_seeds(self) -> None:
        session = SessionSeed("abc")
        click_seed = session.derive("click", "#btn")
        type_seed = session.derive("type", "#btn")
        assert click_seed != type_seed

    def test_derive_different_targets_different_seeds(self) -> None:
        session = SessionSeed("abc")
        s1 = session.derive("click", "#btn1")
        s2 = session.derive("click", "#btn2")
        assert s1 != s2

    def test_derive_empty_when_nondeterministic(self) -> None:
        session = SessionSeed()
        assert session.derive("click", "#btn") == ""

    def test_derive_is_reproducible(self) -> None:
        """Same session seed + same action → same derived seed."""
        s1 = SessionSeed("session-xyz")
        s2 = SessionSeed("session-xyz")
        assert s1.derive("click", "#btn") == s2.derive("click", "#btn")


class TestRng:
    def test_rng_returns_random(self) -> None:
        session = SessionSeed("test")
        rng = session.rng("click", "#btn")
        assert isinstance(rng, random.Random)

    def test_rng_deterministic_with_seed(self) -> None:
        session1 = SessionSeed("repro-001")
        session2 = SessionSeed("repro-001")

        rng1 = session1.rng("click", "#btn")
        rng2 = session2.rng("click", "#btn")

        # Same seed → same sequence
        assert rng1.random() == rng2.random()
        assert rng1.random() == rng2.random()
        assert rng1.randint(0, 1000) == rng2.randint(0, 1000)

    def test_rng_different_actions_independent(self) -> None:
        """Different action types produce independent random streams."""
        session = SessionSeed("test")
        rng_click = session.rng("click", "#btn")
        rng_type = session.rng("type", "#btn")
        assert rng_click.random() != rng_type.random()

    def test_rng_different_targets_independent(self) -> None:
        session = SessionSeed("test")
        rng1 = session.rng("click", "#btn1")
        rng2 = session.rng("click", "#btn2")
        assert rng1.random() != rng2.random()

    def test_rng_unseeded_is_nondeterministic(self) -> None:
        session = SessionSeed()
        rng = session.rng("click", "#btn")
        # Unseeded Random — just verify it produces valid output
        assert 0.0 <= rng.random() <= 1.0


class TestReproducibilityIntegration:
    def test_full_session_reproducible(self) -> None:
        """Same session seed → same sequence of derived seeds."""
        base = "integration-test-001"
        s1 = SessionSeed(base)
        s2 = SessionSeed(base)

        actions = [
            ("navigate", "https://example.com"),
            ("click", "#login"),
            ("type", "#email"),
            ("click", "#submit"),
            ("scroll", "page-down"),
        ]

        seeds1 = [s1.derive(act, tgt) for act, tgt in actions]
        seeds2 = [s2.derive(act, tgt) for act, tgt in actions]

        assert seeds1 == seeds2
        # All seeds unique
        assert len(set(seeds1)) == len(seeds1)
        # All seeds start with base
        for s in seeds1:
            assert s.startswith(base + ":")
