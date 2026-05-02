"""Tests for VisionCache — LRU, dHash invalidation, persistence."""

import asyncio
import json
import tempfile
from pathlib import Path

from super_browser.interaction.types import VisionResponse
from super_browser.vision.cache import VisionCache


def _make_png():
    """Create a valid PNG image — all white (produces dHash 0)."""
    from PIL import Image
    from io import BytesIO
    img = Image.new("L", (100, 100), 255)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _make_png_different():
    """Create a valid PNG image — checkerboard (produces very different dHash)."""
    from PIL import Image
    from io import BytesIO
    img = Image.new("L", (100, 100), 0)
    for x in range(100):
        for y in range(100):
            if (x + y) % 2 == 0:
                img.putpixel((x, y), 255)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


class TestVisionCacheBasic:
    def test_put_get(self):
        cache = VisionCache()
        img = _make_png()
        resp = VisionResponse(found=True, x=100.0, y=200.0, confidence=0.9)
        cache.put(img, "button", resp)
        result = cache.get(img, "button")
        assert result is not None
        assert result.x == 100.0

    def test_miss(self):
        cache = VisionCache()
        assert cache.get(_make_png(), "button") is None

    def test_size(self):
        cache = VisionCache()
        assert cache.size == 0
        cache.put(_make_png(), "btn", VisionResponse(found=True))
        assert cache.size == 1


class TestVisionCacheHitRate:
    def test_initial_rate(self):
        cache = VisionCache()
        assert cache.hit_rate == 0.0

    def test_after_hit(self):
        cache = VisionCache()
        img = _make_png()
        cache.put(img, "btn", VisionResponse(found=True))
        cache.get(img, "btn")
        assert cache.hit_rate == 1.0

    def test_mixed(self):
        cache = VisionCache()
        img = _make_png()
        cache.put(img, "btn", VisionResponse(found=True))
        cache.get(img, "btn")
        cache.get(img, "other")
        assert cache.hit_rate == 0.5


class TestVisionCacheDhashInvalidation:
    def test_same_image_hits(self):
        cache = VisionCache()
        img = _make_png()
        cache.put(img, "btn", VisionResponse(found=True, x=10))
        assert cache.get(img, "btn") is not None

    def test_different_image_misses(self):
        cache = VisionCache(dhash_threshold=0)
        cache.put(_make_png(), "btn", VisionResponse(found=True, x=10))
        assert cache.get(_make_png_different(), "btn") is None


class TestVisionCacheLRU:
    def test_eviction(self):
        cache = VisionCache(max_entries=3)
        img = _make_png()
        for i in range(4):
            cache.put(img, f"btn-{i}", VisionResponse(found=True, x=float(i)))
        assert cache.size == 3
        assert cache.get(img, "btn-0") is None

    def test_clear(self):
        cache = VisionCache()
        cache.put(_make_png(), "btn", VisionResponse(found=True))
        count = cache.clear()
        assert count == 1
        assert cache.size == 0

    def test_invalidate(self):
        cache = VisionCache()
        img = _make_png()
        cache.put(img, "btn", VisionResponse(found=True, x=10))
        assert cache.invalidate("btn") is True
        assert cache.get(img, "btn") is None

    def test_invalidate_no_match(self):
        cache = VisionCache()
        assert cache.invalidate("nonexistent") is False


class TestVisionCachePersistence:
    def test_persist_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = VisionCache(cache_dir=Path(tmpdir))
            img = _make_png()
            cache.put(img, "button", VisionResponse(found=True, x=50.0))

            asyncio.run(cache.persist())
            assert (Path(tmpdir) / "cache.json").exists()

            cache2 = VisionCache(cache_dir=Path(tmpdir))
            count = asyncio.run(cache2.load())
            assert count == 1

    def test_load_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cache = VisionCache(cache_dir=Path(tmpdir))
            count = asyncio.run(cache.load())
            assert count == 0


class TestDhashComputation:
    def test_consistent(self):
        img = _make_png()
        h1 = VisionCache.compute_dhash(img)
        h2 = VisionCache.compute_dhash(img)
        assert h1 == h2

    def test_distance_same(self):
        h = VisionCache.compute_dhash(_make_png())
        assert VisionCache.dhash_distance(h, h) == 0

    def test_distance_different(self):
        h1 = VisionCache.compute_dhash(_make_png())
        h2 = VisionCache.compute_dhash(_make_png_different())
        assert VisionCache.dhash_distance(h1, h2) > 0
