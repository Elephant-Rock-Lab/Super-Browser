"""Behavioral telemetry for the adversarial v3 suite.

Records raw DOM interaction events (mouse moves, keystrokes, scroll deltas)
from a live browser page, returns them as typed Python objects, and lets the
behavioral vectors run their analysis math in Python.

Design contract:
- The recorder is *passive*: it buffers events, it does not analyze them.
- Analysis happens in the vectors (``vectors/behavioral.py``), keeping it
  unit-testable with canned trajectories and keeping the stub honest
  (no JS -> no telemetry -> vectors return SKIPPED).
- The schema is independent of the SDK's ``behavioral/`` types. v3 must not
  import SDK synthesizer code; it only consumes raw observed events.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from adversarial3.core import Page


# ============================================================================
# Event types
# ============================================================================


@dataclass(frozen=True, slots=True)
class MouseEvent:
    """A single observed mouse position."""

    t_ms: float
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class KeystrokeEvent:
    """A single observed keydown."""

    t_ms: float
    key: str


@dataclass(frozen=True, slots=True)
class ScrollEvent:
    """A single observed scroll delta."""

    t_ms: float
    delta_y: float


# ============================================================================
# Telemetry container
# ============================================================================


@dataclass(frozen=True, slots=True)
class BehavioralTelemetry:
    """Raw observed interaction events from one recording window.

    All event lists share the same time origin (``t_ms`` = ms since the
    recorder started). The container carries no analysis -- it is pure data
    for the behavioral vectors to consume.
    """

    mouse: list[MouseEvent] = field(default_factory=list)
    keystrokes: list[KeystrokeEvent] = field(default_factory=list)
    scroll: list[ScrollEvent] = field(default_factory=list)
    viewport: dict[str, int] = field(default_factory=lambda: {"width": 0, "height": 0})
    duration_ms: float = 0.0

    def is_empty(self) -> bool:
        """True if no events of any kind were captured."""
        return not (self.mouse or self.keystrokes or self.scroll)

    def to_dict(self) -> dict[str, Any]:
        return {
            "mouse": [
                {"t_ms": e.t_ms, "x": e.x, "y": e.y} for e in self.mouse
            ],
            "keystrokes": [
                {"t_ms": e.t_ms, "key": e.key} for e in self.keystrokes
            ],
            "scroll": [
                {"t_ms": e.t_ms, "delta_y": e.delta_y} for e in self.scroll
            ],
            "viewport": dict(self.viewport),
            "duration_ms": self.duration_ms,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> BehavioralTelemetry:
        """Round-trip from :meth:`to_dict`.

        Tolerant of missing keys (treats them as empty), but raises
        ``KeyError`` for malformed event entries (missing a required field
        within an event dict). This makes "missing telemetry" cleanly
        distinguishable from "corrupt telemetry".
        """
        if d is None:
            raise ValueError("BehavioralTelemetry.from_dict requires a dict, got None")

        mouse = [
            MouseEvent(t_ms=float(e["t_ms"]), x=float(e["x"]), y=float(e["y"]))
            for e in d.get("mouse") or []
        ]
        keystrokes = [
            KeystrokeEvent(t_ms=float(e["t_ms"]), key=str(e["key"]))
            for e in d.get("keystrokes") or []
        ]
        scroll = [
            ScrollEvent(t_ms=float(e["t_ms"]), delta_y=float(e["delta_y"]))
            for e in d.get("scroll") or []
        ]
        viewport = d.get("viewport") or {"width": 0, "height": 0}
        return cls(
            mouse=mouse,
            keystrokes=keystrokes,
            scroll=scroll,
            viewport={"width": int(viewport.get("width", 0)), "height": int(viewport.get("height", 0))},
            duration_ms=float(d.get("duration_ms", 0.0)),
        )


# ============================================================================
# Passive DOM event recorder (injected after page load)
# ============================================================================

# Buffer raw events for ``__sb_record_ms`` then stop. Passive: no analysis.
# Detaches listeners when the window expires so it does not leak across
# navigations. Exposes the buffer on ``window.__sb_telemetry``.
RECORDER_JS = """
(window, durationMs) => {
    return new Promise((resolve) => {
        if (window.__sb_recording) {
            resolve(window.__sb_telemetry || null);
            return;
        }
        window.__sb_recording = true;
        const startedAt = performance.now();
        const mouse = [];
        const keystrokes = [];
        const scroll = [];

        const onMouseMove = (e) => {
            mouse.push({ t_ms: performance.now() - startedAt, x: e.clientX, y: e.clientY });
        };
        const onKeyDown = (e) => {
            keystrokes.push({ t_ms: performance.now() - startedAt, key: e.key });
        };
        const onWheel = (e) => {
            scroll.push({ t_ms: performance.now() - startedAt, delta_y: e.deltaY });
        };

        document.addEventListener('mousemove', onMouseMove, { passive: true });
        document.addEventListener('keydown', onKeyDown);
        document.addEventListener('wheel', onWheel, { passive: true });

        setTimeout(() => {
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('keydown', onKeyDown);
            document.removeEventListener('wheel', onWheel);
            window.__sb_recording = false;
            window.__sb_telemetry = {
                mouse: mouse,
                keystrokes: keystrokes,
                scroll: scroll,
                viewport: { width: window.innerWidth, height: window.innerHeight },
                duration_ms: durationMs,
            };
            resolve(window.__sb_telemetry);
        }, durationMs);
    });
}
"""

# A minimal in-page driver to generate events for the recorder to capture.
# This is NOT a stealth interaction -- it exists only to exercise the
# telemetry pipeline. Real assessments would record the SDK's synthesized
# motion; here we just need enough movement to validate the structure.
_INTERACTION_DRIVER_JS = """
(durationMs) => {
    // Move the mouse along a curved-ish path.
    let i = 0;
    const moveInterval = setInterval(() => {
        const t = i / 20;
        const x = 50 + 400 * t;
        const y = 50 + 60 * Math.sin(t * Math.PI * 2);
        const evt = new MouseEvent('mousemove', { clientX: x, clientY: y, bubbles: true });
        document.dispatchEvent(evt);
        i += 1;
    }, Math.max(40, durationMs / 20));

    // Scroll a few times.
    let s = 0;
    const scrollInterval = setInterval(() => {
        const evt = new WheelEvent('wheel', { deltaY: 40 + s * 5, bubbles: true });
        document.dispatchEvent(evt);
        s += 1;
    }, Math.max(60, durationMs / 10));

    // Clean up both loops at the end.
    setTimeout(() => {
        clearInterval(moveInterval);
        clearInterval(scrollInterval);
    }, durationMs);
}
"""


async def record_telemetry(page: Page, *, duration_ms: float = 2000.0) -> BehavioralTelemetry:
    """Record a short interaction sample from a live page.

    Injects the passive recorder, drives a minimal scripted interaction to
    generate events to capture, waits for the window to expire, then pulls
    the buffer back as a :class:`BehavioralTelemetry`.

    The page must already be navigated to a document (the recorder attaches
    listeners to ``document``). If the page cannot execute JS, the caller
    should treat telemetry as absent rather than calling this.

    Args:
        page: A live browser page satisfying the ``Page`` protocol.
        duration_ms: Recording window length in milliseconds.

    Returns:
        The captured telemetry. May be empty (no events fired) but is never
        ``None`` -- the recorder always ran.
    """
    # Order matters: start the interaction driver FIRST (its setInterval
    # callbacks fire in the background after evaluate returns), THEN await
    # the recorder's Promise (which resolves after duration_ms). If we
    # awaited the recorder first, the driver's intervals would only fire
    # after the recording window had already closed -- capturing nothing.
    await page.evaluate(f"({_INTERACTION_DRIVER_JS})({duration_ms!r})")
    # Now await the recorder -- this blocks for the recording window while
    # the driver's intervals fire concurrently and the recorder's listeners
    # capture them. The resolved value is the telemetry dict.
    raw = await page.evaluate(f"({RECORDER_JS})(window, {duration_ms!r})")
    if not raw:
        return BehavioralTelemetry()
    return _coerce_raw(raw)


def _coerce_raw(raw: Any) -> BehavioralTelemetry:
    """Coerce the JSON-serialized JS object into a BehavioralTelemetry.

    The JS object is already dict-shaped from ``page.evaluate``; this
    validates and types it. Falls back to empty telemetry on any structural
    problem so the recorder never raises into the harness.
    """
    try:
        return BehavioralTelemetry.from_dict(raw)
    except (KeyError, ValueError, TypeError):
        return BehavioralTelemetry()


__all__ = [
    "BehavioralTelemetry",
    "KeystrokeEvent",
    "MouseEvent",
    "RECORDER_JS",
    "ScrollEvent",
    "record_telemetry",
]
