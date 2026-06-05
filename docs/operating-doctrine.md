# Operating Doctrine — Disk-Verified Large-Wave Execution

This document defines the planning and execution standard for the Super Browser project. All contributors — human or agent — must follow this doctrine when proposing or implementing changes.

## Canonical Principle

```text
Scale by wave.
Ground by disk.
Accept by tests.
Seal by evidence.
```

---

## 1. Large-Wave Execution

A **large wave** is a bounded delivery unit with one clear strategic objective. It may span multiple files, tests, artifacts, and documentation updates, but it must serve one coherent purpose.

A wave is not a large checklist. It is a controlled operating envelope.

### When to Use Large Waves

- The project architecture is stable
- The change touches multiple components for one purpose
- Tests, artifacts, and documentation must move together
- Fragmented micro-tasks would create coordination overhead
- Acceptance criteria can be defined before implementation

### When Not to Use Large Waves

- The architecture is still exploratory
- The design space is unknown
- Production-critical behavior could be mutated accidentally
- Acceptance criteria cannot be stated upfront

### Standard Wave Shape

Every wave must define:

```text
Wave Name:       The capability being added or changed.
Purpose:         Why this wave exists.
Scope:           What may change.
Non-Scope:       What must not change.
Disk Verification: Which files were inspected before planning.
Implementation:  File-by-file changes based only on verified disk state.
Tests:           Unit, integration, regression, and artifact checks.
Acceptance:      Concrete pass/fail conditions.
Seal Criteria:   Evidence proving the wave is complete.
```

---

## 2. Disk-Verified Planning

**No implementation plan is valid until the relevant files have been inspected in the working tree.**

The planning agent must not rely on:

- Documentation alone
- README claims
- Prior conversation memory
- Stale summaries
- Previous wave reports
- Architectural assumptions
- What "should probably exist"

### Core Rule

```text
Documentation is advisory.
Conversation memory is non-authoritative.
Code on disk is authoritative.
```

---

## 3. Execution Protocol

### Phase 1 — Disk Reconnaissance

Before planning, inspect:

```text
Relevant source files
Relevant tests
Schemas and configs
Data fixtures
Generated artifacts
Release or audit files
Dependency boundaries
Existing naming conventions
```

Report observations as facts, separated from proposals:

```text
Observed on disk:
- File A contains X.
- File B already enforces Y.
- Test C covers Z.
- No current implementation found for Q.
```

### Phase 2 — Wave Plan

Only after disk reconnaissance. The plan must be grounded in observed implementation:

```text
Because the current code on disk does X,
this wave should add or change Y,
without mutating Z.
```

### Phase 3 — Implementation

File-specific, with explicit do-not-modify lists:

```text
Add:     path/to/new_file.py
Modify:  path/to/existing_file.py
Do not modify:  path/to/forbidden_file.py
```

### Phase 4 — Verification

Every wave must close with evidence:

```text
Tests passing
Artifacts generated
Schemas validated
No forbidden files changed
Expected outputs confirmed
```

### Phase 5 — Seal

A wave is complete only when:

```text
The intended change exists on disk.
The forbidden change did not happen.
The tests passed.
The artifacts match the new behavior.
```

---

## 4. High-Governance Rules

1. Code on disk is authoritative.
2. Documentation is advisory.
3. Conversation memory is non-authoritative.
4. No plan may be produced before inspecting relevant files.
5. No wave may be accepted without tests or machine-checkable evidence.
6. Approved production state must not be mutated unless the wave explicitly authorizes it.
7. Generated artifacts must be distinguishable from source-of-truth code.
8. Any missing file, missing test, or mismatched assumption must be reported as a blocker.

---

## 5. Reusable Prompt

When starting any wave:

```text
Before planning this wave, inspect the actual code on disk.

Do not rely on documentation, summaries, memory, or previous conversation context
as the source of truth.

First report:
1. Which files you inspected.
2. What the current implementation actually does.
3. Which tests or fixtures already exist.
4. Which assumptions were confirmed or rejected by disk state.

Then produce the wave plan.
```
