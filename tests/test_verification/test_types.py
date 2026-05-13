"""Tests for verification types: enums, PerceptualHash, dataclasses."""

from super_browser.verification.types import (
    ActionVerifiability,
    AXDiffResult,
    PerceptualHash,
    VerificationActionType,
    VerificationLevel,
    VerificationResult,
    VerifierConfig,
)


class TestVerificationLevel:
    def test_values(self):
        assert VerificationLevel.NONE == "none"
        assert VerificationLevel.HASH == "hash"
        assert VerificationLevel.STRUCTURAL_AX == "structural_ax"
        assert VerificationLevel.VLM_FULL == "vlm_full"


class TestVerificationActionType:
    def test_values(self):
        assert VerificationActionType.NAVIGATE == "navigate"
        assert VerificationActionType.CLICK == "click"
        assert VerificationActionType.HOVER == "hover"
        assert VerificationActionType.KEYPRESS == "keypress"


class TestPerceptualHash:
    def test_identical_distance_zero(self):
        h = PerceptualHash(dhash=0b1111111111111111, phash=0b1010101010101010)
        assert h.hamming_distance(h) == 0

    def test_dhash_distance(self):
        a = PerceptualHash(dhash=0b1111000011110000, phash=0)
        b = PerceptualHash(dhash=0b1111000011110001, phash=0)
        assert a.dhash_distance(b) == 1

    def test_phash_distance(self):
        a = PerceptualHash(dhash=0, phash=0b1010101010101010)
        b = PerceptualHash(dhash=0, phash=0b0101010101010101)
        assert a.phash_distance(b) == 16

    def test_hamming_returns_max(self):
        a = PerceptualHash(dhash=0b11110000, phash=0b10101010)
        b = PerceptualHash(dhash=0b11110001, phash=0b01010101)
        assert a.hamming_distance(b) == 8  # max(1, 8)

    def test_completely_different(self):
        a = PerceptualHash(dhash=0, phash=0)
        b = PerceptualHash(dhash=2**64 - 1, phash=2**64 - 1)
        assert a.hamming_distance(b) == 64

    def test_hex_properties(self):
        h = PerceptualHash(dhash=0xDEADBEEFDEADBEEF, phash=0xCAFEBABECAFEBABE)
        assert h.dhash_hex == "deadbeefdeadbeef"
        assert h.phash_hex == "cafebabecafebabe"

    def test_frozen(self):
        h = PerceptualHash(dhash=0, phash=0)
        try:
            h.dhash = 1
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_source_sha256_default(self):
        h = PerceptualHash(dhash=0, phash=0)
        assert h.source_sha256 == ""


class TestAXDiffResult:
    def test_total_interactive_changes(self):
        r = AXDiffResult(nodes_added=2, nodes_removed=1, nodes_changed=3)
        assert r.total_interactive_changes == 6

    def test_zero_changes(self):
        r = AXDiffResult()
        assert r.total_interactive_changes == 0


class TestVerificationResult:
    def test_frozen(self):
        r = VerificationResult(
            changed=True, confidence=0.9, similarity=0.8,
            level=VerificationLevel.HASH,
        )
        try:
            r.changed = False
            assert False, "Should be frozen"
        except AttributeError:
            pass

    def test_with_error(self):
        r = VerificationResult(
            changed=None, confidence=0.0, similarity=0.0,
            level=VerificationLevel.HASH, error="CDP failed",
        )
        assert r.error == "CDP failed"
        assert r.changed is None


class TestVerifierConfig:
    def test_defaults(self):
        c = VerifierConfig()
        assert c.default_level == VerificationLevel.HASH
        assert c.hash_threshold == 10
        assert c.settle_ms == 500
        assert c.hash_cache_size == 256

    def test_frozen(self):
        c = VerifierConfig()
        try:
            c.hash_threshold = 5
            assert False, "Should be frozen"
        except AttributeError:
            pass


class TestActionVerifiability:
    def test_fields(self):
        a = ActionVerifiability(
            action_type=VerificationActionType.CLICK,
            should_verify=True,
            reason="click is state-changing",
        )
        assert a.should_verify
        assert a.recommended_level == VerificationLevel.HASH
