BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-17
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
Fix all 6 critical bugs found in post-release audit, fix remaining P0/P1 UX
issues, and ship as v1.0.1 patch release.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Wire `_check_retry_budget()` into the action dispatch path
  - Fix `replan()` call to use correct protocol kwargs
  - Add public `budget_remaining` property to budget clients
  - Rename dual `BudgetAwareLLMClient` in budget/client.py
  - Replace sync LLM clients with async in vision providers
  - Fix JS injection in checkpoint restore
  - Add built-in `MockLLMClient` to `super_browser.testing`
  - Create `.env.example`
  - Fix README quickstart code
  - Bump version to 1.0.1

What the code MUST NOT do:
  - Add new public API methods (except `MockLLMClient`)
  - Change the `LLMClient` protocol interface
  - Modify any test files from BATCH-01 through BATCH-16
  - Remove any existing public exports

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/ && python -m mypy src/ --ignore-missing-imports

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-17-01: `_check_retry_budget()` MUST be called in `_dispatch_action()` before any tool execution
  HB-17-02: `replan()` call in `loop.py` MUST use kwargs `original_plan`, `failed_step`, `error`
  HB-17-03: All vision providers MUST use async client classes (`AsyncAnthropic`, `AsyncOpenAI`)
  HB-17-04: Checkpoint restore MUST use `Runtime.callFunctionOn` or parameterized CDP — NOT string concatenation into JS
  HB-17-05: No class named `BudgetAwareLLMClient` may exist in `budget/client.py` after rename
  HB-17-06: `MockLLMClient` MUST satisfy `isinstance(mock, LLMClient) == True`
  HB-17-07: README quickstart code MUST run copy-paste without error
  HB-17-08: `__version__` MUST equal `"1.0.1"` after this batch

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
LLMClient.replan() protocol (agent/llm/protocol.py:44):
  async def replan(self, *, instruction: str, original_plan: list[dict],
                   failed_step: int, error: str) -> list[dict]

RetryBudget (agent/types.py):
  @dataclass
  class RetryBudget:
      max_retries_per_action: int = 3
      def can_retry(self, action_name: str, attempt: int) -> bool

BudgetAwareLLMClient (agent/llm/budget_aware.py:66):
  class BudgetAwareLLMClient:
      __init__(self, client: LLMClient, governor: TokenBudgetGovernor, model: str)
      property: budget_remaining -> float

budget/client.py class to rename to `BudgetCascadeClient`:
  __init__(self, governor, cascade, credential_pool, circuit_breaker, compressor, llm_client=None)

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
  - BudgetAwareLLMClient in agent/llm/ remains the primary public class
  - budget/client.py class is internal; rename to avoid confusion
  - All existing tests must continue to pass

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
  Depends on: BATCH-01 through BATCH-16 (v1.0.0 release)
  Depends on: Post-release fix commit b097cba (version, silent errors, extract)

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  1,381 existing tests
  Expected delta (all Tasks):      +18 new tests
  Expected total at Batch close:   1,399

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-17/TASK-01 — Fix 6 Critical Bugs
  Description:      Fix all 6 critical bugs identified in post-release audit
  Files in scope:
    - src/super_browser/agent/loop.py
    - src/super_browser/agent/facade.py
    - src/super_browser/budget/client.py
    - src/super_browser/budget/__init__.py
    - src/super_browser/agent/llm/budget_aware.py
    - src/super_browser/vision/providers.py
    - src/super_browser/recovery/checkpoint.py
  Depends on:       None
  Required Tests:
    | Test ID          | Type        | Pass Criteria                                       |
    |:-----------------|:------------|:----------------------------------------------------|
    | TEST-17-01       | integration | _check_retry_budget blocks action at limit          |
    | TEST-17-02       | integration | _check_retry_budget allows within limit             |
    | TEST-17-03       | unit        | BudgetCascadeClient import works (renamed class)    |
    | TEST-17-04       | unit        | BudgetAwareLLMClient has budget_remaining property  |
    | TEST-17-05       | integration | facade.act() uses budget_remaining (no _governor)   |
    | TEST-17-06       | integration | replan() call uses correct kwargs                   |
    | TEST-17-07       | unit        | AsyncAnthropic used in AnthropicVisionProvider      |
    | TEST-17-08       | unit        | AsyncOpenAI used in OpenAIVisionProvider            |
    | TEST-17-09       | unit        | checkpoint restore uses no string concatenation     |
  Acceptance Criteria:
    AC-01-01: _check_retry_budget() called in _dispatch_action before tool.handler
    AC-01-02: replan() uses original_plan, failed_step, error kwargs
    AC-01-03: budget/client.py class renamed to BudgetCascadeClient
    AC-01-04: BudgetAwareLLMClient has public budget_remaining property
    AC-01-05: facade.py uses budget_remaining not _governor
    AC-01-06: vision/providers.py uses AsyncAnthropic and AsyncOpenAI
    AC-01-07: checkpoint restore uses safe CDP call

TASK-02: BATCH-17/TASK-02 — Fix P0/P1 UX + Add MockLLMClient
  Description:      Fix remaining UX issues, add built-in MockLLMClient, create .env.example
  Files in scope:
    - src/super_browser/testing.py (NEW)
    - src/super_browser/__init__.py
    - .env.example (NEW)
    - README.md
    - docs/api-reference.md
  Depends on:       TASK-01
  Required Tests:
    | Test ID          | Type        | Pass Criteria                                       |
    |:-----------------|:------------|:----------------------------------------------------|
    | TEST-17-10       | unit        | MockLLMClient satisfies LLMClient protocol          |
    | TEST-17-11       | integration | MockLLMClient works with full SuperBrowser lifecycle|
    | TEST-17-12       | unit        | .env.example lists all Config.from_env vars         |
  Acceptance Criteria:
    AC-02-01: MockLLMClient importable from super_browser.testing
    AC-02-02: README quickstart runs copy-paste
    AC-02-03: .env.example exists with documented vars
    AC-02-04: api-reference.md header says v1.0.0

TASK-03: BATCH-17/TASK-03 — Version Bump + Release
  Description:      Bump version to 1.0.1, update CHANGELOG, tag release
  Files in scope:
    - pyproject.toml
    - src/super_browser/__init__.py
    - CHANGELOG.md
  Depends on:       TASK-02
  Required Tests:
    | Test ID          | Type        | Pass Criteria                                       |
    |:-----------------|:------------|:----------------------------------------------------|
    | TEST-17-13       | manual      | __version__ == "1.0.1"                              |
    | TEST-17-14       | manual      | Full test suite passes (1381+ tests)                |
    | TEST-17-15       | manual      | git tag v1.0.1 exists                               |
  Acceptance Criteria:
    AC-03-01: pyproject.toml version = "1.0.1"
    AC-03-02: __version__ = "1.0.1"
    AC-03-03: CHANGELOG has v1.0.1 section
    AC-03-04: git tag v1.0.1 created

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: All 6 critical bugs fixed and verified
  BAC-02: README quickstart code runs copy-paste
  BAC-03: CHANGELOG.md updated with BATCH-17 entry
  BAC-04: All documents archived under /docs/aiv/BATCH-17/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────
[Completed after Phase I-B]

═══════════════════════════════════════════════════════════
