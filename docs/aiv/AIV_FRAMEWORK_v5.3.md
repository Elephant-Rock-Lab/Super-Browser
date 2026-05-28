# AIV FRAMEWORK — STANDARD OPERATING PROCEDURE

### Architect · Implementer · Verifier

**Version:** 5.3 | **Edition:** AI-Executable | **Classification:** Binding Process Document
**Supersedes:** v5.2 | **Based on:** 22 real batch executions (BATCH-05M1 through BATCH-UX10)

---

## TABLE OF CONTENTS

1. [Framework Overview](#1-framework-overview)
2. [Two-Tiered Structure — Batch & Task](#2-two-tiered-structure--batch--task)
3. [Phase I — The Batch Blueprint](#3-phase-i--the-batch-blueprint)
4. [Phase I-B — Blueprint Review](#4-phase-i-b--blueprint-review)
5. [Phase II — Task Execution](#5-phase-ii--task-execution)
6. [Phase II-B — Partial Sign-Off](#6-phase-ii-b--partial-sign-off)
7. [Phase III — Batch Close](#7-phase-iii--batch-close)
8. [Document Lifecycle & Audit Trail](#8-document-lifecycle--audit-trail)
9. [Roles & Responsibilities](#9-roles--responsibilities)
10. [Sprint Checklists](#10-sprint-checklists)
11. [Operational Principles](#11-operational-principles)
12. [Codebase State File](#12-codebase-state-file)
13. [Test Integrity Protocol](#13-test-integrity-protocol)

---

## 1. FRAMEWORK OVERVIEW

The AIV Framework enforces a strict **Plan → Review → Execute → Verify** cycle at two levels: the **Batch** (the sprint goal) and the **Task** (the smallest logical unit of work within a Batch). Work is never considered "Done" at either level without a formal sign-off document.

### 1.1 Design Principles

- **Decoupling:** System design (Lead) is separated from execution (Assistant) and review (Reviewer).
- **Two-tiered scope:** Batches define goals. Tasks define discrete, logically coherent units of work.
- **AI-Executable:** All instructions are written to be followed directly by an AI agent without ambiguity.
- **Lead Sovereignty:** The Lead Programmer has final authority at every decision point.
- **No silent scope changes:** Tasks cannot be added, removed, or modified after the Blueprint is accepted without a formal revision cycle.
- **Source of truth is the artifact:** Completion is determined by the existence of the deliverable file, the git commit, and the signed document — not by session status or infrastructure signals.

### 1.2 Two Cycle Modes

Every Batch runs under exactly one cycle mode, declared in the Blueprint.

| Mode | When to use | Document count |
|:---|:---|:---|
| **Standard Cycle** | Any Batch with >1 Task, or any Task that modifies existing source files, or any Task with Hard Boundaries | `3 + (2 × N Tasks) + 1` |
| **Simplified Cycle** | Exactly 1 Task, no existing source files modified, no Hard Boundaries required, single deliverable | `3` |

The cycle mode is declared in the Blueprint and confirmed by the Reviewer (CHK-00). If the declared mode does not match the conditions above, the Reviewer must flag it.

### 1.3 Full Standard Cycle at a Glance

```
BATCH BLUEPRINT  (defines goal + all Tasks upfront)
│
├── Phase I-B: AI Reviewer evaluates Blueprint + Task list
│   └── Lead Response: ACCEPT / ACCEPT WITH MODIFICATIONS / REJECT
│       (max two review cycles — then Lead decision is final)
│
├── TASK-01
│   ├── Phase II:   Assistant executes Task-01
│   ├──             Task Implementation Report submitted
│   └── Phase II-B: Lead issues Partial Sign-Off (or returns for correction)
│
├── TASK-02
│   ├── Phase II:   Assistant executes Task-02
│   ├──             Task Implementation Report submitted
│   └── Phase II-B: Lead issues Partial Sign-Off (or returns for correction)
│
├── TASK-N  ...
│
└── Phase III: BATCH CLOSE
    Lead issues Batch Sign-Off Certificate
    (coherence check — confirms all Tasks fit together, no boundary gaps)
```

### 1.4 Naming Conventions

All IDs must follow these formats exactly. IDs are identifiers, not filenames. See §8.2 for file naming.

| Entity | ID Format | Example |
|:---|:---|:---|
| Batch | `BATCH-[NN]` | `BATCH-07` |
| Task | `BATCH-[NN]/TASK-[NN]` | `BATCH-07/TASK-03` |
| Review Report | `REVIEW-[BATCH-ID]-[YYYY-MM-DD]` | `REVIEW-BATCH-07-2025-06-14` |
| Task Report | `REPORT-[BATCH-ID]-[TASK-NN]-[YYYY-MM-DD]` | `REPORT-BATCH-07-TASK-03-2025-06-14` |
| Partial Sign-Off | `PARTIAL-[BATCH-ID]-[TASK-NN]-[YYYY-MM-DD]` | `PARTIAL-BATCH-07-TASK-03-2025-06-14` |
| Batch Certificate | `CERT-[BATCH-ID]-[YYYY-MM-DD]` | `CERT-BATCH-07-2025-06-14` |

---

## 2. TWO-TIERED STRUCTURE — BATCH & TASK

### 2.1 What Is a Batch?

A Batch is a sprint goal — a meaningful, deployable outcome. It defines the full scope, all Hard Boundaries, all Authority Rules, and the complete list of Tasks required to reach the goal. A Batch is the unit that gets reviewed (Phase I-B) and finally closed (Phase III).

### 2.2 What Is a Task?

A Task is the smallest logical unit of work within a Batch. Tasks are defined by the Lead in the Batch Blueprint — they cannot be invented by the Assistant during execution.

**A Task must be:**

- Logically coherent — it addresses one clear concern (e.g. one endpoint, one migration, one service module)
- Independently executable — the Assistant can complete it without simultaneously touching unrelated parts of the codebase
- Independently verifiable — the Lead can issue a Partial Sign-Off on it without waiting for other Tasks

**A Task must not be:**

- A catch-all — touching many unrelated files or systems simultaneously
- Artificially granular — splitting a single logical operation across multiple Tasks to create unnecessary overhead
- Undefined — added mid-Batch without a formal Blueprint revision

### 2.3 Task Sequencing

The Batch Blueprint must specify whether Tasks are:

| Mode | Meaning |
|:---|:---|
| **Sequential** | Tasks must be executed in order. Task N cannot begin until Task N-1 has a Partial Sign-Off. |
| **Parallel** | Tasks are independent and may be executed simultaneously. |
| **Mixed** | Some Tasks depend on others. Dependencies are declared explicitly in the Blueprint. |

The Assistant must not begin a Task that has an unresolved dependency.

---

## 3. PHASE I — THE BATCH BLUEPRINT

**Owner:** Lead Programmer
**Timing:** Before any review or execution begins
**Deliverable:** A completed Batch Blueprint document

The Batch Blueprint is the single source of truth for the entire Batch. It must define the full Task list before the Reviewer evaluates it. Tasks cannot be added after the Blueprint is accepted without a formal revision cycle.

### 3.1 Standard Cycle — Batch Blueprint Template

Every field marked MANDATORY must be present. A Blueprint missing any mandatory field is invalid and must not be sent to the Reviewer.

---

```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 [e.g. BATCH-07]
Blueprint Version:        [1.0 on first issue; increment on revision]
Cycle Mode:               STANDARD
Lead Programmer:          [Name / ID]
Date Issued:              [YYYY-MM-DD]
Review SLA:               [Max minutes Lead will respond after Review Report — default 30 min]
Execution SLA per Task:   [Max minutes Assistant has to complete each Task — default 60 min]
Partial Sign-Off SLA:     [Max minutes Lead has to issue each Partial Sign-Off — default 15 min]
Task Sequencing:          [Sequential / Parallel / Mixed]

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
A single clear statement of the deployable outcome this Batch produces:


───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  -
  -

What the code MUST NOT do:
  -
  -

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
The project's lint/clean-build command. Must produce zero warnings.
The Assistant must run this command and include the output in each
Task Implementation Report. Language-agnostic — set per project.

  Lint command:  [e.g. cargo build --workspace, npx tsc --noEmit, ruff check src/]

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
Each boundary must be falsifiable. Vague constraints are invalid (see §3.4).
Hard Boundaries apply across ALL Tasks in this Batch.

  HB-01:
  HB-02:

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
[Exact table definitions, API contracts, field types]
[Include current crate names, module paths, and field names as they exist in the codebase.]
[Stale references here will produce Adaptations in Phase II — see §5.4.]

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
[Trust, security, and state-change rules governing the system]

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
[Prior Batches or modules this Batch depends on]

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────
[§12 — Codebase State File liveness confirmation]

  State file exists:       [ ] YES  [ ] NO — first Batch, will create
  Last Updated:            [date from STATE.md, or N/A]
  Batches since update:    [N — must be <5, or reconciliation audit required]
  Reconciliation audit:    [ ] N/A (< 5 batches since update)
                           [ ] PERFORMED — see audit notes: [reference]

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
State the current test count as a baseline. The Reviewer checks the baseline only.
The Assistant confirms the final count in the Implementation Report.

  Baseline at Blueprint issuance:  [N] existing tests
  Expected delta (all Tasks):      +[M] new tests
  Expected total at Batch close:   [N+M]

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────
All Tasks must be defined here before review begins.
Tasks cannot be added after the Blueprint is accepted.

TASK-01: [BATCH-07/TASK-01]
  Priority:          [Critical / High / Medium / Low — default: Medium]
  Description:       [What this Task does — one logical concern]
  Files in scope:    [List of files expected to be created or modified]
                     [Changes outside this list are Deviations — see §5.3]
  Depends on:        [None / TASK-NN]
  Required Tests:
    | Test ID          | Type                              | Behavior Verified                  | Failure Mode                          | Falsified By                                     | Pass Criteria                             |
    |:-----------------|:----------------------------------|:-----------------------------------|:--------------------------------------|:-------------------------------------------------|:------------------------------------------|
    | TEST-07-01-01    | unit / integration / e2e / manual | [What specific behavior this tests]| [What would go wrong if this breaks]  | [What code change would make this test fail]     | [Specific assertion — see T3]             |
  Acceptance Criteria:
    AC-01-01:
    AC-01-02:
  Traceability:
    AC-01-01 → TEST-07-01-01
    AC-01-02 → TEST-07-01-02

TASK-02: [BATCH-07/TASK-02]
  Priority:          [Critical / High / Medium / Low — default: Medium]
  Description:
  Files in scope:
  Depends on:        [None / TASK-NN]
  Required Tests:
    | Test ID          | Type | Behavior Verified | Failure Mode | Falsified By | Pass Criteria |
    |:-----------------|:-----|:------------------|:-------------|:-------------|:--------------|
    | TEST-07-02-01    |      |                   |              |              |               |
  Acceptance Criteria:
    AC-02-01:
  Traceability:
    AC-02-01 → TEST-07-02-01

[Repeat block for each Task]
[Every test must satisfy T1 (falsifiable). Every Task must satisfy T2 (coverage categories).
 For Critical/High Tasks, T6 (mandatory falsification) applies. See §13.]

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
These criteria are evaluated at Phase III (Batch Close) only.
They confirm that all Tasks are coherent together as a whole.

  BAC-01:
  BAC-02:
  BAC-03: CHANGELOG.md updated with [BATCH-ID] entry.
  BAC-04: All documents archived under /docs/aiv/[BATCH-ID]/.

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
[Completed by Lead after Phase I-B. Leave blank until Review Report is received.]

Reviewer Report ID:       [REVIEW-BATCH-NN-YYYY-MM-DD]
Review Cycle:             [1 or 2 — see §4.4]
Lead Decision:            [ ] ACCEPT   [ ] ACCEPT WITH MODIFICATIONS   [ ] REJECT

If ACCEPT WITH MODIFICATIONS — list each Reviewer flag acted on:
  FLAG-01 → Action taken:
  FLAG-02 → Action taken:

If REJECT — reason and next action:

Blueprint Version after response: [Increment if revised]
Lead Sign:                [Name + YYYY-MM-DD HH:MM]

═══════════════════════════════════════════════════════════
```

---

### 3.2 Simplified Cycle — Batch Blueprint Template

A Batch qualifies for the Simplified Cycle when ALL of the following conditions are true:

1. The Batch has exactly one (1) Task
2. No existing source files are modified (new files only, or documentation/schema/config files)
3. No Hard Boundaries are required
4. The Batch produces a single deliverable

If any condition is false, the Batch must use the Standard Cycle. The Reviewer will flag a misdeclared cycle mode (CHK-00).

Under the Simplified Cycle:

- The Reviewer uses only CHK-00 through CHK-05 (batch-level checklist; task-level checklist is skipped)
- No Partial Sign-Off is issued (single deliverable; Batch Certificate covers it)
- No BATCH_[ID].md task section is required (inline comments + Certificate suffice)
- Document count is exactly 3: Blueprint + Review Report + Batch Sign-Off Certificate

---

```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 [e.g. BATCH-07]
Blueprint Version:        [1.0 on first issue; increment on revision]
Cycle Mode:               SIMPLIFIED
Lead Programmer:          [Name / ID]
Date Issued:              [YYYY-MM-DD]
Review SLA:               [Max minutes — default 30 min]
Execution SLA:            [Max minutes — default 60 min]

SIMPLIFIED CYCLE ELIGIBILITY — confirm all:
  [ ] Exactly 1 Task
  [ ] No existing source files modified
  [ ] No Hard Boundaries required
  [ ] Single deliverable

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────


───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What this deliverable MUST contain or do:
  -

What it MUST NOT do:
  -

───────────────────────────────────────────────────────────
TASK DEFINITION
───────────────────────────────────────────────────────────
  Description:      [What is being produced]
  Files in scope:   [File(s) to be created — no existing source files]
  Priority:         [Critical / High / Medium / Low — default: Medium]
  Required Tests:
    | Test ID         | Type | Behavior Verified | Failure Mode | Falsified By | Pass Criteria |
    |:----------------|:-----|:------------------|:-------------|:-------------|:--------------|
    | TEST-NN-01-01   |      |                   |              |              |               |
  If no tests are applicable:
    Required Tests:   NONE — justification: [why no tests are needed for this deliverable]
  Acceptance Criteria:
    AC-01:
    AC-02:
  Traceability:
    AC-01 → TEST-NN-01-01
    [Every AC must map to at least one test. Tests without an AC are unaccounted scope.]

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01:
  BAC-02:
  BAC-03: All documents archived under /docs/aiv/[BATCH-ID]/.

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
[Completed by Lead after Phase I-B. Leave blank until Review Report is received.]

Reviewer Report ID:
Review Cycle:             [1 or 2]
Lead Decision:            [ ] ACCEPT   [ ] ACCEPT WITH MODIFICATIONS   [ ] REJECT

If ACCEPT WITH MODIFICATIONS:
  FLAG-01 → Action taken:

If REJECT:

Blueprint Version after response:
Lead Sign:                [Name + YYYY-MM-DD HH:MM]

═══════════════════════════════════════════════════════════
```

---

### 3.3 SLA Defaults for AI-Agent Execution

When all roles are executed by AI agents in a session-based infrastructure, the following defaults apply unless the Blueprint declares otherwise:

| SLA | Default | Notes |
|:---|:---|:---|
| Review SLA | 30 minutes | Accounts for session queue + execution |
| Execution SLA per Task | 60 minutes | Accounts for session queue + build + test + commit |
| Partial Sign-Off SLA | 15 minutes | Lead review only; no queue expected |

These are minimums for AI-agent environments. Human-involved workflows may use longer windows.

### 3.4 Hard Boundary Format Rules

Hard Boundaries apply to the entire Batch and all Tasks within it. Every boundary must be a falsifiable statement. The Reviewer will flag any boundary that fails this standard.

**Valid format (falsifiable):**

```
HB-01: The system MUST NOT allow any public-source package to auto-install
       without an explicit admin approval record in the approvals table.
HB-02: No payment logic may be added to the public-readiness layer.
HB-03: User roles MUST NOT be elevated without a confirmed two-factor event.
```

**Invalid format (Reviewer will flag):**

```
✗  "Be careful with security."
✗  "Don't break the auth system."
✗  "Keep payments separate."
```

---

## 4. PHASE I-B — BLUEPRINT REVIEW

**Owner:** AI Reviewer Instance (separate AI call — not the executing Assistant)
**Timing:** After Batch Blueprint is issued; before any Task execution begins
**Deliverable:** Review Report presented to the Lead
**Authority:** Advisory only. The Lead has final decision.
**Scope:** Batch-level only. Individual Tasks are evaluated as part of the Batch Blueprint.

### 4.1 Purpose

The Reviewer evaluates the complete Batch Blueprint against a fixed checklist. It flags issues before they become execution errors. It does not propose solutions, rewrite boundaries, or make binding decisions.

### 4.2 Reviewer Prompt Template

Use this prompt verbatim. Append the full Batch Blueprint after `[BLUEPRINT START]`. Do not modify, summarise, or extend the prompt.

---

```
SYSTEM PROMPT — AIV BLUEPRINT REVIEWER

You are a Blueprint Reviewer in the AIV Framework. Your role is advisory only.
You flag issues. You do not make decisions, propose solutions, or suggest
architectural changes.

Evaluate the Blueprint below against the checklist in order. For each item,
state PASS or FLAG. If FLAG, write one concise sentence explaining the specific
problem. Do not write more than one sentence per flag.

CHECKLIST:

  CHK-00  CYCLE MODE          — Is the declared cycle mode (STANDARD/SIMPLIFIED) consistent
                                with the batch conditions? Flag if the batch has >1 Task but
                                declares SIMPLIFIED, or if it modifies existing source files
                                but declares SIMPLIFIED.

  [For SIMPLIFIED cycle, evaluate CHK-01 through CHK-05 only. Skip CHK-06 onward.]
  [For STANDARD cycle, evaluate all items.]

  CHK-01  BATCH ID            — Is a Batch ID present and correctly formatted?
  CHK-02  SLA FIELDS          — Are Review SLA and Execution SLA defined with numeric values?
  CHK-03  BATCH GOAL          — Is the Batch Goal a single, clear, deployable outcome?
  CHK-04  SCOPE COMPLETENESS  — Does the Scope Statement have at least one MUST and one MUST NOT?
  CHK-05  BATCH ACCEPTANCE    — Do the Batch-level Acceptance Criteria cover the full Batch Goal?

  [STANDARD CYCLE ONLY — continue below]

  CHK-06  HARD BOUNDARIES     — Is every Hard Boundary a falsifiable statement?
                                (Flag each vague boundary individually.)
  CHK-07  DATA MODELS         — Are data models/schema present and specific enough to implement?
                                (Flag if crate names, module paths, or field names appear stale
                                or hypothetical rather than verified against the actual codebase.)
  CHK-08  AUTHORITY RULES     — Are authority rules present? Do any contradict a Hard Boundary?
  CHK-09  DEPENDENCY MAP      — Is the dependency map present? Are any dependencies unresolved?
  CHK-10  TASK COMPLETENESS   — Does every Task have a description, files in scope,
                                test IDs, and acceptance criteria?
  CHK-11  TASK COHERENCE      — Is each Task logically coherent (one concern), or does it
                                appear to mix unrelated concerns?
  CHK-12  TEST COVERAGE       — Does every test have an ID, type, and specific pass criteria?
  CHK-13  TEST SUFFICIENCY    — Given each Task's scope, are there obvious gaps
                                (e.g. no error-path tests, no boundary condition tests)?
  CHK-14  TEST BASELINE       — Is the test baseline present? Is it plausible given the
                                stated scope? (Do not flag minor drift — flag only if the
                                baseline appears incorrect at issuance time.)
  CHK-15  TASK DEPENDENCIES   — Are declared Task dependencies consistent and non-circular?
  CHK-16  SCOPE COVERAGE      — Do the Tasks collectively cover the full Batch Scope
                                with no gaps or overlaps?
  CHK-17  INTERNAL CONSISTENCY — Do any fields across the Blueprint contradict each other?
  CHK-18  LINT COMMAND      — Is the Lint Command field present and non-empty?
                                (If absent, the Reviewer must flag it. Every project must
                                declare its zero-warning gate, even if it is `true` for
                                projects with no compiler.)

  ── INVESTIGATIVE LAYER (STANDARD CYCLE ONLY) ────────────

  Before evaluating CHK-19 through CHK-24, you MUST:
  1. Read /docs/aiv/STATE.md if it exists.
  2. Read every file referenced in the Blueprint's Data Models section.
  3. Read every file listed in any Task's "Files in scope."
  4. For CHK-23, evaluate test quality against the Test Integrity Protocol (§13).

  If you cannot access the filesystem, state:
    INVESTIGATIVE LAYER: SKIPPED — file access unavailable.
  The Lead must then perform these checks manually and document results
  in the Lead Response. A simple "SKIPPED" notation is insufficient.

  CHK-19  DATA MODEL VERIFICATION  — Read every file referenced in the
                                  Blueprint's Data Models / Schema section.
                                  Do the module paths, type names, and field
                                  names exist as stated? Flag each stale
                                  reference individually.
                                  Cross-reference against STATE.md Verified
                                  Module Map if available.

  CHK-20  FILE REALITY CHECK       — For each "Files in scope" entry across
                                  all Tasks: does this file already exist?
                                  If yes, read it and flag if the Task's
                                  description conflicts with the file's current
                                  content or structure. If the file is declared
                                  as "to be created" but already exists, flag it.

  CHK-21  SCOPE FEASIBILITY        — Given the file reality check and the Task
                                  descriptions, does the proposed scope seem
                                  achievable within the declared Execution SLA?
                                  Flag if a single Task touches >8 files or
                                  >500 LOC expected change — these tend to
                                  produce Deviations.

  CHK-22  TASK BOUNDARY INTEGRITY  — Read the Task descriptions and Files in
                                  Scope. Do any two Tasks silently share state
                                  (e.g., both modify the same struct, both
                                  import from the same unstable module) that
                                  isn't declared as a dependency?
                                  Flag undocumented couplings.

  CHK-23  TEST PLAN ADEQUACY       — For each Task, evaluate the test list
                                  against the Task's actual scope and the
                                  Test Integrity Protocol (§13). Specifically:
                                    - Does every test satisfy T1 (falsifiable)?
                                    - Does at least one test cover the error
                                      path / failure mode (T2)?
                                    - Does at least one test cover a boundary
                                      condition (T2)?
                                    - If the Task modifies existing code, is
                                      there a regression test (T2)?
                                    - For Critical/High Tasks: does the test
                                      plan include T6 falsification tests?
                                  Flag per Task per rule.

  CHK-24  STATE CONSISTENCY        — If STATE.md exists, cross-reference the
                                  Blueprint against it. Flag if:
                                    - The Blueprint references a module path
                                      that STATE.md lists as stale/overridden
                                    - The Blueprint claims a test baseline that
                                      contradicts STATE.md's Test Baseline
                                    - The Blueprint ignores a Carry-Forward
                                      Obligation that is relevant to its scope
                                    - STATE.md liveness check is missing or
                                      indicates >5 batches without update and
                                      no reconciliation audit is attached

  ── END INVESTIGATIVE LAYER ──────────────────────────────

Output format — use this template exactly:

---
REVIEW REPORT
Batch ID:            [from Blueprint]
Blueprint Version:   [from Blueprint]
Cycle Mode:          [STANDARD / SIMPLIFIED]
Reviewer:            [AI Reviewer Instance / Lead Programmer (fallback — session stalled)]
Timestamp:           [ISO 8601]
Review Cycle:        [1 or 2]
Report ID:           REVIEW-[BATCH-ID]-[YYYY-MM-DD]

CHECKLIST RESULTS

  CHK-00  CYCLE MODE:           [PASS / FLAG — reason]

  [SIMPLIFIED: CHK-01 through CHK-05 only]
  [STANDARD: CHK-01 through CHK-17]

  CHK-01  BATCH ID:             [PASS / FLAG — reason]
  CHK-02  SLA FIELDS:           [PASS / FLAG — reason]
  CHK-03  BATCH GOAL:           [PASS / FLAG — reason]
  CHK-04  SCOPE COMPLETENESS:   [PASS / FLAG — reason]
  CHK-05  BATCH ACCEPTANCE:     [PASS / FLAG — reason]
  CHK-06  HARD BOUNDARIES:      [PASS / FLAG — reason per boundary if flagged]
  CHK-07  DATA MODELS:          [PASS / FLAG — reason]
  CHK-08  AUTHORITY RULES:      [PASS / FLAG — reason]
  CHK-09  DEPENDENCY MAP:       [PASS / FLAG — reason]
  CHK-10  TASK COMPLETENESS:    [PASS / FLAG per Task]
  CHK-11  TASK COHERENCE:       [PASS / FLAG per Task]
  CHK-12  TEST COVERAGE:        [PASS / FLAG per Task / per test if flagged]
  CHK-13  TEST SUFFICIENCY:     [PASS / FLAG per Task]
  CHK-14  TEST BASELINE:        [PASS / FLAG — reason]
  CHK-15  TASK DEPENDENCIES:    [PASS / FLAG — reason]
  CHK-16  SCOPE COVERAGE:       [PASS / FLAG — identify gap or overlap]
  CHK-17  INTERNAL CONSISTENCY: [PASS / FLAG — reason]
  CHK-18  LINT COMMAND:         [PASS / FLAG — reason]

  ── INVESTIGATIVE LAYER ──────────────────────────────────

  CHK-19  DATA MODEL VERIFICATION:   [PASS / FLAG — per stale reference]
  CHK-20  FILE REALITY CHECK:        [PASS / FLAG — per file conflict]
  CHK-21  SCOPE FEASIBILITY:         [PASS / FLAG — per Task]
  CHK-22  TASK BOUNDARY INTEGRITY:   [PASS / FLAG — per coupling found]
  CHK-23  TEST PLAN ADEQUACY:        [PASS / FLAG — per Task per T-rule]
  CHK-24  STATE CONSISTENCY:         [PASS / FLAG — per contradiction]

  ── END INVESTIGATIVE LAYER ──────────────────────────────

SUMMARY

  Total Flags:      [N]
  Severity:         [LOW / MEDIUM / HIGH]
  Recommendation:   [PROCEED / PROCEED WITH CAUTION / RECOMMEND REVISION]
---

[BLUEPRINT START]
[Paste full Batch Blueprint here]
```

---

### 4.3 Lead Response Rules

After receiving the Review Report, the Lead must complete the **Lead Response** section of the Blueprint before passing it to the Assistant.

| Lead Decision | Meaning | Required Action |
|:---|:---|:---|
| **ACCEPT** | Blueprint approved as-is | Pass Blueprint + Review Report to Assistant. Execution may begin. |
| **ACCEPT WITH MODIFICATIONS** | Blueprint approved after changes | Log each flag acted on. Increment Blueprint Version. Pass revised Blueprint + Review Report to Assistant. |
| **REJECT** | Blueprint requires full revision | Revise Blueprint. Trigger one further Review Cycle (see §4.4). |

The Lead is not required to act on every flag. Flags are advisory. The Lead must document which flags influenced the decision.

### 4.4 Loop-Break Rule

> **The Blueprint may undergo a maximum of two (2) Review Cycles.**
> After the second Review Cycle, the Lead's decision is final regardless of flags raised.
> The Reviewer must record the cycle number in the `Review Cycle` field.
> A third review cycle must not be triggered under any circumstances.

### 4.5 Reviewer Fallback Procedure

If the Reviewer session has not produced a Report within 30 minutes of being spawned, or the session status remains queued for 60 minutes:

1. The Lead writes the Review Report directly using the standard template (CHK-00 through CHK-17)
2. The Report header must state: `Reviewer: Lead Programmer (fallback — session stalled)`
3. The Lead must still complete the Lead Response section separately — the Review is advisory; the Response is the decision
4. This fallback does not count as a Review Cycle
5. The fallback must be noted in the Batch Sign-Off Certificate under Notes

### 4.6 Manual Investigative Review Template

When the AI Reviewer cannot access the filesystem and states `INVESTIGATIVE LAYER: SKIPPED`, the Lead must perform the investigative checks manually and include this completed template in the Lead Response section of the Blueprint.

```
LEAD INVESTIGATIVE REVIEW
═══════════════════════════════════════════════════════════

Performed by:        [Lead Name / ID]
Date:                [YYYY-MM-DD]
Reason:              Reviewer file access unavailable

Files read during this review:
  [List every file read to evaluate CHK-19 through CHK-24]

CHECKLIST RESULTS

  CHK-19  DATA MODEL VERIFICATION:
    [PASS / FLAG — per stale reference, with file evidence]

  CHK-20  FILE REALITY CHECK:
    [PASS / FLAG — per file, with current state noted]

  CHK-21  SCOPE FEASIBILITY:
    [PASS / FLAG — per Task, with LOC estimate and file count]

  CHK-22  TASK BOUNDARY INTEGRITY:
    [PASS / FLAG — per coupling found, with shared-state details]

  CHK-23  TEST PLAN ADEQUACY:
    [PASS / FLAG — per Task per T-rule, with specific test references]

  CHK-24  STATE CONSISTENCY:
    [PASS / FLAG — per contradiction, with STATE.md entry reference]

SUMMARY

  Total Investigative Flags:  [N]
  Severity:                   [LOW / MEDIUM / HIGH]

═══════════════════════════════════════════════════════════
```

---

## 5. PHASE II — TASK EXECUTION

**Owner:** Assistant AI
**Timing:** After the Lead issues ACCEPT or ACCEPT WITH MODIFICATIONS. Tasks with dependencies may only begin after their dependency Tasks have a Partial Sign-Off.
**Deliverable:** Working code + documentation + Task Implementation Report (one per Task)

### 5.1 What the Assistant Reads Before Each Task

Before beginning any Task, the Assistant must confirm it has read:

1. The full Batch Blueprint including the Lead Response section
2. The Review Report (to understand what flags were raised and how the Lead resolved them)
3. The specific Task block for the Task being executed
4. The Partial Sign-Off(s) of any Tasks this Task depends on
5. /docs/aiv/STATE.md — current verified module paths, gotchas, and architectural decisions (if the file exists)

If any mandatory field is missing, or a dependency Task lacks a Partial Sign-Off, the Assistant must **halt and notify the Lead** rather than proceed with assumptions.

### 5.2 Task Implementation Report Template

One report per Task. Every field is mandatory. Free-form substitutions are rejected.

---

```
TASK IMPLEMENTATION REPORT
═══════════════════════════════════════════════════════════

Report ID:             REPORT-[BATCH-ID]-[TASK-NN]-[YYYY-MM-DD]
Batch ID:              [BATCH-NN]
Task ID:               [BATCH-NN/TASK-NN]
Blueprint Version:     [Must match the version passed to the Assistant]
Submitted By:          [Assistant name / system ID]
Submission Timestamp:  [ISO 8601]

───────────────────────────────────────────────────────────
SCOPE CONFIRMATION
───────────────────────────────────────────────────────────
Confirm the Task description from the Blueprint:

  Task Description confirmed: [ ] YES / [ ] NO — reason if NO

  Final test count:  [N] total ([baseline] existing + [delta] new)

───────────────────────────────────────────────────────────
LINT EVIDENCE
───────────────────────────────────────────────────────────
The Lint Command declared in the Blueprint was run. Output:

  Warnings:  [N — must be 0]
  Errors:    [N — must be 0]
  Output excerpt (last 5 lines):
  [paste]

───────────────────────────────────────────────────────────
HARD BOUNDARY AFFIRMATION
───────────────────────────────────────────────────────────
State compliance for each Batch-level Hard Boundary individually.

  HB-01: CONFIRMED — [Restate boundary]. This boundary was NOT violated.
  HB-02: CONFIRMED — [Restate boundary]. This boundary was NOT violated.
  HB-03: VIOLATED  — [Restate boundary]. Violation: [explain]. Remediation: [action taken or flagged].

───────────────────────────────────────────────────────────
FILES CHANGED
───────────────────────────────────────────────────────────

| File Path | Action | In Scope? | Reason |
|:----------|:-------|:----------|:-------|
| src/...   | Created / Modified / Deleted | YES / NO | [Why] |

Files marked NO in "In Scope?" must also appear in Deviations below.

───────────────────────────────────────────────────────────
TEST EVIDENCE
───────────────────────────────────────────────────────────
Every test named in this Task's Blueprint block must have a row.
Tests that cannot be executed in the current environment use the DEFERRED status.
Behavior Verified and Failure Confirmed columns are required by §13 (Test Integrity Protocol).

| Test ID        | Type        | Behavior Verified              | Result  | Failure Confirmed?                                  | Log Reference |
|:---------------|:------------|:-------------------------------|:--------|:----------------------------------------------------|:--------------|
| TEST-NN-NN-01  | unit        | [from Blueprint Behavior col]  | ✓ PASS  | N/A (previously failed in BATCH-NN)                 | ...           |
| TEST-NN-NN-02  | unit        | [from Blueprint Behavior col]  | ✓ PASS  | YES — falsified: introduced bug, test failed, reverted | ...        |
| TEST-NN-NN-03  | e2e         | [from Blueprint Behavior col]  | ⏸ DEFERRED | N/A                                              | [reason]      |

Deferred tests must also appear in the Deferred Tests section below.
Deferred tests must not exceed 20% of the total named test count for this Task.

───────────────────────────────────────────────────────────
FAILURE VERIFICATION  (§13 — Test Integrity Protocol, T6)
───────────────────────────────────────────────────────────
Task Priority: [Critical / High / Medium / Low]

For Critical/High Tasks: every test must have a falsification result.
For Low/Medium Tasks: only tests that have never failed require verification.

  TEST-NN-NN-01: Previously failed in BATCH-NN — verified.
  TEST-NN-NN-02: Never failed. Falsification performed:
    Diff applied:    [exact unified diff that was introduced]
    Test output:     [relevant failure output lines from test runner]
    Revert:          [commit hash / "reverted in working tree before commit"]
  TEST-NN-NN-03: DEFERRED — not applicable.

If any falsification attempt produced a PASS (test did not fail when bug was introduced):
  DEFECTIVE TEST: TEST-NN-NN-XX — falsification did not produce failure.
  Root cause: [explain why test doesn't catch the described failure]
  Resolution: [test was fixed / test was replaced / requires Lead decision]

───────────────────────────────────────────────────────────
TRACEABILITY CONFIRMATION  (§13 — T5)
───────────────────────────────────────────────────────────
Confirm every AC maps to at least one test, and every test maps to at least one AC.

  AC-NN-01 → TEST-NN-NN-01 (✓ PASS), TEST-NN-NN-02 (✓ PASS) — covered
  AC-NN-02 → TEST-NN-NN-03 (⏸ DEFERRED) — deferred, tracked in: [ref]
  Unmapped tests: None
  Uncovered ACs: None

───────────────────────────────────────────────────────────
DEFERRED TESTS
───────────────────────────────────────────────────────────
Tests that cannot be executed in the current batch environment
(e.g. require live sessions, GUI, or external services).
Write "None" if all tests were executed.

STATE.md is the sole authoritative registry for deferred-test obligations.
The Assistant appends entries to STATE.md Carry-Forward Obligations at
Task Report time as PENDING_LEAD_CONFIRMATION (see §12.4).

  DEFER-01: [Test ID] — [reason it cannot run now]
            STATE.md entry: DEFER-BATCH-NN-TASK-NN-TEST-NN (status: PENDING_LEAD_CONFIRMATION)

Deferred tests will be listed in the Partial Sign-Off and flagged at Batch Close.
The Lead confirms or rejects pending entries at Partial Sign-Off (§6.1).

───────────────────────────────────────────────────────────
ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  AC-NN-01: [ ✓ Met / ✗ Failed ] — [comment if failed]
  AC-NN-02: [ ✓ Met / ✗ Failed ] — [comment if failed]

───────────────────────────────────────────────────────────
ADAPTATIONS
───────────────────────────────────────────────────────────
Record any instance where the Blueprint's data model, field names, module paths,
or API contracts did not match the actual codebase, and what was done instead.
Adaptations are not violations — they are records of specification vs. reality.
Write "None" if Blueprint matched codebase exactly.

  ADAPT-01: Blueprint stated [X]. Actual codebase has [Y]. Resolution: [Z].
  ADAPT-02:

Adaptations inform future Blueprint accuracy. The Lead should update the
relevant Blueprint sections based on Adaptations before the next Batch.

───────────────────────────────────────────────────────────
DEVIATIONS
───────────────────────────────────────────────────────────
Any departure from the Blueprint that is not an Adaptation — including
files touched outside the declared scope — must be listed here with justification.
The Lead MAY RETURN the Task for an unapproved out-of-scope change
even if all tests pass.
Write "None" if no deviations occurred.

  DEVIATION-01: [What deviated] — [justification]

───────────────────────────────────────────────────────────
DOCUMENTATION DELIVERED
───────────────────────────────────────────────────────────

  [ ] Inline code comments on all complex logic blocks in this Task
  [ ] Task section added to BATCH_[ID].md under /docs/aiv/[BATCH-ID]/

───────────────────────────────────────────────────────────
ASSISTANT SIGN
───────────────────────────────────────────────────────────

  Assistant ID:   [Name / system ID]
  Timestamp:      [ISO 8601]

═══════════════════════════════════════════════════════════
```

---

### 5.3 Lead Override — Infrastructure Constraints

When the Assistant session cannot be spawned or is stalled for more than 60 minutes:

1. The Lead MAY implement the Task directly
2. The Task Implementation Report must include: `DEVIATION-01: Lead implemented directly. Reason: [infrastructure constraint].`
3. The Partial Sign-Off must include: `Self-Review Acknowledged: YES — Lead acted as both Lead and Assistant for this Task.`
4. This override must not be used for three (3) consecutive Batches. If it occurs three times in a row, halt all work and resolve the infrastructure issue before proceeding.

### 5.3.1 Time-Sensitive Decision Protocol

LLM agents have no subjective perception of elapsed time between tool calls.
`sleep` delays the system, not the agent's experience. Therefore, no time-based
decision may be made without actively computing a timestamp delta.

**Before declaring any session "stalled" or invoking Lead Override:**

```
1. Record spawn_time from the spawn_session response (createdAt field)
2. Query current wall-clock time
3. Compute: elapsed = current_time - spawn_time
4. If elapsed < 5 minutes (300 seconds):
     DO NOT OVERRIDE. Poll again after waiting.
5. If elapsed >= 5 minutes but < 100% of SLA:
     Poll at 5-minute intervals. Override only if deliverables are empty AND SLA is exhausted.
6. If elapsed >= 100% of SLA:
     Override immediately.
```

**Never rely on subjective perception of elapsed time. Always compute from timestamps.**

### 5.3.2 Standard Polling Pattern

Replace ad-hoc `sleep` + check with this structured loop.
This pattern integrates the Session Liveness Confirmation Protocol (§8.4.1).

```
Given: session_id (from spawn_session response)
Given: spawn_time (from session creation response)
Given: sla_seconds = execution_sla_minutes × 60
Given: min_wait = 300  // flat 5-minute initial wait
Given: poll_interval = 300  // 5-minute polling interval
Given: messaged = false

Loop:
  1. current_time = query wall clock
  2. elapsed = current_time - spawn_time
  3. If deliverable file exists on disk: BREAK (success)
  4. If elapsed >= sla_seconds: BREAK (override)
  5. If elapsed < min_wait:
       sleep(min_wait - elapsed)
       GOTO 1
  6. // Past minimum wait. No files yet. Probe liveness.
     If not messaged:
       send_agent_message(session_id, "Confirm: have you completed your task?")
       messaged = true
     sleep(poll_interval)
     // On next iteration: check files again, then check for reply
     GOTO 1
```

### 5.4 Adaptations vs. Deviations

These two categories are distinct. Using the wrong category misrepresents the work.

| Category | Definition | Example | Severity |
|:---|:---|:---|:---|
| **Adaptation** | Blueprint's specification did not match the actual codebase. The Assistant made a correct technical adjustment. | Blueprint referenced `kore_cap::keys::KeyPair`; actual export path is `ed25519_dalek::KeyPair`. Used type alias. | Not a violation — informs Blueprint improvement |
| **Deviation** | The Assistant departed from the Blueprint's instructions in a way not caused by a codebase mismatch. | Blueprint declared 3 files in scope; Assistant also modified a 4th file without declaring it. | Requires justification; Lead may RETURN |

---

## 6. PHASE II-B — PARTIAL SIGN-OFF

**Owner:** Lead Programmer
**Timing:** After each Task Implementation Report is submitted, within the Partial Sign-Off SLA
**Deliverable:** Partial Sign-Off document (one per Task; Standard Cycle only)

The Partial Sign-Off closes a single Task. It does not close the Batch. A Task without a Partial Sign-Off is not done. Any Task that depends on it must not begin.

### 6.1 Partial Sign-Off Template

---

```
PARTIAL SIGN-OFF
═══════════════════════════════════════════════════════════

Partial Sign-Off ID:      PARTIAL-[BATCH-ID]-[TASK-NN]-[YYYY-MM-DD]
Batch ID:                 [BATCH-NN]
Task ID:                  [BATCH-NN/TASK-NN]
Report Reviewed:          [Report ID]
Review Timestamp:         [ISO 8601]
SLA Compliance:           [ ] YES   [ ] NO — reason: [explain]
Self-Review Acknowledged: [ ] N/A   [ ] YES — Lead acted as both Lead and Assistant

───────────────────────────────────────────────────────────
VERDICT
───────────────────────────────────────────────────────────

  [ ] APPROVED — Task is complete and compliant. Dependent Tasks may now begin.
  [ ] RETURNED — See corrections below.

───────────────────────────────────────────────────────────
DEFERRED TESTS NOTED
───────────────────────────────────────────────────────────
List any deferred tests from the Task Report that must be tracked forward.
Write "None" if all tests passed.

The Lead confirms or rejects each PENDING_LEAD_CONFIRMATION entry.
Only Lead-confirmed entries become authoritative Carry-Forward Obligations.

  DEFER-01: [Test ID] — STATE.md entry: DEFER-BATCH-NN-TASK-NN-TEST-NN
    Lead action: [ ] CONFIRMED → status: OPEN  [ ] REJECTED — reason:

───────────────────────────────────────────────────────────
CORRECTIONS REQUIRED  (complete only if RETURNED)
───────────────────────────────────────────────────────────

  CORRECTION-01: [Blueprint field ref] — [Discrepancy description]

Write "N/A" if APPROVED.

───────────────────────────────────────────────────────────
NOTES FOR SUBSEQUENT TASKS
───────────────────────────────────────────────────────────
Any observations relevant to subsequent Tasks or the Batch Close.
Write "None" if not applicable.

───────────────────────────────────────────────────────────
LEAD SIGN
───────────────────────────────────────────────────────────

  Lead Name:   [Name / ID]
  Timestamp:   [ISO 8601]

═══════════════════════════════════════════════════════════
```

---

### 6.2 Return Rules

- A RETURNED Task is resubmitted as a revised Implementation Report. The SLA clock resets.
- A RETURNED Task does not invalidate the Batch or other Tasks that do not depend on it.
- A Task that depends on a RETURNED Task must not begin until the dependency receives APPROVED.

---

## 7. PHASE III — BATCH CLOSE

**Owner:** Lead Programmer
**Timing:** After ALL Tasks in the Batch have an APPROVED Partial Sign-Off (Standard Cycle), or after execution is complete (Simplified Cycle)
**Deliverable:** Batch Sign-Off Certificate

Phase III is a coherence check, not a re-verification of individual Tasks. The Lead confirms that all Tasks fit together as a whole, that no boundary gaps exist between them, and that Batch-level Acceptance Criteria are met.

### 7.1 Batch Sign-Off Certificate Template

---

```
BATCH SIGN-OFF CERTIFICATE
═══════════════════════════════════════════════════════════

Certificate ID:          CERT-[BATCH-ID]-[YYYY-MM-DD]
Batch ID:                [BATCH-NN]
Cycle Mode:              [STANDARD / SIMPLIFIED]
Blueprint Version:       [Final accepted version]
Review Timestamp:        [ISO 8601]

Partial Sign-Offs confirmed (Standard Cycle only):
  [ ] PARTIAL-[BATCH-ID]-[TASK-01]-[DATE]
  [ ] PARTIAL-[BATCH-ID]-[TASK-02]-[DATE]
  [ ] PARTIAL-[BATCH-ID]-[TASK-NN]-[DATE]
  N/A — Simplified Cycle (no Partial Sign-Offs)

DELIVERABLE CONFIRMATION (Simplified Cycle only; mark N/A if Standard)

  Deliverable path:  [file path]
  Exists on disk:    [ ] YES
  Git commit ref:    [hash]
  Commit includes:   [summary of what was delivered]
  Tests (if any):    [N passed / 0 failed / 0 deferred]

  The Lead confirms the deliverable matches the Blueprint's Task Definition
  and meets all Acceptance Criteria.

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: [ ✓ Met / ✗ Failed ] — [comment if failed]
  BAC-02: [ ✓ Met / ✗ Failed ] — [comment if failed]
  BAC-03: [ ✓ Met / ✗ Failed ] CHANGELOG.md updated
  BAC-04: [ ✓ Met / ✗ Failed ] All documents archived under /docs/aiv/[BATCH-ID]/
          (Simplified Cycle: BAC-03 only — BAC-04 uses 3-document count)

───────────────────────────────────────────────────────────
COHERENCE CHECK  (Standard Cycle only; mark N/A if Simplified)
───────────────────────────────────────────────────────────

  [ ] All Tasks together fully deliver the Batch Goal
  [ ] No Hard Boundary gaps exist between Tasks
        (no boundary respected within a Task but violated across Task boundaries)
  [ ] No unresolved Deviations from any Task Report affect the Batch Goal
  [ ] Documentation set is complete: BATCH_[ID].md, CHANGELOG.md, version matrix

───────────────────────────────────────────────────────────
STATE.md UPDATE  (§12 — Codebase State File)
───────────────────────────────────────────────────────────

  [ ] Verified Module Map updated with new/changed paths from this Batch
  [ ] Architectural Decisions updated if this Batch introduced constraints
  [ ] Known Gotchas updated if this Batch discovered surprises
  [ ] Adaptation Log prepended with this Batch's entries
  [ ] Test Baseline updated to final count
  [ ] Carry-Forward Obligations updated (deferred tests added, resolved ones removed)
  [ ] STATE.md committed to repository

───────────────────────────────────────────────────────────
TEST INTEGRITY VERIFICATION  (§13 — Test Integrity Protocol)
───────────────────────────────────────────────────────────
The Lead confirms that test quality — not just test count — has been verified.

  If STANDARD CYCLE:
  [ ] All tests in this Batch satisfy T1 (falsifiable — each has a
      described code change that would make it fail)
  [ ] Every Task has at least happy-path + error-path coverage (T2)
  [ ] Traceability section maps every AC to at least one test, and
      every test to at least one AC (T5)
  [ ] All Critical/High Tasks have falsification results in their
      Implementation Reports — no unresolved “NOT PERFORMED” entries (T6)
  [ ] No defective tests (tests where falsification produced a PASS)
      remain unresolved

  If SIMPLIFIED CYCLE:
  [ ] All tests satisfy T1 (each has a described Falsified By change)
  [ ] Happy-path + error-path coverage present, or absence justified (T2)
  [ ] Every AC maps to at least one test and vice versa (T5)
  [ ] T6 falsification performed for Critical/High priority Task (or N/A — Medium/Low)

  T1 violations:     [N — must be 0]
  T2 violations:     [N — must be 0]
  T5 coverage gaps:  [N — must be 0]
  T6 unresolved:     [N — must be 0 if Critical/High]

───────────────────────────────────────────────────────────
DEFERRED TESTS SUMMARY
───────────────────────────────────────────────────────────
Carry forward all deferred tests from all Task Partial Sign-Offs.
Write "None" if no tests were deferred across this Batch.

  DEFER-01: [Test ID] — STATE.md entry: DEFER-BATCH-NN-TASK-NN-TEST-NN (status: OPEN)

Reconciled against STATE.md:
  [ ] YES — all deferred tests in this Certificate match STATE.md Carry-Forward Obligations
  [ ] NO  — Batch Close is BLOCKED until reconciliation is complete

───────────────────────────────────────────────────────────
NOTES
───────────────────────────────────────────────────────────
Include: Reviewer fallback used (Y/N), Lead Override used (Y/N + count),
any Adaptations that require Blueprint corrections in the next Batch.
Write "None" if not applicable.

───────────────────────────────────────────────────────────
VERDICT
───────────────────────────────────────────────────────────

  [ ] APPROVED — Batch is closed. Work is merged into release target.
  [ ] RETURNED — See corrections below.

───────────────────────────────────────────────────────────
CORRECTIONS REQUIRED  (complete only if RETURNED)
───────────────────────────────────────────────────────────

  CORRECTION-01: [Scope / Task ref] — [Issue description]

Write "N/A" if APPROVED.

───────────────────────────────────────────────────────────
RELEASE TARGET
───────────────────────────────────────────────────────────
Version / tag this Batch is merged into (e.g. v0.34.0-prealpha):

───────────────────────────────────────────────────────────
LEAD PROGRAMMER SIGN
───────────────────────────────────────────────────────────

  Lead Name:   [Name / ID]
  Timestamp:   [ISO 8601]

═══════════════════════════════════════════════════════════
```

---

### 7.2 Batch Close Rules

- The Batch Certificate may only be issued after every Task has an APPROVED Partial Sign-Off (Standard Cycle) or execution is complete (Simplified Cycle).
- A RETURNED Batch Certificate does not re-open individual Tasks unless the Lead explicitly identifies which Task is implicated.
- Once APPROVED, no further changes may be made to this Batch's documents.

---

## 8. DOCUMENT LIFECYCLE & AUDIT TRAIL

### 8.1 Document Count by Cycle Mode

**The document count formula depends on the declared cycle mode.**

**Standard Cycle** (N = number of Tasks):

```
Total documents = 3 + (2 × N) + 1

Breakdown:
  3 = Blueprint (v1.0) + Review Report + Blueprint with Lead Response
  2 × N = Task Implementation Report + Partial Sign-Off, per Task
  1 = Batch Sign-Off Certificate
```

Example: Standard Cycle with 4 Tasks → `3 + (2 × 4) + 1 = 12 documents`

| # | Document | Author | Timing |
|:--|:---|:---|:---|
| 1 | Batch Blueprint (v1.0) | Lead Programmer | Before review |
| 2 | Review Report | AI Reviewer Instance | After Blueprint issued |
| 3 | Batch Blueprint with Lead Response | Lead Programmer | After review |
| 4…(3+N) | Task Implementation Report × N | Assistant AI | After each Task executed |
| (4+N)…(3+2N) | Partial Sign-Off × N | Lead Programmer | After each Task Report reviewed |
| (4+2N) | Batch Sign-Off Certificate | Lead Programmer | After all Tasks approved |

---

**Simplified Cycle:**

```
Total documents = 3

Breakdown:
  1 = Blueprint (includes Lead Response after review)
  1 = Review Report
  1 = Batch Sign-Off Certificate

Documents NOT produced in Simplified Cycle:
  ✗ Task Implementation Report (no separate Task document)
  ✗ Partial Sign-Off (Certificate covers the single deliverable)
  ✗ BATCH_[ID].md task section (inline comments suffice)
```

| # | Document | Author | Timing |
|:--|:---|:---|:---|
| 1 | Batch Blueprint (with Lead Response after review) | Lead Programmer | Before + after review |
| 2 | Review Report | AI Reviewer Instance | After Blueprint issued |
| 3 | Batch Sign-Off Certificate | Lead Programmer | After execution complete |

---

An agent confirming document count must first determine the cycle mode from the Blueprint before applying the formula. Applying the Standard Cycle formula to a Simplified Cycle batch (or vice versa) is an error.

### 8.2 File Naming Convention

IDs (§1.4) are identifiers used in document headers and cross-references. Filenames are what gets committed to disk. These are not the same.

```
/docs/aiv/[BATCH-ID]/
  BLUEPRINT.md
  REVIEW-REPORT.md
  REPORT-TASK-01-[YYYY-MM-DD].md
  REPORT-TASK-02-[YYYY-MM-DD].md
  PARTIAL-TASK-01-[YYYY-MM-DD].md
  PARTIAL-TASK-02-[YYYY-MM-DD].md
  SIGN-OFF-CERTIFICATE.md
  BATCH_[BATCH-ID].md              ← implementation record (Standard Cycle only)
```

Simplified Cycle:

```
/docs/aiv/[BATCH-ID]/
  BLUEPRINT.md
  REVIEW-REPORT.md
  SIGN-OFF-CERTIFICATE.md
```

### 8.3 Git Commit Rules

1. Every commit message must reference the Batch ID and, where applicable, the Task ID:

   ```
   feat(batch-07/task-02): add remote agent transport
   docs(batch-07/task-01): update SDK reference
   chore(batch-07): Batch Sign-Off Certificate
   ```

2. One commit per role action:
   - Lead: Blueprint commit
   - Assistant: Implementation commit (code + tests)
   - Lead: Partial Sign-Off commit
   - Lead: Batch Certificate commit

3. The Assistant's implementation commit must include in the commit body:
   - Test evidence summary (N passed, M failed, K deferred)
   - LOC delta
   - Files changed count

4. The Lead must not combine code changes with certificate commits.

### 8.4 Session Status Caveat

**Session status is unreliable.** Known platform behaviours:

- Sessions may complete their work but their status remains "To Do" or "Queued"
- Sessions may end (process terminates) while the platform still shows an active status
- Session status transitions may be delayed by minutes or never occur at all

The source of truth for completion is, in order:

1. The deliverable file exists on disk at the declared path
2. The git commit exists with the correct reference
3. The signed document (Report, Partial Sign-Off, or Certificate) is written and complete

Do not gate progress on session status. Gate progress on the existence of the signed document.

### 8.4.1 Session Liveness Confirmation Protocol

Because status is unreliable, the Lead must confirm session liveness before
taking any action (override, closure, or proceeding to the next Task).
Use this protocol instead of trusting status:

```
Given: session_id (from spawn_session response)
Given: spawn_time (from session creation)

1. Wait the minimum polling interval (see §5.3.2)

2. CHECK FILES:
   - Do the expected deliverable files exist on disk?
   - Does git log show a new commit from this session?
   If YES → session likely completed. Proceed to verify contents.
   If NO → continue to step 3.

3. SEND MESSAGE to the session:
   - Use send_agent_message with a status probe:
     "Confirm: have you completed your task? List all files written."
   - Wait for a reply (see §5.3.2 polling interval)

4. EVALUATE REPLY:
   If reply confirms completion → check files again, then proceed.
   If reply indicates still working → resume polling loop (§5.3.2).
   If no reply after poll interval → see step 5.

5. NO REPLY + NO FILES + ELAPSED >= SLA:
   Invoke Lead Override (§5.3).

6. NO REPLY + NO FILES + ELAPSED < SLA:
   Resume polling. Do NOT override yet.
```

**Key principle:** A message probe is more reliable than status checks because
it tests the session's actual ability to respond — not the platform's status tracker.
A session that replies is alive regardless of what its status field says.
A session that doesn't reply AND has no files on disk is either still working
or genuinely stalled — the elapsed time vs. SLA determines which.

### 8.5 Retention Rules

- All documents must be retained for a minimum of 12 months
- Documents must not be edited after signing
- The Lead is responsible for confirming archive completeness at Batch close

---

## 9. ROLES & RESPONSIBILITIES

| Role | Responsibility | May Not |
|:---|:---|:---|
| **Lead Programmer** | Writes Blueprint; defines all Tasks; responds to Review; issues Partial Sign-Offs and Batch Certificate | Skip Phase I-B; add Tasks after Blueprint is accepted without a formal revision |
| **AI Reviewer Instance** | Evaluates Batch Blueprint + Task list against fixed checklist; produces Review Report | Propose solutions; rewrite boundaries; communicate with Assistant; trigger a third review cycle |
| **Assistant AI** | Reads Blueprint and Review Report; executes Tasks in declared order; submits Task Reports | Begin a Task with an unresolved dependency; substitute or omit named tests without Lead approval; add scope beyond declared Task without recording it as a Deviation |

### 9.1 Boundaries of Reviewer Authority

The AI Reviewer Instance:

- **MAY:** Flag missing fields, vague Hard Boundaries, test gaps, Task coherence issues, scope gaps or overlaps, stale data model references, internal contradictions
- **MAY NOT:** Propose architectural solutions, rewrite Hard Boundaries, suggest code approaches, make binding decisions, communicate with the Assistant, trigger a third review cycle

### 9.2 Lead Override — Infrastructure Constraints

See §5.3 for full procedure. Summary:

- Lead may implement a Task directly if the Assistant session is unavailable for >60 minutes
- The Task Report must record this as a Deviation with reason
- The Partial Sign-Off must acknowledge the self-review
- Three consecutive overrides triggers a mandatory infrastructure halt

---

## 10. SPRINT CHECKLISTS

### Lead Programmer — Before Issuing Batch Blueprint

```
[ ] Determine cycle mode: STANDARD or SIMPLIFIED (verify all conditions — see §3.2)
[ ] Batch ID assigned and correctly formatted (BATCH-NN)
[ ] Batch Goal is a single, clear, deployable outcome
[ ] SLA fields populated (use defaults from §3.3 if AI-agent execution)
[ ] Blueprint Version set to 1.0

  If STANDARD:
  [ ] All Hard Boundaries written in falsifiable format (see §3.4)
  [ ] All Tasks defined in the Task List — none to be added after acceptance
  [ ] Each Task has: description, files in scope, dependency declaration,
      named tests with IDs and pass criteria, acceptance criteria
  [ ] Task sequencing declared (Sequential / Parallel / Mixed)
  [ ] Task dependencies are non-circular
  [ ] Test Baseline populated (existing count + expected delta)
  [ ] STATE.md STATUS section completed — liveness confirmed (see §12.1)
  [ ] Test table uses v5.3 format: Behavior Verified, Failure Mode, Falsified By columns (see §13)
  [ ] Traceability section present in each Task block (T5)
  [ ] Task Priority declared for each Task (Critical/High/Medium/Low)
  [ ] Batch-level Acceptance Criteria include BAC-03 (CHANGELOG) and BAC-04 (archive)

  If SIMPLIFIED:
  [ ] All four eligibility conditions confirmed (see §3.2)
  [ ] Task Definition block completed
  [ ] Batch-level Acceptance Criteria include BAC-03 (archive)

[ ] Lead Response section left blank (to be completed after review)
[ ] Blueprint ready to send to AI Reviewer Instance
```

### Lead Programmer — After Receiving Review Report

```
[ ] Review Report read in full
[ ] Lead Response section of Blueprint completed
[ ] Decision recorded: ACCEPT / ACCEPT WITH MODIFICATIONS / REJECT
[ ] If ACCEPT WITH MODIFICATIONS: each flag acted on is logged with action taken
[ ] If REJECT: Blueprint revised and re-sent for second Review Cycle (max — see §4.4)
[ ] Blueprint Version incremented if revised
[ ] Accepted Blueprint (with Lead Response) and Review Report sent to Assistant
[ ] If Reviewer stated INVESTIGATIVE LAYER SKIPPED: Manual Investigative Review (§4.6) completed and attached to Lead Response
```

### Assistant AI — Before Beginning Each Task

```
[ ] Full Batch Blueprint read including Lead Response section
[ ] Review Report read
[ ] /docs/aiv/STATE.md read (if exists) — verified module paths, gotchas noted
[ ] Cycle mode noted: STANDARD or SIMPLIFIED
[ ] Specific Task block identified and read (Standard) or full Task Definition read (Simplified)
[ ] All dependency Tasks confirmed APPROVED — Partial Sign-Off exists (Standard, Sequential/Mixed)
[ ] All mandatory Blueprint fields confirmed present
[ ] If any field is missing or dependency is unresolved: HALT and notify Lead
```

### Assistant AI — Before Submitting Each Task Implementation Report

```
[ ] Lint Command from Blueprint executed — zero warnings, zero errors
[ ] Lint Evidence section populated with output excerpt
[ ] Report ID follows format: REPORT-[BATCH-ID]-[TASK-NN]-[YYYY-MM-DD]
[ ] Task description confirmed
[ ] Final test count recorded (baseline + delta)
[ ] Every Batch-level Hard Boundary affirmed individually
[ ] Files Changed table complete: path | action | in-scope | reason
[ ] Every file changed outside declared scope listed in Deviations
[ ] Every named test has a row: PASS, FAIL, or DEFERRED (with tracking ref)
[ ] Behavior Verified column populated for every test (§13)
[ ] Failure Confirmed column populated for every test (§13)
[ ] FAILURE VERIFICATION section completed — mandatory for Critical/High Tasks (T6)
[ ] TRACEABILITY CONFIRMATION section completed — every AC maps to tests, no orphans (T5)
[ ] Deferred tests do not exceed 20% of total named tests for this Task
[ ] Deferred Tests section completed or states "None"
[ ] Every Task Acceptance Criteria item confirmed or failed with reason
[ ] Adaptations section completed or states "None"
[ ] Deviations section completed or states "None"
[ ] Task section added to BATCH_[ID].md (Standard Cycle)
[ ] Report signed with Assistant ID and timestamp
```

### Lead Programmer — Before Issuing Each Partial Sign-Off (Standard Cycle)

```
[ ] Task Implementation Report received within Execution SLA
[ ] Lint Evidence section confirmed: zero warnings, zero errors
[ ] Report reviewed against Task block in Blueprint
[ ] Partial Sign-Off ID follows format: PARTIAL-[BATCH-ID]-[TASK-NN]-[YYYY-MM-DD]
[ ] SLA compliance recorded
[ ] Self-Review field completed (N/A or YES)
[ ] Deferred tests from Report carried forward into Partial Sign-Off
[ ] Verdict stated: APPROVED or RETURNED
[ ] If RETURNED: corrections itemised with Blueprint field references
[ ] If APPROVED: notify Assistant that dependent Tasks may begin (Sequential/Mixed)
[ ] Partial Sign-Off committed and filed at /docs/aiv/[BATCH-ID]/PARTIAL-TASK-NN-DATE.md
```

### Lead Programmer — Before Issuing Batch Sign-Off Certificate

```
[ ] Cycle mode confirmed: STANDARD or SIMPLIFIED

  If STANDARD:
  [ ] All Tasks have an APPROVED Partial Sign-Off
  [ ] All Partial Sign-Off IDs listed in the Certificate
  [ ] Coherence check completed (all four items confirmed)
  [ ] BATCH_[ID].md, CHANGELOG.md, and version matrix confirmed complete

  If SIMPLIFIED:
  [ ] Execution confirmed complete (deliverable exists on disk, commit exists)
  [ ] Deliverable Confirmation section completed in Certificate
  [ ] CHANGELOG.md confirmed updated
  [ ] Coherence check marked N/A

[ ] Batch-level Acceptance Criteria evaluated
[ ] Deferred Tests Summary compiled from all Partial Sign-Offs (or Task Report if Simplified)
[ ] Notes section completed: Reviewer fallback, Lead Override count, Adaptations to carry forward
[ ] Certificate ID follows format: CERT-[BATCH-ID]-[YYYY-MM-DD]
[ ] Verdict stated: APPROVED or RETURNED
[ ] Release target confirmed
[ ] Certificate signed with name and timestamp
[ ] Test Integrity Verification section completed — all counts are 0 (§13)
[ ] STATE.md updated and committed (§12)
[ ] All documents (correct count for cycle mode) archived under /docs/aiv/[BATCH-ID]/
[ ] Batch marked closed in project tracker
```

---

## 11. OPERATIONAL PRINCIPLES

These principles are derived from 6 batch executions under v3. They are forward-looking guidance for agents executing future Batches — not a retrospective of past failures.

**P1 — Specification accuracy is the Lead's primary quality lever.**
Every Adaptation logged by the Assistant reflects a gap between the Blueprint's data model and the actual codebase. Adaptations are not failures — they are signals. After every Batch, the Lead should update the relevant Blueprint sections with verified module paths, field names, and API contracts. A Blueprint that produces few Adaptations relative to its Task count is well-calibrated.

**P2 — Session infrastructure is unreliable; documents and probes are not.**
Session status signals, queue times, and completion indicators cannot be trusted as progress signals (see §8.4). A session may have finished but still show "To Do". The signed document is the primary indicator that a phase is complete. When documents are absent and the status is ambiguous, send a message probe (§8.4.1) — a session that replies is alive regardless of its status field. Design all monitoring and gating logic around document existence and message probes, not session status.

**P3 — The Reviewer's value is in catching gaps before they become errors.**
A Reviewer that flags the same category of issue repeatedly (e.g. stale test counts) is a signal that the Blueprint template needs a structural fix — not that the Reviewer is overly strict. Recurring flags should be addressed in the template, not dismissed.

**P4 — The Simplified Cycle is a privilege, not a shortcut.**
A Batch that qualifies for the Simplified Cycle still goes through Phase I-B review. The reduced document count reflects reduced scope, not reduced rigour. Misdeclaring a Simplified Cycle to avoid overhead is a process violation.

**P5 — Deferred tests are debts, not dismissals.**
Every deferred test carries a tracking reference. A test deferred without a tracking reference is a lost obligation. At Batch Close, deferred tests are explicitly listed in the Certificate. They must be re-attempted in a declared future Batch or test plan — not quietly dropped.

**P6 — The Lead Override is an escape valve, not a workflow.**
Three consecutive Lead Overrides indicate a systemic infrastructure failure. The framework provides the override to prevent deadlock — not to normalise a Lead doing both roles. If the override is used repeatedly, the infrastructure problem takes priority over all pending Batches.

**P7 — Hard Boundaries are a contract, not a checklist.**
A Hard Boundary that the Reviewer passes but the Assistant silently violates is a framework failure. The Assistant's Hard Boundary Affirmation section exists precisely to make this visible. A boundary affirmed as CONFIRMED and later found violated is grounds for RETURNING the Task regardless of test results.

**P8 — Commit discipline is audit discipline.**
Commits that mix role actions (e.g. code changes bundled with a certificate commit) make the audit trail ambiguous. One commit per role action is not administrative overhead — it is the mechanism that makes the paper trail trustworthy.

**P9 — Zero warnings is a gate, not an aspiration.**
The Lint Command declared in the Blueprint is a mandatory quality gate. An Assistant that submits a Task Report without lint evidence, or with non-zero warnings, has not completed the Task. The Lead must not issue a Partial Sign-Off without verifying the lint output. This gate is language-agnostic — every project declares its own command — but the principle is universal: clean compilation is a minimum standard, not an optional nicety. Warnings that survive Review, Sign-Off, and Batch Close are process failures, not cosmetic issues.

**P10 — LLM agents have no sense of time.**
Between tool calls, no subjective duration passes. An agent cannot distinguish 3 minutes from 30 minutes without actively computing a timestamp delta. Any time-based decision (override, SLA enforcement, stall detection) MUST query wall-clock time and compute elapsed time from the session's creation timestamp. `sleep` is a system delay, not an agent experience. See §5.3.1 for the mandated protocol.

**P11 — STATE.md is the codebase's long-term memory.**
A Batch that closes without updating STATE.md is a Batch that forgets. Every Adaptation, every gotcha, every architectural decision that isn't written to STATE.md will be re-discovered — at higher cost — by a future session. The state file is not documentation overhead; it is the mechanism that makes multi-Batch development cumulative rather than repetitive. A stale STATE.md is worse than no STATE.md — it provides false confidence. The liveness rule (§12.1) ensures the state file remains trustworthy.

**P12 — A review that doesn't read the code is a rubber stamp.**
The Structural Layer confirms the Blueprint is well-formed. The Investigative Layer confirms it is well-informed. A Blueprint that passes all structural checks but references stale module paths, ignores existing files, or proposes tests that don't cover failure modes will still produce Adaptations and Deviations in Phase II. The Investigative Layer is what turns review from ceremony into quality assurance. When the Reviewer cannot access files, the Lead must perform the investigative checks and document the results — otherwise the layer is optional in practice, which means it will erode.

**P13 — A test that has never failed is a test that has never been tested.**
Tests exist to catch bugs. A test that passes on first run and is never challenged has not proven it can catch anything. The Test Integrity Protocol (§13) ensures every test declares what it guards against and how it could fail. A test without a falsification path is not a test — it is a decoration. For Critical and High priority Tasks, falsification is mandatory — the Assistant must prove each test can fail before the Task can be signed off. For Low and Medium Tasks, the never-failed rule applies. The framework does not require every test to fail during development, but it requires every test to describe how it *would* fail, and it requires that description to be verified for high-stakes work.

---

*AIV Framework v5.3 — AI-Executable Edition*
*All templates in this document are binding. Free-form substitutions are not permitted.*
*Standard Cycle document count: 3 + (2 × N Tasks) + 1*
*Simplified Cycle document count: 3*
*Determine cycle mode from Blueprint before applying any formula.*

---

## 12. CODEBASE STATE FILE

### 12.0 Purpose

STATE.md is the project's persistent cross-session memory. It captures verified module paths, architectural decisions, known gotchas, and accumulated Adaptations — so new sessions don't start from zero. Every Batch opens by reading it and closes by updating it.

**Location:** `/docs/aiv/STATE.md`
**Owner:** Lead Programmer (updated at every Batch Close)
**Read by:** Assistant AI (before reading the Blueprint), AI Reviewer Instance (before evaluating the Blueprint)
**Created:** First Batch under v5.3

### 12.1 Stale State Detection

STATE.md is only valuable when accurate. A stale STATE.md is worse than no STATE.md — it gives false confidence.

**Liveness Rule:** If STATE.md's "Last Updated" date is older than 5 Batches (i.e., 5 Batch Close events have occurred without an update), the Lead must perform a **reconciliation audit** before opening a new Batch.

**Reconciliation Audit Procedure:**
1. Read every entry in the Verified Module Map
2. For each entry, verify the module path and export still exist in the codebase
3. For each Architectural Decision marked Active, confirm it is still enforced
4. For each Known Gotcha marked OPEN, confirm it is still unresolved
5. Update "Last Updated" and "Verified in" fields for every confirmed entry
6. Archive or strike through entries that are no longer relevant
7. Commit the updated STATE.md before issuing the next Blueprint

The Batch Blueprint must include the STATE.md STATUS section confirming liveness. If the section is missing, the Reviewer must flag it under CHK-24.

### 12.2 STATE.md Template

```
# CODEBASE STATE

Last Updated:       [YYYY-MM-DD]
Updated By:         [Lead Name / ID — via BATCH-NN Close]
Framework Version:  [e.g. 5.3]

───────────────────────────────────────────────────────────
VERIFIED MODULE MAP
───────────────────────────────────────────────────────────
Verified paths and exports that future Batches can rely on.
Every entry here was confirmed by an Adaptation or manual audit.

  Module / Crate:     [e.g. kore_cap::keys]
  Actual export:      [e.g. ed25519_dalek::SigningKey]
  Verified in:        [BATCH-NN]
  Notes:              [e.g. "KeyPair was renamed in v0.3.0"]

  [Repeat for each verified module]

───────────────────────────────────────────────────────────
ARCHITECTURAL DECISIONS
───────────────────────────────────────────────────────────
Decisions that constrain future work. Each entry explains WHY, not just WHAT.

  DEC-001:  [e.g. "All payment logic lives in the payment crate.
             Public-readiness layer must not import payment types.
             Reason: regulatory separation requirement — see BATCH-02."]
  Source:    [BATCH-NN / design doc ref]
  Active:    YES
  Overridden: [NO / YES — by DEC-NNN in BATCH-NN]

  [Repeat for each decision]

───────────────────────────────────────────────────────────
KNOWN GOTCHAS
───────────────────────────────────────────────────────────
Things that surprised a previous Batch. Prevents re-surprise.

  GOTCHA-001: [e.g. "The test suite requires DATABASE_URL set even for
               unit tests. Tests will silently pass with wrong schema
               if the env var points to a stale migration."]
  Discovered:  [BATCH-NN]
  Status:      [OPEN / MITIGATED — describe mitigation]

  [Repeat for each gotcha]

───────────────────────────────────────────────────────────
ADAPTATION LOG (ROLLING — LAST 10 BATCHES)
───────────────────────────────────────────────────────────
Consolidated from all Task Reports. New entries prepend.
Entries older than 10 Batches are archived to STATE_ARCHIVE.md.

  BATCH-07/TASK-02: Blueprint stated [X]. Actual: [Y]. Resolution: [Z].
  BATCH-06/TASK-01: ...

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
Current total test count. Updated at every Batch Close.

  Last verified count: [N]
  Verified in:         [BATCH-NN / date]
  Breakdown:           [e.g. 142 unit / 23 integration / 4 e2e]

───────────────────────────────────────────────────────────
CARRY-FORWARD OBLIGATIONS
───────────────────────────────────────────────────────────
Deferred tests, known gaps, and promises from previous Batches
that are still outstanding. STATE.md is the sole authoritative
registry — all other references (Task Reports, Partial Sign-Offs,
Certificates) are reference fields that point here.

Entry format for deferred tests:
  DEFER-BATCH-NN-TASK-NN-TEST-NN: [description]
    Status:   [PENDING_LEAD_CONFIRMATION / OPEN / RESOLVED / VERIFIED_CLOSED / REJECTED]
    Source:    [Task Report ID]
    Promised:  [BATCH-NN]
    Resolved:  [BATCH-NN — only if RESOLVED or VERIFIED_CLOSED]

Entry format for known gaps:
  GAP-BATCH-NN: [description]
    Status:   [OPEN / CLOSED]

═══════════════════════════════════════════════════════════
```

### 12.3 STATE.md Validity

STATE.md is VALID only when:
1. It contains at least one non-placeholder entry in any section, AND
2. Every non-placeholder entry has a "Verified in" reference to a real Batch, AND
3. The "Last Updated" field contains a real date (not "[YYYY-MM-DD]")

STATE.md is INVALID when:
1. It contains only bracket placeholders (no real data), OR
2. The "Last Updated" field is the placeholder "[YYYY-MM-DD]", OR
3. Every section body consists entirely of template instructions with no Batch-verified entries

A STATE.md that is INVALID is treated as if it does not exist:
- The Assistant must not read placeholder data as verified fact
- The Reviewer must not cross-reference against placeholder entries
- The Blueprint's STATE.md STATUS section must state: `STATE.md: NOT YET CREATED — first Batch`

**EXCEPTION — Bootstrap Batch:**
The first Batch executed under v5.3 may open with no STATE.md file at all, or with a placeholder file. This is the ONLY situation where a placeholder/absent STATE.md is acceptable. The Batch Sign-Off Certificate for this Batch MUST create STATE.md with at least one real entry (Verified Module Map, Adaptation Log, or Test Baseline — whichever the Batch produces).

### 12.4 Deferred-Test Authority Guardrail

STATE.md is the sole authoritative registry for deferred-test obligations. Deferred tests are entered into STATE.md at Task Report time as append-only `PENDING_LEAD_CONFIRMATION` entries.

**Assistant permissions:**
- MAY: append new deferred-test entries with status `PENDING_LEAD_CONFIRMATION`
- MUST NOT: edit, delete, resolve, or overwrite existing STATE.md entries

**Lead permissions:**
- Confirms or rejects each pending entry at Partial Sign-Off or Batch Close
- Only Lead-confirmed entries become authoritative Carry-Forward Obligations
- May resolve entries (`RESOLVED`, `VERIFIED_CLOSED`) at any Batch

**Deferred-test lifecycle:**

```
PENDING_LEAD_CONFIRMATION  (created by Assistant at Task Report time)
  → OPEN                      (Lead confirms at Partial Sign-Off)
    → RESOLVED                (test executed in a later Batch)
      → VERIFIED_CLOSED       (falsification confirmed in resolving Batch)

PENDING_LEAD_CONFIRMATION
  → REJECTED                  (Lead determines deferral is invalid)
```

**Certificate gate:**
The Batch Sign-Off Certificate MUST reconcile all deferred tests against STATE.md before Batch Close. If reconciliation fails, Batch Close is BLOCKED.

---

## 13. TEST INTEGRITY PROTOCOL

### 13.0 Purpose

All tests declared in the Batch Blueprint must satisfy the Test Integrity Protocol. This applies to both Standard and Simplified cycles. The protocol ensures every test is falsifiable, covers meaningful categories, and maps to a specific Acceptance Criterion.

### 13.1 Revised Test Table Format

The Blueprint test table uses the following columns (see §3.1 template):

| Column | Purpose |
|:---|:---|
| **Test ID** | Standard ID format |
| **Type** | unit / integration / e2e / manual |
| **Behavior Verified** | What specific behavior this test checks (not generic) |
| **Failure Mode** | What would go wrong if this behavior were broken |
| **Falsified By** | What concrete code change would make this test fail |
| **Pass Criteria** | Specific assertion(s) — not "works correctly" |

### 13.2 Test Integrity Rules

**T1 — Every test must be falsifiable.**
The "Falsified By" column must describe a concrete code change that would make the test fail. If no such change can be described, the test does not test the system. Examples of non-falsifiable tests that must be flagged:
- Tests that assert constants (`assert_eq!(MAX_SIZE, 1024)`)
- Tests that only check that code runs without panicking (unless testing for panic-safety specifically)
- Tests that assert type existence without testing behavior
- Tests whose assertions are unreachable or always true regardless of implementation

**T2 — Every Task must cover at least three categories of test.**

| Category | Purpose | Required? |
|:---|:---|:---|
| **Happy path** | Correct input produces correct output | Yes — at least 1 per Task |
| **Error / failure path** | Invalid input, missing data, or failed precondition produces the expected error | Yes — at least 1 per Task that handles input |
| **Boundary condition** | Edge of valid range (zero, empty, max, off-by-one) is handled correctly | Required if the Task involves numeric ranges, collections, or limits |
| **Regression guard** | Protects against re-introduction of a known bug | Required if the Task fixes a bug or modifies existing code |

If a Task has no error-path tests and no boundary tests, the Reviewer must flag it under CHK-23.

**T3 — Pass criteria must be specific to the test.**
Generic pass criteria ("works correctly", "returns expected output") are invalid. Each test must declare specific assertions:
```
Pass Criteria: assert_eq!(result.status, Rejected) AND assert!(result.error.contains('insufficient'))
```

**T4 — No orphan assertions.**
Every assertion in a test must relate to the "Behavior Verified" column. If a test asserts five things but declares it tests "payment processing," either split into multiple tests with clear behavior declarations, or expand the Behavior Verified to cover all assertions.

**T5 — Test-to-AC traceability.**
The Blueprint must include a Traceability section in each Task block mapping every Acceptance Criterion to at least one test. Tests that don't map to any AC are unaccounted scope. ACs without tests are unverified claims.

**T6 — Mandatory falsification for Critical/High priority Tasks.**

For any Task designated **Critical** or **High** priority, the Assistant MUST perform falsification during execution. This is non-optional.

**Falsification procedure:**
1. For each test in the Task, read the "Falsified By" column
2. Introduce the described code change
3. Run the test suite — confirm the target test FAILS
4. Record the evidence in the Task Implementation Report's FAILURE VERIFICATION section:
   - The exact unified diff that was introduced
   - The relevant failure output lines from the test runner
   - The revert method (commit hash or "reverted in working tree before commit")
5. Revert the code change

Working-tree revert is the default. A dedicated commit is required only if the Lead's project conventions demand it. The diff + test output are the real evidence; the revert method is hygiene.

If a falsification attempt produces a PASS (the test does not fail when the bug is introduced), the test is **defective**. The Assistant must:
1. Flag the test as defective in the Implementation Report
2. Investigate why the test doesn't catch the described failure
3. Fix the test so it catches the described failure mode
4. Re-run falsification to confirm the fix works

For **Low/Medium** priority Tasks: falsification is mandatory only for tests that have never failed in any previous Batch. Otherwise optional. A "NOT PERFORMED" entry for a never-failed test is acceptable but must be justified.

### 13.3 Task Priority Declaration

The Batch Blueprint Task block must include a Priority field:
```
TASK-01: [BATCH-07/TASK-01]
  Priority:          [Critical / High / Medium / Low]
```
If no priority is declared, default is **Medium**.

### 13.4 Failure Verification in Implementation Report

The Task Implementation Report (§5.2) includes a FAILURE VERIFICATION section. This section records:
- Task Priority (Critical/High/Medium/Low)
- For each test: whether falsification was performed, and the result
- Any defective tests discovered during falsification

The TRACEABILITY CONFIRMATION section confirms every AC maps to at least one test and vice versa.

---

*AIV Framework v5.3 — AI-Executable Edition*
*All templates in this document are binding. Free-form substitutions are not permitted.*
*Standard Cycle document count: 3 + (2 × N Tasks) + 1*
*Simplified Cycle document count: 3*
*Determine cycle mode from Blueprint before applying any formula.*
