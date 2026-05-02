# Quality Gates

## Purpose

Minimum quality requirements for analysis files. These gates prevent the quality inconsistency seen in v1 analyses, where files ranged from 1.1KB stubs to 23KB deep dives with no enforcement mechanism.

An analysis file that fails any mandatory gate is incomplete. Do not mark the project as analyzed in SESSION-STATE.md until all gates pass.

## Mandatory Gates (all must pass)

### Gate 1: Minimum Depth

The analysis file (excluding metadata header) must meet size thresholds:

| Project Tier | Minimum Size | Rationale |
|-------------|-------------|-----------|
| Tier 1 (highest subsystem ≥3.5) | ≥ 8KB | Tier 1 projects have multiple sophisticated subsystems that require detailed analysis |
| Tier 2 (highest subsystem 2.5-3.49) | ≥ 5KB | Tier 2 projects have notable patterns worth documenting |
| Tier 3 (highest subsystem <2.5) | ≥ 3KB | Even thin projects need a structured disposition |

**Exception**: Projects that are genuinely thin wrappers (no source files, or only config/manifest files) may be shorter but must include a Thin Project Disposition section explaining what was checked and why it was insufficient.

### Gate 2: Subsystem Inventory Completeness

The Subsystem Inventory table must cover the project's actual subsystems:

| Source File Count | Minimum Subsystem Entries |
|------------------|--------------------------|
| > 50 files | ≥ 5 entries |
| 20-50 files | ≥ 3 entries |
| < 20 files | ≥ 1 entry |

Every Tier 1 subsystem must have all 4 scoring dimensions filled. Zero-score entries are forbidden — if a subsystem is worth cataloging, it deserves at least a 1 in each dimension.

### Gate 3: Evidence Standard

Adoption recommendations must be backed by evidence:

| Metric | Threshold |
|--------|-----------|
| "Verified in code" adoption entries | ≥ 60% of total |
| "Could not verify" entries | ≤ 20% of total |

If the "Could not verify" threshold is exceeded, re-read the relevant source files before finalizing the analysis. If source files are inaccessible, note this explicitly.

### Gate 4: Unguided Findings

- Every Tier 1 project analysis must include a `## Unguided Findings` section
- If no unguided findings exist, the section must state: "All Tier 1 subsystems map to known gaps" — do not omit the section
- Expected: at least 1 unguided finding per Tier 1 project unless the project is narrow in scope (justified in the section)

### Gate 5: Pillar Coverage

- The Pillar Coverage table must list all active pillars from the domain pack
- No pillar may have empty Key Files if Coverage is not "○ None"
- Coverage values must use controlled vocabulary from 03-OUTPUT-CONTRACT.md
- Discovered pillars (from domain discovery) must also appear in the table

### Gate 6: Gap-Aware Mapping

- Every Tier 1 subsystem must have a gap mapping annotation in the Subsystem Inventory
- Subsystems with no gap mapping must appear in Unguided Findings
- The mapping must be specific: "Gap #3" not "a memory gap"
- Tier 2 subsystems should have gap mapping where applicable

## Validation Procedure

Before marking an analysis file as complete:

1. Check file size against Gate 1 thresholds
2. Count Subsystem Inventory entries against Gate 2
3. Count evidence labels against Gate 3
4. Verify Unguided Findings section exists for Tier 1 projects (Gate 4)
5. Verify Pillar Coverage table completeness (Gate 5)
6. Verify Tier 1 subsystems have gap annotations (Gate 6)
7. Record pass/fail in the analysis file metadata header: `Quality Gate Status: PASS` or `Quality Gate Status: FAIL — [list failed gates]`

## Consequences of Failure

If any gate fails:

1. Do NOT mark the project as analyzed in SESSION-STATE.md
2. Expand the analysis until it passes
3. If context is insufficient to pass all gates, write handoff notes in SESSION-STATE.md specifying which gates failed and what additional reading is needed
4. The next session must complete the failing gates before moving to new projects

## Gate Application by Phase

| Gate | Applied In |
|------|-----------|
| Gate 1 (Depth) | Phase 2B completion |
| Gate 2 (Inventory) | Phase 2A completion |
| Gate 3 (Evidence) | Phase 2B completion |
| Gate 4 (Unguided) | Phase 2B completion |
| Gate 5 (Pillars) | Phase 2B completion |
| Gate 6 (Mapping) | Phase 2B completion |

All gates are re-verified before marking the project complete in SESSION-STATE.md.
