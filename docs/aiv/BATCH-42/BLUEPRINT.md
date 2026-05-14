```
BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-42
Blueprint Version:        1.1
Cycle Mode:               STANDARD
Lead Programmer:          Lead
Date Issued:              2026-05-14
Task Sequencing:          TASK-01 → TASK-02

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────

Add a deterministic agent efficiency benchmark for regression
detection, and high-level action presets (job, qa) that compile
to existing controller calls for common workflows.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────

What the code MUST do:
  - Create a benchmark script that models representative
    workflows and measures tool call count, output bytes,
    stale-ref rate, and category coverage
  - Output JSON + Markdown report
  - Support --compare baseline.json for regression detection
  - Add BrowserJob preset: declarative step sequence that
    compiles to controller calls, returns ActionResult list
  - Add QASmoke preset: diagnostic smoke test sequence
    (open → wait → assert → network check → screenshot)
  - Both presets return structured results with categories

What the code MUST NOT do:
  - Change the stealth stack
  - Change Patchright/CDP interaction patterns
  - Add new runtime dependencies
  - Spawn browsers in benchmark (mock-based)
  - Modify existing controller or facade methods

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────

  HB-01: All 1,990+ existing tests MUST continue passing.
  HB-02: No browser spawning in benchmark or preset tests.
  HB-03: Benchmark is mock-based — no real browser required.
  HB-04: Presets are thin compilation layers — they delegate
         to existing controller/facade methods, never bypass.

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-42/TASK-01
  Priority:          P1
  Description:       Deterministic agent efficiency benchmark.
                     Models representative workflows, measures
                     call count, output bytes, stale-ref rate,
                     and category coverage. Outputs JSON + MD.
  Files in scope:
    scripts/agent_efficiency_benchmark.py           (NEW)
    tests/test_benchmark/test_efficiency.py         (NEW — 6 tests)
  Depends on:        BATCH-40 (result categories)
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Failure Mode               | Falsified By                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------|:------------------------------------|:---------------------------------------|
    | TEST-42-01-01    | unit   | Benchmark produces JSON output           | Missing output format      | Run benchmark with mock data        | Output is valid JSON with required keys |
    | TEST-42-01-02    | unit   | Benchmark counts tool calls              | Incorrect count            | Run with 5 mock actions             | call_count == 5 |
    | TEST-42-01-03    | unit   | Benchmark measures output bytes          | Byte count off             | Run with known-size results         | output_bytes matches expected |
    | TEST-42-01-04    | unit   | Benchmark computes stale-ref rate        | Rate calculation error     | 2 stale out of 10 actions           | stale_ref_rate == 0.2 |
    | TEST-42-01-05    | unit   | --compare detects regression             | False negative             | Compare against baseline with higher call count | report.regression == True |
    | TEST-42-01-06    | unit   | Benchmark produces Markdown summary      | Missing MD output          | Run benchmark                       | Output contains table header |
  Traceability:
    AC-01-01 → TEST-42-01-01
    AC-01-02 → TEST-42-01-02, TEST-42-01-03
    AC-01-03 → TEST-42-01-04
    AC-01-04 → TEST-42-01-05
    AC-01-05 → TEST-42-01-06

  Benchmark output schema (JSON):
    {
      "timestamp": "2026-05-14T...",
      "version": "1.6.0",
      "workflows": {
        "navigate_and_extract": {
          "call_count": 4,
          "output_bytes": 1234,
          "stale_ref_count": 0,
          "stale_ref_rate": 0.0,
          "category_distribution": {"navigation": 2, "mutation": 1, "stale_ref": 1},
          "duration_ms": 56.7
        }
      },
      "aggregate": {
        "total_calls": 12,
        "total_output_bytes": 4567,
        "overall_stale_ref_rate": 0.083,
        "category_coverage": ["navigation", "mutation", "inspection", "stale_ref"]
      }
    }

  Benchmark workflow models (mock-based):
    - "navigate_and_extract": navigate → observe → extract → screenshot
    - "form_fill": navigate → fill → fill → click → assert
    - "qa_smoke": open → wait → assert → network_check → screenshot
    - "error_recovery": click (stale) → retry → click (ok) → verify

  --compare mode:
    Load baseline JSON, compare aggregate metrics.
    Flag regression if: call_count > baseline * 1.2,
    output_bytes > baseline * 1.3, stale_ref_rate > baseline * 1.5.

TASK-02: BATCH-42/TASK-02
  Priority:          P2
  Description:       High-level action presets. BrowserJob
                     compiles declarative steps to controller
                     calls. QASmoke runs a diagnostic sequence.
                     Both return structured ActionResult lists.
  Files in scope:
    src/super_browser/interaction/presets.py           (NEW)
    src/super_browser/interaction/__init__.py          (MODIFY — export CompiledStep, BrowserJob, QASmoke)
    tests/test_interaction/test_presets.py             (NEW — 8 tests)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type   | Behavior Verified                        | Failure Mode               | Falsified By                        | Pass Criteria                          |
    |:-----------------|:-------|:-----------------------------------------|:---------------------------|:------------------------------------|:---------------------------------------|
    | TEST-42-02-01    | unit   | BrowserJob class exists                  | Missing class              | Import BrowserJob                   | Class is callable |
    | TEST-42-02-02    | unit   | BrowserJob validates step schemas        | Invalid step accepted      | Step without "action" key           | Raises ValueError |
    | TEST-42-02-03    | unit   | BrowserJob compiles to action list       | Compilation failure        | 3-step job                          | compile() returns 3 CompiledStep items |
    | TEST-42-02-04    | unit   | BrowserJob compiles known actions        | Unknown action rejected    | Step with action="fly"              | Raises ValueError with valid actions list |
    | TEST-42-02-05    | unit   | QASmoke generates 5-step sequence        | Wrong step count           | QASmoke(url="https://x.com")       | len(steps) == 5 |
    | TEST-42-02-06    | unit   | QASmoke steps have correct actions       | Wrong action types         | Inspect step.action for each        | [open, wait, assert, network, screenshot] |
    | TEST-42-02-07    | unit   | CompiledStep has target and params       | Missing fields             | Inspect compiled step               | action, params, description all present |
    | TEST-42-02-08    | unit   | Caller maps CompiledSteps to ActionResult| Wrong integration path      | Mock controller, map compiled step  | Mapped result is ActionResult |
  Traceability:
    AC-02-01 → TEST-42-02-01, TEST-42-02-02, TEST-42-02-03, TEST-42-02-04
    AC-02-02 → TEST-42-02-05, TEST-42-02-06, TEST-42-02-07, TEST-42-02-08

  BrowserJob design:
    ```python
    @dataclass
    class CompiledStep:
        action: str
        params: dict[str, Any]
        description: str

    class BrowserJob:
        VALID_ACTIONS = frozenset({
            "open", "click", "fill", "select", "hover",
            "scroll", "keypress", "screenshot", "assert_text",
            "wait", "extract", "network", "assert",
        })

        def __init__(self, steps: list[dict], *, name: str = "unnamed"):
            self.steps = steps
            self.name = name
            self._validate()

        def _validate(self) -> None: ...
        def compile(self) -> list[CompiledStep]: ...
    ```

  QASmoke design:
    ```python
    class QASmoke:
        def __init__(self, url: str, *, assert_text: str = "",
                     wait_seconds: float = 2.0):
            self.url = url
            self.assert_text = assert_text
            self.wait_seconds = wait_seconds

        def compile(self) -> list[CompiledStep]:
            return [
                CompiledStep("open", {"url": self.url}, "Open target page"),
                CompiledStep("wait", {"seconds": self.wait_seconds}, "Wait for page load"),
                CompiledStep("assert_text", {"text": self.assert_text}, "Assert expected text"),
                CompiledStep("network", {"check_console_errors": True}, "Check for console errors"),
                CompiledStep("screenshot", {"path": "qa_smoke.png"}, "Capture evidence screenshot"),
            ]
    ```

  IMPORTANT: Presets compile to step descriptions. They do NOT
  execute anything directly. Execution is the caller's responsibility
  (the agent loop, CLI, or test code calls the controller methods).
  This keeps presets as pure data transformations with zero
  browser dependency.

  Benchmark version field: sourced from `super_browser.__version__`
  dynamically, not hardcoded. (CHK-07)

  --compare regression thresholds are initial tuning targets
  (1.2/1.3/1.5 for call_count/output_bytes/stale_ref_rate).
  These can be made configurable via CLI flags in future.
  (CHK-04)

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────

  BAC-01: Benchmark produces valid JSON + Markdown reports
  BAC-02: Benchmark supports --compare regression detection
  BAC-03: BrowserJob validates and compiles declarative steps
  BAC-04: QASmoke generates a 5-step diagnostic sequence
  BAC-05: All 1,990+ existing tests continue passing
  BAC-06: python -m ruff check src/ scripts/ → zero warnings
  BAC-07: All docs archived under /docs/aiv/BATCH-42/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer: 260514-calm-steel (7 flags: 3 Must Fix, 3 Advisory, 1 Nit)

CHK-01 [Must Fix] → RESOLVED. "network" added to VALID_ACTIONS.
CHK-02 [Must Fix] → RESOLVED. "assert_text" already in set;
  also added "assert" for broader coverage.
CHK-03 [Must Fix] → RESOLVED. Category distribution now uses
  full category names (navigation, mutation, stale_ref, etc.)
  instead of success/failure buckets.
CHK-04 [Advisory] → ACCEPTED. Note added about thresholds
  being initial tuning targets.
CHK-05 [Advisory] → ACCEPTED. Export list specified:
  CompiledStep, BrowserJob, QASmoke.
CHK-06 [Advisory] → ACCEPTED. TEST-42-02-08 reworded to test
  caller integration path (compile → mock-execute → ActionResult).
CHK-07 [Nit] → ACCEPTED. Version sourced from
  super_browser.__version__.

**LEAD DECISION: ACCEPT WITH MODIFICATIONS. Blueprint v1.1.**

═══════════════════════════════════════════════════════════
```
