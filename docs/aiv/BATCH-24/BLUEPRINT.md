BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-24
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead Programmer
Date Issued:              2026-05-08
Review SLA:               30 min
Execution SLA per Task:   90 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Sequential

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
Transform the CLI from minimal (version/info/run) into a full interactive
and batch automation tool with persistent browser sessions, YAML script
execution, recording replay, and one-shot agent commands.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Provide interactive REPL mode with 9 commands (open, click, fill, extract, scroll, screenshot, observe, tabs, close)
  - Browser persists between commands in interactive mode
  - Execute YAML script files with step-by-step actions
  - Replay recording JSON files from the CLI
  - Support one-shot `act "instruction"` agent execution
  - Report progress per step in script mode

What the code MUST NOT do:
  - Require LLM credentials for non-agent commands
  - Break any existing test
  - Change any existing public API signature
  - Require interactive mode to use the CLI

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/ --ignore-missing-imports

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-24-01: Interactive mode MUST keep browser alive between commands (single SuperBrowser instance)
  HB-24-02: Script mode MUST report progress per step (step N/total: action result)
  HB-24-03: CLI MUST NOT require LLM credentials for non-agent commands (open, click, fill, extract, etc.)
  HB-24-04: Unknown commands MUST print help text, not crash

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
Interactive commands:
  open <url>         → navigate
  click <selector>   → click
  fill <sel> <value> → fill
  extract [selector] → extract
  scroll <direction> → scroll (up/down/left/right)
  screenshot [path]  → screenshot
  observe            → observe (URL, title, elements)
  tabs               → list_tabs
  close              → stop browser and exit

YAML script format:
  steps:
    - action: navigate
      url: "https://example.com"
    - action: click
      selector: "#button"
    - action: fill
      selector: "#email"
      value: "test@example.com"
    - action: extract
      selector: "h1"
  stop_on_error: true
  output: "results.json"

CLI entry point: super_browser.cli:main (already registered in pyproject.toml)

Existing modules to modify:
  - src/super_browser/cli.py (MODIFY — major rewrite)
New modules:
  - src/super_browser/cli/interactive.py (NEW)
  - src/super_browser/cli/commands.py (NEW)
  - src/super_browser/cli/script.py (NEW)

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
  - Interactive mode uses MockLLMClient by default (no API key needed)
  - Agent commands (`act`) require a valid LLM provider
  - Script mode stops on first error if stop_on_error is true

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
  Depends on: BATCH-22 (EventBus), BATCH-23 (Recording)
  Required by: BATCH-26 (integration tests)

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────
  State file exists:       [ ] NO — will create at BATCH-26
  Last Updated:            N/A
  Batches since update:    N/A
  Reconciliation audit:    N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  ~1,400 (1,385 + ~15 from BATCH-23)
  Expected delta (all Tasks):      +9 new tests
  Expected total at Batch close:   ~1,409

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-24/TASK-01 — Interactive Mode
  Priority:          High
  Description:       Add persistent interactive REPL mode with 9 browser commands.
                     Single SuperBrowser instance kept alive between commands.
  Files in scope:
    - src/super_browser/cli.py (MODIFY)
    - src/super_browser/cli/__init__.py (NEW)
    - src/super_browser/cli/interactive.py (NEW)
    - src/super_browser/cli/commands.py (NEW)
  Depends on:        None
  Required Tests:
    | Test ID          | Type | Behavior Verified                          | Failure Mode                        | Falsified By                                         | Pass Criteria                          |
    |:-----------------|:-----|:-------------------------------------------|:------------------------------------|:-----------------------------------------------------|:---------------------------------------|
    | TEST-24-01-01    | unit | "open https://example.com" navigates       | URL not passed to navigate          | Hardcode URL in command handler                       | page.url contains "example.com"        |
    | TEST-24-01-02    | unit | "click #btn" calls sb.click                | Click not dispatched                | Skip click in command dispatch map                   | sb.click called with "#btn"            |
    | TEST-24-01-03    | unit | "close" shuts down browser                 | Browser left running                | Skip stop() call in close handler                    | sb._running == False                   |
    | TEST-24-01-04    | unit | Unknown command shows help                 | Error not handled                   | Raise ValueError on unknown command                  | "Unknown command" in output            |
    | TEST-24-01-05    | unit | Browser persists between commands          | New browser per command             | Create new SuperBrowser in each command               | same session across 2 commands         |
  Acceptance Criteria:
    AC-01-01: All 9 commands work with correct dispatch
    AC-01-02: Browser stays alive between commands
    AC-01-03: Unknown commands show help, not crash
    AC-01-04: No LLM credentials required for interactive mode
  Traceability:
    AC-01-01 → TEST-24-01-01, TEST-24-01-02
    AC-01-02 → TEST-24-01-05
    AC-01-03 → TEST-24-01-04
    AC-01-04 → TEST-24-01-05

TASK-02: BATCH-24/TASK-02 — Script Mode & Replay Command
  Priority:          Medium
  Description:       Add `super-browser script tasks.yaml` for YAML batch execution.
                     Add `super-browser replay recording.json` for recording replay.
                     Add `super-browser act "instruction" --url <url>` for one-shot agent.
  Files in scope:
    - src/super_browser/cli.py (MODIFY — add subcommands)
    - src/super_browser/cli/script.py (NEW)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type | Behavior Verified                      | Failure Mode                    | Falsified By                                   | Pass Criteria                          |
    |:-----------------|:-----|:---------------------------------------|:--------------------------------|:-----------------------------------------------|:---------------------------------------|
    | TEST-24-02-01    | unit | YAML script executes all steps          | Steps skipped after first       | Break loop after first step                    | all 3 steps executed                   |
    | TEST-24-02-02    | unit | Script stops on error with flag         | Continues after error           | Remove error check                             | execution stops at failing step         |
    | TEST-24-02-03    | unit | replay command loads recording          | Recording not loaded            | Skip file read                                 | replay called with correct path         |
    | TEST-24-02-04    | unit | act command calls sb.act()              | act() never called              | Return early before act call                   | act() called with instruction text      |
  Acceptance Criteria:
    AC-02-01: YAML script mode executes all steps in order
    AC-02-02: Script stops on error when stop_on_error is true
    AC-02-03: `replay` command replays a recording file
    AC-02-04: `act` command runs a one-shot agent task
  Traceability:
    AC-02-01 → TEST-24-02-01
    AC-02-02 → TEST-24-02-02
    AC-02-03 → TEST-24-02-03
    AC-02-04 → TEST-24-02-04

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: Interactive mode works with all 9 commands
  BAC-02: YAML script mode executes task lists
  BAC-03: replay command replays recordings
  BAC-04: act command runs one-shot agent tasks
  BAC-05: No existing tests broken
  BAC-06: CHANGELOG deferred to BATCH-26
  BAC-07: All documents archived under /docs/aiv/BATCH-24/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
Reviewer Report ID:       REVIEW-BATCH-24-2026-05-08
Review Cycle:             1
Lead Decision:            [x] ACCEPT

Reviewer fallback applied proactively per §4.5 — prior two Reviewer sessions
(BATCH-22, BATCH-23) both exhausted SLA with no deliverable.

Blueprint Version after response: 1.0
Lead Sign:                Lead Programmer — 2026-05-08 03:05

═══════════════════════════════════════════════════════════
