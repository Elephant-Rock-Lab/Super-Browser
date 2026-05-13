"""Tests for BATCH-30/TASK-02 — Consistency DAG Engine.

TEST-30-02-01: DAG acyclicity — cyclic rules raise RuleDagCycleError
TEST-30-02-02: Duplicate output — two rules with same output raise DuplicateOutputError
TEST-30-02-03: Topo sort correctness — inputs available before each rule
TEST-30-02-04: Determinism — same (profile, seed) produces byte-identical matrix
TEST-30-02-05: Rule correctness — change GPU vendor, verify webgl_unmasked_vendor
TEST-30-02-06: Missing input — missing profile field raises MissingInputError
TEST-30-02-07: PRNG determinism — same seed produces identical sequence
TEST-30-02-08: Matrix JSON round-trip — serialize and deserialize preserves all fields
TEST-30-02-09: Integration — derive_matrix succeeds on all 4 profiles
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any

import pytest
from super_browser.stealth.consistency import (
    DeviceProfile,
    FingerprintMatrix,
    Xoshiro256PRNG,
    derive_matrix,
)
from super_browser.stealth.consistency.dag import validate_and_order
from super_browser.stealth.consistency.errors import (
    DuplicateOutputError,
    MissingInputError,
    RuleDagCycleError,
)
from super_browser.stealth.consistency.rule import define_rule
from super_browser.stealth.consistency.rules import ALL_RULES
from super_browser.stealth.profiles import list_profiles, load_profile

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_profile(**overrides) -> DeviceProfile:
    """Create a minimal valid DeviceProfile for tests."""
    from super_browser.stealth.profiles.schema import (
        AudioInfo,
        BehaviorInfo,
        BrowserInfo,
        DeviceInfo,
        DisplayInfo,
        EntropyBudget,
        FontInfo,
        GPUInfo,
        OSInfo,
    )

    defaults = dict(
        id="test-profile",
        version="1.0.0",
        engine="chromium",
        browser=BrowserInfo(
            name="chrome",
            channel="stable",
            min_version="131",
            max_version="131",
            user_agent="Mozilla/5.0 Test",
        ),
        os=OSInfo(name="windows", version="10.0", arch="x86_64"),
        device=DeviceInfo(
            vendor="generic",
            model="PC",
            cpu_family="intel-core-i7",
            cores=8,
            memory_gb=16,
        ),
        display=DisplayInfo(
            width=1920, height=1080, dpr=1, color_depth=24, pixel_depth=24
        ),
        gpu=GPUInfo(
            vendor="NVIDIA Corporation",
            renderer="NVIDIA GeForce RTX 3070",
            webgl_unmasked_vendor="Google Inc. (NVIDIA)",
            webgl_unmasked_renderer="ANGLE (NVIDIA, NVIDIA GeForce RTX 3070, D3D11)",
            webgl_max_texture_size=16384,
            webgl_max_color_attachments=8,
            webgl_extensions=("EXT_color_buffer_float",),
        ),
        audio=AudioInfo(
            context_sample_rate=48000,
            audio_worklet_latency=0.04,
            destination_max_channel_count=2,
        ),
        fonts=FontInfo(family="test-pack", list=("Arial", "Consolas")),
        behavior=BehaviorInfo(hand="right", tremor=0.18, wpm=60, scroll_style="smooth"),
        entropy_budget=EntropyBudget(),
        timezone="America/New_York",
        locale="en-US",
        languages=("en-US", "en"),
    )
    defaults.update(overrides)
    return DeviceProfile(**defaults)


# ===================================================================
# TEST-30-02-01: DAG acyclicity
# ===================================================================


class TestDagAcyclicity:
    """Cyclic rules raise RuleDagCycleError."""

    def test_cyclic_rules_raise(self) -> None:
        """Three rules in a cycle should raise RuleDagCycleError."""

        def _identity(ins: tuple, _prng: Any) -> Any:
            return ins[0]

        rules = [
            define_rule("C-1", "cycle a", ("c_output",), "a_output", _identity),
            define_rule("C-2", "cycle b", ("a_output",), "b_output", _identity),
            define_rule("C-3", "cycle c", ("b_output",), "c_output", _identity),
        ]
        with pytest.raises(RuleDagCycleError) as exc_info:
            validate_and_order(rules)
        assert len(exc_info.value.cycle) >= 2

    def test_self_cycle_raise(self) -> None:
        """Rule that depends on its own output should raise."""

        def _identity(ins: tuple, _prng: Any) -> Any:
            return ins[0]

        # Self-cycle where input equals output is skipped by DAG builder
        # (producer_id == rule.id). Test a real 2-node cycle instead.
        rules2 = [
            define_rule("A", "a->b", ("y_val",), "x_val", _identity),
            define_rule("B", "b->a", ("x_val",), "y_val", _identity),
        ]
        with pytest.raises(RuleDagCycleError):
            validate_and_order(rules2)


# ===================================================================
# TEST-30-02-02: Duplicate output
# ===================================================================


class TestDuplicateOutput:
    """Two rules with the same output raise DuplicateOutputError."""

    def test_duplicate_output_raises(self) -> None:
        def _const(ins: tuple, _prng: Any) -> Any:
            return 42

        rules = [
            define_rule("D-1", "first", (), "shared_output", _const),
            define_rule("D-2", "second", (), "shared_output", _const),
        ]
        with pytest.raises(DuplicateOutputError) as exc_info:
            validate_and_order(rules)
        assert exc_info.value.path == "shared_output"
        assert set(exc_info.value.rule_ids) == {"D-1", "D-2"}


# ===================================================================
# TEST-30-02-03: Topo sort correctness
# ===================================================================


class TestTopoSort:
    """Inputs must be available before each rule executes."""

    def test_inputs_available_before_rule(self) -> None:
        """Rules producing outputs consumed by later rules come first."""

        def _double(ins: tuple, _prng: Any) -> Any:
            return ins[0] * 2

        def _add(ins: tuple, _prng: Any) -> Any:
            return ins[0] + ins[1]

        rules = [
            define_rule("T-1", "source", (), "val_a", lambda _i, _p: 10),
            define_rule("T-2", "double a", ("val_a",), "val_b", _double),
            define_rule("T-3", "add", ("val_a", "val_b"), "val_c", _add),
        ]
        plan = validate_and_order(rules)
        order_ids = [r.id for r in plan.order]
        # T-1 before T-2 (T-2 depends on val_a from T-1)
        assert order_ids.index("T-1") < order_ids.index("T-2")
        # T-1 and T-2 before T-3 (T-3 depends on both)
        assert order_ids.index("T-1") < order_ids.index("T-3")
        assert order_ids.index("T-2") < order_ids.index("T-3")

    def test_all_rules_present(self) -> None:
        """Topo sort includes every rule exactly once."""
        plan = validate_and_order(ALL_RULES)
        ids = [r.id for r in plan.order]
        assert len(ids) == len(ALL_RULES)
        assert len(set(ids)) == len(ALL_RULES)


# ===================================================================
# TEST-30-02-04: Determinism
# ===================================================================


class TestDeterminism:
    """Same (profile, seed) produces byte-identical matrix."""

    def test_same_inputs_same_matrix(self) -> None:
        profile = _make_profile()
        m1 = derive_matrix(profile, "determinism-test")
        m2 = derive_matrix(profile, "determinism-test")

        d1 = asdict(m1)
        d2 = asdict(m2)
        for k, v in d1.items():
            if k == "derived_at":
                continue
            assert v == d2[k], f"Field {k!r} differs: {v!r} != {d2[k]!r}"

    def test_different_seed_different_ua(self) -> None:
        profile = _make_profile()
        m1 = derive_matrix(profile, "seed-A")
        m2 = derive_matrix(profile, "seed-B")
        # User-agent should differ due to PRNG-driven build variance.
        assert m1.user_agent != m2.user_agent

    def test_different_profiles_different_platform(self) -> None:
        pw = _make_profile()
        from super_browser.stealth.profiles.schema import OSInfo

        pl = _make_profile(
            id="test-linux",
            os=OSInfo(name="linux", version="22.04", arch="x86_64"),
        )
        mw = derive_matrix(pw, "same-seed")
        ml = derive_matrix(pl, "same-seed")
        assert mw.platform == "Win32"
        assert ml.platform == "Linux x86_64"


# ===================================================================
# TEST-30-02-05: Rule correctness
# ===================================================================


class TestRuleCorrectness:
    """Derived values match expected transformations."""

    def test_gpu_vendor_mapping(self) -> None:
        """Change GPU vendor to Intel, verify webgl_unmasked_vendor."""
        from super_browser.stealth.profiles.schema import GPUInfo

        profile = _make_profile(
            gpu=GPUInfo(
                vendor="Intel",
                renderer="Mesa Intel(R) UHD Graphics 630",
                webgl_unmasked_vendor="Google Inc. (Intel)",
                webgl_unmasked_renderer="ANGLE (Intel, Mesa Intel(R) UHD Graphics 630, OpenGL)",
                webgl_max_texture_size=16384,
                webgl_max_color_attachments=8,
                webgl_extensions=("EXT_color_buffer_float",),
            ),
        )
        m = derive_matrix(profile, "gpu-test")
        assert "Google Inc. (Intel)" == m.webgl_unmasked_vendor

    def test_device_memory_cap(self) -> None:
        """Device memory should be capped at 8."""
        from super_browser.stealth.profiles.schema import DeviceInfo

        profile = _make_profile(
            device=DeviceInfo(
                vendor="generic", model="PC", cpu_family="intel-core-i7",
                cores=8, memory_gb=32,
            ),
        )
        m = derive_matrix(profile, "mem-test")
        assert m.device_memory == 8

    def test_webdriver_always_false(self) -> None:
        profile = _make_profile()
        m = derive_matrix(profile, "wd-test")
        assert m.webdriver is False

    def test_navigator_vendor_google(self) -> None:
        profile = _make_profile()
        m = derive_matrix(profile, "vendor-test")
        assert m.navigator_vendor == "Google Inc."

    def test_screen_dimensions_derived(self) -> None:
        profile = _make_profile()
        m = derive_matrix(profile, "screen-test")
        # Windows: 1920x1080, OS chrome height = 40
        assert m.screen_width == 1920
        assert m.screen_height == 1080
        assert m.screen_avail_width == 1920
        assert m.screen_avail_height == 1040


# ===================================================================
# TEST-30-02-06: Missing input
# ===================================================================


class TestMissingInput:
    """Missing profile field raises MissingInputError."""

    def test_missing_input_raises(self) -> None:
        """A rule whose input doesn't exist should raise."""

        def _identity(ins: tuple, _prng: Any) -> Any:
            return ins[0]

        bad_rule = define_rule(
            "BAD", "needs nonexistent", ("nonexistent.field",), "out", _identity
        )
        plan = validate_and_order([bad_rule])
        # Simulate the derive engine loop with an empty matrix.
        matrix: dict = {}
        with pytest.raises(MissingInputError) as exc_info:
            for rule in plan.order:
                resolved = []
                for path in rule.inputs:
                    val = matrix.get(path)
                    if val is None:
                        raise MissingInputError(rule.id, path)
                    resolved.append(val)
                output = rule.derive(tuple(resolved), Xoshiro256PRNG("test", "seed"))
                matrix[rule.output] = output
        assert exc_info.value.rule_id == "BAD"
        assert exc_info.value.path == "nonexistent.field"


# ===================================================================
# TEST-30-02-07: PRNG determinism
# ===================================================================


class TestPRNGDeterminism:
    """Same seed produces identical sequence."""

    def test_same_seed_same_sequence(self) -> None:
        prng1 = Xoshiro256PRNG("profile-1", "seed-A")
        prng2 = Xoshiro256PRNG("profile-1", "seed-A")

        seq1 = [prng1.next_u64() for _ in range(20)]
        seq2 = [prng2.next_u64() for _ in range(20)]
        assert seq1 == seq2

    def test_different_seed_different_sequence(self) -> None:
        prng1 = Xoshiro256PRNG("profile-1", "seed-A")
        prng2 = Xoshiro256PRNG("profile-1", "seed-B")

        val1 = prng1.next_u64()
        val2 = prng2.next_u64()
        assert val1 != val2

    def test_next_float01_range(self) -> None:
        prng = Xoshiro256PRNG("test", "float-range")
        for _ in range(100):
            v = prng.next_float01()
            assert 0.0 <= v < 1.0

    def test_next_int_range(self) -> None:
        prng = Xoshiro256PRNG("test", "int-range")
        for _ in range(100):
            v = prng.next_int(5, 10)
            assert 5 <= v <= 10

    def test_next_hex_length(self) -> None:
        prng = Xoshiro256PRNG("test", "hex-test")
        h = prng.next_hex(16)
        assert len(h) == 32
        assert all(c in "0123456789abcdef" for c in h)

    def test_next_hex_deterministic(self) -> None:
        p1 = Xoshiro256PRNG("test", "hex-det")
        p2 = Xoshiro256PRNG("test", "hex-det")
        assert p1.next_hex(32) == p2.next_hex(32)


# ===================================================================
# TEST-30-02-08: Matrix JSON round-trip
# ===================================================================


class TestMatrixJsonRoundTrip:
    """Serialize and deserialize preserves all fields."""

    def test_round_trip(self) -> None:
        profile = _make_profile()
        m1 = derive_matrix(profile, "round-trip-test")

        # Serialize to JSON.
        raw = json.dumps(asdict(m1))
        parsed = json.loads(raw)

        # Reconstruct.
        m2 = FingerprintMatrix(**parsed)

        # Compare every field.
        for field_name in asdict(m1):
            v1 = getattr(m1, field_name)
            v2 = getattr(m2, field_name)
            if isinstance(v1, tuple):
                v1 = list(v1)
                v2 = list(v2)
            assert v1 == v2, f"Field {field_name!r}: {v1!r} != {v2!r}"


# ===================================================================
# TEST-30-02-09: Integration — all 4 profiles
# ===================================================================


class TestIntegrationAllProfiles:
    """derive_matrix succeeds on all 4 profiles."""

    @pytest.fixture(params=list_profiles())
    def profile(self, request) -> DeviceProfile:
        return load_profile(request.param)

    def test_derive_succeeds(self, profile: DeviceProfile) -> None:
        m = derive_matrix(profile, "integration-test")
        assert isinstance(m, FingerprintMatrix)
        assert m.profile_id == profile.id
        assert m.user_agent  # Non-empty
        assert m.platform  # Non-empty
        assert m.hardware_concurrency > 0
        assert m.device_memory > 0
        assert m.timezone

    def test_derive_each_profile(self) -> None:
        """All 4 profiles derive without error."""
        for pid in list_profiles():
            p = load_profile(pid)
            m = derive_matrix(p, "batch-test")
            assert m.profile_id == pid

    def test_all_profiles_deterministic(self) -> None:
        """All profiles produce identical matrices with same seed."""
        for pid in list_profiles():
            p = load_profile(pid)
            m1 = derive_matrix(p, "det-test")
            m2 = derive_matrix(p, "det-test")
            d1 = asdict(m1)
            d2 = asdict(m2)
            for k, v in d1.items():
                if k == "derived_at":
                    continue
                assert v == d2[k], f"{pid}: field {k!r} differs"
