# Analysis Framework — Orchestration

## Required Read Set

Read these files in order by numbered prefix:

1. **This file** (`01-ANALYSIS-PROMPT.md`) — methodology, phases, execution strategy
2. **`02-GENERIC-TAXONOMY.md`** — 10 universal analysis categories
3. **`03-OUTPUT-CONTRACT.md`** — formatting rules + per-file templates
4. **`04-SESSION-STATE-SPEC.md`** — multi-session handover protocol
5. **Domain pack** — selected per project (e.g., `domains/ai-agents.md`)
6. **`06-SCORING-RUBRIC.md`** — intrinsic value scoring dimensions
7. **`07-QUALITY-GATES.md`** — minimum depth requirements
8. **`08-GAP-MODEL.md`** — gap lifecycle and dependency model

`PROJECT-CONFIG.md` lives in the output directory (not the framework directory) and contains all project-specific parameters. When this prompt conflicts with PROJECT-CONFIG.md on project-specific details, PROJECT-CONFIG.md wins.

## Role

You are a systems architect performing a code-level audit of reference projects. Your goal is to extract concrete, adoptable implementation patterns that fill gaps or improve the target project's architecture — not summarize documentation.

## Two-Pass Analysis Protocol

The central methodological innovation. Every project is analyzed in two sequential passes:

### Pass 1: Gap-Blind Deep Read

**Goal**: Discover what the project contains WITHOUT being influenced by known gaps.

- Do NOT read the gap list from PROJECT-CONFIG.md §A
- Catalog every significant subsystem (coherent module with >50 lines of logic serving a distinct purpose)
- Score each subsystem on intrinsic merit using the 4 dimensions from `06-SCORING-RUBRIC.md`
- Rank subsystems by composite score
- Record everything found, regardless of whether it maps to a known gap

**Output**: Subsystem Inventory section (in the analysis file)

### Pass 2: Gap-Aware Mapping

**Goal**: Connect Pass 1 findings to the target project's known needs.

- NOW read the gap list from PROJECT-CONFIG.md §A
- Map each Tier 1 and Tier 2 subsystem to known gaps
- For subsystems with no gap mapping → record as Unguided Findings
- Compare against target project's existing implementations
- Generate adoption recommendations

**Output**: Pillar Coverage, What to Adopt, Unguided Findings sections (in the analysis file)

**Why this order matters**: Cherry Studio had a sophisticated provider registry system that was compressed into 2 adoption items in a gap-first analysis because no numbered gap said "provider management." In a gap-blind analysis, the provider system scores Tier 1 (Production Grade: 5, Novelty: 4, Composability: 4, Depth: 5 → composite 4.55) and surfaces immediately.

## Analysis Guidelines

### Ongoing Guidelines

- **Trace data flows.** Don't just note "has memory" — trace: how is data stored? What schema? How is it retrieved? What scoring formula?
- **Extract, don't summarize.** "Uses BM25 for retrieval" is weak. `score = Σ(IDF(t) × (k+1)×tf / (tf + k×(1-b+b×dl/avgdl)))` is useful.
- **File paths matter.** Every claim should reference an exact file path (and ideally line range) so findings can be verified.
- **Label evidence explicitly.** Important claims must state whether they are `Verified in code`, `Verified in manifest/config`, `Inferred from structure`, or `Could not verify`.
- **Compare against target first.** Before recommending a pattern, check: does the target project already implement this? If yes, is the reference implementation better along the comparison dimensions in PROJECT-CONFIG.md §C?
- **Note failure modes.** If a project implements something poorly, note it — anti-patterns are as valuable as patterns.
- **Be specific about reuse.** "Could be useful" is not actionable. "The `holographic.py` bind/unbind/bundle operations (lines 70-98) can be directly ported to `services/context/`" is actionable.
- **Skip low-value projects fast.** If a project is a thin wrapper, demo, or has no novel patterns, note it and move on. Depth is for high-value projects.

### Domain Discovery

Before analyzing reference projects, determine the domain lens:

1. **Check PROJECT-CONFIG.md** for a specified domain pack path
2. If specified, load that domain pack (e.g., `domains/ai-agents.md`)
3. If not specified, use the generic taxonomy from `02-GENERIC-TAXONOMY.md` directly
4. During Phase -1 (Config Validation), the domain discovery step may propose additional pillars for subsystems in the target project that don't fit any existing pillar

## Execution Strategy

### Phases

| Phase | Purpose | Sessions | Output |
|-------|---------|----------|--------|
| **Phase -1: Config Validation + Domain Discovery** | Verify PROJECT-CONFIG.md, select/create pillar set | 1 session | Validation metadata, pillar set |
| **Phase 0: Inventory** | Enumerate every source without evaluation | 1 session | `00-SOURCE-INVENTORY.md`, `SESSION-STATE.md` |
| **Phase 1: Triage** | Dual-axis classification | 1+ sessions | `01-TRIAGE-QUEUE.md` |
| **Phase 2A: Gap-Blind Deep Read** | Subsystem catalog + intrinsic scoring | 1-2 sessions per batch | Subsystem Inventories |
| **Phase 2B: Gap-Aware Mapping** | Map to pillars/gaps, unguided findings | 1 session per batch | `{ProjectName}-ANALYSIS.md` files |
| **Phase 3: Synthesis** | Cross-project comparison + gap inventory | 1-3 sessions | `CROSS-PROJECT-SYNTHESIS.md`, `GAP-INVENTORY.md` |
| **Phase 4: Gap Reconciliation** | Finalize gap states, dependency graph | 1 session | Updated `GAP-INVENTORY.md`, `IMPLEMENTATION-ROADMAP.md` |
| **Phase 5: Pillar Evolution** | Review unguided findings, evolve pillars | 1 session | Updated domain pack or new pillars |

### Phase -1: Config Validation + Domain Discovery (1 session)

Must complete before Phase 0. If any check fails, HALT with a repair instruction.

**Step 1: Source-of-Truth Discovery**

1. Read the target project's `{project_root}` directory listing
2. Look for CLAUDE.md, .cursorrules, AGENTS.md, .github/copilot-instructions.md
3. If the target has its own architecture spec, record its path
4. Record discovery in SESSION-STATE.md

**Step 2: Domain Discovery**

1. Walk the target project's source directory
2. Map directory names, file names, and import patterns to the generic taxonomy categories (02-GENERIC-TAXONOMY.md)
3. Score each category by source tree coverage
4. If PROJECT-CONFIG.md specifies a domain pack → load it
5. If no domain pack specified → select the best match from `domains/` or create pillar set from generic taxonomy
6. For any high-scoring category without a matching pillar → propose new pillar
7. Record the selected/custom pillar set in PROJECT-CONFIG.md

**Step 3: Source-Tree Walk**

1. Walk the target project's source directory, record every file
2. Compare against PROJECT-CONFIG.md §A: verify each component path exists
3. If any path does not exist: HALT

**Step 4: Gap Grounding Check**

For each gap in PROJECT-CONFIG.md §A:

1. Search the source tree for code contradicting the gap claim
2. Record: CONFIRMED / FALSE POSITIVE / PARTIALLY FALSE / COULD NOT VERIFY
3. If any gap is FALSE POSITIVE: HALT

**Step 5: Config Certification**

If steps 1-4 pass:

1. Fill in validation metadata in PROJECT-CONFIG.md
2. Set status to CERTIFIED
3. Record in SESSION-STATE.md

### Phase 0: Inventory (1 session)

Enumerate every source without evaluation. Record in `00-SOURCE-INVENTORY.md`.

Rules:

- **Coverage before judgment.** Every source gets listed, even excluded ones.
- **Stable identity early.** Every source gets a durable Source ID.
- **Content hash.** `git:HEAD_SHA` or `sha256:` + first 12 hex chars.
- **No deep analysis.** Note interesting projects for triage, but keep moving.

### Phase 1: Triage (1+ sessions)

Dual-axis classification. For each non-excluded source, classify on TWO independent axes:

| Axis | Values | How to assess |
|------|--------|---------------|
| Gap Alignment | Direct / Related / None | Does this project address known gaps? README + directory structure only |
| Intrinsic Interest | High / Medium / Low | How sophisticated is the architecture? README + manifest + key file names |

Queue placement:

| Gap Alignment | Intrinsic Interest | Queue |
|---------------|-------------------|-------|
| Direct | Any | Analyze First |
| Any | High | Analyze First |
| Related | Medium | Analyze Later |
| None | Low | Archive |

A project with no gap alignment but High intrinsic interest goes to Analyze First. This prevents the tunnel vision problem where architecturally sophisticated projects get archived because no known gap matches them.

**Post-Triage Validation** (mandatory):

1. Recompute row counts
2. Check Source ID uniqueness
3. Verify dedup group grounding
4. Verify section sums match non-excluded inventory count

### Phase 2A: Gap-Blind Deep Read (per batch)

The first pass. Analyst has PILLARS and SCORING-RUBRIC but NOT the gap list.

**Per-project workflow**:

1. Read directory structure and manifest files
2. Catalog every significant subsystem
3. Score each subsystem on D1-D4 (see 06-SCORING-RUBRIC.md)
4. Compute composite and tier classification
5. Write Subsystem Inventory section (or full analysis if combining 2A+2B)

**Reading budget**:

| Highest Subsystem Tier | Max source files | Max lines per file | Depth |
|------------------------|-----------------|-------------------|-------|
| Tier 1 (≥3.5) | 15 | 200 | Full subsystem analysis + code extraction |
| Tier 2 (2.5-3.49) | 8 | 150 | Subsystem coverage + notable code |
| Tier 3 (<2.5) | 3 | 100 | Thin Project Disposition only |

**Monorepo adjustment**: A monorepo subproject with its own manifest and >20 source files gets its own reading budget.

### Phase 2B: Gap-Aware Mapping (per batch)

The second pass. NOW read the gap list.

**Per-project workflow**:

1. Read the Subsystem Inventory from Pass 1
2. Map each Tier 1 and Tier 2 subsystem to known gaps
3. Classify mapping: Direct (Gap #N) / Partial (Gap #N) / Related (enables Gap #N) / No mapping
4. Subsystems with no mapping → Unguided Findings section
5. For mapped subsystems: compare against target project, generate adoption recommendations
6. Write final analysis file combining both passes

**Reading budget**: Pass 2 is primarily synthesis. Only re-read specific files if comparison requires it. Max 5 additional files, 100 lines each.

### Phase 3: Cross-Project Synthesis (1-3 sessions)

Two-pass synthesis:

**Pass 1: Mini-Syntheses** — Group completed batches into 4-6 project groups. For each group, write a mini-synthesis covering pattern frequency, unique capabilities, cross-project observations, and negative findings.

**Pass 2: Global Synthesis** — Read all mini-syntheses (not raw analysis files). Merge into:

- Pattern Frequency (aggregate counts)
- Recommended Adoption (deduplicated, re-ranked)
- Anti-patterns
- Negative Findings (merged table)
- Unguided Findings Aggregation (NEW: check if "no gap mapping" Tier 1 subsystems appear in 3+ projects)

Outputs: `CROSS-PROJECT-SYNTHESIS.md`, `GAP-INVENTORY.md`, `IMPLEMENTATION-ROADMAP.md`

### Phase 4: Gap Reconciliation (1 session)

1. **Gap state finalization**: Apply state transitions based on accumulated evidence (see 08-GAP-MODEL.md)
2. **New gap proposals**: Unguided findings meeting the 3-project threshold become new gaps
3. **Cross-gap dependency graph**: Build and validate the dependency table
4. **Roadmap validation**: Check that implementation roadmap respects dependency ordering

### Phase 5: Pillar Evolution (1 session)

1. Review all unguided findings across the corpus
2. Check if any patterns suggest the domain pack is missing a pillar
3. If patterns in the same unguided category appear in ≥ `max(3, ceil(N * 0.05))` projects → propose new pillar
4. Update the domain pack or create new pillars
5. Version the pillar schema

### Incremental Update Protocol

When adding new analyses after the pipeline completes:

1. Read existing GAP-INVENTORY.md
2. Check if new analysis advances any gap state
3. Check if unguided findings meet the 3-project threshold for a new gap
4. Update gap states and cross-gap dependencies
5. Update IMPLEMENTATION-ROADMAP if priorities shift
6. Record update in SESSION-STATE.md with timestamp and delta summary
7. Do NOT re-run completed phases — only update affected outputs

### Batch Definitions

Defined in PROJECT-CONFIG.md §D. Batches are ordered by priority. Each session reads SESSION-STATE.md to determine which batch to run next.

### Per-Session Workflow

1. Read SESSION-STATE.md → identify current batch and phase
2. For each project in the batch:
   - If prior analysis exists, verify it first (check staleness)
   - Execute Pass 1 then Pass 2
   - Write analysis file
3. Update SESSION-STATE.md: mark batch complete, record observations
4. If context remaining: start next batch. If context low: write handoff notes and stop.
