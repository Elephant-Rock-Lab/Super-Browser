BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-23
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
Create a session recording system that captures every browser action with
before/after screenshots and DOM snapshots, saves recordings as JSON and
HTML, and supports replay with mismatch detection. This builds on the
EventBus from BATCH-22.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Record every navigate, click, fill, extract, scroll, observe, and error
  - Each record includes: timestamp, action, params, before/after screenshot (base64), page URL, title, error details
  - Save/load recordings as JSON with schema_version
  - Export recordings as HTML audit reports
  - Replay recordings against a live browser with mismatch detection
  - Expose sb.recording property and sb.replay(path) method

What the code MUST NOT do:
  - Slow down any action by more than 50ms
  - Block actions on screenshot capture failure
  - Break any existing test
  - Change any existing public API signature

───────────────────────────────────────────────────────────
LINT COMMAND
───────────────────────────────────────────────────────────
  Lint command: python -m ruff check src/ --ignore-missing-imports

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-23-01: Recording MUST NOT slow down any action by more than 50ms (measured via time.monotonic delta)
  HB-23-02: Screenshot capture failures MUST NOT block the action — log and continue with screenshot=None
  HB-23-03: Recording JSON MUST include a schema_version field (string, e.g. "1.0")
  HB-23-04: Recording files MUST NOT contain API keys or credentials (context values are filtered)

───────────────────────────────────────────────────────────
DATA MODELS / SCHEMA
───────────────────────────────────────────────────────────
RecordingSession:
  - session_id: str (UUID)
  - started_at: float (monotonic)
  - actions: list[ActionRecord]
  - metadata: dict (action_count, error_count, duration_ms, schema_version)

ActionRecord:
  - index: int
  - timestamp: float
  - action: str
  - params: dict
  - url: str
  - title: str
  - screenshot_before: Optional[str] (base64)
  - screenshot_after: Optional[str] (base64)
  - ok: bool
  - error: Optional[str]
  - duration_ms: float

SessionRecorder:
  - __init__(event_bus: EventBus, cdp_bridge: CDPBridge, max_screenshots: int = 100)
  - start() → None
  - stop() → RecordingSession
  - export_json() → str
  - export_html() → str
  - save(path: str) → None
  - @classmethod load(path: str) → RecordingSession

RecordingReplayer:
  - __init__(sb: SuperBrowser)
  - replay(recording: RecordingSession, delay_ms: float = 100) → ReplayReport

ReplayReport:
  - total_actions: int
  - matched: int
  - mismatches: list[MismatchRecord]
  - duration_ms: float

MismatchRecord:
  - index: int
  - action: str
  - expected: dict
  - actual: dict
  - reason: str

SuperBrowser additions:
  - self._recorder: Optional[SessionRecorder]
  - self.recording → Optional[SessionRecorder] (property)
  - async def replay(path: str) → ActionResult

Existing modules to modify:
  - src/super_browser/agent/facade.py — add _recorder, recording property, replay() method, enable_recording() in start()
  - src/super_browser/events/types.py — event context already emitted by BATCH-22

───────────────────────────────────────────────────────────
AUTHORITY RULES
───────────────────────────────────────────────────────────
  - Recording is opt-in: must call sb.enable_recording() or pass config flag
  - Replay does not modify the original recording file
  - Screenshots are capped at max_screenshots to prevent memory exhaustion

───────────────────────────────────────────────────────────
DEPENDENCY MAP
───────────────────────────────────────────────────────────
  Depends on: BATCH-22 (EventBus, lifecycle hooks)
  Required by: BATCH-24 (CLI replay command), BATCH-25 (memory from recordings)

───────────────────────────────────────────────────────────
STATE.md STATUS
───────────────────────────────────────────────────────────
  State file exists:       [ ] NO — will create at BATCH-26 or earlier if required
  Last Updated:            N/A
  Batches since update:    N/A
  Reconciliation audit:    N/A

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  1,385 existing tests (1,358 + 27 from BATCH-22)
  Expected delta (all Tasks):      +15 new tests
  Expected total at Batch close:   1,400

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-23/TASK-01 — Recording Engine
  Priority:          Critical
  Description:       Create SessionRecorder that subscribes to EventBus lifecycle
                     events and captures action records with timestamps, params,
                     URLs, and screenshots. Implements start(), stop(), export_json().
  Files in scope:
    - src/super_browser/recording/__init__.py (NEW)
    - src/super_browser/recording/recorder.py (NEW)
    - src/super_browser/recording/types.py (NEW)
  Depends on:        None (uses EventBus from BATCH-22)
  Required Tests:
    | Test ID          | Type | Behavior Verified                          | Failure Mode                        | Falsified By                                         | Pass Criteria                              |
    |:-----------------|:-----|:-------------------------------------------|:------------------------------------|:-----------------------------------------------------|:-------------------------------------------|
    | TEST-23-01-01    | unit | Recorder captures navigate event           | Navigate events not captured        | Remove event subscription in recorder.__init__        | records[0].action == "navigate"            |
    | TEST-23-01-02    | unit | Recorder captures click with selector      | Selector missing from record        | Don't store params in record                         | record.params["target"] == "#btn"          |
    | TEST-23-01-03    | unit | Recorder captures error events             | Errors not recorded                 | Only subscribe to success events                     | record.error is not None                    |
    | TEST-23-01-04    | unit | Recorder respects max_screenshots limit    | Memory grows unbounded              | Remove size check before appending screenshot        | len(screenshots) <= max_screenshots         |
    | TEST-23-01-05    | unit | export_json() produces valid JSON          | Export returns invalid string       | Return raw dict instead of json.dumps                | json.loads(export_json()) succeeds          |
    | TEST-23-01-06    | unit | Records include timestamps > 0             | Timestamps are 0                    | Don't call time.monotonic() on record creation       | all timestamps > 0                          |
  Acceptance Criteria:
    AC-01-01: Recorder subscribes to all lifecycle events and captures action records
    AC-01-02: Each record has timestamp, action, params, url, title
    AC-01-03: Screenshot capture failure does not block recording
    AC-01-04: max_screenshots limit is enforced
    AC-01-05: export_json() produces parseable JSON with schema_version
  Traceability:
    AC-01-01 → TEST-23-01-01, TEST-23-01-02, TEST-23-01-03
    AC-01-02 → TEST-23-01-06
    AC-01-03 → TEST-23-01-04
    AC-01-04 → TEST-23-01-04
    AC-01-05 → TEST-23-01-05

TASK-02: BATCH-23/TASK-02 — Persistence & HTML Export
  Priority:          High
  Description:       Add save/load for recordings (JSON files) and HTML report
                     generation. Include recording metadata.
  Files in scope:
    - src/super_browser/recording/persistence.py (NEW)
    - src/super_browser/recording/report.py (NEW)
  Depends on:        TASK-01
  Required Tests:
    | Test ID          | Type | Behavior Verified                      | Failure Mode                  | Falsified By                                   | Pass Criteria                              |
    |:-----------------|:-----|:---------------------------------------|:------------------------------|:-----------------------------------------------|:-------------------------------------------|
    | TEST-23-02-01    | unit | save() writes JSON file to disk        | File not created              | Skip file write call                            | os.path.exists(path) is True               |
    | TEST-23-02-02    | unit | load() reconstructs full recording     | Fields lost in serialization  | Don't deserialize action records                | loaded.actions == original.actions          |
    | TEST-23-02-03    | unit | export_html() produces valid HTML      | Output is empty               | Return empty string instead of template         | "<html>" in html_output                    |
    | TEST-23-02-04    | unit | Metadata includes action_count         | Count is 0                    | Hardcode 0 instead of len(actions)              | metadata["action_count"] == len(actions)   |
  Acceptance Criteria:
    AC-02-01: save() writes a valid JSON file that load() can reconstruct
    AC-02-02: export_html() produces a human-readable audit report
    AC-02-03: Metadata includes action_count, error_count, duration_ms, schema_version
  Traceability:
    AC-02-01 → TEST-23-02-01, TEST-23-02-02
    AC-02-02 → TEST-23-02-03
    AC-02-03 → TEST-23-02-04

TASK-03: BATCH-23/TASK-03 — Replay Engine & Facade Integration
  Priority:          High
  Description:       Create RecordingReplayer that replays a saved recording
                     against a live browser. Wire sb.recording property and
                     sb.replay(path) into the SuperBrowser facade.
  Files in scope:
    - src/super_browser/recording/replayer.py (NEW)
    - src/super_browser/agent/facade.py (MODIFY — add recording property, replay())
  Depends on:        TASK-01, TASK-02
  Required Tests:
    | Test ID          | Type        | Behavior Verified                          | Failure Mode                    | Falsified By                                   | Pass Criteria                              |
    |:-----------------|:------------|:-------------------------------------------|:--------------------------------|:-----------------------------------------------|:-------------------------------------------|
    | TEST-23-03-01    | unit        | Replayer dispatches navigate actions       | Navigate skipped                | Skip "navigate" case in dispatch                | navigate called with recorded URL           |
    | TEST-23-03-02    | unit        | Replayer dispatches click actions          | Click not executed              | Skip "click" case in dispatch                   | click called with recorded selector         |
    | TEST-23-03-03    | unit        | Replayer dispatches fill actions           | Fill not executed               | Skip "fill" case in dispatch                    | fill called with recorded value             |
    | TEST-23-03-04    | unit        | Replayer detects mismatches               | Mismatch not detected           | Always return matched=True                       | report.mismatches is populated              |
    | TEST-23-03-05    | unit        | sb.recording returns SessionRecorder      | Returns None                    | Don't initialize _recorder                      | isinstance(sb.recording, SessionRecorder)   |
  Acceptance Criteria:
    AC-03-01: Replayer replays navigate, click, fill, extract, scroll actions
    AC-03-02: ReplayReport lists mismatches between recorded and actual results
    AC-03-03: sb.recording property provides access to the active recorder
    AC-03-04: sb.replay(path) loads and replays a recording file
  Traceability:
    AC-03-01 → TEST-23-03-01, TEST-23-03-02, TEST-23-03-03
    AC-03-02 → TEST-23-03-04
    AC-03-03 → TEST-23-03-05
    AC-03-04 → TEST-23-03-05

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: SessionRecorder captures all lifecycle action types + errors
  BAC-02: Recordings can be saved as JSON and loaded back
  BAC-03: HTML export produces human-readable audit reports
  BAC-04: Replayer replays recordings with mismatch detection
  BAC-05: No existing tests broken (1,385 baseline maintained)
  BAC-06: CHANGELOG update deferred to BATCH-26
  BAC-07: All documents archived under /docs/aiv/BATCH-23/

───────────────────────────────────────────────────────────
LEAD RESPONSE TO REVIEW REPORT
───────────────────────────────────────────────────────────

Reviewer Report ID:       REVIEW-BATCH-23-2026-05-08
Review Cycle:             1
Lead Decision:            [x] ACCEPT

Reviewer session stalled (30 min SLA exhausted, no reply to message probe).
Lead wrote Review Report directly per §4.5 (Reviewer Fallback Procedure).

Blueprint Version after response: 1.0
Lead Sign:                Lead Programmer — 2026-05-08 02:05

═══════════════════════════════════════════════════════════
