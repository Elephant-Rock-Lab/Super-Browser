# Session State Specification

## Purpose

Defines the multi-session handover protocol. Every session reads SESSION-STATE.md first and writes it last. SESSION-STATE.md lives in the output directory, not the framework directory.

## SESSION-STATE.md Structure

### Header

```markdown
# Session State — [Project Name] Analysis
> Last Updated: [YYYY-MM-DD HH:MM]
> Current Phase: [phase number and name]
> Domain Pack: [name and version]
> Pillar Schema Version: [version]
```

### Inventory Coverage

```markdown
## Inventory Coverage
- Total sources: N
- Included: N
- Excluded: N
- Untriaged: N
- Previously analyzed: N
- Coverage status: Complete / In Progress
```

### Domain Discovery Results

```markdown
## Domain Discovery
- Domain pack selected: [name] (auto-selected / user-specified)
- Generic taxonomy coverage:
  | Category | Score | Has Pillar? |
  |----------|-------|-------------|
  | Data & Storage | High | Yes |
  | ... | ... | ... |
- Discovered pillars (proposed during Phase -1): [list or "None"]
- Pillar set version: [version]
```

### Progress

```markdown
## Progress

| Batch | Phase | Status | Session Date | Projects Analyzed | Notes |
|-------|-------|--------|-------------|-------------------|-------|
| 2A | 2A+2B | Complete | 2026-04-17 | 8 | All passed quality gates |
| 2B | 2A+2B | In Progress | 2026-04-18 | 3/6 | 3 remaining |
```

Track Phase 2A and Phase 2B per project. A project can be marked:
- `Not Started`
- `2A Complete` (subsystem inventory done, gap-blind)
- `2A+2B Complete` (full analysis done, quality gates passed)
- `2A Complete — 2B Pending` (ran out of context before Pass 2)

### Unguided Findings Backlog

```markdown
## Unguided Findings Backlog

| Pattern | Category | Projects Found | Highest Tier | Threshold Met? | Proposed Gap? |
|---------|----------|---------------|-------------|----------------|---------------|
| Provider Registry | Integration & Extension | 1 | Tier 1 | No | No |
| [pattern] | [category] | N | [tier] | Yes/No | Yes/No |
```

Accumulates across all batches. Patterns meeting the 3-project threshold are flagged for gap proposal in Phase 4.

### Cross-Batch Observations

```markdown
## Cross-Batch Observations

Observations from one batch relevant to future batches.

### Pattern Emergence
- [pattern]: appeared in N projects so far

### Pillar Coverage Deltas
- [pillar]: coverage improved/degraded in batch X

### Convergence/Divergence Signals
- [signal description]
```

### Confirmed Novel

```markdown
## Confirmed Novel
Patterns NOT found in any analyzed reference project:
- [pattern description]
```

### Gap State Tracking

```markdown
## Gap State Tracking

| Gap # | Name | State | Last Updated | Evidence |
|-------|------|-------|-------------|----------|
| 1 | [name] | Confirmed | 2026-04-17 | No reference project addresses this |
| 15 | [name] | Partially Addressed | 2026-04-18 | [project] has partial implementation |
```

### Synthesis Readiness

```markdown
## Synthesis Readiness
- Gap counts: Confirmed N, Partially Addressed N, Resolved N, Evolved N, Discovered N
- Adoption source counts: N projects contributed adoption recommendations
- Batch completion ratio: N/M batches complete
- Unguided findings threshold check: N patterns at ≥3 projects
```

### Pillar Mutations

```markdown
## Pillar Mutations
- Added: [Pillar Name] (reason, date)
- Dropped: [Pillar Name] (reason, date)
- Split: [Pillar] → [Pillar.1] + [Pillar.2] (reason, date)
```

### Deduplication Decisions

```markdown
## Deduplication Decisions
- DG-001: [canonical source] selected over [alternatives] because [reason]
```

### Next Session Instructions

```markdown
## Next Session Instructions
1. Start with batch [ID], phase [2A/2B]
2. Priority projects: [list Source IDs]
3. Specific files to re-read: [list]
4. Notes from previous session: [context]
```

### Incremental Updates

```markdown
## Incremental Updates

| Date | Trigger | Gaps Changed | New Gaps | Roadmap Changed? |
|------|---------|-------------|----------|-------------------|
| 2026-04-20 | CherryStudio analysis added | #2: Confirmed→Partially Addressed | None | No |
```

## Session Handoff Protocol

### Starting a Session

1. Read SESSION-STATE.md
2. Check Config Validation status (must be CERTIFIED)
3. Check inventory coverage
4. Check domain discovery results
5. Read dedup decisions
6. Find first In Progress or Pending batch
7. Read Next Session Instructions and Cross-Batch Observations
8. Begin analysis

### Ending a Session

1. Update all sections with current state
2. Update Progress table with batch status
3. Add Unguided Findings to backlog
4. Record any gap state changes
5. Write Post-Batch Structured Summary if a batch completed
6. Write specific Next Session Instructions
7. Persist SESSION-STATE.md before stopping

### Recovery from Interruption

1. Check batch status vs. existing analysis files
2. For each "In Progress" project: check if 2A or 2B completed
3. Repair incomplete analysis files
4. Reconcile inventory counts
5. Handle phantom sources (listed but not analyzed)

## Consistency Invariants

These must hold before resuming work:

1. **Source count invariant**: SESSION-STATE totals match inventory rows
2. **Triage coverage invariant**: every non-excluded entry in triage exactly once
3. **Batch completion invariant**: Complete batches have all analysis files
4. **Pillar schema invariant**: SESSION-STATE version matches domain pack
5. **Deduplication invariant**: every DG has a canonical source recorded
6. **Cross-reference invariant**: every Source ID in analysis files maps to inventory
7. **Subtotal arithmetic invariant**: claimed row counts match actual rows in triage
8. **Source ID uniqueness invariant**: no duplicate Source IDs in triage
9. **Dedup group grounding invariant**: every DG in triage exists in inventory
10. **Config validation invariant**: PROJECT-CONFIG.md must have CERTIFIED status
11. **Subsystem inventory invariant**: every Phase 2A-complete project has ≥3 subsystem entries (or Thin Project Disposition)
12. **Unguided findings invariant**: every Tier 1 project with Phase 2B complete has Unguided Findings section
13. **Quality gate invariant**: every Phase 2B-complete project has PASS status or explicit FAIL with failed gates listed
