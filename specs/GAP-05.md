# GAP-05: Domain Skill Registry

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap          | #5                                                           |
| Title        | Domain Skill Registry                                        |
| Phase        | Phase 4 (Domain Skills -- Weeks 7-8)                         |
| Status       | Spec Complete                                                 |
| Depends-On   | GAP-02 (MultimodalController -- skills store preferred tiers/selectors) |
| Enables      | GAP-04 (Self-Healing -- selector recovery from skill hints), GAP-07 (Agent Orchestration -- skill-aware action dispatch), GAP-09 (Token Budget -- skills reduce exploration cost) |
| Build Order  | Week 3-4 (core), Week 7-8 (ACT-R activation), Week 11-12 (evolution) |
| Effort       | Low (core) / Medium (ACT-R + evolution)                      |

---

## 1. Problem

Super Browser must accumulate site-specific knowledge over time -- which selectors work on GitHub, what login flow GitHub uses, how to handle Amazon's dynamic IDs, what wait strategy Reddit requires. Without persistent domain skills, every navigation to a known site starts from scratch: the agent re-explores page structure, re-discovers stable selectors, and re-learns the same quirks it already solved in previous sessions. This wastes tokens, increases latency, and reduces reliability.

Browser-harness demonstrates the value: 67 markdown domain-skill files covering Amazon, GitHub, Reddit, Spotify, arXiv, SEC EDGAR, Zillow, and 50+ more sites. Each file documents URL patterns, stable selectors, private APIs, framework quirks, wait requirements, gotchas, and traps. The `goto()` function auto-discovers matching skills by hostname and returns them alongside CDP results.

The challenge is threefold: (1) providing a registry that stores, indexes, and retrieves skills by domain with CRUD operations; (2) implementing a decay-based activation model (ACT-R) so frequently used skills stay "hot" while rarely used skills are archived without deletion; and (3) enabling the agent to generate skills from successful task trajectories so the knowledge base grows autonomously without human authoring.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                                    |
|-------|--------------------------------------------------------------------------------------------------------------------------------|
| R1    | Provide a `DomainSkill` dataclass with fields: `skill_id`, `domain`, `name`, `selectors` (dict), `actions` (dict), `provenance` (enum), `access_count`, `last_used`, `preferred_tier`, `description`, `quirks`, `wait_strategy`, `created_at`, `updated_at` |
| R2    | Provide a `SkillProvenance` enum with values: `DISCOVERED` (auto-loaded from markdown), `LEARNED` (agent-generated from successful trajectory), `MANUAL` (human-authored) |
| R3    | Provide a `SkillRegistry` class with CRUD operations: `register()`, `get()`, `update()`, `delete()`, `list_by_domain()`, `search()` |
| R4    | Skills persist as JSON files at `~/.super-browser/browser-skills/<domain>/<skill_id>.json` with atomic writes (write-to-temp + rename) |
| R5    | On `navigate()` to a URL, auto-discover skills matching the hostname via `SkillRegistry.auto_discover(url)` and inject them into the agent context |
| R6    | Hostname matching supports exact match (e.g., `github.com`) and wildcard subdomain match (e.g., `*.github.com` matches `gist.github.com`) |
| R7    | Implement ACT-R activation scoring: `activation = base_level + context_boost + recency_bonus` where `base_level = log(access_count + 1)`, `recency_bonus = decay_factor ^ hours_since_last_use`, `context_boost = semantic_similarity(current_task, skill_description)` |
| R8    | Skills above a configurable activation threshold (default: 1.0) are loaded into "hot" memory (in-memory cache); skills below threshold are archived on disk but not deleted |
| R9    | Provide `SkillRegistry.hot_skills(domain)` returning only skills above the activation threshold, sorted by descending activation score |
| R10   | When a task completes successfully, the agent may call `SkillRegistry.learn_from_trajectory(domain, task_description, actions_taken, selectors_used)` to auto-generate a skill |
| R11   | The `learn_from_trajectory()` method extracts stable selectors that were used successfully (from `ActionResult.meta.method` and tier preference cache entries), generates a `DomainSkill` with `provenance=LEARNED`, and persists it |
| R12   | Skill selectors are validated against the current page before injection: if a selector in the skill no longer exists in the DOM, the skill is marked as `stale=True` and a warning is returned alongside the skill |
| R13   | Stale skills with `access_count > 10` and no successful use in the last 30 days are automatically archived (moved to `~/.super-browser/browser-skills/_archived/<domain>/`) |
| R14   | Skills store the `preferred_tier` per action (inherited from GAP-02 `TierPreferenceCache` entries) so the MultimodalController can skip exploration on known domains |
| R15   | Provide a `SkillImportError` hierarchy for validation failures: `InvalidSkillFormat`, `SelectorConflictWarning`, `SkillSizeExceeded` (max 15 KB per skill) |
| R16   | Support bulk import from browser-harness markdown format: `SkillRegistry.import_markdown(directory)` parsing the 67 `.md` files into `DomainSkill` objects with `provenance=DISCOVERED` |
| R17   | Skill JSON schema includes a `version` field (currently `1`) to support future schema migrations |
| R18   | All skill operations are logged via the tracing subsystem (GAP-11) with `skill_id`, `domain`, `operation`, `activation_score`, `duration_ms` |

### Non-Functional

| ID    | Requirement                                                                                                          |
|-------|----------------------------------------------------------------------------------------------------------------------|
| NFR1  | Auto-discovery (hostname match + activation scoring) must complete in under 5 ms for a registry of 500+ skills       |
| NFR2  | Hot skill lookup (in-memory) must complete in under 1 ms; no disk I/O on the hot path                                |
| NFR3  | Skill persistence (JSON write) must be asynchronous and non-blocking; skill registration never blocks navigation     |
| NFR4  | The registry must handle at least 1000 skills across 200 domains without degradation                                 |
| NFR5  | Skill JSON files must be human-readable and manually editable (no binary serialization)                              |
| NFR6  | The activation scoring computation must be O(1) per skill (no scan of the full registry to score one skill)          |
| NFR7  | Atomic file writes prevent skill corruption on crash (write-to-temp + os.replace)                                     |
| NFR8  | Skill size capped at 15 KB per skill file; larger skills are rejected with `SkillSizeExceeded`                       |

### Out of Scope

- Automated skill evolution via GEPA/DSPy optimization -- deferred to Week 12, informed by Hermes Self-Evolution analysis
- Plugin slot architecture (OpenClaw-style exclusive capability slots) -- deferred to GAP-07 (Agent Orchestration)
- Skill marketplace / sharing (Hermes ClawHub) -- not in roadmap scope
- Cross-agent skill synchronization -- not in roadmap scope
- Skill versioning with rollback -- future enhancement after evolution is implemented

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | Domain Skills as Markdown (67 sites) | browser-harness `domain-skills/` | 3.90 | Low | Initial content + format |
| P2 | Hostname Auto-Discovery on Navigate | browser-harness `helpers.py:50-53` | 3.90 | Low | Skill loading trigger |
| P3 | Action Registry with Domain Gating | browser-use `tools/registry/service.py` | 3.70 | Low | Domain-based filtering |
| P4 | Skill CRUD + Marketplace | Hermes `tools/skills_tool.py`, `tools/skills_hub.py` | 3.70 | Low | Skill management operations |
| P5 | Plugin Manifest (openclaw.plugin.json) | OpenClaw `plugins/registry.ts` | 4.80 | Low | Skill schema / manifest pattern |
| P6 | Skill-as-Optimizable-Parameter | Hermes Self-Evolution `skills/skill_module.py` | 3.75 | High | Evolution mechanism (Week 12) |
| P7 | Agent-Editable Skills | browser-harness `SKILL.md` design | 3.90 | Low | Agent-generated skill authoring |
| P8 | Session Mining for Skill Extraction | Hermes Self-Evolution `core/external_importers.py` | 4.50 | Medium | Trajectory-to-skill pipeline |
| P9 | Constraint Validation Guardrails | Hermes Self-Evolution `core/constraints.py` | 3.15 | Low | Skill size/format validation |

### Per-Pattern Adoption Notes

**P1 -- Domain Skills as Markdown (browser-harness)**
Adopt the 67 markdown domain-skill files as the initial seed content. Each file documents URL patterns, stable selectors, private APIs, framework quirks, wait requirements, gotchas, and traps for a specific site. The import process parses these into `DomainSkill` objects with `provenance=DISCOVERED`. The content is production-ready; only the storage format changes (markdown to JSON) to support programmatic CRUD and activation scoring. The `import_markdown()` method handles this conversion.

**P2 -- Hostname Auto-Discovery on Navigate (browser-harness)**
Adopt the pattern where `goto()` returns matching skills alongside CDP results. In Super Browser, the `navigate()` method on the facade calls `SkillRegistry.auto_discover(url)` after navigation completes, which extracts the hostname, matches against registered skills, computes activation scores, and returns hot skills for injection into the agent context. This is the core loading trigger -- skills load automatically when the agent navigates to a matching domain.

**P3 -- Action Registry with Domain Gating (browser-use)**
Adopt the domain-based filtering pattern. browser-use's action registry uses glob patterns per action to enable/disable actions for specific domains. For Super Browser, this becomes skill applicability filtering: each skill has an optional `url_patterns` list (glob patterns) that further refines when a skill applies beyond simple hostname matching. For example, a `github.com/login` skill applies only to `https://github.com/login*`, not all github.com pages.

**P4 -- Skill CRUD + Marketplace (Hermes)**
Adopt the skill management operations pattern from Hermes's `skills_tool.py`. Hermes provides create, read, update, delete, list, and search operations on skills stored as YAML frontmatter + markdown body. Super Browser adapts this to JSON storage with the `SkillRegistry` class. The search operation supports filtering by domain, provenance, and keyword in description/selectors.

**P5 -- Plugin Manifest (OpenClaw)**
Adopt the manifest-driven validation pattern. OpenClaw's `openclaw.plugin.json` declares plugin metadata, capabilities, and security constraints. Super Browser's skill JSON schema serves a similar role: each skill declares its domain, selectors, actions, and constraints. The `SkillImportError` hierarchy (P9 below) validates skills against this schema on registration, rejecting malformed or oversized entries.

**P6 -- Skill-as-Optimizable-Parameter (Hermes Self-Evolution)**
Deferred to Week 12. When implemented, the GEPA-based optimization pipeline will treat skill content as an optimizable parameter, evolving selectors and actions based on success rates. The current spec provides the `DomainSkill` dataclass and storage format that the evolution pipeline will consume. The `version` field in the JSON schema supports schema migrations as the evolution system adds fields.

**P7 -- Agent-Editable Skills (browser-harness)**
Adopt the principle from browser-harness's SKILL.md design: "agent-generated skills only." The agent records what actually worked, not what a human guessed would work. The `learn_from_trajectory()` method implements this: after a successful task, the agent extracts the selectors and actions that worked, generates a `DomainSkill` with `provenance=LEARNED`, and registers it. Human review is optional.

**P8 -- Session Mining for Skill Extraction (Hermes Self-Evolution)**
Adopt the pattern of mining real usage data for skill generation. Hermes's external importers mine session history from Claude Code, GitHub Copilot, and Hermes itself. Super Browser's `learn_from_trajectory()` is a simplified version: it mines the current session's successful actions rather than importing from external sources. Future enhancement could add external session mining.

**P9 -- Constraint Validation Guardrails (Hermes Self-Evolution)**
Adopt the constraint validation pattern for skill size and format. Hermes's `ConstraintValidator` enforces size limits per type (15 KB skills, 500-char tool descriptions). Super Browser enforces: max 15 KB per skill JSON, valid JSON structure, required fields present, selector values are valid CSS selectors or XPath expressions. The `SkillImportError` hierarchy provides structured validation feedback.

---

## 4. Interface Contract

### Dataclasses

```python
from __future__ import annotations

import enum
import math
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SkillProvenance(enum.Enum):
    """How a domain skill was created."""
    DISCOVERED = "discovered"   # Auto-loaded from browser-harness markdown files
    LEARNED = "learned"         # Agent-generated from successful task trajectory
    MANUAL = "manual"           # Human-authored via editor or API


class SkillStatus(enum.Enum):
    """Lifecycle status of a domain skill."""
    ACTIVE = "active"           # Normal state, eligible for hot loading
    STALE = "stale"             # Selectors no longer validate against current page
    ARCHIVED = "archived"       # Moved to _archived/ due to low activation


# ---------------------------------------------------------------------------
# DomainSkill (matches roadmap Phase 4 definition)
# ---------------------------------------------------------------------------

@dataclass
class DomainSkill:
    """
    Site-specific knowledge for a domain.

    Storage: ~/.super-browser/browser-skills/<domain>/<skill_id>.json

    Matches the roadmap definition from Phase 4:
      skill_id, domain, name, selectors, actions, provenance, access_count, last_used

    Extended with: description, preferred_tier, quirks, wait_strategy,
    url_patterns, status, created_at, updated_at, version.
    """

    # -- Identity --------------------------------------------------------------
    skill_id: str                            # UUID or slug, e.g., "github-login-abc123"
    domain: str                              # Hostname, e.g., "github.com"
    name: str                                # Human-readable, e.g., "login", "create_issue"
    description: str = ""                    # Natural language summary for context_boost

    # -- Content ---------------------------------------------------------------
    selectors: dict[str, str] = field(default_factory=dict)
    # semantic_name -> CSS selector or XPath
    # e.g., {"username_input": "#login_field", "password_input": "#password",
    #        "submit_button": "input[type='submit']"}

    actions: dict[str, Any] = field(default_factory=dict)
    # action_name -> step definition
    # e.g., {"login": {"steps": ["fill username_input", "fill password_input",
    #                               "click submit_button"]}}

    quirks: list[str] = field(default_factory=list)
    # Site-specific gotchas, e.g., ["GitHub adds __ prefixes to dynamic IDs",
    #                                "Wait for .js-login-form to be visible"]

    wait_strategy: dict[str, Any] = field(default_factory=dict)
    # e.g., {"after_navigate": {"selector": ".dashboard", "timeout": 5000}}

    # -- Tier preferences (from GAP-02 TierPreferenceCache) --------------------
    preferred_tier: dict[str, str] = field(default_factory=dict)
    # selector_pattern -> "SELECTOR" | "COORDINATE" | "VISION"
    # e.g., {"button.*": "COORDINATE", "input[type='text']": "SELECTOR"}

    # -- Applicability ---------------------------------------------------------
    url_patterns: list[str] = field(default_factory=list)
    # Glob patterns for URL-level filtering beyond hostname
    # e.g., ["https://github.com/login*", "https://github.com/session"]

    # -- Provenance & lifecycle ------------------------------------------------
    provenance: SkillProvenance = SkillProvenance.LEARNED
    status: SkillStatus = SkillStatus.ACTIVE
    access_count: int = 0
    last_used: float = 0.0                   # monotonic timestamp
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    # -- Schema ---------------------------------------------------------------
    version: int = 1                         # Schema version for future migrations

    # -- Computed: ACT-R activation score (not persisted) ----------------------
    _activation_score: float = 0.0

    def touch(self) -> None:
        """Record an access: increment count and update timestamp."""
        self.access_count += 1
        self.last_used = time.monotonic()
        self.updated_at = time.time()

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        return {
            "skill_id": self.skill_id,
            "domain": self.domain,
            "name": self.name,
            "description": self.description,
            "selectors": self.selectors,
            "actions": self.actions,
            "quirks": self.quirks,
            "wait_strategy": self.wait_strategy,
            "preferred_tier": self.preferred_tier,
            "url_patterns": self.url_patterns,
            "provenance": self.provenance.value,
            "status": self.status.value,
            "access_count": self.access_count,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DomainSkill:
        """Deserialize from dict (handles enum strings)."""
        data = dict(data)  # copy
        data["provenance"] = SkillProvenance(data["provenance"])
        data["status"] = SkillStatus(data.get("status", "active"))
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    def size_bytes(self) -> int:
        """Approximate size in bytes when serialized to JSON."""
        import json
        return len(json.dumps(self.to_dict()).encode("utf-8"))

    def matches_url(self, url: str) -> bool:
        """Check if this skill applies to the given URL."""
        from fnmatch import fnmatch
        if not self.url_patterns:
            return True  # no patterns = applies to all URLs on this domain
        return any(fnmatch(url, pattern) for pattern in self.url_patterns)


# ---------------------------------------------------------------------------
# ACT-R Activation Scoring (Novel Work)
# ---------------------------------------------------------------------------

@dataclass
class ActivationConfig:
    """Configuration for ACT-R activation scoring."""
    decay_factor: float = 0.5               # Decay per hour since last use (0.0-1.0)
    activation_threshold: float = 1.0       # Minimum score to be "hot" (loaded into memory)
    base_level_weight: float = 1.0          # Weight for log(access_count + 1)
    recency_weight: float = 1.0             # Weight for decay_factor ^ hours
    context_weight: float = 0.5             # Weight for semantic similarity
    stale_penalty: float = -2.0             # Penalty for stale skills
    max_context_boost: float = 2.0          # Cap on semantic similarity contribution


def compute_activation(
    skill: DomainSkill,
    current_task: str = "",
    config: ActivationConfig = ActivationConfig(),
    *,
    similarity_fn: Optional[callable] = None,
) -> float:
    """
    Compute ACT-R activation score for a skill.

    Novel work: No reference project implements decay-based skill relevance scoring.

    Formula:
        activation = base_level + context_boost + recency_bonus

    Where:
        base_level    = log(access_count + 1)
        recency_bonus = decay_factor ^ hours_since_last_use
        context_boost = semantic_similarity(current_task, skill_description)
                        * context_weight, capped at max_context_boost

    Stale skills receive a flat penalty (stale_penalty).
    Skills with access_count == 0 get base_level = 0.0 (log(1) = 0).

    Args:
        skill: The domain skill to score.
        current_task: Natural language description of the current task.
        config: Activation scoring parameters.
        similarity_fn: Optional function(text_a, text_b) -> float [0.0-1.0].
                       If None, context_boost is 0.0.

    Returns:
        Float activation score. Skills above config.activation_threshold
        are loaded into "hot" memory.
    """
    # Base level: log-transformed access frequency
    base_level = config.base_level_weight * math.log(skill.access_count + 1)

    # Recency bonus: exponential decay since last use
    if skill.last_used > 0:
        hours_since = (time.monotonic() - skill.last_used) / 3600.0
        recency_bonus = config.recency_weight * (config.decay_factor ** hours_since)
    else:
        recency_bonus = 0.0  # never used

    # Context boost: semantic similarity to current task
    context_boost = 0.0
    if current_task and similarity_fn and skill.description:
        similarity = similarity_fn(current_task, skill.description)
        context_boost = min(
            config.context_weight * similarity,
            config.max_context_boost,
        )

    # Stale penalty
    stale_penalty = config.stale_penalty if skill.status == SkillStatus.STALE else 0.0

    activation = base_level + recency_bonus + context_boost + stale_penalty
    return activation


# ---------------------------------------------------------------------------
# Skill Registry
# ---------------------------------------------------------------------------

@dataclass
class SkillQuery:
    """Query parameters for skill search."""
    domain: Optional[str] = None
    provenance: Optional[SkillProvenance] = None
    status: Optional[SkillStatus] = None
    name_contains: Optional[str] = None
    min_access_count: int = 0


class SkillRegistry:
    """
    Domain skill registry with CRUD, auto-discovery, and ACT-R activation.

    Storage:
        ~/.super-browser/browser-skills/<domain>/<skill_id>.json
        ~/.super-browser/browser-skills/_archived/<domain>/<skill_id>.json

    Usage:
        registry = SkillRegistry()
        await registry.load_domain("github.com")

        # Auto-discover skills for current URL
        skills = await registry.auto_discover("https://github.com/login")

        # Get hot skills (above activation threshold)
        hot = registry.hot_skills("github.com")

        # Learn from successful trajectory
        await registry.learn_from_trajectory(
            domain="github.com",
            task_description="Login to GitHub",
            actions_taken=["fill #login_field", "fill #password", "click input[type=submit]"],
            selectors_used={"#login_field": "SELECTOR", "#password": "SELECTOR"},
        )
    """

    SKILLS_DIR = Path.home() / ".super-browser" / "browser-skills"
    ARCHIVED_DIR = Path.home() / ".super-browser" / "browser-skills" / "_archived"
    MAX_SKILL_SIZE_BYTES = 15 * 1024  # 15 KB

    def __init__(
        self,
        activation_config: Optional[ActivationConfig] = None,
        skills_dir: Optional[Path] = None,
    ) -> None:
        self._config = activation_config or ActivationConfig()
        self._skills_dir = skills_dir or self.SKILLS_DIR
        self._archived_dir = self._skills_dir / "_archived"

        # In-memory index: domain -> {skill_id -> DomainSkill}
        self._index: dict[str, dict[str, DomainSkill]] = {}

        # Hot cache: domain -> sorted list of (activation_score, DomainSkill)
        self._hot_cache: dict[str, list[tuple[float, DomainSkill]]] = {}

        # Loaded domains set (tracks which domains have been loaded from disk)
        self._loaded_domains: set[str] = set()

    # -- CRUD -----------------------------------------------------------------

    async def register(self, skill: DomainSkill) -> DomainSkill:
        """
        Register a new domain skill.

        Validates skill format and size. Assigns a skill_id if not provided.
        Persists to disk asynchronously.

        Raises:
            SkillSizeExceeded: if skill exceeds MAX_SKILL_SIZE_BYTES.
            InvalidSkillFormat: if required fields are missing or invalid.
        """
        ...

    async def get(self, domain: str, skill_id: str) -> Optional[DomainSkill]:
        """
        Retrieve a specific skill by domain and skill_id.

        Returns None if not found. Does not load the domain automatically.
        """
        ...

    async def update(self, domain: str, skill_id: str, **updates) -> DomainSkill:
        """
        Update fields on an existing skill.

        Accepts keyword arguments matching DomainSkill fields.
        Increments updated_at. Re-persists to disk.

        Raises:
            KeyError: if skill not found.
        """
        ...

    async def delete(self, domain: str, skill_id: str) -> bool:
        """
        Delete a skill from the registry and disk.

        Returns True if deleted, False if not found.
        """
        ...

    async def list_by_domain(self, domain: str, *, include_archived: bool = False) -> list[DomainSkill]:
        """
        List all skills for a domain.

        Args:
            domain: Hostname to list skills for.
            include_archived: If True, include archived skills.

        Returns:
            List of DomainSkill objects.
        """
        ...

    async def search(self, query: SkillQuery) -> list[DomainSkill]:
        """
        Search skills by multiple criteria.

        Supports filtering by domain, provenance, status, name substring,
        and minimum access count.
        """
        ...

    # -- Auto-Discovery -------------------------------------------------------

    async def auto_discover(
        self,
        url: str,
        current_task: str = "",
        *,
        similarity_fn: Optional[callable] = None,
    ) -> list[DomainSkill]:
        """
        Auto-discover skills matching a URL.

        1. Extract hostname from URL.
        2. Load domain skills from disk if not already loaded.
        3. Filter by hostname match (exact or wildcard subdomain).
        4. Filter by url_patterns if present.
        5. Compute ACT-R activation scores.
        6. Return skills above activation threshold, sorted by score descending.
        7. Touch each returned skill (increment access_count, update last_used).

        This is the primary entry point called by the Super Browser facade
        after navigate().
        """
        ...

    # -- Hot Skills ------------------------------------------------------------

    def hot_skills(self, domain: str) -> list[DomainSkill]:
        """
        Return skills above activation threshold for a domain.

        Uses the in-memory hot cache (populated by auto_discover or
        compute_activation). No disk I/O.

        Returns skills sorted by descending activation score.
        """
        ...

    def compute_and_cache_activations(
        self,
        domain: str,
        current_task: str = "",
        *,
        similarity_fn: Optional[callable] = None,
    ) -> list[tuple[float, DomainSkill]]:
        """
        Compute activation scores for all skills in a domain and update
        the hot cache.

        Returns all (score, skill) tuples sorted by descending score.
        """
        ...

    # -- Learning --------------------------------------------------------------

    async def learn_from_trajectory(
        self,
        domain: str,
        task_description: str,
        actions_taken: list[str],
        selectors_used: dict[str, str],
        *,
        preferred_tier: Optional[dict[str, str]] = None,
    ) -> DomainSkill:
        """
        Generate a skill from a successful task trajectory.

        Extracts stable selectors from the action sequence, builds a
        DomainSkill with provenance=LEARNED, and registers it.

        Args:
            domain: Hostname the task was performed on.
            task_description: What the agent was trying to accomplish.
            actions_taken: Ordered list of actions performed.
            selectors_used: Map of selector -> tier that worked.
            preferred_tier: Optional tier preferences from GAP-02 cache.

        Returns:
            The newly created DomainSkill.
        """
        ...

    # -- Import ----------------------------------------------------------------

    async def import_markdown(self, directory: Path) -> int:
        """
        Import browser-harness markdown domain skills.

        Parses the directory structure where each subdirectory is a domain
        and contains .md files with site-specific knowledge.

        Each markdown file is parsed into a DomainSkill with:
          - domain = directory name
          - name = filename stem
          - provenance = DISCOVERED
          - selectors, quirks, wait_strategy extracted from structured sections

        Returns the number of skills imported.
        """
        ...

    # -- Persistence -----------------------------------------------------------

    async def _persist_skill(self, skill: DomainSkill) -> None:
        """
        Write a single skill to disk as JSON.
        Atomic write: write to temp file, then os.replace().
        File: ~/.super-browser/browser-skills/<domain>/<skill_id>.json
        """
        ...

    async def load_domain(self, domain: str) -> int:
        """
        Load all skills for a domain from disk into the in-memory index.

        Returns the number of skills loaded.
        No error if directory does not exist -- starts with empty index.
        """
        ...

    # -- Archival --------------------------------------------------------------

    async def archive_stale_skills(self, domain: str, *, max_age_days: int = 30, min_access_count: int = 10) -> int:
        """
        Archive skills that are stale and haven't been used recently.

        A skill is archived if:
          - status == STALE
          - access_count >= min_access_count
          - last_used > max_age_days days ago

        Archived skills are moved to _archived/<domain>/ but NOT deleted.
        They can be restored via update(status=ACTIVE).
        """
        ...

    # -- Validation ------------------------------------------------------------

    async def validate_skill(self, skill: DomainSkill) -> list[str]:
        """
        Validate a skill against the current page DOM.

        Checks each selector in skill.selectors to see if it exists.
        Returns a list of warnings (empty if all selectors are valid).
        Does NOT modify the skill -- caller decides whether to mark stale.
        """
        ...


# ---------------------------------------------------------------------------
# Error Hierarchy
# ---------------------------------------------------------------------------

class SkillImportError(Exception):
    """Base error for skill import/registration failures."""
    pass


class InvalidSkillFormat(SkillImportError):
    """Skill JSON is malformed or missing required fields."""
    pass


class SelectorConflictWarning(SkillImportError):
    """A selector in the new skill conflicts with an existing skill."""
    pass


class SkillSizeExceeded(SkillImportError):
    """Skill exceeds the maximum allowed size (15 KB)."""
    pass
```

### Storage Schema

```json
{
  "version": 1,
  "skill_id": "github-login-a1b2c3d4",
  "domain": "github.com",
  "name": "login",
  "description": "Standard GitHub login flow via username/password form",
  "selectors": {
    "username_input": "#login_field",
    "password_input": "#password",
    "submit_button": "input[type='submit']",
    "error_message": ".flash-error"
  },
  "actions": {
    "login": {
      "steps": [
        "fill username_input with username",
        "fill password_input with password",
        "click submit_button",
        "assert not_visible error_message"
      ]
    }
  },
  "quirks": [
    "GitHub adds __ prefixes to dynamically generated IDs -- avoid selecting by ID alone",
    "Login form may be inside a nested container after SSO redirect"
  ],
  "wait_strategy": {
    "after_navigate": {"selector": ".js-login-form", "timeout": 5000},
    "after_submit": {"selector": ".dashboard", "timeout": 10000}
  },
  "preferred_tier": {
    "input[type='*']": "SELECTOR",
    "button.*": "COORDINATE"
  },
  "url_patterns": [
    "https://github.com/login*",
    "https://github.com/session"
  ],
  "provenance": "learned",
  "status": "active",
  "access_count": 47,
  "last_used": 1745326800.123456,
  "created_at": 1744000000.0,
  "updated_at": 1745326800.123456
}
```

---

## 5. Data Flow

```
                        Agent / SuperBrowser Facade
                                   |
                          navigate("https://github.com/login")
                                   |
                         +---------+----------+
                         |   Navigation       |
                         |   completes        |
                         +---------+----------+
                                   |
                         auto_discover("https://github.com/login")
                                   |
                         +---------+----------+
                         |  SkillRegistry     |
                         |                    |
                         | 1. Extract hostname|
                         |    "github.com"    |
                         |                    |
                         | 2. Load domain     |
                         |    from disk if    |
                         |    not cached      |
                         |    (lazy load)     |
                         +---------+----------+
                                   |
                         +---------+----------+
                         |  Hostname matching  |
                         |                     |
                         |  Exact match:       |
                         |  "github.com"       |
                         |    -> github.com/*  |
                         |                     |
                         |  Wildcard match:    |
                         |  "*.github.com"     |
                         |    -> gist.github.  |
                         |       com           |
                         +---------+-----------+
                                   |
                         +---------+----------+
                         | URL pattern filter  |
                         |                     |
                         | Skill has patterns? |
                         |   Yes: fnmatch(url) |
                         |   No: match all     |
                         +---------+----------+
                                   |
                         +---------+----------+
                         | ACT-R Activation    |
                         | Scoring             |
                         |                     |
                         | For each candidate: |
                         |                     |
                         | base = log(N+1)     |
                         | recency = d^hours   |
                         | context = sim()*w   |
                         |                     |
                         | score = base +      |
                         |   recency + context |
                         +---------+----------+
                                   |
                    +--------------+--------------+
                    |                             |
              score >= threshold           score < threshold
              (default: 1.0)                     |
                    |                             v
                    |                     Remains on disk
                    v                     NOT loaded to memory
           +--------+--------+
           | Hot Skills List  |
           | (in-memory)      |
           | Sorted by score  |
           +--------+--------+
                    |
           touch() each skill
           (access_count++, last_used=now)
                    |
           Async persist
           updated stats
                    |
                    v
           +--------+--------+----------+
           | Inject into Agent Context   |
           |                             |
           | System prompt augmentation: |
           | "Domain skills for          |
           |  github.com:                |
           |  - login (score: 3.72)      |
           |    selectors: {...}         |
           |    quirks: [...]            |
           |  - create_issue (score: 1.2)|
           |    selectors: {...}         |
           +-----------------------------+


    Skill Learning Flow (after successful task):

    Agent completes task on github.com
                |
                v
    learn_from_trajectory(
      domain="github.com",
      task="Login to GitHub",
      actions=["fill #login_field", ...],
      selectors={"#login_field": "SELECTOR", ...},
      preferred_tier={"input[type='*']": "SELECTOR"}
    )
                |
                v
    +-----------+-----------+
    | Extract selectors     |
    | that succeeded        |
    | (from selectors_used) |
    +-----------+-----------+
                |
                v
    +-----------+-----------+
    | Build DomainSkill     |
    | skill_id = uuid4()    |
    | provenance = LEARNED  |
    | domain = "github.com" |
    | name = task slug      |
    +-----------+-----------+
                |
                v
    +-----------+-----------+
    | Validate & Register   |
    | - Size < 15KB         |
    | - Required fields OK  |
    | - No format errors    |
    +-----------+-----------+
                |
                v
    Atomic write to:
    ~/.super-browser/browser-skills/
      github.com/
        <skill_id>.json
                |
                v
    Update in-memory index
    for domain "github.com"


    Markdown Import Flow:

    browser-harness/domain-skills/
      amazon.com/
        shopping.md
        checkout.md
      github.com/
        login.md
        issues.md
      reddit.com/
        browse.md
      ... (67 domains)
                |
                v
    import_markdown(directory)
                |
                v
    For each .md file:
      Parse structured sections
      Extract selectors, quirks, waits
      DomainSkill(provenance=DISCOVERED)
                |
                v
    register() -> persist to JSON
                |
                v
    67 domains, ~120 skills imported
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| GAP-02: `MultimodalController` | Spec complete | `TierPreferenceCache` entries populate skill `preferred_tier`; `ActionResult.meta.method` records which tier worked, used by `learn_from_trajectory()` |
| GAP-02: `TierPreferenceCache` | Spec complete | Tier preference data is the primary source for skill tier hints; skills store preferred tiers per selector pattern |
| GAP-12: `ActionResult` | Spec complete | Structured action results provide the selector/tier data that `learn_from_trajectory()` mines |
| Python | >= 3.11 | `math.log`, `time.monotonic`, `dataclass`, `enum`, `pathlib` |
| `fnmatch` | stdlib | URL pattern matching for skill applicability filtering |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| GAP-11: Tracing subsystem | Log skill operations (load, register, activation score) for observability | Skill operations proceed without tracing |
| Semantic similarity function | `context_boost` in ACT-R scoring requires a text similarity function | `context_boost` defaults to 0.0; scoring degrades to `base_level + recency_bonus` only |
| `sentence-transformers` or embedding API | Compute semantic similarity between current task and skill description for context_boost | Simple keyword overlap as fallback similarity_fn |
| GAP-01: `BrowserSession` | Skill selector validation requires page DOM access via CDP | Validation skipped (all selectors assumed valid) |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-05 |
|-----|--------------------------|
| GAP-04 (Self-Healing & Session Recovery) | Skill selectors as fallback candidates when primary selectors break; skill quirks inform recovery strategy selection |
| GAP-07 (Agent Orchestration & Facade) | Skill-aware action dispatch -- facade injects domain skills into agent context after navigate(); `learn_from_trajectory()` called by facade after successful task completion |
| GAP-09 (Token Budget & Cost Control) | Skills reduce exploration cost by providing pre-validated selectors, avoiding expensive Tier 3 vision calls on known domains |

---

## 7. Acceptance Criteria

### AC1: DomainSkill Dataclass Matches Roadmap Definition
The `DomainSkill` dataclass must include all fields specified in the roadmap Phase 4 definition: `skill_id` (str), `domain` (str), `name` (str), `selectors` (dict), `actions` (dict), `provenance` (str/enum), `access_count` (int, default 0), `last_used` (float, default 0.0). Additional fields (`description`, `quirks`, `wait_strategy`, `preferred_tier`, `url_patterns`, `status`, `created_at`, `updated_at`, `version`) must be present with correct types and defaults.

### AC2: SkillRegistry CRUD Operations
Calling `registry.register(skill)` must persist the skill to `~/.super-browser/browser-skills/<domain>/<skill_id>.json` as valid JSON. Calling `registry.get(domain, skill_id)` must return the same `DomainSkill` (field-equivalent). Calling `registry.update(domain, skill_id, name="new_name")` must mutate the persisted skill. Calling `registry.delete(domain, skill_id)` must remove both the in-memory entry and the JSON file. Calling `registry.get(domain, skill_id)` after delete must return `None`.

### AC3: Auto-Discovery on Navigate
After navigating to `https://github.com/login`, calling `registry.auto_discover("https://github.com/login")` must: (1) extract hostname `github.com`, (2) load skills for that domain if not already loaded, (3) return skills matching the hostname, (4) filter by `url_patterns` if present, (5) compute activation scores, (6) return skills above threshold sorted by descending activation score, (7) increment `access_count` and update `last_used` for each returned skill.

### AC4: ACT-R Activation Scoring
Given a skill with `access_count=9` and `last_used=0.5 hours ago` with `decay_factor=0.5`, the activation score must equal `log(10) * 1.0 + 0.5^0.5 * 1.0 = 2.302 + 0.707 = 3.009` (approximately). A skill with `access_count=0` and `last_used=0` must score `0.0` (base_level=0, recency=0, no context). A stale skill must have `stale_penalty` (-2.0 by default) applied.

### AC5: Hot Skills Threshold
Calling `registry.hot_skills("github.com")` must return only skills with activation score >= `config.activation_threshold` (default 1.0). A skill with `access_count=0` (score ~0) must not appear in hot skills. A skill with `access_count=10` used recently (score ~2.3+) must appear in hot skills. The list must be sorted by descending activation score.

### AC6: Learn from Trajectory
Calling `registry.learn_from_trajectory(domain="github.com", task_description="Login to GitHub", actions_taken=["fill #login_field", "click input[type=submit]"], selectors_used={"#login_field": "SELECTOR", "input[type=submit]": "SELECTOR"})` must create a new `DomainSkill` with `provenance=LEARNED`, extract the selectors from `selectors_used`, generate a skill name from the task description, assign a UUID as `skill_id`, and persist the JSON file. The skill must be immediately retrievable via `registry.get()`.

### AC7: Markdown Import from browser-harness
Calling `registry.import_markdown(path_to_domain_skills_dir)` with the browser-harness `domain-skills/` directory must parse all 67 domain subdirectories, create `DomainSkill` objects with `provenance=DISCOVERED` for each `.md` file, and persist them as JSON. The method must return the count of imported skills (at least 67, one per domain directory). Each imported skill must have the correct domain extracted from the directory name.

### AC8: Skill Validation Against DOM
After registering a skill with selector `"#nonexistent-element"`, calling `registry.validate_skill(skill)` on a page where that selector does not exist must return a list containing a warning string that mentions the invalid selector. Calling `validate_skill()` with all valid selectors must return an empty list. The skill's `status` must not be modified by `validate_skill()` alone -- the caller decides.

### AC9: Stale Skill Archival
Given a skill with `status=STALE`, `access_count=15`, and `last_used=45 days ago`, calling `registry.archive_stale_skills(domain, max_age_days=30, min_access_count=10)` must move the skill's JSON file from `browser-skills/<domain>/` to `browser-skills/_archived/<domain>/`. The skill must be removed from the in-memory index. Calling `registry.get(domain, skill_id)` must return `None`. The archived file must still exist on disk and be restorable.

### AC10: Atomic File Writes
If the process crashes mid-write during `registry.register()`, no partial or corrupt JSON file must exist at the target path. The write must use a temp file in the same directory followed by `os.replace()` (atomic on the same filesystem). After a crash and restart, `registry.load_domain()` must succeed without JSON parse errors.

### AC11: Skill Size Limit
Registering a skill whose JSON serialization exceeds 15 KB must raise `SkillSizeExceeded` without creating any file. Registering a skill exactly at 15 KB must succeed. The error message must include the actual size and the maximum allowed size.

### AC12: Wildcard Subdomain Matching
A skill registered with domain `*.github.com` must be returned by `auto_discover("https://gist.github.com/some-gist")` (subdomain match). A skill registered with domain `github.com` must NOT match `gist.github.com` (exact match only). A skill registered with domain `*.github.com` must also match `github.com` itself (bare domain).

### Test Scenarios

| ID  | Scenario | Steps | Expected Outcome | AC |
|-----|----------|-------|------------------|----|
| T1  | Register and retrieve a skill | `register(skill)`, then `get(domain, skill_id)` | Retrieved skill matches registered skill field-for-field | AC1, AC2 |
| T2  | Update skill fields | `register(skill)`, `update(domain, skill_id, name="new")`, `get()` | Name updated, `updated_at` incremented | AC2 |
| T3  | Delete skill | `register(skill)`, `delete(domain, skill_id)`, `get()` | Returns `None`, JSON file removed | AC2 |
| T4  | Auto-discover by hostname | Register 3 skills for `github.com`, call `auto_discover("https://github.com/login")` | Returns matching skills sorted by activation score, each touched | AC3 |
| T5  | Auto-discover with URL pattern filter | Skill with `url_patterns=["https://github.com/login*"]`, discover `https://github.com/login` vs `https://github.com/repo` | Returns skill for `/login`, excludes for `/repo` | AC3 |
| T6  | Activation score: high access + recent use | Skill with `access_count=99`, `last_used=0.1h ago` | Score >= 4.6 (log(100) + ~0.93) | AC4 |
| T7  | Activation score: never used | Skill with `access_count=0`, `last_used=0` | Score == 0.0 | AC4 |
| T8  | Activation score: stale penalty | Skill with `status=STALE`, `access_count=10` | Score = log(11) - 2.0 = ~0.4 (below threshold) | AC4 |
| T9  | Hot skills filtering | Register 5 skills with varying access counts, call `hot_skills()` | Only skills with score >= 1.0 returned, sorted descending | AC5 |
| T10 | Learn from trajectory | Call `learn_from_trajectory()` with selectors and actions | New skill created with `provenance=LEARNED`, selectors populated, persisted | AC6 |
| T11 | Markdown import | Call `import_markdown()` on browser-harness `domain-skills/` | >= 67 skills imported, each with correct domain and `provenance=DISCOVERED` | AC7 |
| T12 | Validate selectors against DOM | Register skill with invalid selector, call `validate_skill()` | Returns list with warning for invalid selector | AC8 |
| T13 | Archive stale skills | Create stale skill with high access count and old `last_used`, call `archive_stale_skills()` | Skill moved to `_archived/`, removed from index | AC9 |
| T14 | Restore archived skill | After T13, call `update(archived_domain, skill_id, status=ACTIVE)` | Skill restored to active directory and index | AC9 |
| T15 | Atomic write crash recovery | Register skill, simulate crash (delete temp file exists), restart, `load_domain()` | No corrupt files, `load_domain()` succeeds | AC10 |
| T16 | Skill size limit exceeded | Create skill with 20 KB JSON, call `register()` | Raises `SkillSizeExceeded`, no file created | AC11 |
| T17 | Wildcard subdomain match | Register skill for `*.github.com`, auto-discover `https://gist.github.com/test` | Skill returned (subdomain match) | AC12 |
| T18 | Exact domain match excludes subdomains | Register skill for `github.com`, auto-discover `https://gist.github.com/test` | Skill NOT returned (exact match only) | AC12 |
| T19 | Tier preference propagation | `learn_from_trajectory()` with `preferred_tier={"button.*": "COORDINATE"}` | Skill has `preferred_tier` populated, usable by MultimodalController | AC6 |
| T20 | Search by provenance | Register 5 skills (3 LEARNED, 2 DISCOVERED), `search(SkillQuery(provenance=LEARNED))` | Returns exactly 3 skills with `provenance=LEARNED` | AC2 |

---

## 8. Novel Work

**ACT-R Activation Scoring for Domain Skills**

No reference project implements decay-based skill relevance scoring. The five source projects provide skill storage (browser-harness), domain gating (browser-use), CRUD management (Hermes), plugin architecture (OpenClaw), and evolution (Hermes Self-Evolution), but none addresses the problem of skill lifecycle management with relevance decay. As skill libraries grow (browser-harness already has 67 domains), loading all skills for every navigation wastes context space. A principled activation model solves this.

Design:

1. **Activation Formula**:
   ```
   activation = base_level + recency_bonus + context_boost
   ```
   where:
   - `base_level = log(access_count + 1)` -- logarithmic frequency scaling prevents popular skills from dominating linearly
   - `recency_bonus = decay_factor ^ hours_since_last_use` -- exponential decay ensures skills unused for weeks gradually fade; with `decay_factor=0.5`, a skill unused for 10 hours has recency = 0.001, effectively zero
   - `context_boost = min(semantic_similarity(task, description) * context_weight, max_context_boost)` -- optional semantic relevance to the current task; capped to prevent similarity from overwhelming frequency and recency signals

2. **Threshold-Based Hot/Cold Split**: Skills above `activation_threshold` (default 1.0) are loaded into "hot" memory (injected into agent context). Skills below threshold remain on disk and are not loaded. This bounds the context cost of domain skills regardless of registry size.

3. **Stale Penalty**: Skills whose selectors no longer validate receive a flat `stale_penalty` (-2.0), pushing them below threshold. They are not deleted -- they can be restored if selectors become valid again after a site redesign.

4. **Archival Without Deletion**: Skills that are stale AND rarely used AND old are moved to `_archived/` but never deleted. The design principle is that learned knowledge should not be destroyed -- a skill that was useful once may become useful again if a site reverts a redesign.

5. **Decay Factor Calibration**: The default `decay_factor=0.5` means:
   - 1 hour since last use: recency = 0.5
   - 6 hours: recency = 0.016
   - 24 hours: recency ~ 0.0000001
   This ensures skills used within the current session remain hot, while skills from yesterday require higher access counts to stay above threshold. A skill used 100 times has `base_level = log(101) = 4.62`, which stays above threshold even with zero recency. A skill used 2 times has `base_level = log(3) = 1.10`, which drops below threshold after ~1 hour of inactivity.

---

## 9. Adoption Timeline

| Week | Deliverable | Source Pattern |
|------|-------------|----------------|
| 3 | `DomainSkill` dataclass with all fields matching roadmap definition | P1, P5 |
| 3 | `SkillRegistry` with CRUD operations and JSON persistence | P4, P5 |
| 3 | `import_markdown()` for browser-harness 67 domain skill files | P1 |
| 3 | `auto_discover()` with hostname matching and URL pattern filtering | P2, P3 |
| 4 | `learn_from_trajectory()` for agent-generated skill creation | P7, P8 |
| 4 | Skill validation against current page DOM (selector checking) | P9 |
| 4 | Stale skill detection and archival | P9 |
| 7 | ACT-R activation scoring with `compute_activation()` | Novel |
| 7 | Hot/cold skill split with activation threshold | Novel |
| 7 | `context_boost` via semantic similarity integration | Novel |
| 8 | `SkillRegistry` integration with Super Browser facade (auto-discover on navigate) | P2 |
| 8 | Tier preference propagation from GAP-02 `TierPreferenceCache` into skills | P2 |
| 8 | End-to-end test: navigate -> auto-discover -> inject skills -> learn -> verify | All |
| 11 | OpenClaw-style plugin slot architecture for skill extensibility | P5 |
| 12 | Hermes Self-Evolution GEPA-based skill optimization pipeline | P6 |
