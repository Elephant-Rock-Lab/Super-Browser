"""Markdown skill importer — parse browser-harness domain skill files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from super_browser.skills.types import DomainSkill, SkillProvenance


def parse_markdown_skills(directory: Path) -> list[DomainSkill]:
    skills = []
    if not directory.is_dir():
        return skills
    for domain_dir in sorted(directory.iterdir()):
        if not domain_dir.is_dir():
            continue
        domain = domain_dir.name
        for md_file in sorted(domain_dir.glob("*.md")):
            skill = _parse_single_markdown(md_file, domain)
            if skill:
                skills.append(skill)
    return skills


def _parse_single_markdown(path: Path, domain: str) -> DomainSkill | None:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None

    name = path.stem
    sections = _split_sections(text)

    selectors = _parse_selectors(sections.get("Selectors", ""))
    quirks = _parse_list_items(sections.get("Quirks", sections.get("Gotchas", "")))
    wait_strategy = _parse_wait_strategy(sections.get("Wait Strategy", ""))
    actions = _parse_actions(sections.get("Actions", sections.get("Steps", "")))

    return DomainSkill(
        skill_id=f"{domain.replace('*', '_wc_')}-{name}",
        domain=domain,
        name=name,
        description=_extract_title(text) or name,
        selectors=selectors,
        actions=actions,
        quirks=quirks,
        wait_strategy=wait_strategy,
        provenance=SkillProvenance.DISCOVERED,
    )


def _split_sections(text: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current = "header"
    lines: list[str] = []
    for line in text.split("\n"):
        m = re.match(r"^##\s+(.+)", line)
        if m:
            sections[current] = "\n".join(lines)
            current = m.group(1).strip()
            lines = []
        else:
            lines.append(line)
    sections[current] = "\n".join(lines)
    return sections


def _extract_title(text: str) -> str:
    for line in text.split("\n"):
        m = re.match(r"^#\s+(.+)", line)
        if m:
            return m.group(1).strip()
    return ""


def _parse_selectors(text: str) -> dict[str, str]:
    selectors: dict[str, str] = {}
    for line in text.split("\n"):
        m = re.match(r"[-*]\s+`([^`]+)`\s*:?\s*(.*)", line)
        if m:
            selectors[m.group(1)] = m.group(2).strip()
    return selectors


def _parse_list_items(text: str) -> list[str]:
    items = []
    for line in text.split("\n"):
        m = re.match(r"[-*]\s+(.+)", line)
        if m:
            items.append(m.group(1).strip())
    return items


def _parse_wait_strategy(text: str) -> dict[str, Any]:
    strategy: dict[str, Any] = {}
    for line in text.split("\n"):
        m = re.match(r"[-*]\s+(?:after[_ ])?(\w+)\s*:\s*(.+)", line, re.IGNORECASE)
        if m:
            strategy[m.group(1).lower()] = m.group(2).strip()
    return strategy


def _parse_actions(text: str) -> dict[str, Any]:
    steps = _parse_list_items(text)
    if steps:
        return {"steps": steps}
    return {}
