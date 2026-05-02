"""Perceptual hash computation — dHash, pHash, and LRU hash cache."""

from __future__ import annotations

import hashlib
import math
from collections import OrderedDict
from io import BytesIO
from typing import Optional

from super_browser.verification.types import PerceptualHash

try:
    import numpy as np
    _HAS_NUMPY = True
except ImportError:
    _HAS_NUMPY = False

try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


# ---------------------------------------------------------------------------
# dHash — difference hash (9x8 gradient → 64-bit)
# ---------------------------------------------------------------------------

def compute_dhash(image_bytes: bytes) -> int:
    img = Image.open(BytesIO(image_bytes)).convert("L").resize((9, 8), Image.BILINEAR)
    pixels = list(img.getdata())
    hash_val = 0
    for y in range(8):
        for x in range(8):
            left = pixels[y * 9 + x]
            right = pixels[y * 9 + x + 1]
            hash_val = (hash_val << 1) | (1 if left > right else 0)
    return hash_val


# ---------------------------------------------------------------------------
# pHash — perceptual hash (32x32 DCT-II → 64-bit)
# ---------------------------------------------------------------------------

def compute_phash(image_bytes: bytes) -> int:
    img = Image.open(BytesIO(image_bytes)).convert("L").resize((32, 32), Image.BILINEAR)
    if _HAS_NUMPY:
        matrix = _pil_to_numpy(img)
        dct_block = _dct2_numpy(matrix)
    else:
        matrix = _pil_to_list(img)
        dct_block = _dct2_pure(matrix)

    low_freq = []
    for r in range(8):
        for c in range(8):
            low_freq.append(dct_block[r][c])

    median = sorted(low_freq)[32]
    hash_val = 0
    for val in low_freq:
        hash_val = (hash_val << 1) | (1 if val > median else 0)
    return hash_val


def _pil_to_numpy(img: Image.Image):
    return [[float(img.getpixel((c, r))) for c in range(32)] for r in range(32)]


def _pil_to_list(img: Image.Image) -> list[list[float]]:
    return [[float(img.getpixel((c, r))) for c in range(32)] for r in range(32)]


def _dct2_numpy(matrix: list[list[float]]) -> list[list[float]]:
    arr = np.array(matrix, dtype=np.float64)
    N = arr.shape[0]
    result = np.zeros_like(arr)
    for k in range(N):
        for n in range(N):
            result[k] += arr[n] * math.cos(math.pi * k * (2 * n + 1) / (2 * N))
    out_rows = result.tolist()
    col_result: list[list[float]] = [[0.0] * N for _ in range(N)]
    for r in range(N):
        for k in range(N):
            s = 0.0
            for n in range(N):
                s += out_rows[r][n] * math.cos(math.pi * k * (2 * n + 1) / (2 * N))
            col_result[r][k] = s
    return col_result


def _dct2_pure(matrix: list[list[float]]) -> list[list[float]]:
    N = len(matrix)
    row_dct: list[list[float]] = [[0.0] * N for _ in range(N)]
    for r in range(N):
        for k in range(N):
            s = 0.0
            for n in range(N):
                s += matrix[r][n] * math.cos(math.pi * k * (2 * n + 1) / (2 * N))
            row_dct[r][k] = s
    col_dct: list[list[float]] = [[0.0] * N for _ in range(N)]
    for c in range(N):
        for k in range(N):
            s = 0.0
            for n in range(N):
                s += row_dct[n][c] * math.cos(math.pi * k * (2 * n + 1) / (2 * N))
            col_dct[k][c] = s
    return col_dct


# ---------------------------------------------------------------------------
# Combined hash
# ---------------------------------------------------------------------------

def compute_hash(image_bytes: bytes) -> PerceptualHash:
    sha = hashlib.sha256(image_bytes).hexdigest()
    return PerceptualHash(
        dhash=compute_dhash(image_bytes),
        phash=compute_phash(image_bytes),
        source_sha256=sha,
    )


# ---------------------------------------------------------------------------
# Hash Cache (LRU via OrderedDict)
# ---------------------------------------------------------------------------

class HasherCache:
    def __init__(self, max_size: int = 256) -> None:
        self._cache: OrderedDict[str, PerceptualHash] = OrderedDict()
        self._max_size = max_size

    def get(self, sha256: str) -> Optional[PerceptualHash]:
        if sha256 in self._cache:
            self._cache.move_to_end(sha256)
            return self._cache[sha256]
        return None

    def put(self, sha256: str, phash: PerceptualHash) -> None:
        if sha256 in self._cache:
            self._cache[sha256] = phash
            self._cache.move_to_end(sha256)
            return
        if len(self._cache) >= self._max_size:
            self._cache.popitem(last=False)
        self._cache[sha256] = phash

    def clear(self) -> None:
        self._cache.clear()

    @property
    def size(self) -> int:
        return len(self._cache)
