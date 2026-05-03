BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-18
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead (single-session override)
Date Issued:              2026-05-03
Review SLA:               30 min
Execution SLA per Task:   60 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Sequential

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
Adopt 5 high-value patterns from Clawd Cursor v0.8.7 analysis:
safety gate, deterministic router, runaway guard, prompt injection
defense, and ActionResult convenience methods.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Add tier-based safety gate evaluating every facade method
  - Add deterministic router intercepting URL/click/scroll patterns
  - Add diagnostic hints to loop detector runaway detection
  - Wrap untrusted screen content in prompt injection defense tags
  - Add raise_for_error() and ok_or_raise() to ActionResult

What the code MUST NOT do:
  - Break any existing test
  - Change the public API surface of facade methods
  - Add new dependencies

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/ && python -m mypy src/ --ignore-missing-imports

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-18-01: Safety gate MUST be a pure function with no side effects
  HB-18-02: Deterministic router MUST always fall back to LLM when pattern doesn't match
  HB-18-03: Runaway guard hints MUST be action-specific (different hint for click vs extract vs navigate)
  HB-18-04: Prompt injection defense MUST preserve page content (no stripping)
  HB-18-05: raise_for_error() MUST NOT raise when ok=True

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
SafetyDecision (security/gate.py):
  tier: str  # "read" | "input" | "destructive" | "system"
  allowed: bool
  reason: str | None

RouteResult (agent/router.py):
  handled: bool
  action: str | None
  params: dict | None
  description: str | None

RunawayResult (agent/loop_detector.py enhancement):
  is_runaway: bool
  repeats: int
  hint: str | None

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
  - Safety gate is advisory — facade may still execute (confirm vs block)
  - Router is advisory — returns handled=False when uncertain
  - Runaway guard exits the agent loop with "give_up"

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
  Depends on: BATCH-17 (v1.0.1 patch release)

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  1,370 existing tests
  Expected delta (all Tasks):      +37 new tests
  Expected total at Batch close:   1,407

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-18/TASK-01 — Safety Gate + Deterministic Router
  Description:      New security/gate.py and agent/router.py modules
  Files in scope:
    - src/super_browser/security/gate.py (NEW)
    - src/super_browser/agent/router.py (NEW)
    - src/super_browser/agent/facade.py
  Depends on:       None
  Required Tests:
    | Test ID          | Type | Pass Criteria                                       |
    |:-----------------|:-----|:----------------------------------------------------|
    | TEST-18-01       | unit | Read tier always allowed                            |
    | TEST-18-02       | unit | System tier requires confirm                        |
    | TEST-18-03       | unit | Destructive tier requires confirm                   |
    | TEST-18-04       | unit | "Send" label escalates to confirm                   |
    | TEST-18-05       | unit | URL pattern routes to navigate                      |
    | TEST-18-06       | unit | Click pattern routes to click                       |
    | TEST-18-07       | unit | Scroll pattern routes to scroll                     |
    | TEST-18-08       | unit | Compound tasks are rejected                         |
    | TEST-18-09       | unit | Ambiguous tasks fall back                           |
  Acceptance Criteria:
    AC-01-01: evaluate() returns correct tier for every facade method
    AC-01-02: router.route() handles URL/click/scroll without LLM
    AC-01-03: router.route() returns handled=False for ambiguous tasks

TASK-02: BATCH-18/TASK-02 — Runaway Guard + Prompt Defense + Result Methods
  Description:      Enhance loop detector, add injection defense, add ActionResult methods
  Files in scope:
    - src/super_browser/agent/loop_detector.py
    - src/super_browser/agent/loop.py
    - src/super_browser/results/types.py
  Depends on:       TASK-01
  Required Tests:
    | Test ID          | Type | Pass Criteria                                       |
    | TEST-18-10       | unit | Runaway detected at threshold 3                     |
    | TEST-18-11       | unit | Click hint mentions selectors/observe               |
    | TEST-18-12       | unit | Extract hint mentions observe/selector              |
    | TEST-18-13       | unit | Window enforcement — old actions don't count        |
    | TEST-18-14       | unit | <untrusted-screen-content> wrapping applied          |
    | TEST-18-15       | unit | Defense instruction present in output               |
    | TEST-18-16       | unit | raise_for_error() does not raise on ok=True         |
    | TEST-18-17       | unit | raise_for_error() raises on ok=False                |
    | TEST-18-18       | unit | ok_or_raise() returns data on ok=True               |
    | TEST-18-19       | unit | ok_or_raise() raises on ok=False                    |
  Acceptance Criteria:
    AC-02-01: Runaway guard provides per-action hints
    AC-02-02: _build_prompt wraps content in untrusted tags
    AC-02-03: raise_for_error() and ok_or_raise() work correctly

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: All 5 patterns implemented and tested
  BAC-02: Full test suite passes (1370+ tests)
  BAC-03: CHANGELOG.md updated with BATCH-18 entry
  BAC-04: All documents archived under /docs/aiv/BATCH-18/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
[Completed after Phase I-B]

═══════════════════════════════════════════════════════════
