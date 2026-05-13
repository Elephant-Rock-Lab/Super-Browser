"""QWERTY keyboard layout helpers for keystroke synthesis.

Provides adjacency lookup, hand assignment, and same-hand detection.
"""

from __future__ import annotations

import random
__all__ = ["adjacent_key", "hand_for", "is_same_hand"]

# Row-by-row QWERTY layout (US). Each row is a list of characters in
# left-to-right order.
_ROWS: list[list[str]] = [
    list("`1234567890-="),
    list("qwertyuiop[]\\"),
    list("asdfghjkl;'"),
    list("zxcvbnm,./"),
]

# Shift-row equivalents for digits.
_SHIFT_ROWS: list[list[str]] = [
    list('~!@#$%^&*()_+'),
    list("QWERTYUIOP{}|"),
    list('ASDFGHJKL:"'),
    list("ZXCVBNM<>?"),
]

# Build flat maps: char → (row_index, col_index).
_CHAR_POS: dict[str, tuple[int, int]] = {}
for _ri, _row in enumerate(_ROWS):
    for _ci, _ch in enumerate(_row):
        _CHAR_POS[_ch] = (_ri, _ci)
for _ri, _row in enumerate(_SHIFT_ROWS):
    for _ci, _ch in enumerate(_row):
        _CHAR_POS[_ch] = (_ri, _ci)

# Add space bar (treated as row -1, col 0) — always present.
_CHAR_POS[" "] = (-1, 0)

# Left-hand columns (standard touch-typing): rows 0 cols 0-5, rows 1-3 cols 0-4.
_LEFT_COLS: dict[int, set[int]] = {
    0: {0, 1, 2, 3, 4, 5},
    1: {0, 1, 2, 3, 4},
    2: {0, 1, 2, 3, 4},
    3: {0, 1, 2, 3},
}

# Adjacent keys: for a character at (row, col), adjacent keys are
# (row±0..1, col±1) and (row±0..1, col) where valid.
_ALL_ROWS = _ROWS + _SHIFT_ROWS


def _adjacent_positions(row: int, col: int) -> list[str]:
    """Return list of adjacent characters for a given (row, col)."""
    results: list[str] = []
    # Check same-row neighbours and diagonals on rows above/below.
    # All rows list has length 8: 4 base + 4 shift.
    # For adjacency, characters in row i share adjacency with the
    # corresponding shift/base row.
    # Simplify: find characters near the same position across all rows.
    target_char = _char_at(row, col)
    if target_char is None:
        return results

    for ri, rows_group in enumerate([_ROWS, _SHIFT_ROWS]):
        for ci, r in enumerate(rows_group):
            if col < len(r):
                ch = r[col]
                if ch != target_char:
                    results.append(ch)
            if col - 1 >= 0 and col - 1 < len(r):
                ch = r[col - 1]
                if ch != target_char:
                    results.append(ch)
            if col + 1 < len(r):
                ch = r[col + 1]
                if ch != target_char:
                    results.append(ch)
    return results


def _char_at(row: int, col: int) -> str | None:
    """Look up a character at (row, col) across both base and shift rows."""
    for group in (_ROWS, _SHIFT_ROWS):
        for ri, r in enumerate(group):
            if ri == row and col < len(r):
                return r[col]
    return None


def _get_adjacent(ch: str) -> list[str]:
    """Return list of adjacent keys for *ch* on QWERTY layout."""
    pos = _CHAR_POS.get(ch)
    if pos is None:
        return []
    row, col = pos
    results: set[str] = set()

    # Check all rows for characters at col±1 and same col.
    for rows_group in (_ROWS, _SHIFT_ROWS):
        if row < 0 or row >= len(rows_group):
            continue
        r = rows_group[row]
        for dc in (-1, 0, 1):
            c = col + dc
            if 0 <= c < len(r):
                candidate = r[c]
                if candidate != ch:
                    results.add(candidate)
        # Check row above and below (±1 offset, same col/col±1).
        for dr in (-1, 1):
            nr = row + dr
            if 0 <= nr < len(rows_group):
                nr_row = rows_group[nr]
                for dc in (-1, 0, 1):
                    c = col + dc
                    if 0 <= c < len(nr_row):
                        candidate = nr_row[c]
                        if candidate != ch:
                            results.add(candidate)

    return list(results)


# Pre-compute adjacency map.
_ADJACENCY: dict[str, list[str]] = {}
for _ch in _CHAR_POS:
    _ADJACENCY[_ch] = _get_adjacent(_ch)


def adjacent_key(ch: str, rng: random.Random | None = None) -> str | None:
    """Return a random adjacent key to *ch* on the QWERTY layout.

    Returns ``None`` if *ch* has no neighbours defined.
    """
    neighbours = _ADJACENCY.get(ch)
    if not neighbours:
        return None
    if rng is not None:
        return rng.choice(neighbours)
    import random as _rng

    return _rng.choice(neighbours)


def hand_for(ch: str) -> str:
    """Return ``"left"`` or ``"right"`` for *ch* based on touch-typing rules.

    Returns ``"right"`` as the default for unknown characters.
    """
    pos = _CHAR_POS.get(ch)
    if pos is None:
        return "right"
    row, col = pos
    if row in _LEFT_COLS and col in _LEFT_COLS[row]:
        return "left"
    return "right"


def is_same_hand(a: str, b: str) -> bool:
    """Return ``True`` if both characters are typed with the same hand."""
    return hand_for(a) == hand_for(b)
