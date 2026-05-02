# Intrinsic Value Scoring Rubric

## Purpose

Scoring happens during Pass 1 (gap-blind analysis). Every subsystem cataloged gets scored on its own merits BEFORE any gap mapping occurs. This prevents the tunnel vision problem where valuable patterns are underweighted because no known gap asks for them.

## Scoring Dimensions

Four dimensions, each scored 1-5. The scale is deliberately small to reduce scoring ambiguity — the analyst distinguishes "3 or 4?" not "37 or 42?"

### D1: Production Grade (weight: 0.30)

How production-ready is this subsystem?

| Score | Criteria |
|-------|----------|
| 1 | Prototype/demo only, no error handling |
| 2 | Research proof-of-concept, handles happy path |
| 3 | Functional with basic error handling |
| 4 | Production with error handling, tests, and logging |
| 5 | Production with monitoring, fallbacks, documented edge cases, and load testing |

**Why highest weight**: Adoptable patterns must be production-viable. A brilliant architecture that breaks under load is less valuable than a solid implementation of a standard approach.

### D2: Novelty (weight: 0.20)

How different is this from the common approach seen across reference projects?

| Score | Criteria |
|-------|----------|
| 1 | Standard implementation (same as 5+ other projects) |
| 2 | Minor variation on a standard approach |
| 3 | Meaningful variation with different tradeoffs |
| 4 | Novel approach not seen elsewhere in the corpus |
| 5 | Unique architecture with no close equivalent |

**Why lowest weight**: A standard-but-excellent implementation (e.g., khoj's two-stage retrieval) is often more valuable than a novel-but-immature one.

### D3: Composability (weight: 0.25)

How easily could this be extracted and integrated into a different project?

| Score | Criteria |
|-------|----------|
| 1 | Tightly coupled to its host, cannot be separated |
| 2 | Separable with significant refactoring (>1 week) |
| 3 | Moderately coupled, adapter layer needed (1-3 days) |
| 4 | Well-interfaced, drop-in with thin adapter (<1 day) |
| 5 | Standalone library or self-contained module with clear API |

**Why high weight**: The entire purpose of the analysis is to find adoptable patterns. Composability directly determines adoption feasibility.

### D4: Depth (weight: 0.25)

How complete is the implementation?

| Score | Criteria |
|-------|----------|
| 1 | Single file, <50 lines of logic |
| 2 | Single module, 50-200 lines |
| 3 | Multi-file module with clear structure |
| 4 | Multi-file system with tests and configuration |
| 5 | Full subsystem with API, storage, retrieval, lifecycle management, and documentation |

**Why high weight**: Depth indicates maturity and completeness. A shallow wrapper around an API is rarely worth adopting; a complete subsystem often is.

## Composite Score

```text
intrinsic_value = (D1 × 0.30) + (D2 × 0.20) + (D3 × 0.25) + (D4 × 0.25)
```

Range: 1.0 to 5.0

## Tier Classification

| Tier | Composite Range | Analysis Depth | Reading Budget |
|------|----------------|----------------|----------------|
| Tier 1 | ≥ 3.5 | Full subsystem analysis + code extraction | 15 files, 200 lines each |
| Tier 2 | 2.5 - 3.49 | Subsystem summary + notable patterns | 8 files, 150 lines each |
| Tier 3 | < 2.5 | Thin Project Disposition only | 3 files, 100 lines each |

## Usage in Pass 1

For each subsystem cataloged:

1. Score on all 4 dimensions
2. Compute composite
3. Record in Subsystem Inventory table
4. Rank subsystems by composite descending

The highest-tier subsystem in a project determines the project's overall reading budget.

## Usage in Triage

The highest intrinsic value across all subsystems determines the project's `Intrinsic Interest` axis:

| Highest Subsystem Tier | Intrinsic Interest |
|------------------------|--------------------|
| Tier 1 | High |
| Tier 2 | Medium |
| Tier 3 | Low |

This is independent of the `Gap Alignment` axis. A project with High intrinsic interest and no gap alignment still goes to "Analyze First."

## Usage in Pass 2

When mapping subsystems to gaps, the intrinsic value score accompanies each mapping:

- Tier 1 subsystem with Direct gap mapping → high-priority adoption candidate
- Tier 1 subsystem with No gap mapping → Unguided Finding (may become new gap)
- Tier 2 subsystem with Direct gap mapping → standard adoption candidate
- Tier 2 subsystem with No gap mapping → noted but not flagged as Unguided Finding
- Tier 3 subsystems → Thin Project Disposition

## Scoring Examples

### Example 1: Cherry Studio Provider Registry

- D1 (Production Grade): 5 — Singleton pattern, LRU caching, in-flight dedup, error wrapping
- D2 (Novelty): 4 — Multi-backend routing by model prefix, variant system
- D3 (Composability): 4 — Clean extension interface, but TypeScript/Electron-specific
- D4 (Depth): 5 — 24 providers, strategy chain for model discovery, health check system

Composite: (5×0.30) + (4×0.20) + (4×0.25) + (5×0.25) = 1.50 + 0.80 + 1.00 + 1.25 = **4.55** → Tier 1

### Example 2: A simple REST client wrapper

- D1: 3 — Basic error handling
- D2: 1 — Standard HTTP client pattern
- D3: 4 — Easy to extract
- D4: 2 — Single module

Composite: (3×0.30) + (1×0.20) + (4×0.25) + (2×0.25) = 0.90 + 0.20 + 1.00 + 0.50 = **2.60** → Tier 2
