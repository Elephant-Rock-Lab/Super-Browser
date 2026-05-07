BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-20
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead (single-session override)
Date Issued:              2026-05-07
Review SLA:               30 min
Execution SLA per Task:   90 min
Partial Sign-Off SLA:     15 min
Task Sequencing:          Sequential (T1→T2→T3)

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
Add core web automation features: multi-tab support, file upload/download,
iframe interaction, Shadow DOM piercing, and network interception.
Ship as v1.1.0.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Support opening, switching between, and closing multiple tabs
  - Upload files to <input type="file"> elements
  - Download files and return the path
  - Enter and interact with iframe content
  - Pierce Shadow DOM for element queries
  - Intercept, mock, and block network requests
  - Maintain backward compatibility with all existing APIs

What the code MUST NOT do:
  - Change any existing public API signatures
  - Break any existing test
  - Add new required dependencies

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-20-01: open_tab() returns a TabHandle with an integer tab_id
  HB-20-02: switch_tab(tab_id) changes the active page for all subsequent actions
  HB-20-03: upload_file(selector, path) sets the file on <input type="file">
  HB-20-04: download(url_or_selector) returns a DownloadResult with file_path
  HB-20-05: enter_frame(selector) scopes all subsequent interactions to that frame
  HB-20-06: query_shadow(host_selector, inner_selector) returns element text/bounds
  HB-20-07: intercept_requests(pattern, handler) enables network interception

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline at Blueprint issuance:  1,370 existing tests
  Expected delta (all Tasks):      +20 new tests
  Expected total at Batch close:   1,390

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-20/TASK-01 — Multi-Tab Support + File I/O
  Description:      Add tab management and file upload/download
  Files in scope:
    - src/super_browser/browser/session.py
    - src/super_browser/browser/page.py
    - src/super_browser/browser/tabs.py (NEW)
    - src/super_browser/agent/facade.py
    - src/super_browser/results/__init__.py
    - src/super_browser/results/types.py
  Depends on:       None
  Required Tests:
    | Test ID    | Type  | Pass Criteria                                    |
    |:-----------|:------|:-------------------------------------------------|
    | TEST-20-01 | unit  | open_tab() creates new tab, returns TabHandle    |
    | TEST-20-02 | unit  | switch_tab(tab_id) changes active page           |
    | TEST-20-03 | unit  | close_tab(tab_id) removes tab                    |
    | TEST-20-04 | unit  | list_tabs() returns all open tabs                |
    | TEST-20-05 | unit  | upload_file(selector, path) triggers file input  |
    | TEST-20-06 | unit  | download() returns DownloadResult with file_path |
  Acceptance Criteria:
    AC-01-01: Can open, switch, list, and close tabs
    AC-01-02: Can upload a file to a form
    AC-01-03: Can download a file and get its path

TASK-02: BATCH-20/TASK-02 — iframe + Shadow DOM
  Description:      Add frame scoping and shadow DOM piercing
  Files in scope:
    - src/super_browser/browser/frames.py (NEW)
    - src/super_browser/browser/page.py
    - src/super_browser/interaction/controller.py
    - src/super_browser/agent/facade.py
  Depends on:       TASK-01
  Required Tests:
    | Test ID    | Type  | Pass Criteria                                        |
    |:-----------|:------|:-----------------------------------------------------|
    | TEST-20-07 | unit  | enter_frame(selector) scopes interactions             |
    | TEST-20-08 | unit  | exit_frame() returns to main frame                    |
    | TEST-20-09 | unit  | Nested frame enter/exit works                         |
    | TEST-20-10 | unit  | query_shadow(host, inner) returns element data        |
    | TEST-20-11 | unit  | Shadow DOM pierce for click/fill cascades correctly   |
  Acceptance Criteria:
    AC-02-01: Can enter and interact with iframe content
    AC-02-02: Can exit iframe back to main frame
    AC-02-03: Can query elements inside Shadow DOM

TASK-03: BATCH-20/TASK-03 — Network Interception + Version Bump
  Description:      Add network interception and bump to v1.1.0
  Files in scope:
    - src/super_browser/browser/network.py (NEW)
    - src/super_browser/agent/facade.py
    - src/super_browser/__init__.py
    - pyproject.toml
    - CHANGELOG.md
  Depends on:       TASK-02
  Required Tests:
    | Test ID    | Type  | Pass Criteria                                        |
    |:-----------|:------|:-----------------------------------------------------|
    | TEST-20-12 | unit  | intercept_requests(pattern, handler) intercepts req   |
    | TEST-20-13 | unit  | block_requests(pattern) blocks matching requests      |
    | TEST-20-14 | unit  | mock_response(pattern, body) returns mocked response  |
    | TEST-20-15 | unit  | clear_interceptions() removes all handlers            |
  Acceptance Criteria:
    AC-03-01: Can intercept, block, and mock network requests
    AC-03-02: Version bumped to 1.1.0
    AC-03-03: CHANGELOG updated
    AC-03-04: All 1,390 tests pass

───────────────────────────────────────────────────────────
BATCH-LEVEL ACCEPTANCE CRITERIA
───────────────────────────────────────────────────────────
  BAC-01: Multi-tab support fully functional
  BAC-02: File upload and download working
  BAC-03: iframe and Shadow DOM support
  BAC-04: Network interception operational
  BAC-05: Full test suite passes
  BAC-06: CHANGELOG.md updated
  BAC-07: All documents archived under /docs/aiv/BATCH-20/

═══════════════════════════════════════════════════════════
