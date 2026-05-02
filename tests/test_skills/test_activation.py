"""Tests for ACT-R activation scoring formula."""

import math
import time

import pytest

from super_browser.skills.activation import compute_activation
from super_browser.skills.types import ActivationConfig, DomainSkill, SkillStatus


def _skill(**overrides):
    defaults = dict(
        skill_id="x", domain="d.com", name="n",
        access_count=0, last_used=0.0, status=SkillStatus.ACTIVE,
    )
    defaults.update(overrides)
    return DomainSkill(**defaults)


class TestBaseLevel:
    def test_never_used_is_zero(self):
        s = _skill(access_count=0, last_used=0.0)
        assert compute_activation(s) == 0.0

    def test_single_use(self):
        s = _skill(access_count=1, last_used=time.monotonic())
        score = compute_activation(s)
        assert score > math.log(2)  # includes recency bonus

    def test_high_access_recent(self):
        s = _skill(access_count=99, last_used=time.monotonic())
        score = compute_activation(s)
        assert score >= 4.6


class TestRecency:
    def test_recently_used_has_bonus(self):
        s = _skill(access_count=1, last_used=time.monotonic())
        s_old = _skill(access_count=1, last_used=time.monotonic() - 3600 * 10)
        assert compute_activation(s) > compute_activation(s_old)

    def test_never_used_no_recency(self):
        s = _skill(access_count=5, last_used=0.0)
        score = compute_activation(s)
        assert abs(score - math.log(6)) < 0.01


class TestContextBoost:
    def test_no_similarity_fn_no_boost(self):
        s = _skill(access_count=0, last_used=0.0, description="Login flow")
        assert compute_activation(s, current_task="Login") == 0.0

    def test_with_similarity_fn(self):
        sim = lambda a, b: 1.0 if a == b else 0.0
        s = _skill(access_count=1, last_used=time.monotonic(), description="Login")
        score = compute_activation(s, current_task="Login", similarity_fn=sim)
        assert score > compute_activation(s, current_task="Login")

    def test_context_boost_capped(self):
        sim = lambda a, b: 10.0
        cfg = ActivationConfig(context_weight=1.0, max_context_boost=2.0)
        s = _skill(access_count=0, last_used=0.0, description="x")
        score = compute_activation(s, current_task="x", config=cfg, similarity_fn=sim)
        assert score <= 2.0


class TestStalePenalty:
    def test_stale_penalty_applied(self):
        s = _skill(access_count=10, last_used=time.monotonic(), status=SkillStatus.STALE)
        score = compute_activation(s)
        s_active = _skill(access_count=10, last_used=time.monotonic(), status=SkillStatus.ACTIVE)
        score_active = compute_activation(s_active)
        assert score == score_active - 2.0

    def test_stale_below_threshold(self):
        s = _skill(access_count=2, last_used=0.0, status=SkillStatus.STALE)
        score = compute_activation(s)
        assert score < 1.0


class TestCustomWeights:
    def test_zero_base_level_weight(self):
        cfg = ActivationConfig(base_level_weight=0.0, recency_weight=0.0)
        s = _skill(access_count=100, last_used=time.monotonic())
        score = compute_activation(s, config=cfg)
        assert score == 0.0

    def test_custom_decay(self):
        cfg_fast = ActivationConfig(decay_factor=0.1)
        cfg_slow = ActivationConfig(decay_factor=0.9)
        s = _skill(access_count=1, last_used=time.monotonic() - 3600)
        fast = compute_activation(s, config=cfg_fast)
        slow = compute_activation(s, config=cfg_slow)
        assert slow > fast
