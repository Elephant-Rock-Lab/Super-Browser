# Track D — API Ergonomics Audit

> **v2.1.1 baseline** — 2026-06-16
>
> Discovery document for the v2.2 "API Ergonomics" track.
> No code changes in this audit — findings only.

---

## Methodology

Systematic inspection of:

1. Public API surface (`__all__`, signatures, return types)
2. CLI help output, command naming, option consistency
3. Testing utilities (`E2EContext`, `MockLLMClient`, report builders)
4. Documentation (quickstart, API reference, architecture, examples)
5. Migration remnants from v1.x → v2.0

---

## Findings

### Bucket 1 — Patch-safe (docs, help text, examples, aliases)

These changes are safe to ship without any risk to existing code.

#### 1.1 Stale `SuperBrowserConfig` in API reference

`docs/api-reference.md` still references `SuperBrowserConfig` in three
places — a class removed in v2.0:

- Line 45: constructor signature shows `config: Optional[SuperBrowserConfig]`
- Line 54: parameter table lists `SuperBrowserConfig | None`
- Line 631: `AgentConfig.core` field table references `SuperBrowserConfig`

**Fix:** Replace all `SuperBrowserConfig` → `Config` in the API reference.

#### 1.2 Inconsistent import paths in examples and quickstart

The top-level package exports `SuperBrowser`, `Config`, `ActionResult`,
`StreamEvent`, and `create_llm` via `__all__`. But examples and docs use
inconsistent deep-import paths:

| Canonical (top-level) | Deep import used in docs/examples |
|:----------------------|:----------------------------------|
| `from super_browser import SuperBrowser` | `from super_browser.agent.facade import SuperBrowser` |
| `from super_browser import create_llm` | `from super_browser.agent.llm.factory import create_llm` |
| `from super_browser import Config` | `from super_browser.config import Config` |

Files affected:
- `examples/basic_usage.py`
- `examples/budget_tracking.py`
- `examples/error_handling.py`
- `examples/multi_tab_workflow.py`
- `examples/session_persistence.py`
- `docs/quickstart.md` (multiple sections)

**Fix:** Standardize all examples and quickstart to use top-level imports.

#### 1.3 Quickstart verification command uses deep import

```bash
# Current (deep import):
python -c "from super_browser.agent.facade import SuperBrowser; print('OK')"

# Should be:
python -c "from super_browser import SuperBrowser; print('OK')"
```

#### 1.4 `raw_page` deprecation message is stale

The `DeprecationWarning` says:

> `raw_page is deprecated, use backend_page instead. Will be removed in v2.1.`

We are in v2.1.1. Either:

- **(a)** Update the message to say "Will be removed in v2.2" (defer)
- **(b)** Actually remove `raw_page` (breaking, see Bucket 3)

Recommendation: **(a)** — update the message, defer removal.

#### 1.5 CLI has no `python -m super_browser` entry point

Neither `python -m super_browser` nor `python -m super_browser.cli` works —
only the `superbrowser` console script does. Adding a `__main__.py` is a
common user expectation and trivially safe.

**Fix:** Add `src/super_browser/__main__.py` that calls `cli.main()`.

#### 1.6 CLI `result-demo` command is internal-looking

`result-demo` is a demonstration command that has no production use.
It clutters the top-level help output. Consider hiding it from the main
help listing or moving it to a `--debug` subgroup.

**Fix:** Remove from help listing (keep functional for backward compat).

#### 1.7 CLI `stealth-check` vs `stealth-validate` naming is confusing

Two similarly named commands with different purposes:

| Command | Purpose |
|:--------|:--------|
| `stealth-check` | Offline fingerprint scoring + report |
| `stealth-validate` | Fingerprint validation against baselines + CI mode |

**Fix:** Clarify in help text. Renaming would be a breaking change (defer).

### Bucket 2 — Backward-compatible polish

These add convenience without breaking existing code.

#### 2.1 `create_llm` should be in `__all__` already (confirmed OK)

Verified — `create_llm` is already exported at top level. No action needed.

#### 2.2 `ActionResult.ok` could have a boolean alias property

`ActionResult` uses `.ok` for success/failure. Some users may expect `.success`
or `.is_ok`. Currently only `.ok` exists. Adding a read-only property alias is
backward-compatible.

**Decision:** Low value, skip unless explicitly requested.

#### 2.3 `Config.from_env()` is not in quickstart's verification flow

The quickstart shows `Config.from_env()` but doesn't show how to verify it
succeeded without an LLM API key (validation will report a missing key).

**Fix:** Add a note in quickstart that `validate()` returns errors but doesn't
raise, and that the missing-API-key error is expected for browser-only use.

#### 2.4 Testing utilities could export `build_e2e_json_report` at a stable path

`build_e2e_json_report` is in `super_browser.testing` — good. But the E2E
schema v3 validator (`scripts/validate_e2e_report.py`) is not importable.
If users want to validate reports programmatically, they'd need to run the
script. Consider extracting the validator into an importable function.

**Decision:** Defer unless external consumers request it.

### Bucket 3 — Defer / avoid (risk to v2.x stability)

#### 3.1 Removing `raw_page` alias entirely

The migration doc said it would be removed in v2.1, but it still works with
a deprecation warning. Removing it would break any v1.x code that hasn't
migrated. Since v2.0 just shipped, defer to v3.0.

**Decision:** Defer. Update deprecation message to say "v3.0" instead.

#### 3.2 Removing legacy `core` sub-dict compat in `_build_agent()`

`_build_agent()` still merges a legacy `core` sub-dict for v1.x backward
compatibility. Removing it would break old YAML/dict configs. Defer.

**Decision:** Defer. No urgency — the compat path is ~5 lines of code.

#### 3.3 Renaming CLI commands

Renaming `stealth-check` → `stealth-score` or `stealth-validate` →
`stealth-baseline` would improve clarity but break scripts/automation.

**Decision:** Defer to a major version if at all.

#### 3.4 Removing `result-demo` CLI command

Removing it entirely would break anyone who uses it. Keep it functional
but hide from help (Bucket 1.6).

---

## Summary

| Bucket | Items | Risk | Recommended PR |
|:-------|------:|:-----|:---------------|
| **Patch-safe** | 7 | None | PR #163 |
| **Backward-compatible polish** | 4 | Minimal | Optional |
| **Defer** | 4 | Breaking | v3.0 |

### Recommended PR #163 scope (patch-safe only)

1. Fix `SuperBrowserConfig` → `Config` in API reference (3 occurrences)
2. Standardize examples to use top-level imports
3. Standardize quickstart to use top-level imports
4. Fix quickstart verification command
5. Update `raw_page` deprecation message to "v3.0"
6. Add `__main__.py` for `python -m super_browser` support
7. Hide `result-demo` from CLI help listing
8. Clarify `stealth-check` vs `stealth-validate` help text

All items are documentation, help text, or additive-only code changes.
No public API signatures change.
