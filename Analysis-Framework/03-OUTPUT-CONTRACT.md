# Output Format Contract

Formatting rules for all generated output files. Violating any rule produces an invalid report.

## Section A: Format Rules

### Structural Rules

1. **One top-level heading per file.** Each analysis file starts with `# [ProjectName]`. No exceptions.
2. **Mandatory sections appear in order.** Each file type has required sections in a fixed sequence. Optional sections may be omitted but cannot be reordered.
3. **No empty sections.** If a section has no content, omit it entirely. Never write `## Notable Code\n\nNone found.`
4. **Markdown only.** No HTML tags. No LaTeX. No raw JSON outside fenced code blocks.

### Table Rules

5. **Every table has a header row and a separator row.** Format: `| Col1 | Col2 |` newline `|------|------|`.
6. **Pipe-aligned columns.** Every row has the same number of `|` separators.
7. **No merged cells, no colspan.** One value per cell. Use comma-separated lists inside a cell if needed.
8. **Controlled vocabulary for enumerated columns:**
   - Coverage: `● Full` | `◐ Partial` | `○ None` — always symbol + word
   - Depth: `Production` | `Research` | `Concept`
   - Quality: `Production-ready` | `Needs adaptation` | `Proof-of-concept`
   - Effort: `Low` | `Medium` | `High`
   - Severity: `Blocker` | `Critical` | `Important`
   - Evidence: `Verified in code` | `Verified in manifest/config` | `Inferred from structure` | `Could not verify`
   - Verification Status: `Not Required` | `Required` | `Metadata Refreshed` | `Partially Re-checked` | `Fully Re-analyzed` | `Verified Current`
   - Canonical Status: `Canonical` | `Related` | `Standalone`
   - Project Status: `Implemented` | `Spec'd` | `Gap` | `Better than [Project]`
   - Gap State: `Confirmed` | `Partially Addressed` | `Resolved` | `Evolved` | `Discovered`
   - Subsystem Tier: `Tier 1` | `Tier 2` | `Tier 3`
   - Pillar Schema Status: `Current` | `Stale — requires migration` | `Stale — reviewed, still valid`

### Code Block Rules

9. **Every code block has a language tag.** Use ```typescript, ```python, ```sql, etc.
10. **Code snippets include file path and line numbers as a comment on line 1.** Format: `// path/to/file.ts:42-58` or `# path/to/file.py:42-58`.
11. **No pseudocode.** Only extract real, runnable code from source files.

### Cross-Reference Rules

12. **File paths are always relative to the project root.** Prefix with the project directory name: `NagaAgent/src/memory/store.py`.
13. **Project file paths are relative to the project root.** Example: `services/context/contextSchema.ts`, not `c:\Next AI\MyProject\services\context\contextSchema.ts`.

### Prose Rules

14. **Bullet lists use `-` (hyphen), not `*` (asterisk).**
15. **Bold for field labels in structured prose.** `**Pattern**: Name` not `Pattern: Name`.
16. **No hedging language.** Replace "might be useful" with a concrete assessment. Replace "seems to" with "does" or "does not." If uncertain, state the uncertainty explicitly.

## Section B: Per-File Templates

### File 1: `00-SOURCE-INVENTORY.md`

```markdown
# Source Inventory — [Project Name] Analysis

| # | Source ID | Directory | Language | Manifests | Source Present | Content Hash | Dedup Group | Canonical Status | Status | Notes |
|---|-----------|-----------|----------|-----------|----------------|--------------|-------------|------------------|--------|-------|
| 1 | SRC-001 | project-name | TypeScript | `package.json` | Yes | `git:abc1234` | DG-001 | Canonical | Included | Monorepo root |
| 2 | SRC-002 | mirror-project | Python | `pyproject.toml` | Yes | `sha256:def567...` | DG-001 | Related | Excluded | Duplicate mirror |
| 3 | SRC-003 | docs-only | Unknown | — | No | — | — | Standalone | Excluded | No source files |

Total sources: N
Included: N
Excluded: N
```

### File 2: `01-TRIAGE-QUEUE.md`

```markdown
# Triage Queue — [Project Name] Analysis

| # | Source ID | Directory | Gap Alignment | Intrinsic Interest | Queue | Verification Status | Dedup Group | Canonical Status | Language | Theme | Batch | Reason |
|---|-----------|-----------|---------------|-------------------|-------|---------------------|-------------|------------------|----------|-------|-------|--------|
| 1 | SRC-001 | project-name | Direct | High | Analyze First | Required | DG-001 | Canonical | TypeScript | Memory + Reasoning | 2A | Direct hit for semantic retrieval gap |
| 2 | SRC-004 | project-two | None | High | Analyze First | Not Required | — | Standalone | Python | Provider Registry | 2E | Sophisticated architecture despite no gap match |
| 3 | SRC-005 | project-three | None | Low | Archive | Not Required | — | Standalone | Rust | Tooling | — | Thin wrapper, no novel patterns |

Analyze First: N
Analyze Later: N
Archive: N
```

Note the dual-axis classification: Gap Alignment and Intrinsic Interest are independent. High intrinsic interest promotes to Analyze First regardless of gap alignment.

### File 3: `{ProjectName}-ANALYSIS.md`

```markdown
# [Project Name]

> One-line description
> Source ID: [stable source ID]
> Language: [primary language]
> Scale: [LOC estimate or file count]
> Last Verified: [YYYY-MM-DD]
> Verification Status: [controlled vocabulary]
> Domain Pack: [name and version]
> Pillar Schema Version: [version]
> Analysis Version: v2 (two-pass)
> Quality Gate Status: [PASS / FAIL — list failed gates]

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | [name] | [generic category] | `path/to/file` | 1-5 | 1-5 | 1-5 | 1-5 | [computed] | 1/2/3 | [Gap #N / Partial #N / No mapping] |
| 2 | ... | ... | ... | ... | ... | ... | ... | ... | ... | ... |

Tier 1 count: N | Tier 2 count: N | Tier 3 count: N

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | [Project] Status |
|--------|----------|-------|-----------|-----------------|
| 1. [Pillar Name] | [controlled vocab] | [controlled vocab] | `path/` | [controlled vocab] |
| ... | ... | ... | ... | ... |

## What to Adopt

For each pattern worth adopting:
- **Pattern**: [name]
- **Subsystem**: [# from Subsystem Inventory]
- **Intrinsic score**: [composite from scoring rubric]
- **Source file**: `exact/path/to/file.ext` (line XX-YY)
- **Evidence**: [controlled vocabulary]
- **What it does**: [1-2 sentences]
- **Integration target**: Which file/service receives this
- **Overlap**: What the target project already has and why this is better
- **Quality**: [controlled vocabulary]
- **Effort**: [controlled vocabulary]

## Unguided Findings

High-value subsystems (Tier 1) that do NOT map to any known gap.

### [Subsystem Name] (composite: X.XX)

- **What it does**: [description]
- **Why it matters**: [why this is valuable independent of gaps]
- **Architecture**: [how it works]
- **Key files**: `path/to/file`
- **Adoption feasibility**: [assessment]

If no unguided findings: "All Tier 1 subsystems map to known gaps."

## Notable Code

```typescript
// path/to/file.ts:42-58
[exact code snippet]
```

## Thin Project Disposition

For projects with no Tier 1 subsystems:
- **Highest subsystem tier**: [2 or 3]
- **Highest composite score**: [value]
- **What was checked**: [directories and files examined]
- **Why it is thin**: [specific reason]
- **Revisit condition**: [what would make this worth re-analyzing]
```

### File 4: `CROSS-PROJECT-SYNTHESIS.md`

```markdown
# Cross-Project Synthesis

## Pillar Mutations

Record any pillar additions, removals, or splits.

## Pattern Frequency

| Pattern | Pillar | Projects | Best Implementation | [Project] Status |
|---------|--------|----------|-------------------|------------------|
| [pattern] | [pillar] | N of M | [Project] (detail) | [status] |

## Unique Capabilities

Patterns found in only ONE project.

## Recommended Adoption

| Priority | Pattern | Pillar | Source(s) | Integration Target | Effort | Rationale |
|----------|---------|--------|-----------|-------------------|--------|-----------|
| 1 | [pattern] | [pillar] | [projects] | [file/path] | [effort] | [why] |

## Anti-patterns

What NOT to do, with examples.

## Negative Findings

| Pattern | Pillar | Projects Checked | Depth of Search | Conclusion |
|---------|--------|-----------------|-----------------|------------|
| [pattern] | [pillar] | N of M | [depth] | [conclusion] |

## Unguided Findings Aggregation

Patterns appearing as Unguided Findings across multiple projects. Those meeting the 3-project threshold are proposed as new gaps.

| Pattern | Projects | Tier | Threshold Met? | Proposed Gap? |
|---------|----------|------|----------------|---------------|
| [pattern] | N | 1 | Yes/No | Yes/No |

## Validation Targets

Projects that would serve as E2E test references.
```

### File 5: `GAP-INVENTORY.md`

```markdown
# Gap Inventory — [Project Name]

For each gap:
- **Gap**: [name]
- **Pillar**: [which pillar]
- **State**: [Confirmed / Partially Addressed / Resolved / Evolved / Discovered]
- **Severity**: Blocker / Critical / Important
- **What exists**: [closest implementation in reference projects AND target project]
- **What's missing**: [exactly what needs to be built]
- **Impact**: [what can't work without this]
- **Evidence**: [file paths and source projects]
- **Build vs. Adopt**: [can we adopt, or must we build?]
- **Dependencies**: [Blocks/Enables/Overlaps/Conflicts — which other gaps]

## Cross-Gap Dependencies

| From Gap | To Gap | Type | Rationale |
|----------|--------|------|-----------|
| #N | #M | Blocks/Enables/Overlaps/Conflicts | [why] |
```

### File 6: `IMPLEMENTATION-ROADMAP.md`

```markdown
# Implementation Roadmap — [Project Name]

## Adoption Order

| Priority | Gap / Capability | State | Source(s) | Evidence | Target Area | Effort | Dependency |
|----------|------------------|-------|-----------|----------|-------------|--------|------------|
| 1 | [name] | [state] | [projects] | Verified in code | `path/` | [effort] | None |
| 2 | [name] | [state] | [projects] | Verified in code | `path/` | [effort] | 1 |

## Work Packages

- **Work Package**: [name]
- **Goal**: [what this delivers]
- **Inputs**: [which synthesis findings or analyses feed it]
- **Target files/services**: [where the work lands]
- **Risk**: [main risk]
- **Validation**: [how success will be tested]

## Sequencing Notes

Why the build order is what it is.

## Deferred Adoptions

Patterns worth keeping on the backlog.
```

## Format Validation Checklist

Before writing each file:

- [ ] Exactly one `#` heading
- [ ] All mandatory sections present
- [ ] All tables pipe-aligned with matching column counts
- [ ] All enumerated columns use controlled vocabulary
- [ ] All code blocks have language tags and file-path comments
- [ ] No HTML, no LaTeX, no callout syntax
- [ ] All file paths are relative
- [ ] No hedging language
- [ ] Quality gates checked (07-QUALITY-GATES.md)
