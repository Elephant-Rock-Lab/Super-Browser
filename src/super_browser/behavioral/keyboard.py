"""Keystroke synthesis — pure data, no CDP.

Per PLAN §11.2:

- Per-letter press duration = Gaussian(80, 25) ms, clamped [20, 200].
- Digraph delays:
    same-hand   → lognormal(μ=4.7, σ=0.35)
    cross-hand  → lognormal(μ=4.4, σ=0.30)
    after-space → lognormal(μ=4.9, σ=0.40)
    after-punct → 1.3 × same-hand
- Mistake injection: adjacent wrong key → pause → Backspace → pause → correct.
- WPM scaling: target_mean = 60000 / (wpm * 5), scale = target_mean / 110.

Determinism: same ``(text, seed)`` → byte-identical event array.
"""

from __future__ import annotations

from super_browser.behavioral.gauss import GaussianSampler
from super_browser.behavioral.prng import prng_for
from super_browser.behavioral.qwerty import adjacent_key, hand_for
from super_browser.behavioral.types import BehaviorProfile, KeystrokeEvent

__all__ = ["synthesize_keystrokes"]

_DEFAULT_PROFILE = BehaviorProfile()
_DEFAULT_MISTAKE_RATE = 0.02
_LOGNORMAL_BASELINE_MEAN_MS = 110.0


def synthesize_keystrokes(
    text: str,
    profile: BehaviorProfile | None = None,
    seed: str | None = None,
    mistake_rate: float = _DEFAULT_MISTAKE_RATE,
) -> list[KeystrokeEvent]:
    """Synthesize keystroke events for a literal text string.

    Parameters
    ----------
    text:
        The string to type.
    profile:
        Behavioral profile; ``None`` uses defaults.
    seed:
        Deterministic seed string.
    mistake_rate:
        Per-character mistake probability (0–1). Default 0.02.
    """
    prof = profile if profile is not None else _DEFAULT_PROFILE
    prng = prng_for("keys", seed)
    g = GaussianSampler(prng)
    m_rate = _clamp01(mistake_rate)

    # WPM scaling.
    target_mean_ms = 60_000.0 / (max(1, prof.wpm) * 5)
    wpm_scale = max(0.25, min(4.0, target_mean_ms / _LOGNORMAL_BASELINE_MEAN_MS))

    out: list[KeystrokeEvent] = []
    now = 0.0
    prev_char: str | None = None

    for ch in text:
        # Inter-key delay.
        if prev_char is not None:
            now += _inter_key_delay(prev_char, ch, g, wpm_scale, prng)

        # Mistake injection.
        will_mistake = m_rate > 0 and prng.next_float01() < m_rate
        if will_mistake:
            wrong = adjacent_key(ch)
            if wrong is not None:
                # Type wrong key.
                wrong_down = now
                wrong_press = _press_duration(g)
                wrong_up = wrong_down + wrong_press
                out.append(
                    KeystrokeEvent(
                        t_ms=wrong_down,
                        key=wrong,
                        event_type="keydown",
                        is_correction=False,
                    )
                )
                out.append(
                    KeystrokeEvent(
                        t_ms=wrong_up,
                        key=wrong,
                        event_type="keyup",
                        is_correction=False,
                    )
                )
                now = wrong_up

                # Realisation delay: 200..500 ms.
                now += 200 + prng.next_float01() * 300

                # Backspace.
                bs_down = now
                bs_up = bs_down + _press_duration(g)
                out.append(
                    KeystrokeEvent(
                        t_ms=bs_down,
                        key="Backspace",
                        event_type="keydown",
                        is_correction=True,
                    )
                )
                out.append(
                    KeystrokeEvent(
                        t_ms=bs_up,
                        key="Backspace",
                        event_type="keyup",
                        is_correction=True,
                    )
                )
                now = bs_up

                # Recovery delay: 100..300 ms.
                now += 100 + prng.next_float01() * 200

        # Correct key.
        down_ms = now
        up_ms = down_ms + _press_duration(g)
        out.append(
            KeystrokeEvent(
                t_ms=down_ms,
                key=ch,
                event_type="keydown",
                is_correction=False,
            )
        )
        out.append(
            KeystrokeEvent(
                t_ms=up_ms,
                key=ch,
                event_type="keyup",
                is_correction=False,
            )
        )
        now = up_ms
        prev_char = ch

    return out


# ------------------------------------------------------------------
# Internal helpers
# ------------------------------------------------------------------


def _press_duration(g: GaussianSampler) -> float:
    """Per-letter press duration: clamped Gaussian(80, 25) ms."""
    return g.next_clamped(80.0, 25.0, 20.0, 200.0)


def _inter_key_delay(
    prev: str,
    curr: str,
    g: GaussianSampler,
    wpm_scale: float,
    prng: object,
) -> float:
    """Inter-key delay based on character pair and WPM scale."""
    if prev.isspace():
        return g.lognormal(4.9, 0.40) * wpm_scale

    if _is_punctuation(prev):
        return g.lognormal(4.7, 0.35) * 1.3 * wpm_scale

    if hand_for(prev) == hand_for(curr):
        return g.lognormal(4.7, 0.35) * wpm_scale

    # Cross-hand (or unknown).
    return g.lognormal(4.4, 0.30) * wpm_scale


def _is_punctuation(ch: str) -> bool:
    return ch in {".", ",", ";", ":", "!", "?", "'", '"', "(", ")", "[", "]", "{", "}", "-", "/", "\\"}


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))
