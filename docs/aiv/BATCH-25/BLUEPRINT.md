BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-25
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
Create a cross-session agent memory system that remembers successful action
sequences, working selectors, and user preferences per domain. Memory is
opt-in, persisted as JSON, and used to accelerate repeat tasks.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Store per-domain memory: action sequences, selector maps, preferences
  - Persist to ~/.config/super-browser/memory/<domain>.json
  - Inject memory context into agent loop prompts
  - Save successful sequences on task completion
  - NOT save failed sequences
  - Provide sb.memory property and CLI management commands
  - Respect TTL (default 30 days) for pruning stale entries
  - Handle corrupted files gracefully

What the code MUST NOT do:
  - Write any files if memory_enabled is False
  - Store API keys or credentials in memory files
  - Break any existing test
  - Change any existing public API signature
  - Require memory to be enabled

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/ --ignore-missing-imports

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-25-01: Memory MUST be opt-in — no files written if memory_enabled=False
  HB-25-02: Corrupted memory files MUST NOT crash the agent — graceful fallback to empty store
  HB-25-03: Memory files MUST NOT contain API keys or credential values
  HB-25-04: Memory pruning MUST respect TTL (default 30 days)

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
DomainMemory:
  - domain: str
  - sequences: list[ActionSequence]
  - selectors: dict[str, str]  (element_name → CSS selector)
  - preferences: dict[str, Any]
  - created_at: float
  - updated_at: float

ActionSequence:
  - task: str (task description)
  - actions: list[dict] (ordered action records)
  - success: bool
  - created_at: float
  - used_count: int

MemoryStore:
  - __init__(memory_dir: Path, ttl_days: int = 30)
  - save(domain: str, memory: DomainMemory) → None
  - load(domain: str) → DomainMemory
  - list_domains() → list[str]
  - clear(domain: str) → None
  - prune() → int (number of entries removed)
  - record_sequence(domain: str, task: str, actions: list[dict], success: bool) → None
  - record_selector(domain: str, element: str, selector: str) → None
  - get_context_for_prompt(domain: str) → str

SuperBrowser additions:
  - self._memory_store: Optional[MemoryStore]
  - sb.memory → Optional[MemoryStore] (property)

Config additions:
  - memory_enabled: bool = False
  - memory_dir: str = "~/.config/super-browser/memory"

CLI additions:
  - super-browser memory list — show domains with memory
  - super-browser memory show <domain> — display domain memory
  - super-browser memory clear <domain> — delete domain memory

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
  - Memory is append-only during a session
  - Only successful task completions are recorded
  - Selectors are only recorded if the action succeeded
  - Memory context is injected as advisory text, not command

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
  Depends on: BATCH-22 (EventBus), BATCH-23 (Recording for sequence data)
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
  Baseline at Blueprint issuance:  ~1,409
  Expected delta (all Tasks):      +15 new tests
  Expected total at Batch close:   ~1,424

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-25/TASK-01 — Memory Store
  Priority:          Critical
  Description:       Create MemoryStore with per-domain persistence, TTL pruning,
                     corrupted file handling, and prompt context generation.
  Files in scope:
    - src/super_browser/memory/__init__.py (NEW)
    - src/super_browser/memory/store.py (NEW)
    - src/super_browser/memory/types.py (NEW)
  Depends on:        None
  Required Tests:
    | Test ID          | Type | Behavior Verified                          | Failure Mode                        | Falsified By                                         | Pass Criteria                          |
    |:-----------------|:-----|:-------------------------------------------|:------------------------------------|:-----------------------------------------------------|:---------------------------------------|
    | TEST-25-01-01    | unit | store.save() writes domain file            | File not written                    | Skip file write call                                 | os.path.exists(domain_path)            |
    | TEST-25-01-02    | unit | store.load() reads domain file             | Returns empty store                 | Don't read file                                      | loaded.actions == saved.actions        |
    | TEST-25-01-03    | unit | store.get_context() returns prompt text    | Returns empty string                | Return "" instead of formatted context                | "Previous successful" in context       |
    | TEST-25-01-04    | unit | store.prune() removes expired entries      | Stale entries remain                | Remove TTL check in prune()                          | len(store) < before                    |
    | TEST-25-01-05    | unit | Corrupted JSON returns empty store         | Crash on load                       | Remove try/except in load()                          | empty store, error logged              |
    | TEST-25-01-06    | unit | Entries have timestamps > 0               | Timestamps missing                  | Don't set timestamp on creation                      | all entries.created_at > 0             |
  Acceptance Criteria:
    AC-01-01: MemoryStore persists domain memory to JSON files
    AC-01-02: load() reconstructs full memory from file
    AC-01-03: get_context_for_prompt() generates advisory text
    AC-01-04: prune() removes entries older than TTL
    AC-01-05: Corrupted files return empty store without crashing
  Traceability:
    AC-01-01 → TEST-25-01-01
    AC-01-02 → TEST-25-01-02
    AC-01-03 → TEST-25-01-03
    AC-01-04 → TEST-25-01-04
    AC-01-05 → TEST-25-01-05

TASK-02: BATCH-25/TASK-02 — Memory-Aware Agent Loop
  Priority:          High
  Description:       Wire memory into the agent loop. Load context on task start,
                     save on success, skip on failure. Wire sb.memory property.
  Files in scope:
    - src/super_browser/agent/loop.py (MODIFY)
    - src/super_browser/agent/facade.py (MODIFY)
    - src/super_browser/memory/integration.py (NEW)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type | Behavior Verified                          | Failure Mode                    | Falsified By                                   | Pass Criteria                          |
    |:-----------------|:-----|:-------------------------------------------|:--------------------------------|:-----------------------------------------------|:---------------------------------------|
    | TEST-25-02-01    | unit | Successful task saves action sequence      | Not saved                       | Skip save on success                           | store has entry for domain             |
    | TEST-25-02-02    | unit | Failed task does NOT save sequence         | Failed sequence saved            | Remove failure check                           | store has no new entry                 |
    | TEST-25-02-03    | unit | Memory context injected into LLM prompt    | Prompt unchanged                | Skip memory injection                          | "Previous successful" in prompt        |
    | TEST-25-02-04    | unit | Working selector saved to selector map     | Selector not saved              | Skip selector recording                       | store.selectors has entry              |
    | TEST-25-02-05    | unit | sb.memory returns MemoryStore              | Returns None                    | Don't initialize _memory_store                | isinstance(sb.memory, MemoryStore)     |
  Acceptance Criteria:
    AC-02-01: Successful tasks save action sequences to memory
    AC-02-02: Failed tasks do not save sequences
    AC-02-03: Memory context is injected into the LLM prompt
    AC-02-04: Successful selectors are recorded
    AC-02-05: sb.memory provides access to the store
  Traceability:
    AC-02-01 → TEST-25-02-01
    AC-02-02 → TEST-25-02-02
    AC-02-03 → TEST-25-02-03
    AC-02-04 → TEST-25-02-04
    AC-02-05 → TEST-25-02-05

TASK-03: BATCH-25/TASK-03 — Memory CLI & Config
  Priority:          Medium
  Description:       Add super-browser memory list/show/clear commands.
                     Add Config.memory_enabled and memory_dir settings.
  Files in scope:
    - src/super_browser/cli.py (MODIFY)
    - src/super_browser/config.py (MODIFY)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type | Behavior Verified                      | Failure Mode                    | Falsified By                                   | Pass Criteria                          |
    |:-----------------|:-----|:---------------------------------------|:--------------------------------|:-----------------------------------------------|:---------------------------------------|
    | TEST-25-03-01    | unit | "memory list" shows domains            | Empty output                    | Don't read memory dir                         | domain name in output                  |
    | TEST-25-03-02    | unit | "memory clear" deletes domain file     | File not deleted                | Skip os.remove                                | not os.path.exists(path)               |
    | TEST-25-03-03    | unit | Config.memory_enabled defaults to False | Defaults to True                | Change default to True                        | config.memory_enabled == False         |
    | TEST-25-03-04    | unit | Credentials not stored in memory       | API key leaked                  | Don't filter credential fields                | "api_key" not in memory JSON           |
  Acceptance Criteria:
    AC-03-01: CLI memory commands work
    AC-03-02: memory_enabled defaults to False
    AC-03-03: Credentials are filtered from memory files
  Traceability:
    AC-03-01 → TEST-25-03-01, TEST-25-03-02
    AC-03-02 → TEST-25-03-03
    AC-03-03 → TEST-25-03-04

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: MemoryStore persists action sequences per domain
  BAC-02: Agent loop uses memory to accelerate repeat tasks
  BAC-03: CLI commands for memory management
  BAC-04: Memory is opt-in (disabled by default)
  BAC-05: No existing tests broken
  BAC-06: CHANGELOG deferred to BATCH-26
  BAC-07: All documents archived under /docs/aiv/BATCH-25/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
Reviewer Report ID:       REVIEW-BATCH-25-2026-05-08
Review Cycle:             1
Lead Decision:            [x] ACCEPT

Reviewer fallback applied per §4.5.

Blueprint Version after response: 1.0
Lead Sign:                Lead Programmer — 2026-05-08 04:05

═══════════════════════════════════════════════════════════
