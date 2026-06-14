# RFC: v2.0 Decomposition Roadmap

## Status

Draft / planning-only. No implementation in this document.

## Context

v1.11.0 shipped streaming (`act_stream()` + `StreamEvent`), provider token
streaming, 10 default built-in tools, prompt/tool isolation, an exhaustive
17-method facade security perimeter, controller rebinding after tab switches,
docs alignment, and release metadata. The v1.x line is stable and shippable.

The old v2.0 PR (#112) was closed unmerged. It bundled multiple unrelated
tracks — breaking config simplification, `_legacy_core` removal, `raw_page`
removal, TLS/IP/proxy stealth, behavioral simulation, Turnstile/Kasada/cache
work, and E2E validation — into a single monolithic branch based on a stale
`main` SHA from before Waves 6–12. That approach is not viable on the current
codebase.

## Decision

**Do not reopen PR #112.** Decompose v2.0 into staged, independently
reviewable tracks. Each track ships as its own PR with its own acceptance
criteria, test plan, rollback plan, and compatibility note.

`main` remains the stable v1.x release line throughout the v2.0 effort.

## Non-goals

- No v2.0 implementation in this RFC.
- No release version bump.
- No public API removal without a migration path.
- No real-network tests in default CI.

---

## Proposed tracks

### Track A — Breaking API simplification (v2.0-alpha.1)

**Scope:**
- Flatten `AgentConfig` into the composition root.
- Remove legacy config bridge (`_legacy_core`).
- Remove `SuperBrowserConfig` if fully superseded.
- Remove `Config.from_legacy()` migration helper.
- Decide `raw_page` policy: remove, deprecate, or retain with documented risks.

**Acceptance criteria:**
- Migration guide with before/after examples for every removed API.
- Deprecation mapping table (`old → new`).
- Tests for config loading from dict, YAML, and environment variables.
- Clear incompatibility list: what breaks and why.

**Rollback plan:** Revert the PR. No runtime state migration is needed since
config changes are construction-time only.

**Compatibility note:** This is a **breaking change**. Existing code
constructing `SuperBrowser(SuperBrowserConfig(...))` or using
`Config.from_legacy()` must migrate.

---

### Track B — Network stealth (v2.0-alpha.2)

**Scope:**
- Proxy pool with rotation and health checks.
- IP reputation lookup (offline database or opt-in API).
- JA4/TLS fingerprint reporting and validation.

**Acceptance criteria:**
- Offline-first tests using local fixtures.
- Real-network tests opt-in only (environment variable gate).
- Provider/API failures are non-fatal (log warning, continue).
- No mandatory dependency on external services.

**Rollback plan:** Revert the PR. Existing stealth stack (CDP, Patchright)
remains unaffected.

**Compatibility note:** Additive — new optional config fields. No existing API
changes.

---

### Track C — Behavioral realism (v2.0-alpha.3)

**Scope:**
- Dwell time before/after actions.
- Natural scroll patterns (variable speed, momentum).
- Bézier mouse paths with Fitts's Law timing.
- Navigation variation (human-like URL entry, referral patterns).

**Acceptance criteria:**
- Deterministic seeded tests (same seed → same behavior).
- No hidden delays in normal unit tests (mocked time).
- Documented configuration knobs with sensible defaults.
- Behavioral synthesis runs are reproducible.

**Rollback plan:** Revert the PR. Default behavioral profile is unchanged.

**Compatibility note:** Additive — new `BehaviorConfig` section. Existing
`HumanConfig` presets continue to work.

---

### Track D — Challenge infrastructure (v2.0-alpha.4)

**Scope:**
- Turnstile detection and classification (version detection, not solving).
- Token cache for solved challenges (TTL-based eviction).
- Kasada PoW detection-only (no solver in v2.0).

**Acceptance criteria:**
- No solver claims unless a working solver is implemented and tested.
- No bypass language in docs or code comments.
- Cache TTL/eviction unit tests.
- Detection logic does not false-positive on normal pages.

**Rollback plan:** Revert the PR. Challenge detection is opt-in.

**Compatibility note:** Additive — new `ChallengeConfig` section. Detection
reports are informational only.

---

### Track E — Real-browser benchmark / E2E harness (v2.0-alpha.5)

**Scope:**
- Opt-in real-browser test suite (separate from unit/integration tests).
- Local HTML fixtures by default.
- External network tests quarantined behind explicit opt-in.
- Stable JSON/Markdown benchmark output.

**Acceptance criteria:**
- Skipped by default in CI unless explicitly enabled via environment variable.
- Stable output format (versioned JSON schema).
- Documented environment variables for enabling real-browser tests.
- No mandatory dependency on ip-api.com, example.com, or any external service.

**Rollback plan:** Revert the PR. Existing test suite is unaffected.

**Compatibility note:** Test infrastructure only — no runtime API changes.

---

## Sequencing

```
RFC approval (this document)
    │
    ▼
v2.0-alpha.1 ── Track A: Breaking API simplification
    │
    ▼
v2.0-alpha.2 ── Track B: Network stealth
    │
    ▼
v2.0-alpha.3 ── Track C: Behavioral realism
    │
    ▼
v2.0-alpha.4 ── Track D: Challenge infrastructure
    │
    ▼
v2.0-alpha.5 ── Track E: Real-browser benchmark / E2E harness
    │
    ▼
v2.0.0 release
```

Each alpha is a mergeable PR targeting a `v2.0` branch (created from `main`
at the start of Track A). The `v2.0` branch rebases on `main` before each
track to incorporate v1.x hardening.

## Risk controls

- **Keep v1.x viable.** `main` continues to receive v1.x patches and releases.
- **One PR per track.** No track is large enough to warrant splitting, but no
  track may be combined with another.
- **Docs and migration notes with every breaking change.** No silent removals.
- **Opt-in flags for flaky/real-network validation.** Default CI never depends
  on external services.
- **Each track has a clean rollback.** Reverting the PR restores prior behavior.

## Historical context

PR #112 (`feat/v2.0-breaking-simplification`) was opened on the old
`Elephant-Rock-Lab/super-browser` repo and closed on 2026-06-14 without merge.
Its branch remains on the remote for reference but is based on a pre-Waves-6–12
`main` SHA and cannot be rebased cleanly. The work it attempted is captured in
the five tracks above, scoped for the post-v1.11 codebase.
