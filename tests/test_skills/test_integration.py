"""Integration tests for GAP-05 — config, facade wiring, imports."""

import asyncio

import pytest

from super_browser.agent.config import SuperBrowserConfig
from super_browser.skills import (
    ActivationConfig,
    DomainSkill,
    SkillProvenance,
    SkillQuery,
    SkillRegistry,
    SkillStatus,
    compute_activation,
)


class TestConfigWiring:
    def test_default_skills_disabled(self):
        cfg = SuperBrowserConfig()
        assert cfg.enable_skills is False
        assert cfg.skills_dir == ""

    def test_custom_skills_config(self):
        cfg = SuperBrowserConfig(enable_skills=True, skills_dir="/tmp/skills")
        assert cfg.enable_skills is True
        assert cfg.skills_dir == "/tmp/skills"


class TestImportCheck:
    def test_all_public_types_importable(self):
        from super_browser.skills import (
            InvalidSkillFormat,
            SelectorConflictWarning,
            SkillImportError,
            SkillQuery,
            SkillSizeExceeded,
            parse_markdown_skills,
        )
        assert SkillQuery is not None
        assert parse_markdown_skills is not None

    def test_compute_activation_importable(self):
        assert callable(compute_activation)

    def test_skill_registry_importable(self):
        assert SkillRegistry is not None


class TestSpanKind:
    def test_skill_span_kind_exists(self):
        from super_browser.tracing.types import SpanKind
        assert SpanKind.SKILL == "skill"
        assert len(SpanKind) == 10


class TestEndToEndFlow:
    def test_register_discover_learn(self, tmp_path):
        reg = SkillRegistry(skills_dir=tmp_path / "skills")

        async def _test():
            import time as _time
            # Register a skill
            s = await reg.register(DomainSkill(
                skill_id="gh-login",
                domain="github.com",
                name="login",
                description="Login flow",
                selectors={"username": "#login_field"},
                access_count=10,
                last_used=_time.monotonic(),
            ))

            # Auto-discover
            discovered = await reg.auto_discover("https://github.com/login")
            assert len(discovered) >= 1
            assert discovered[0].skill_id == "gh-login"

            # Learn from trajectory
            learned = await reg.learn_from_trajectory(
                domain="github.com",
                task_description="Create an issue",
                actions_taken=["click .btn-new-issue"],
                selectors_used={".btn-new-issue": "SELECTOR"},
            )
            assert learned.provenance == SkillProvenance.LEARNED

            # Search
            results = await reg.search(SkillQuery(domain="github.com"))
            assert len(results) == 2

        asyncio.run(_test())
