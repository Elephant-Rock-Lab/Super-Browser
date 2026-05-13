"""Tests for markdown skill importer."""

from pathlib import Path

from super_browser.skills.markdown import parse_markdown_skills
from super_browser.skills.types import SkillProvenance


def _write_md(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestParseMarkdown:
    def test_parse_single_skill(self, tmp_path):
        _write_md(
            tmp_path / "github.com" / "login.md",
            "# GitHub Login\n\n"
            "## Selectors\n"
            "- `#login_field`: Username input\n"
            "- `#password`: Password input\n\n"
            "## Quirks\n"
            "- Dynamic IDs have __ prefix\n"
            "- SSO redirect possible\n\n"
            "## Wait Strategy\n"
            "- after_navigate: wait for .js-login-form\n",
        )

        skills = parse_markdown_skills(tmp_path)
        assert len(skills) == 1
        s = skills[0]
        assert s.domain == "github.com"
        assert s.name == "login"
        assert s.provenance == SkillProvenance.DISCOVERED
        assert "#login_field" in s.selectors
        assert "#password" in s.selectors
        assert len(s.quirks) == 2

    def test_parse_multiple_domains(self, tmp_path):
        _write_md(tmp_path / "github.com" / "login.md", "# GH Login\n\n## Selectors\n- `#f`: field\n")
        _write_md(tmp_path / "reddit.com" / "browse.md", "# Browse\n\n## Quirks\n- Slow loading\n")

        skills = parse_markdown_skills(tmp_path)
        assert len(skills) == 2
        domains = {s.domain for s in skills}
        assert domains == {"github.com", "reddit.com"}

    def test_empty_directory(self, tmp_path):
        skills = parse_markdown_skills(tmp_path / "nonexistent")
        assert skills == []

    def test_missing_sections(self, tmp_path):
        _write_md(tmp_path / "example.com" / "basic.md", "# Basic Skill\n\nJust a description.\n")
        skills = parse_markdown_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].selectors == {}
        assert skills[0].quirks == []

    def test_actions_parsed(self, tmp_path):
        _write_md(
            tmp_path / "example.com" / "actions.md",
            "# Actions Test\n\n## Actions\n- Click submit button\n- Wait for result\n",
        )
        skills = parse_markdown_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].actions.get("steps")
        assert len(skills[0].actions["steps"]) == 2

    def test_title_used_as_description(self, tmp_path):
        _write_md(tmp_path / "example.com" / "x.md", "# My Great Skill\n\n## Selectors\n- `a`: link\n")
        skills = parse_markdown_skills(tmp_path)
        assert skills[0].description == "My Great Skill"

    def test_files_without_sections_still_parsed(self, tmp_path):
        _write_md(tmp_path / "example.com" / "empty.md", "Just some free text\n")
        skills = parse_markdown_skills(tmp_path)
        assert len(skills) == 1
        assert skills[0].name == "empty"
