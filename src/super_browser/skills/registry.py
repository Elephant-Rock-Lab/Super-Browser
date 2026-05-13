"""SkillRegistry — CRUD, auto-discovery, ACT-R activation, and trajectory learning."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse

from super_browser.skills.activation import compute_activation
from super_browser.skills.types import (
    ActivationConfig,
    DomainSkill,
    InvalidSkillFormat,
    SkillProvenance,
    SkillQuery,
    SkillSizeExceeded,
    SkillStatus,
)

logger = logging.getLogger(__name__)


class SkillRegistry:
    MAX_SKILL_SIZE_BYTES = 15 * 1024

    def __init__(
        self,
        activation_config: Optional[ActivationConfig] = None,
        skills_dir: Optional[Path] = None,
    ) -> None:
        self._config = activation_config or ActivationConfig()
        self._skills_dir = skills_dir or (Path.home() / ".super-browser" / "browser-skills")
        self._archived_dir = self._skills_dir / "_archived"
        self._index: dict[str, dict[str, DomainSkill]] = {}
        self._hot_cache: dict[str, list[tuple[float, DomainSkill]]] = {}
        self._loaded_domains: set[str] = set()

    @staticmethod
    def _safe_dir(domain: str) -> str:
        return domain.replace("*", "_wildcard_")

    # -- CRUD -----------------------------------------------------------------

    async def register(self, skill: DomainSkill) -> DomainSkill:
        if not skill.domain:
            raise InvalidSkillFormat("Skill must have a domain")
        if not skill.name:
            raise InvalidSkillFormat("Skill must have a name")
        if not skill.skill_id:
            skill.skill_id = f"{self._safe_dir(skill.domain)}-{uuid.uuid4().hex[:8]}"

        size = skill.size_bytes()
        if size > self.MAX_SKILL_SIZE_BYTES:
            raise SkillSizeExceeded(
                f"Skill size {size} bytes exceeds maximum {self.MAX_SKILL_SIZE_BYTES} bytes"
            )

        domain_skills = self._index.setdefault(skill.domain, {})
        domain_skills[skill.skill_id] = skill
        await self._persist_skill(skill)
        logger.info("Registered skill %s for domain %s", skill.skill_id, skill.domain)
        return skill

    async def get(self, domain: str, skill_id: str) -> Optional[DomainSkill]:
        domain_skills = self._index.get(domain)
        if domain_skills is None:
            return None
        return domain_skills.get(skill_id)

    async def update(self, domain: str, skill_id: str, **updates: Any) -> DomainSkill:
        domain_skills = self._index.get(domain)
        if domain_skills is None or skill_id not in domain_skills:
            raise KeyError(f"Skill {skill_id} not found in domain {domain}")
        skill = domain_skills[skill_id]
        for key, value in updates.items():
            if key in ("provenance",) and isinstance(value, str):
                value = SkillProvenance(value)
            if key in ("status",) and isinstance(value, str):
                value = SkillStatus(value)
            if hasattr(skill, key):
                setattr(skill, key, value)
        skill.updated_at = time.time()
        await self._persist_skill(skill)
        return skill

    async def delete(self, domain: str, skill_id: str) -> bool:
        domain_skills = self._index.get(domain)
        if domain_skills is None or skill_id not in domain_skills:
            return False
        del domain_skills[skill_id]
        path = self._skills_dir / self._safe_dir(domain) / f"{skill_id}.json"
        if path.exists():
            path.unlink()
        return True

    async def list_by_domain(self, domain: str, *, include_archived: bool = False) -> list[DomainSkill]:
        domain_skills = self._index.get(domain, {})
        if include_archived:
            return list(domain_skills.values())
        return [s for s in domain_skills.values() if s.status != SkillStatus.ARCHIVED]

    async def search(self, query: SkillQuery) -> list[DomainSkill]:
        results = []
        domains = [query.domain] if query.domain else list(self._index.keys())
        for domain in domains:
            for skill in self._index.get(domain, {}).values():
                if query.provenance and skill.provenance != query.provenance:
                    continue
                if query.status and skill.status != query.status:
                    continue
                if query.name_contains and query.name_contains.lower() not in skill.name.lower():
                    continue
                if skill.access_count < query.min_access_count:
                    continue
                results.append(skill)
        return results

    # -- Auto-Discovery -------------------------------------------------------

    async def auto_discover(
        self,
        url: str,
        current_task: str = "",
        *,
        similarity_fn: Optional[Callable] = None,
    ) -> list[DomainSkill]:
        hostname = self._extract_hostname(url)
        if not hostname:
            return []

        candidates = self._match_by_hostname(hostname)
        if not candidates:
            return []

        candidates = [s for s in candidates if s.matches_url(url)]
        if not candidates:
            return []

        # Score candidates directly rather than by domain key
        scored = []
        for skill in candidates:
            score = compute_activation(skill, current_task, self._config, similarity_fn=similarity_fn)
            scored.append((score, skill))
        scored.sort(key=lambda x: x[0], reverse=True)

        hot = [
            (score, skill) for score, skill in scored
            if score >= self._config.activation_threshold and skill.matches_url(url)
        ]
        hot.sort(key=lambda x: x[0], reverse=True)

        result = [skill for _, skill in hot]
        for skill in result:
            skill.touch()
            await self._persist_skill(skill)

        return result

    # -- Hot Skills -----------------------------------------------------------

    def hot_skills(self, domain: str) -> list[DomainSkill]:
        cached = self._hot_cache.get(domain, [])
        return [skill for _, skill in cached]

    def compute_and_cache_activations(
        self,
        domain: str,
        current_task: str = "",
        *,
        similarity_fn: Optional[Callable] = None,
    ) -> list[tuple[float, DomainSkill]]:
        domain_skills = self._index.get(domain, {})
        scored = []
        for skill in domain_skills.values():
            score = compute_activation(skill, current_task, self._config, similarity_fn=similarity_fn)
            scored.append((score, skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        hot = [(s, sk) for s, sk in scored if s >= self._config.activation_threshold]
        self._hot_cache[domain] = hot
        return scored

    # -- Learning -------------------------------------------------------------

    async def learn_from_trajectory(
        self,
        domain: str,
        task_description: str,
        actions_taken: list[str],
        selectors_used: dict[str, str],
        *,
        preferred_tier: Optional[dict[str, str]] = None,
    ) -> DomainSkill:
        slug = re.sub(r"[^a-z0-9]+", "_", task_description.lower())[:40].strip("_") or "task"
        skill = DomainSkill(
            skill_id="",
            domain=domain,
            name=slug,
            description=task_description,
            selectors=selectors_used,
            actions={"steps": actions_taken},
            preferred_tier=preferred_tier or {},
            provenance=SkillProvenance.LEARNED,
        )
        return await self.register(skill)

    # -- Import ---------------------------------------------------------------

    async def import_markdown(self, directory: Path) -> int:
        from super_browser.skills.markdown import parse_markdown_skills
        skills = parse_markdown_skills(directory)
        for skill in skills:
            await self.register(skill)
        return len(skills)

    # -- Archival -------------------------------------------------------------

    async def archive_stale_skills(
        self, domain: str, *, max_age_days: int = 30, min_access_count: int = 10,
    ) -> int:
        domain_skills = self._index.get(domain, {})
        to_archive = []
        now = time.monotonic()
        for skill_id, skill in list(domain_skills.items()):
            if skill.status != SkillStatus.STALE:
                continue
            if skill.access_count < min_access_count:
                continue
            if skill.last_used <= 0:
                continue
            age_days = (now - skill.last_used) / 86400.0
            if age_days > max_age_days:
                to_archive.append(skill_id)

        archived_dir = self._archived_dir / self._safe_dir(domain)
        for skill_id in to_archive:
            skill = domain_skills.pop(skill_id)
            skill.status = SkillStatus.ARCHIVED
            archived_dir.mkdir(parents=True, exist_ok=True)
            await self._persist_skill_to(skill, archived_dir / f"{skill_id}.json")
            old_path = self._skills_dir / self._safe_dir(domain) / f"{skill_id}.json"
            if old_path.exists():
                old_path.unlink()

        if to_archive:
            self._hot_cache.pop(domain, None)

        return len(to_archive)

    # -- Validation -----------------------------------------------------------

    async def validate_skill(self, skill: DomainSkill) -> list[str]:
        warnings = []
        if not self._cdp:
            return warnings
        for name, selector in skill.selectors.items():
            try:
                result = await self._cdp.send("Runtime.evaluate", {
                    "expression": f'document.querySelector("{selector}") !== null',
                    "returnByValue": True,
                })
                if result.ok and result.data:
                    val = result.data.get("result", {}).get("value")
                    if val is False:
                        warnings.append(f"Selector '{name}' ({selector}) not found in DOM")
            except Exception:
                pass
        return warnings

    # -- Persistence ----------------------------------------------------------

    async def _persist_skill(self, skill: DomainSkill) -> None:
        path = self._skills_dir / self._safe_dir(skill.domain) / f"{skill.skill_id}.json"
        await self._persist_skill_to(skill, path)

    async def _persist_skill_to(self, skill: DomainSkill, path: Path) -> None:
        def _write():
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(skill.to_dict(), f, indent=2)
            os.replace(tmp, path)
        await asyncio.to_thread(_write)

    async def load_domain(self, domain: str) -> int:
        domain_dir = self._skills_dir / self._safe_dir(domain)
        if not domain_dir.is_dir():
            self._loaded_domains.add(domain)
            return 0
        domain_skills = self._index.setdefault(domain, {})
        count = 0
        for path in domain_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                skill = DomainSkill.from_dict(data)
                domain_skills[skill.skill_id] = skill
                count += 1
            except Exception:
                logger.warning("Failed to load skill from %s", path)
        self._loaded_domains.add(domain)
        return count

    # -- Hostname matching ----------------------------------------------------

    def _match_by_hostname(self, hostname: str) -> list[DomainSkill]:
        results = []
        for domain, skills in self._index.items():
            if domain == hostname:
                results.extend(skills.values())
            elif domain.startswith("*."):
                suffix = domain[2:]
                if hostname == suffix or hostname.endswith("." + suffix):
                    results.extend(skills.values())
        return results

    @staticmethod
    def _extract_hostname(url: str) -> str:
        try:
            return urlparse(url).hostname or ""
        except Exception:
            return ""

    # -- CDP reference for validation -----------------------------------------

    _cdp: Any = None

    def set_cdp(self, cdp: Any) -> None:
        self._cdp = cdp
