"""Tests for HumanConfig Track C dwell fields — Wave 22.

Covers new dwell fields, preset propagation, and backward compat.
"""

from __future__ import annotations

from super_browser.stealth.human_config import HumanConfig


class TestDwellFields:
    def test_defaults(self) -> None:
        cfg = HumanConfig()
        assert cfg.dwell_pre_action_ms == (200.0, 1500.0)
        assert cfg.dwell_post_action_ms == (300.0, 3000.0)
        assert cfg.dwell_page_settle_ms == 800.0
        assert cfg.dwell_variability == 0.7

    def test_custom_values(self) -> None:
        cfg = HumanConfig(
            dwell_pre_action_ms=(10.0, 50.0),
            dwell_post_action_ms=(20.0, 100.0),
            dwell_page_settle_ms=50.0,
            dwell_variability=0.3,
        )
        assert cfg.dwell_pre_action_ms == (10.0, 50.0)
        assert cfg.dwell_post_action_ms == (20.0, 100.0)
        assert cfg.dwell_page_settle_ms == 50.0
        assert cfg.dwell_variability == 0.3


class TestPresetPropagation:
    def test_default_preset_has_dwell_fields(self) -> None:
        cfg = HumanConfig(preset="default")
        assert cfg.dwell_pre_action_ms == (200.0, 1500.0)
        assert cfg.dwell_post_action_ms == (300.0, 3000.0)
        assert cfg.dwell_page_settle_ms == 800.0
        assert cfg.dwell_variability == 0.7

    def test_careful_preset_has_longer_dwell(self) -> None:
        cfg = HumanConfig(preset="careful")
        assert cfg.dwell_pre_action_ms == (500.0, 2500.0)
        assert cfg.dwell_post_action_ms == (800.0, 5000.0)
        assert cfg.dwell_page_settle_ms == 1500.0

    def test_fast_preset_has_shorter_dwell(self) -> None:
        cfg = HumanConfig(preset="fast")
        assert cfg.dwell_pre_action_ms == (50.0, 400.0)
        assert cfg.dwell_post_action_ms == (100.0, 800.0)
        assert cfg.dwell_page_settle_ms == 300.0


class TestBackwardCompat:
    def test_legacy_fields_unchanged(self) -> None:
        cfg = HumanConfig()
        assert cfg.typing_delay_ms == (50, 150)
        assert cfg.mouse_jitter_px == 3.0
        assert cfg.click_hold_ms == (50, 200)
        assert cfg.pause_between_actions == (0.3, 1.5)

    def test_session_seed_field_exists(self) -> None:
        cfg = HumanConfig(session_seed="test-123")
        assert cfg.session_seed == "test-123"

    def test_behavior_profile_still_works(self) -> None:
        cfg = HumanConfig()
        profile = cfg.to_behavior_profile()
        assert profile.hand == "right"
        assert profile.wpm == 60
