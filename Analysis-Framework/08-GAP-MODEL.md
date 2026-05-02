# Gap Model

## Gap States

Gaps progress through a lifecycle as analysis reveals solutions.

| State | Meaning | Indicator |
|-------|---------|-----------|
| Confirmed | Gap verified, no reference project addresses it | No Tier 1/2 subsystem maps to this gap across entire corpus |
| Partially Addressed | At least one reference project has a partial solution | One or more Tier 1/2 subsystems address some requirements |
| Resolved | A complete adoptable solution exists | Tier 1 subsystem(s) fully cover the gap's requirements |
| Evolved | The gap's scope has changed | Analysis revealed the original scope was too narrow or too broad |
| Discovered | New gap found during analysis | Unguided finding pattern appears in ≥3 projects |

## State Transitions

```text
Confirmed ──→ Partially Addressed ──→ Resolved
    │                  │
    └──→ Evolved ←─────┘
              ↑
Discovered ──→ Confirmed (after source-tree verification)
```

### Transition Triggers

**Confirmed → Partially Addressed**: Pass 2 analysis finds a reference project with a partial implementation that covers some but not all of the gap's requirements. Must cite: specific source project, file path, what it covers, what it misses.

**Confirmed/Partially Addressed → Resolved**: Analysis finds a complete, adoptable implementation. May be composed from multiple reference projects. Must cite: which projects, which subsystems, how they compose to fully address the gap.

**Any → Evolved**: Analysis reveals the gap's scope was wrong. Either too narrow (missed a dimension) or too broad (conflated two separate concerns). Must cite: what evidence revealed the scope error, what the new scope should be.

**Discovered → Confirmed**: A new gap proposed from unguided findings passes source-tree verification against the target project (same grounding as Phase -1 gap verification).

## Cross-Gap Dependencies

### Dependency Types

| Type | Meaning | Example |
|------|---------|---------|
| Blocks | Gap A must be resolved before Gap B can be addressed | Plugin system (A) blocks tool use (B) |
| Enables | Resolving Gap A makes Gap B easier or more valuable | Hybrid retrieval (A) enables RAG pipeline (B) |
| Overlaps | Gaps share solution space; resolving one may partially resolve the other | Cross-agent memory (A) overlaps multi-agent coordination (B) |
| Conflicts | Resolving Gap A one way may make Gap B harder | Sandboxing (A) may conflict with plugin architecture (B) |

### Dependency Table Format

| From Gap | To Gap | Type | Rationale |
|----------|--------|------|-----------|
| #2 | #19 | Blocks | Plugin system required before tools can be loaded |
| #15 | #3 | Enables | Hybrid retrieval is prerequisite for RAG |

### Usage

- **Implementation roadmap**: Blocks dependencies must be resolved first. Enables dependencies inform ordering.
- **Risk assessment**: Circular Blocks dependencies between two gaps are a red flag — the gaps may need to be merged or their scope revised.
- **Work package grouping**: Overlapping gaps should be analyzed together; conflicting gaps should be designed together.

## Gap Discovery from Unguided Findings

When Pass 1 catalogs a Tier 1 subsystem that does not map to any known gap:

1. Record in the Unguided Findings section of the analysis file
2. In Phase 3 synthesis, aggregate all Unguided Findings across the corpus
3. Check if the same pattern (same generic taxonomy category, similar implementation) appears in ≥3 projects
4. If yes, propose a new gap:
   - **Name**: descriptive, following existing naming conventions
   - **Pillar**: from the domain pack or a new pillar
   - **What exists**: the reference implementations found
   - **What's missing**: what the target project lacks in this area
   - **Severity**: Blocker / Critical / Important
5. In Phase 4, verify the new gap against the target project's source tree (same grounding as Phase -1)
6. If grounded, add to PROJECT-CONFIG.md with state `Discovered`

## Incremental Update Protocol

When adding new analyses after the pipeline completes:

1. Read existing GAP-INVENTORY.md
2. For each new analysis:
   - Check if any Tier 1 subsystem maps to an existing gap → may advance gap state
   - Check if any Unguided Finding matches an existing gap → may advance gap state
   - Check if any Unguided Finding creates a pattern meeting the 3-project threshold → propose new gap
3. Apply gap state transitions with evidence
4. Update cross-gap dependencies if new relationships emerge
5. Update IMPLEMENTATION-ROADMAP.md if adoption priorities change
6. Record in SESSION-STATE.md:
   - Timestamp of update
   - Which gaps changed state (from → to)
   - Any new gaps proposed
   - Any dependency changes
   - Whether roadmap priorities shifted

## Gap Entry Format

Each gap in GAP-INVENTORY.md:

```markdown
- **Gap**: [name]
- **Pillar**: [which pillar from domain pack]
- **State**: [Confirmed / Partially Addressed / Resolved / Evolved / Discovered]
- **Severity**: Blocker / Critical / Important
- **What exists**: [closest partial implementation across reference projects AND in target project]
- **What's missing**: [exactly what needs to be built]
- **Impact**: [what can't work without this]
- **Evidence**: [file paths and source projects that address this gap]
- **Build vs. Adopt**: [can we adopt from a reference project, or must we build novel?]
- **Dependencies**: [Blocks/Enables/Overlaps/Conflicts — which other gaps]
```
