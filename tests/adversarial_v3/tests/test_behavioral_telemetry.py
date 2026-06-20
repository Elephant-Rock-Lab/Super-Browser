"""Tests for the behavioral telemetry schema and round-trip.

Covers: dataclass construction, to_dict/from_dict round-trip, is_empty
behavior, and tolerance to missing/optional keys vs rejection of malformed
event entries (the distinction the vector contract relies on).
"""

from __future__ import annotations

import pytest
from adversarial3.behavioral_telemetry import (
    BehavioralTelemetry,
    KeystrokeEvent,
    MouseEvent,
    ScrollEvent,
)


class TestEventTypes:
    def test_mouse_event_fields(self):
        e = MouseEvent(t_ms=1.5, x=10.0, y=20.0)
        assert e.t_ms == 1.5
        assert e.x == 10.0
        assert e.y == 20.0

    def test_keystroke_event_fields(self):
        e = KeystrokeEvent(t_ms=2.0, key="a")
        assert e.t_ms == 2.0
        assert e.key == "a"

    def test_scroll_event_fields(self):
        e = ScrollEvent(t_ms=3.0, delta_y=-40.0)
        assert e.t_ms == 3.0
        assert e.delta_y == -40.0


class TestIsEmpty:
    def test_default_is_empty(self):
        assert BehavioralTelemetry().is_empty() is True

    def test_with_mouse_only_not_empty(self):
        t = BehavioralTelemetry(mouse=[MouseEvent(0, 1, 1)])
        assert t.is_empty() is False

    def test_with_keystrokes_only_not_empty(self):
        t = BehavioralTelemetry(keystrokes=[KeystrokeEvent(0, "a")])
        assert t.is_empty() is False

    def test_with_scroll_only_not_empty(self):
        t = BehavioralTelemetry(scroll=[ScrollEvent(0, -10.0)])
        assert t.is_empty() is False

    def test_empty_lists_are_empty(self):
        t = BehavioralTelemetry(mouse=[], keystrokes=[], scroll=[])
        assert t.is_empty() is True


class TestRoundTrip:
    def test_to_dict_has_all_fields(self):
        t = BehavioralTelemetry(
            mouse=[MouseEvent(0.0, 1.0, 2.0)],
            keystrokes=[KeystrokeEvent(10.0, "a")],
            scroll=[ScrollEvent(20.0, -5.0)],
            viewport={"width": 1280, "height": 720},
            duration_ms=2000.0,
        )
        d = t.to_dict()
        assert set(d.keys()) == {"mouse", "keystrokes", "scroll", "viewport", "duration_ms"}
        assert d["mouse"] == [{"t_ms": 0.0, "x": 1.0, "y": 2.0}]
        assert d["keystrokes"] == [{"t_ms": 10.0, "key": "a"}]
        assert d["scroll"] == [{"t_ms": 20.0, "delta_y": -5.0}]
        assert d["viewport"] == {"width": 1280, "height": 720}
        assert d["duration_ms"] == 2000.0

    def test_round_trip_preserves_all_events(self):
        original = BehavioralTelemetry(
            mouse=[MouseEvent(0.0, 1.0, 2.0), MouseEvent(5.0, 3.0, 4.0)],
            keystrokes=[KeystrokeEvent(0.0, "h"), KeystrokeEvent(80.0, "i")],
            scroll=[ScrollEvent(0.0, -10.0)],
            viewport={"width": 1920, "height": 1080},
            duration_ms=1500.0,
        )
        round_tripped = BehavioralTelemetry.from_dict(original.to_dict())

        assert len(round_tripped.mouse) == 2
        assert round_tripped.mouse[0].x == 1.0
        assert round_tripped.mouse[1].t_ms == 5.0
        assert len(round_tripped.keystrokes) == 2
        assert round_tripped.keystrokes[1].key == "i"
        assert len(round_tripped.scroll) == 1
        assert round_tripped.scroll[0].delta_y == -10.0
        assert round_tripped.viewport == {"width": 1920, "height": 1080}
        assert round_tripped.duration_ms == 1500.0

    def test_round_trip_empty_telemetry(self):
        original = BehavioralTelemetry()
        round_tripped = BehavioralTelemetry.from_dict(original.to_dict())
        assert round_tripped.is_empty() is True


class TestFromDictTolerance:
    def test_missing_event_keys_treated_as_empty(self):
        # Missing "mouse"/"keystrokes"/"scroll" -> empty lists, not errors.
        t = BehavioralTelemetry.from_dict({"viewport": {"width": 100, "height": 100}})
        assert t.mouse == []
        assert t.keystrokes == []
        assert t.scroll == []

    def test_missing_viewport_defaults(self):
        t = BehavioralTelemetry.from_dict({})
        assert t.viewport == {"width": 0, "height": 0}

    def test_none_dict_raises(self):
        with pytest.raises(ValueError, match="requires a dict"):
            BehavioralTelemetry.from_dict(None)  # type: ignore[arg-type]

    def test_malformed_mouse_event_raises(self):
        # An event dict present but missing a required field (x) is corrupt,
        # not merely absent. This distinction matters: the vectors rely on
        # from_dict to surface corrupt telemetry rather than silently drop it.
        with pytest.raises(KeyError):
            BehavioralTelemetry.from_dict({"mouse": [{"t_ms": 0.0, "y": 1.0}]})

    def test_partial_viewport_uses_defaults(self):
        t = BehavioralTelemetry.from_dict({"viewport": {"width": 800}})
        assert t.viewport == {"width": 800, "height": 0}
