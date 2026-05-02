# Analysis Framework v2 — Architecture Summary

> **IMPORTANT**: This file describes the analysis framework itself, NOT any target project. Never use it as a source of facts about a project being analyzed.

## Purpose

A domain-agnostic analysis operating system for studying software codebases and turning them into verified, deduplicated implementation guidance for a specific target project. Works for any domain — AI agents, GIS, e-commerce, or anything else.

## Core Components

| File | Role |
|------|------|
| `01-ANALYSIS-PROMPT.md` | Orchestration — methodology, phases, two-pass protocol |
| `02-GENERIC-TAXONOMY.md` | 10 universal analysis categories |
| `03-OUTPUT-CONTRACT.md` | Formatting rules and per-file templates |
| `04-SESSION-STATE-SPEC.md` | Multi-session handover protocol |
| `05-PROJECT-CONFIG-TEMPLATE.md` | Blank template for new target projects |
| `06-SCORING-RUBRIC.md` | Intrinsic value scoring (4 dimensions, 1-5 scale) |
| `07-QUALITY-GATES.md` | Minimum depth requirements (6 gates) |
| `08-GAP-MODEL.md` | Gap lifecycle (5 states), dependencies (4 types) |
| `09-ARCHITECTURE-SUMMARY.md` | This file |
| `domains/ai-agents.md` | AI agent domain pack (14 pillars) |

## Key Design Decisions

### 1. Two-Pass Analysis (Gap-Blind → Gap-Aware)

Pass 1 catalogs every subsystem and scores intrinsic value WITHOUT reading the gap list. Pass 2 maps findings to gaps. This prevents the tunnel vision problem where valuable patterns are missed because no known gap asks for them.

### 2. Domain-Agnostic Architecture

The framework ships with a generic taxonomy (10 categories) applicable to any software. Domain-specific pillar sets live in separate domain pack files (`domains/`). A domain discovery step in Phase -1 selects or creates the right pillar set.

### 3. Intrinsic Value Scoring

Every subsystem scored on 4 dimensions: Production Grade (30%), Novelty (20%), Composability (25%), Depth (25%). Tier classification (1/2/3) determines analysis depth. This ensures valuable patterns surface regardless of gap alignment.

### 4. Quality Gates

6 mandatory quality gates enforce minimum analysis depth, evidence standards, and completeness. Analysis files that fail any gate are not marked complete.

### 5. Gap Lifecycle

Gaps have 5 states (Confirmed → Partially Addressed → Resolved, plus Evolved and Discovered). Cross-gap dependencies (Blocks, Enables, Overlaps, Conflicts) model implementation ordering.

### 6. Output Separation

Framework files are read-only. All outputs go to a project-specific output directory. The framework never writes to itself.

## Execution Flow

```text
Phase -1: Config Validation + Domain Discovery
  → Verify PROJECT-CONFIG.md against source tree
  → Walk source tree, map to generic taxonomy
  → Select/create domain pack
  → Certify config

Phase 0: Source Inventory
  → Enumerate all reference sources
  → Assign stable Source IDs and content hashes

Phase 1: Triage (dual-axis)
  → Classify each source on Gap Alignment AND Intrinsic Interest
  → High intrinsic interest → Analyze First regardless of gap alignment

Phase 2A: Gap-Blind Deep Read
  → Catalog subsystems, score intrinsic value
  → NO gap list consulted

Phase 2B: Gap-Aware Mapping
  → Map subsystems to pillars/gaps
  → Unguided Findings for high-value subsystems with no gap mapping
  → Apply quality gates

Phase 3: Cross-Project Synthesis
  → Pattern frequency, unique capabilities, recommended adoption
  → Aggregate unguided findings across corpus

Phase 4: Gap Reconciliation
  → Finalize gap states, dependency graph
  → Propose new gaps from unguided findings meeting 3-project threshold

Phase 5: Pillar Evolution
  → Review unguided findings, evolve domain pack
  → Propose new pillars for recurring unmapped patterns
```

## Comparison with v1

| Aspect | v1 | v2 |
|--------|----|----|
| Analysis flow | Gap-first (top-down) | Gap-blind first, gap-aware second (bottom-up) |
| Pillar source | Hardcoded 12 pillars | Generic taxonomy + configurable domain packs |
| Pillar count | Fixed at 12 | Variable per domain (AI agents: 14) |
| Infrastructure coverage | Single catch-all pillar | Split into Plugin, Runtime, Provider Management |
| Gap states | Binary (confirmed/not) | 5 states with lifecycle |
| Cross-gap dependencies | None modeled | 4 dependency types |
| Quality enforcement | None | 6 mandatory gates |
| Unguided findings | Blind spot scan (optional) | Structural part of every Tier 1 analysis |
| Pillar mutation threshold | `ceil(N*0.15)` = 46 (never fires) | `ceil(N*0.05)` = 16 |
| Domain applicability | AI agents only | Any domain via taxonomy + domain packs |
| Output separation | Mixed with framework | Framework is read-only, outputs separate |

## Limitations

- Requires a validated PROJECT-CONFIG.md before analysis can proceed
- Domain discovery is heuristic-based (directory/file naming patterns) — may misclassify unfamiliar architectures
- Quality gates enforce minimum depth but cannot enforce analytical insight
- The two-pass approach increases per-project analysis time compared to v1's single pass
