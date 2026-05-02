# SKYLL (SRC-054) -- Reference Analysis for SUPER-BROWSER

**Project**: skyll-main
**Theme**: Skill learning patterns
**Location**: `C:\Next AI\ref\skyll-main`
**Version**: 0.1.1 (Beta)
**License**: Apache-2.0
**Stack**: Python 3.10+, FastAPI, httpx, Pydantic v2, FastMCP

---

## 1. Project Summary

Skyll is a REST API and MCP server that lets any AI agent search for and learn agent skills (SKILL.md files) at runtime. It aggregates skills from multiple sources (skills.sh marketplace, local curated registry), fetches full SKILL.md content from GitHub, and returns structured JSON ready for context injection. The project ships a lightweight async Python client (`skyll` package) and a self-hostable server with both REST and MCP interfaces.

**Core value proposition**: Agents discover and inject skills on-demand without pre-installation, removing a key friction point in agent skill usage.

---

## 2. Directory Structure

```
skyll-main/
  skyll/                  # Lightweight pip-installable client library
    __init__.py
    client.py             # Async httpx client (Skyll class)
    models.py             # Pydantic models for client (Skill, SearchResponse)
  src/                    # Server implementation
    api/routes.py         # FastAPI REST endpoints
    cache/
      base.py             # Abstract CacheBackend (ABC)
      memory.py           # InMemoryCache implementation
    clients/
      github.py           # GitHub API client for fetching SKILL.md + references
      skillssh.py         # skills.sh API client wrapper
    core/
      models.py           # Server-side Pydantic models (Skill, SearchRequest, SearchResponse, etc.)
      parser.py           # SKILL.md frontmatter parser (YAML)
      service.py          # SkillSearchService -- main orchestrator
    main.py               # FastAPI app entry point
    mcp_server.py         # MCP server (FastMCP) -- 4 tools
    ranking/
      base.py             # Abstract Ranker (ABC)
      hybrid.py           # HybridRanker (placeholder for future)
      relevance.py        # RelevanceRanker -- 6-signal scoring (content quality, structure, refs, metadata, query match, popularity)
      semantic.py         # Semantic ranker (placeholder)
    sources/
      base.py             # SkillSource Protocol (async context manager + search)
      registry.py         # Local SKILLS.md registry source
      skillssh.py         # skills.sh marketplace source
  registry/
    SKILLS.md             # Community-curated skill list
  skills/
    skyll/SKILL.md        # Skyll's own agent skill definition
  tests/                  # Test suite
  docs/                   # API, architecture, ranking, sources, references docs
  web/                    # Demo UI + landing page
```

---

## 3. Subsystem Catalog

### S1: Skill Discovery Service (`src/core/service.py`)
- Central orchestrator: coordinates sources, caching, parsing, ranking, deduplication
- DI-friendly: all components (cache, ranker, sources) are pluggable via constructor
- Async context manager lifecycle
- Over-fetches from sources (2x limit) for better ranking pool

### S2: Multi-Source Architecture (`src/sources/`)
- `SkillSource` Protocol: defines `search()`, `refresh()`, async context manager
- Two implementations: `SkillsShSource` (live API), `SkillRegistrySource` (local Markdown)
- Deduplication across sources using `unique_key` (owner/repo + skill_id)
- Preference rules: skills.sh results prioritized (have install counts)

### S3: Ranking Engine (`src/ranking/`)
- `RelevanceRanker`: 6-signal weighted scoring totaling 100 points:
  - Content Quality (30 pts): length-based grading (100-2000+ char range)
  - Content Structure (5 pts): headers, code blocks, tables, lists
  - References Depth (10 pts): graded by count (1-6+)
  - Metadata Completeness (5 pts): description, version, allowed_tools
  - Query Match (30 pts): multi-field whole-word matching (ID > title > desc > content)
  - Popularity (20 pts): log-scaled install count (ceiling 50k)
  - Curated Registry Boost: up to 5 extra points for registry skills
- `HybridRanker`: placeholder for future embedding-based semantic ranking
- Extensible: `Ranker` ABC with `rank()` method

### S4: GitHub Content Fetcher (`src/clients/github.py`)
- Fetches SKILL.md and reference files from GitHub repos
- Repo tree caching with TTL (1h success, 5min failure)
- Fuzzy skill path resolution: handles naming conventions (prefix stripping, suffix matching, contains matching)
- Reference file discovery: sibling .md files + subdirectories (references/, resources/, docs/, examples/, rules/)
- Cache invalidation + retry on stale cache
- Fallback direct URL patterns

### S5: Cache Backend (`src/cache/`)
- Abstract `CacheBackend`: get, set, delete, exists, clear, stats
- `InMemoryCache`: default implementation with TTL
- Designed for extension to Redis, SQLite

### S6: MCP Server (`src/mcp_server.py`)
- 4 tools: `search_skills`, `add_skill`, `get_skill`, `get_cache_stats`
- Hosted mode (api.skyll.app/mcp) and self-hosted (stdio/sse/http)
- Rich system prompt with usage guidance
- Dual-mode: mounted (shared service) and standalone (lifespan-managed)
- Input validation with length limits

### S7: REST API (`src/api/routes.py`)
- FastAPI endpoints: GET /search, GET /skills/{source}/{skill_id}, GET /health
- Full OpenAPI docs at /docs

### S8: Python Client (`skyll/client.py`)
- Async context manager with httpx
- `search()`, `get()`, `health()` methods
- Minimal dependencies: httpx + pydantic only

---

## 4. Dimensional Scoring

| Dimension | Score | Rationale |
|-----------|-------|-----------|
| **D1: Production Grade** (0.30) | **3/10** | Clean code, typed, async, but MVP status. HybridRanker and semantic ranking are placeholders. No auth, no rate limiting on own API, no persistence beyond in-memory cache. Single-developer project at beta stage. |
| **D2: Novelty** (0.20) | **4/10** | The "runtime skill discovery for agents" concept is genuinely useful. The multi-signal ranking with log-scaled popularity is competent. The fuzzy skill path resolution is a nice touch. But the core is an API wrapper + search aggregator -- no novel algorithms or architectures. |
| **D3: Composability** (0.25) | **7/10** | Strong DI design: CacheBackend, Ranker, SkillSource are all pluggable protocols/ABCs. Clean separation of concerns across layers. MCP + REST dual interface is well-done. The client library is properly standalone. The Protocol-based source abstraction is a good pattern for SUPER-BROWSER's domain skill registry. |
| **D4: Depth** (0.25) | **3/10** | Each subsystem is well-structured but shallow. The ranking engine is the deepest piece at ~260 lines. The cache is trivial (in-memory dict). No embeddings, no vector search, no learning from usage. The GitHub client handles one specific content format (SKILL.md). |

**Weighted Score: 4.25/10**

---

## 5. SUPER-BROWSER Gap Mapping

| Gap | Relevance | Patterns to Extract |
|-----|-----------|-------------------|
| **G1: Browser Session & CDP** | None | Skyll has no browser automation. |
| **G2: Three-Tier Interaction** | None | No interaction engine. |
| **G3: Visual Verification** | None | No visual/screenshot capabilities. |
| **G4: Self-Healing & Recovery** | Low | Cache invalidation + retry pattern in GitHub client is a minor analog. |
| **G5: Domain Skill Registry** | **HIGH** | This is Skyll's core. The `SkillSource` Protocol + multi-source aggregation + deduplication + relevance ranking directly maps to SUPER-BROWSER's domain skill registry. The ranking engine's multi-signal scoring is a strong pattern. |
| **G6: Vision-Based Location** | None | No vision/canvas capabilities. |
| **G7: Agent Orchestration** | Low | The service orchestrator pattern (sources + cache + parser + ranker) is a lightweight DI pattern useful for SUPER-BROWSER's facade. |
| **G8: Stealth & Anti-Bot** | None | No stealth measures. |
| **G9: Token Budget & Cost** | None | No token tracking or cost control. |
| **G10: Security Envelope** | Low | Input validation in MCP server (length limits). GitHub token handling. Minimal. |
| **G11: Tracing & Observability** | Low | Cache stats endpoint. Structured logging. No distributed tracing. |
| **G12: Structured Action Results** | Medium | Pydantic models (Skill, SearchResponse, ErrorResponse) are a good pattern for structured results, but not action-oriented. |

---

## 6. Key Patterns Worth Extracting

### P1: Protocol-Based Source Abstraction
```python
class SkillSource(Protocol):
    name: str
    enabled: bool
    async def search(query, limit) -> list[SkillSearchResult]: ...
    async def refresh() -> None: ...
```
Maps directly to SUPER-BROWSER's domain skill registry: define a `DomainSkillSource` protocol for per-domain skill providers.

### P2: Multi-Signal Weighted Ranking
The RelevanceRanker's 6-signal scoring with normalized weights is a clean pattern for ranking domain skills by applicability. SUPER-BROWSER could use a similar approach to rank which skill set applies to the current page/domain.

### P3: Fuzzy Path Resolution with Cache Invalidation
The GitHub client's multi-strategy path finding (direct match, prefix stripping, suffix matching, contains matching) + cache invalidation + retry is a good pattern for SUPER-BROWSER's element location fallback chain.

### P4: MCP Tool Registration with Rich Prompts
The MCP server's tool registration pattern with detailed docstrings and system prompts is directly applicable to SUPER-BROWSER's tool surface.

---

## 7. Thin Project Disposition

Skyll is a **thin project** relative to SUPER-BROWSER's scope. It is a well-architected but narrow skill-discovery API with clean composability patterns (Protocol-based sources, pluggable rankers, cache backends). Its direct relevance is confined to **Gap 5 (Domain Skill Registry)**, where its multi-source aggregation, deduplication, and multi-signal ranking patterns are genuinely useful. For all other gaps (browser automation, vision, stealth, orchestration, etc.), Skyll provides no applicable patterns. Extract the Protocol-based source abstraction, the ranking engine design, and the MCP integration pattern. The rest of the project is not relevant to SUPER-BROWSER.
