BATCH BLUEPRINT
═══════════════════════════════════════════════════════════

Batch ID:                 BATCH-21
Blueprint Version:        1.0
Cycle Mode:               STANDARD
Lead Programmer:          Lead (single-session override)
Date Issued:              2026-05-07
Task Sequencing:          Sequential (T1→T2→T3→T4)

───────────────────────────────────────────────────────────
BATCH GOAL
───────────────────────────────────────────────────────────
Add distribution infrastructure and agent ecosystem integration:
PyPI publishing prep, Docker image, MCP server, and cloud browser support.
Ship as v1.2.0.

───────────────────────────────────────────────────────────
SCOPE STATEMENT
───────────────────────────────────────────────────────────
What the code MUST do:
  - Package ready for PyPI (metadata, classifiers, entry point)
  - Dockerfile + docker-compose.yml for containerized deployment
  - MCP server exposing browser tools to any MCP-compatible agent
  - Cloud browser connector (Browserbase/Steel abstract interface)
  - Structured schema extraction for extract()

What the code MUST NOT do:
  - Auto-publish to PyPI (manual publish step)
  - Require Docker to use the library
  - Require cloud browser credentials
  - Break any existing test

───────────────────────────────────────────────────────────
HARD BOUNDARIES
───────────────────────────────────────────────────────────
  HB-21-01: pyproject.toml has all PyPI classifiers and metadata
  HB-21-02: Dockerfile builds and runs `python -c "from super_browser import __version__"`
  HB-21-03: MCP server exposes at least: navigate, click, fill, extract, observe, screenshot
  HB-21-04: Cloud browser connector has a unified abstract base with connect() returning BrowserSession
  HB-21-05: extract(schema=...) validates output against JSON schema

───────────────────────────────────────────────────────────
TEST BASELINE
───────────────────────────────────────────────────────────
  Baseline:  1,358 tests
  Expected:  +15 new tests
  Total:     ~1,373

───────────────────────────────────────────────────────────
TASK LIST
───────────────────────────────────────────────────────────

TASK-01: BATCH-21/TASK-01 — PyPI Publishing Prep + Docker
  Description:      Finalize pyproject.toml, add CLI entry point, create Dockerfile
  Files in scope:
    - pyproject.toml
    - src/super_browser/cli.py (NEW)
    - Dockerfile (NEW)
    - docker-compose.yml (NEW)
  Acceptance Criteria:
    AC-01-01: pyproject.toml has PyPI metadata, classifiers, [console_scripts]
    AC-01-02: `super-browser --version` CLI command works
    AC-01-03: Dockerfile builds successfully

TASK-02: BATCH-21/TASK-02 — MCP Server
  Description:      Create MCP server exposing browser tools
  Files in scope:
    - src/super_browser/mcp_server.py (NEW)
  Acceptance Criteria:
    AC-02-01: MCP server exposes navigate, click, fill, extract, observe, screenshot
    AC-02-02: Can be run with `python -m super_browser.mcp_server`

TASK-03: BATCH-21/TASK-03 — Cloud Browser + Schema Extraction
  Description:      Cloud browser abstraction + structured extraction
  Files in scope:
    - src/super_browser/browser/cloud.py (NEW)
    - src/super_browser/agent/facade.py
  Acceptance Criteria:
    AC-03-01: CloudBrowserConnector ABC with connect() → BrowserSession
    AC-03-02: BrowserbaseConnector implementation
    AC-03-03: extract(schema={...}) validates output

TASK-04: BATCH-21/TASK-04 — Version Bump + CHANGELOG
  Files in scope:
    - src/super_browser/__init__.py
    - pyproject.toml
    - CHANGELOG.md
  Acceptance Criteria:
    AC-04-01: Version = 1.2.0
    AC-04-02: CHANGELOG updated

═══════════════════════════════════════════════════════════
