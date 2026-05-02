"""Tests for SkillRegistry — CRUD, auto-discovery, hot skills, learning, archival."""

import asyncio
import json
import time

import pytest

from super_browser.skills.registry import SkillRegistry
from super_browser.skills.types import (
    ActivationConfig,
    DomainSkill,
    InvalidSkillFormat,
    SkillProvenance,
    SkillQuery,
    SkillSizeExceeded,
    SkillStatus,
)


def _make_skill(domain="example.com", name="login", skill_id="", **kw):
    return DomainSkill(skill_id=skill_id, domain=domain, name=name, **kw)


def _registry(tmp_path, **cfg_overrides):
    cfg = ActivationConfig(**cfg_overrides) if cfg_overrides else None
    return SkillRegistry(activation_config=cfg, skills_dir=tmp_path / "skills")


class TestRegisterAndGet:
    def test_register_assigns_id(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill())
            assert s.skill_id != ""
            got = await reg.get(s.domain, s.skill_id)
            assert got is not None
            assert got.name == "login"

        asyncio.run(_test())

    def test_register_persists_json(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill())
            path = tmp_path / "skills" / "example.com" / f"{s.skill_id}.json"
            assert path.exists()
            data = json.loads(path.read_text())
            assert data["name"] == "login"

        asyncio.run(_test())

    def test_register_requires_domain(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            with pytest.raises(InvalidSkillFormat):
                await reg.register(DomainSkill(skill_id="x", domain="", name="n"))

        asyncio.run(_test())

    def test_register_requires_name(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            with pytest.raises(InvalidSkillFormat):
                await reg.register(DomainSkill(skill_id="x", domain="d.com", name=""))

        asyncio.run(_test())

    def test_get_missing_returns_none(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            assert await reg.get("x.com", "y") is None

        asyncio.run(_test())


class TestSizeLimit:
    def test_oversized_skill_rejected(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            big_selectors = {f"sel_{i}": "x" * 200 for i in range(100)}
            s = _make_skill(selectors=big_selectors)
            with pytest.raises(SkillSizeExceeded):
                await reg.register(s)

        asyncio.run(_test())


class TestUpdate:
    def test_update_fields(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill())
            updated = await reg.update(s.domain, s.skill_id, name="new_name")
            assert updated.name == "new_name"
            got = await reg.get(s.domain, s.skill_id)
            assert got.name == "new_name"

        asyncio.run(_test())

    def test_update_missing_raises(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            with pytest.raises(KeyError):
                await reg.update("x.com", "missing", name="n")

        asyncio.run(_test())

    def test_update_status_string(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill())
            updated = await reg.update(s.domain, s.skill_id, status="stale")
            assert updated.status == SkillStatus.STALE

        asyncio.run(_test())


class TestDelete:
    def test_delete_removes_skill(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill())
            sid = s.skill_id
            assert await reg.delete("example.com", sid) is True
            assert await reg.get("example.com", sid) is None
            path = tmp_path / "skills" / "example.com" / f"{sid}.json"
            assert not path.exists()

        asyncio.run(_test())

    def test_delete_missing_returns_false(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            assert await reg.delete("x.com", "missing") is False

        asyncio.run(_test())


class TestListByDomain:
    def test_lists_skills(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            await reg.register(_make_skill(name="a"))
            await reg.register(_make_skill(name="b"))
            skills = await reg.list_by_domain("example.com")
            assert len(skills) == 2

        asyncio.run(_test())

    def test_excludes_archived(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s1 = await reg.register(_make_skill(name="active"))
            s2 = await reg.register(_make_skill(name="archived"))
            s2.status = SkillStatus.ARCHIVED
            skills = await reg.list_by_domain("example.com")
            assert len(skills) == 1
            skills_all = await reg.list_by_domain("example.com", include_archived=True)
            assert len(skills_all) == 2

        asyncio.run(_test())


class TestSearch:
    def test_search_by_provenance(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            await reg.register(_make_skill(name="a", provenance=SkillProvenance.LEARNED))
            await reg.register(_make_skill(name="b", provenance=SkillProvenance.DISCOVERED))
            await reg.register(_make_skill(name="c", provenance=SkillProvenance.LEARNED))
            results = await reg.search(SkillQuery(provenance=SkillProvenance.LEARNED))
            assert len(results) == 2

        asyncio.run(_test())

    def test_search_by_name(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            await reg.register(_make_skill(name="login_flow"))
            await reg.register(_make_skill(name="checkout"))
            results = await reg.search(SkillQuery(name_contains="login"))
            assert len(results) == 1
            assert results[0].name == "login_flow"

        asyncio.run(_test())

    def test_search_min_access(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s1 = await reg.register(_make_skill(name="popular"))
            s1.access_count = 50
            await reg.register(_make_skill(name="new"))
            results = await reg.search(SkillQuery(min_access_count=10))
            assert len(results) == 1

        asyncio.run(_test())


class TestAutoDiscover:
    def test_exact_hostname_match(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = _make_skill(access_count=10, last_used=time.monotonic())
            await reg.register(s)
            discovered = await reg.auto_discover("https://example.com/login")
            assert len(discovered) >= 1

        asyncio.run(_test())

    def test_url_pattern_filter(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = _make_skill(
                access_count=10, last_used=time.monotonic(),
                url_patterns=["https://example.com/login*"],
            )
            await reg.register(s)
            assert len(await reg.auto_discover("https://example.com/login")) >= 1
            assert len(await reg.auto_discover("https://example.com/other")) == 0

        asyncio.run(_test())

    def test_touches_returned_skills(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill(access_count=5, last_used=time.monotonic()))
            old_count = s.access_count
            await reg.auto_discover("https://example.com/page")
            assert s.access_count == old_count + 1

        asyncio.run(_test())

    def test_empty_hostname(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            assert await reg.auto_discover("") == []

        asyncio.run(_test())


class TestWildcardSubdomain:
    def test_wildcard_matches_subdomain(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = _make_skill(
                domain="*.github.com", access_count=10, last_used=time.monotonic(),
            )
            await reg.register(s)
            discovered = await reg.auto_discover("https://gist.github.com/test")
            assert len(discovered) >= 1

        asyncio.run(_test())

    def test_wildcard_matches_bare_domain(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = _make_skill(
                domain="*.github.com", access_count=10, last_used=time.monotonic(),
            )
            await reg.register(s)
            discovered = await reg.auto_discover("https://github.com/test")
            assert len(discovered) >= 1

        asyncio.run(_test())

    def test_exact_does_not_match_subdomain(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = _make_skill(
                domain="github.com", access_count=10, last_used=time.monotonic(),
            )
            await reg.register(s)
            discovered = await reg.auto_discover("https://gist.github.com/test")
            assert len(discovered) == 0

        asyncio.run(_test())


class TestHotSkills:
    def test_only_hot_returned(self, tmp_path):
        reg = _registry(tmp_path, activation_threshold=2.0)

        async def _test():
            s_hot = await reg.register(_make_skill(name="hot", access_count=50, last_used=time.monotonic()))
            s_cold = await reg.register(_make_skill(name="cold", access_count=0, last_used=0.0))
            reg.compute_and_cache_activations("example.com")
            hot = reg.hot_skills("example.com")
            hot_names = [s.name for s in hot]
            assert "hot" in hot_names
            assert "cold" not in hot_names

        asyncio.run(_test())


class TestLearnFromTrajectory:
    def test_creates_learned_skill(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.learn_from_trajectory(
                domain="github.com",
                task_description="Login to GitHub",
                actions_taken=["fill #login_field", "click submit"],
                selectors_used={"#login_field": "SELECTOR"},
            )
            assert s.provenance == SkillProvenance.LEARNED
            assert s.domain == "github.com"
            assert "login" in s.name
            assert s.selectors == {"#login_field": "SELECTOR"}
            got = await reg.get(s.domain, s.skill_id)
            assert got is not None

        asyncio.run(_test())

    def test_with_preferred_tier(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.learn_from_trajectory(
                domain="d.com",
                task_description="Do something",
                actions_taken=["click btn"],
                selectors_used={"btn": "COORDINATE"},
                preferred_tier={"btn.*": "COORDINATE"},
            )
            assert s.preferred_tier == {"btn.*": "COORDINATE"}

        asyncio.run(_test())


class TestArchival:
    def test_archive_stale_old_skills(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill(name="old", access_count=15))
            s.status = SkillStatus.STALE
            # Use a very recent last_used, and set max_age_days=0 to trigger archival
            s.last_used = time.monotonic() - 1.0
            count = await reg.archive_stale_skills("example.com", max_age_days=0, min_access_count=10)
            assert count == 1
            assert await reg.get("example.com", s.skill_id) is None
            archived_path = tmp_path / "skills" / "_archived" / "example.com" / f"{s.skill_id}.json"
            assert archived_path.exists()

        asyncio.run(_test())

    def test_does_not_archive_active(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill(name="active", access_count=15))
            s.last_used = time.monotonic() - 86400 * 45
            count = await reg.archive_stale_skills("example.com", max_age_days=30, min_access_count=10)
            assert count == 0

        asyncio.run(_test())

    def test_does_not_archive_low_access(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill(name="rare", access_count=3))
            s.status = SkillStatus.STALE
            s.last_used = time.monotonic() - 86400 * 45
            count = await reg.archive_stale_skills("example.com", max_age_days=30, min_access_count=10)
            assert count == 0

        asyncio.run(_test())


class TestLoadDomain:
    def test_load_from_disk(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            s = await reg.register(_make_skill())
            reg._index.clear()
            reg._loaded_domains.clear()
            count = await reg.load_domain("example.com")
            assert count == 1
            assert await reg.get("example.com", s.skill_id) is not None

        asyncio.run(_test())

    def test_load_nonexistent_domain(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            count = await reg.load_domain("nonexistent.com")
            assert count == 0

        asyncio.run(_test())


class TestComputeActivations:
    def test_sorted_descending(self, tmp_path):
        reg = _registry(tmp_path)

        async def _test():
            await reg.register(_make_skill(name="low", access_count=1, last_used=time.monotonic()))
            await reg.register(_make_skill(name="high", access_count=100, last_used=time.monotonic()))
            scored = reg.compute_and_cache_activations("example.com")
            assert scored[0][1].name == "high"
            assert scored[-1][1].name == "low"

        asyncio.run(_test())
