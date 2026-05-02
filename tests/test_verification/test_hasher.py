"""Tests for perceptual hash computation: dHash, pHash, cache."""

import hashlib
import io

import pytest
from PIL import Image

from super_browser.verification.hasher import (
    HasherCache,
    compute_dhash,
    compute_hash,
    compute_phash,
)
from super_browser.verification.types import PerceptualHash


def _make_image(width=1920, height=1080, color="red") -> bytes:
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_checkerboard(size=200, block=10) -> bytes:
    img = Image.new("L", (size, size))
    for x in range(size):
        for y in range(size):
            val = 255 if (x // block + y // block) % 2 == 0 else 0
            img.putpixel((x, y), val)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestDHash:
    def test_same_image_identical(self):
        data = _make_image()
        assert compute_dhash(data) == compute_dhash(data)

    def test_different_images_differ(self):
        h1 = compute_dhash(_make_checkerboard())
        h2 = compute_dhash(_make_image(color="white"))
        assert h1 != h2

    def test_returns_64bit(self):
        h = compute_dhash(_make_image())
        assert 0 <= h < 2**64

    def test_checkerboard_has_structure(self):
        h = compute_dhash(_make_checkerboard())
        assert h != 0


class TestPHash:
    def test_same_image_identical(self):
        data = _make_image()
        assert compute_phash(data) == compute_phash(data)

    def test_returns_64bit(self):
        h = compute_phash(_make_image())
        assert 0 <= h < 2**64

    def test_resilient_to_reencoding(self):
        original = _make_image()
        img = Image.open(io.BytesIO(original))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        reencoded = buf.getvalue()
        h1 = compute_phash(original)
        h2 = compute_phash(reencoded)
        dist = bin(h1 ^ h2).count("1")
        assert dist < 5

    def test_different_images_differ(self):
        h1 = compute_phash(_make_image(color="white"))
        h2 = compute_phash(_make_image(color="black"))
        dist = bin(h1 ^ h2).count("1")
        assert dist > 5


class TestComputeHash:
    def test_returns_perceptual_hash(self):
        data = _make_image()
        h = compute_hash(data)
        assert isinstance(h, PerceptualHash)
        assert h.source_sha256 == hashlib.sha256(data).hexdigest()

    def test_deterministic(self):
        data = _make_image()
        h1 = compute_hash(data)
        h2 = compute_hash(data)
        assert h1.dhash == h2.dhash
        assert h1.phash == h2.phash


class TestHasherCache:
    def test_miss_returns_none(self):
        cache = HasherCache(max_size=10)
        assert cache.get("nonexistent") is None

    def test_put_and_get(self):
        cache = HasherCache(max_size=10)
        ph = PerceptualHash(dhash=42, phash=99, source_sha256="abc")
        cache.put("abc", ph)
        assert cache.get("abc") == ph

    def test_eviction(self):
        cache = HasherCache(max_size=3)
        for i in range(5):
            cache.put(f"key{i}", PerceptualHash(dhash=i, phash=i))
        assert cache.size == 3
        assert cache.get("key0") is None
        assert cache.get("key4") is not None

    def test_lru_eviction_order(self):
        cache = HasherCache(max_size=3)
        cache.put("a", PerceptualHash(dhash=1, phash=1))
        cache.put("b", PerceptualHash(dhash=2, phash=2))
        cache.put("c", PerceptualHash(dhash=3, phash=3))
        cache.get("a")  # access 'a', making it most recent
        cache.put("d", PerceptualHash(dhash=4, phash=4))  # evicts 'b'
        assert cache.get("a") is not None
        assert cache.get("b") is None
        assert cache.get("c") is not None

    def test_clear(self):
        cache = HasherCache(max_size=10)
        cache.put("x", PerceptualHash(dhash=0, phash=0))
        cache.clear()
        assert cache.size == 0
        assert cache.get("x") is None

    def test_overwrite_existing(self):
        cache = HasherCache(max_size=10)
        cache.put("k", PerceptualHash(dhash=1, phash=1))
        cache.put("k", PerceptualHash(dhash=2, phash=2))
        result = cache.get("k")
        assert result.dhash == 2
        assert cache.size == 1
