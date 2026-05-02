# Project Configuration Template

> Copy this file to your output directory as `PROJECT-CONFIG.md` and fill in all sections.

## §A — Project Context

### What the Project Has

| Layer | Component | Implementation | Key Files | Verified |
|-------|-----------|----------------|-----------|----------|
| [Layer] | [Component] | [Description] | `path/to/file` | [Phase -1 fills] |

### Known Architectural Gaps

| # | Gap | Evidence of Absence | Verification | Gap State | Phase -1 Status |
|---|-----|---------------------|--------------|-----------|-----------------|
| 1 | [gap name] | [how verified] | [method] | Confirmed | [Phase -1 fills] |

### Domain Configuration

- **Domain pack**: [path to domain pack file, e.g., `domains/ai-agents.md`]
- **Domain selection method**: [auto-detected / user-specified]
- **Discovered pillars**: [list any pillars proposed during Phase -1 discovery]

### Cross-Gap Dependencies

| From Gap | To Gap | Type | Rationale |
|----------|--------|------|-----------|
| #N | #M | Blocks/Enables/Overlaps/Conflicts | [why] |

### Incremental Update Rules

- **Auto-advance gap states**: Yes/No — whether new analyses can advance gap states without re-running synthesis
- **Unguided findings threshold**: 3 projects — minimum before proposing new gaps
- **Roadmap sensitivity**: High/Medium — whether new analyses can reorder roadmap priorities

## §B — Pillar Targets

| Pillar | Target Components | Key Files |
|--------|-------------------|-----------|
| 1. [Pillar from domain pack] | [components] | `path/` |
| ... | ... | ... |

## §C — Output Configuration

- **`{framework_path}`**: [path to Analysis-Framework directory]
- **`{analysis_root}`**: [path where analysis outputs are written]
- **`{reference_dir}`**: [path to reference project sources]
- **`{project_root}`**: [path to target project source]
- **Domain pack**: [path relative to framework, e.g., `domains/ai-agents.md`]
- **Source ID format**: `SRC-001`
- **Deduplication rule**: [how to identify duplicates]
- **Key comparison question**: "Does the target project already have this, and if so, is this implementation better?"
- **Comparison dimensions**:

| Dimension | Weight | Description |
|-----------|--------|-------------|
| [name] | [1-5] | [what it measures] |

## §D — Batch Definitions

| Batch | Pillar Focus | Projects | Priority |
|-------|-------------|----------|----------|
| 2A | [pillars] | [from triage] | Highest |
| 2B | [pillars] | [from triage] | High |
| ... | ... | ... | ... |

## §E — Verification and Deduplication Rules

### Verification Thresholds

- **Metadata refresh only**: [what changed]
- **Partial re-check**: [what changed]
- **Full re-analysis**: [what changed]

### Deduplication Policy

- **Canonical source preference**: [rule]
- **Meaningful divergence rule**: [threshold]
- **Monorepo rule**: [criteria for subproject Source IDs]

## §F — Config Validation

> Auto-populated by Phase -1. Do not edit manually.

- **Validation date**: [YYYY-MM-DD]
- **Validator**: [Phase -1 session N]
- **Source-tree file count**: N files across N directories
- **Components verified**: N/N paths exist
- **Gaps confirmed**: N/N confirmed, N/N partially false
- **False positives found**: N
- **Domain pack selected**: [name] ([auto/user])
- **Discovered pillars**: [list or "None"]
- **SoT document used**: [path or "None found"]
- **Target architecture spec**: [path or "None found"]
- **Validation status**: [PENDING / CERTIFIED / FAILED]
