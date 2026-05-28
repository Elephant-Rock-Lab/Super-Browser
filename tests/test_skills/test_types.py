"""Tests for GAP-05 skills types — enums, dataclasses, serialization."""

import json

import pytest

from super_browser.skills.types import (
    ActivationConfig,
    DomainSkill,
    InvalidSkillFormat,
    SelectorConflictWarning,
    SkillImportError,
    SkillProvenance,
    SkillQuery,
    SkillSizeExceeded,
    SkillStatus,
)

# -- Enums --


class TestSkillProvenance:
    def test_values(self):
        assert SkillProvenance.DISCOVERED == "discovered"
        assert SkillProvenance.LEARNED == "learned"
        assert SkillProvenance.MANUAL == "manual"

    def test_count(self):
        assert len(SkillProvenance) == 3


class TestSkillStatus:
    def test_values(self):
        assert SkillStatus.ACTIVE == "active"
        assert SkillStatus.STALE == "stale"
        assert SkillStatus.ARCHIVED == "archived"

    def test_count(self):
        assert len(SkillStatus) == 3


# -- DomainSkill --


class TestDomainSkill:
    def test_defaults(self):
        s = DomainSkill(skill_id="x", domain="example.com", name="login")
        assert s.description == ""
        assert s.selectors == {}
        assert s.actions == {}
        assert s.quirks == []
        assert s.preferred_tier == {}
        assert s.url_patterns == []
        assert s.provenance == SkillProvenance.LEARNED
        assert s.status == SkillStatus.ACTIVE
        assert s.access_count == 0
        assert s.last_used == 0.0
        assert s.version == 1

    def test_touch(self):
        s = DomainSkill(skill_id="x", domain="example.com", name="login")
        s.touch()
        assert s.access_count == 1
        assert s.last_used > 0
        s.touch()
        assert s.access_count == 2

    def test_to_dict_roundtrip(self):
        s = DomainSkill(
            skill_id="gh-login",
            domain="github.com",
            name="login",
            description="Login flow",
            selectors={"username": "#login_field"},
            provenance=SkillProvenance.MANUAL,
        )
        d = s.to_dict()
        assert d["skill_id"] == "gh-login"
        assert d["provenance"] == "manual"
        assert d["selectors"]["username"] == "#login_field"

    def test_from_dict(self):
        d = {
            "skill_id": "gh-login",
            "domain": "github.com",
            "name": "login",
            "provenance": "discovered",
            "status": "stale",
            "selectors": {"user": "#field"},
        }
        s = DomainSkill.from_dict(d)
        assert s.provenance == SkillProvenance.DISCOVERED
        assert s.status == SkillStatus.STALE
        assert s.selectors == {"user": "#field"}

    def test_from_dict_ignores_extra_fields(self):
        d = {
            "skill_id": "x", "domain": "d.com", "name": "n",
            "provenance": "learned",
            "_activation_score": 5.0,
        }
        s = DomainSkill.from_dict(d)
        assert s.skill_id == "x"

    def test_size_bytes(self):
        s = DomainSkill(skill_id="x", domain="d.com", name="n")
        size = s.size_bytes()
        assert size > 0
        assert size == len(json.dumps(s.to_dict()).encode("utf-8"))

    def test_matches_url_no_patterns(self):
        s = DomainSkill(skill_id="x", domain="d.com", name="n")
        assert s.matches_url("https://d.com/anything") is True

    def test_matches_url_with_patterns(self):
        s = DomainSkill(
            skill_id="x", domain="github.com", name="login",
            url_patterns=["https://github.com/login*"],
        )
        assert s.matches_url("https://github.com/login") is True
        assert s.matches_url("https://github.com/repo") is False


# -- ActivationConfig --


class TestActivationConfig:
    def test_defaults(self):
        cfg = ActivationConfig()
        assert cfg.decay_factor == 0.5
        assert cfg.activation_threshold == 1.0
        assert cfg.stale_penalty == -2.0

    def test_frozen(self):
        cfg = ActivationConfig()
        with pytest.raises(AttributeError):
            cfg.decay_factor = 0.9


# -- SkillQuery --


class TestSkillQuery:
    def test_defaults(self):
        q = SkillQuery()
        assert q.domain is None
        assert q.provenance is None
        assert q.min_access_count == 0


# -- Error hierarchy --


class TestErrors:
    def test_skill_import_error_base(self):
        with pytest.raises(SkillImportError):
            raise SkillImportError("test")

    def test_invalid_skill_format(self):
        assert issubclass(InvalidSkillFormat, SkillImportError)

    def test_selector_conflict_warning(self):
        assert issubclass(SelectorConflictWarning, SkillImportError)

    def test_skill_size_exceeded(self):
        assert issubclass(SkillSizeExceeded, SkillImportError)
