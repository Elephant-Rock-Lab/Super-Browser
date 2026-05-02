"""VisionCache — LRU cache with dHash-based invalidation for vision results."""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections import OrderedDict
from pathlib import Path
from typing import Any, Optional

from super_browser.vision.types import VisionCacheEntry

logger = logging.getLogger(__name__)

_HAS_PIL = False
try:
    from PIL import Image
    from io import BytesIO
    _HAS_PIL = True
except ImportError:
    pass


class VisionCache:

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_entries: int = 500,
        dhash_threshold: int = 4,
    ) -> None:
        self._cache_dir = cache_dir or Path.home() / ".super-browser" / "vision-cache"
        self._max_entries = max_entries
        self._dhash_threshold = dhash_threshold
        self._entries: OrderedDict[str, VisionCacheEntry] = OrderedDict()
        self._hits = 0
        self._misses = 0

    def get(self, screenshot: bytes, description: str) -> Optional[Any]:
        dhash = self.compute_dhash(screenshot)
        key = self._make_key(dhash, description)
        entry = self._entries.get(key)
        if entry is None:
            self._misses += 1
            return None
        distance = self.dhash_distance(dhash, entry.image_dhash)
        if distance > self._dhash_threshold:
            del self._entries[key]
            self._misses += 1
            return None
        entry.last_hit = time.monotonic()
        entry.hit_count += 1
        self._entries.move_to_end(key)
        self._hits += 1
        return entry.response

    def put(self, screenshot: bytes, description: str, response: Any) -> None:
        dhash = self.compute_dhash(screenshot)
        key = self._make_key(dhash, description)
        if key in self._entries:
            del self._entries[key]
        if len(self._entries) >= self._max_entries:
            self._entries.popitem(last=False)
        self._entries[key] = VisionCacheEntry(
            key=key, description=description,
            response=response, image_dhash=dhash,
        )

    def invalidate(self, description: str) -> bool:
        keys_to_remove = [
            k for k, e in self._entries.items() if e.description == description
        ]
        for k in keys_to_remove:
            del self._entries[k]
        return len(keys_to_remove) > 0

    def clear(self) -> int:
        count = len(self._entries)
        self._entries.clear()
        self._hits = 0
        self._misses = 0
        return count

    async def persist(self) -> None:
        import asyncio
        data = {
            "version": 1,
            "entries": {},
            "metadata": {
                "max_entries": self._max_entries,
                "dhash_threshold": self._dhash_threshold,
                "last_persisted": time.time(),
            },
        }
        for key, entry in self._entries.items():
            resp = entry.response
            data["entries"][key] = {
                "key": entry.key,
                "description": entry.description,
                "image_dhash": entry.image_dhash,
                "created_at": entry.created_at,
                "last_hit": entry.last_hit,
                "hit_count": entry.hit_count,
                "response": resp if isinstance(resp, (dict, list, str, int, float, bool, type(None))) else str(resp),
            }

        def _write():
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            path = self._cache_dir / "cache.json"
            path.write_text(json.dumps(data, default=str), encoding="utf-8")

        await asyncio.to_thread(_write)

    async def load(self) -> int:
        import asyncio

        def _read() -> Optional[dict]:
            path = self._cache_dir / "cache.json"
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))

        data = await asyncio.to_thread(_read)
        if data is None:
            return 0
        entries = data.get("entries", {})
        count = 0
        for key, entry_data in entries.items():
            entry = VisionCacheEntry(
                key=entry_data["key"],
                description=entry_data["description"],
                response=entry_data.get("response"),
                image_dhash=entry_data.get("image_dhash", 0),
                created_at=entry_data.get("created_at", time.monotonic()),
                last_hit=entry_data.get("last_hit", time.monotonic()),
                hit_count=entry_data.get("hit_count", 0),
            )
            self._entries[key] = entry
            count += 1
        return count

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    @property
    def size(self) -> int:
        return len(self._entries)

    @staticmethod
    def compute_dhash(image_bytes: bytes, hash_size: int = 8) -> int:
        if _HAS_PIL:
            img = Image.open(BytesIO(image_bytes)).convert("L").resize((hash_size + 1, hash_size))
            pixels = list(img.getdata())
            hash_val = 0
            for y in range(hash_size):
                for x in range(hash_size):
                    left = pixels[y * (hash_size + 1) + x]
                    right = pixels[y * (hash_size + 1) + x + 1]
                    hash_val = (hash_val << 1) | (1 if left > right else 0)
            return hash_val
        sha = hashlib.sha256(image_bytes).hexdigest()
        return int(sha[:16], 16)

    @staticmethod
    def dhash_distance(hash_a: int, hash_b: int) -> int:
        return bin(hash_a ^ hash_b).count("1")

    @staticmethod
    def _make_key(dhash: int, description: str) -> str:
        raw = f"{dhash:x}|{description}"
        return hashlib.sha256(raw.encode()).hexdigest()
