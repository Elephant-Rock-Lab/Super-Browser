# Pi Agent Browser Native — Competitive Analysis

**Date:** 2026-05-14  
**Repo:** `C:\Next AI\ref\pi-agent-browser-native-main` (v0.2.24)  
**Author:** Mitch Fultz (fitchmultz)  
**License:** MIT  
**Upstream dependency:** [agent-browser](https://agent-browser.dev/) (Vercel Labs)  

---

## What Is This?

A **Pi coding agent extension** that exposes `agent-browser` (a CLI browser automation tool) as a native `agent_browser` tool. Instead of agents constructing brittle shell commands, they get a structured JSON tool interface with smart result formatting, session management, secret redaction, and recovery guidance.

**Not a browser library.** It's a **wrapper around an existing CLI tool** (`agent-browser`) that makes it agent-friendly.

---

## Architecture

```
┌──────────────────────────────────────────────┐
│             Pi Coding Agent (host)            │
│  ┌──────────────────────────────────────────┐│
│  │  agent_browser (native tool)              ││
│  │  ┌──────────────────────────────────────┐ ││
│  │  │  index.ts (3,268 LOC)                │ ││
│  │  │  ├─ Tool schema (TypeBox)            │ ││
│  │  │  ├─ semanticAction → find argv       │ ││
│  │  │  ├─ job → batch compilation          │ ││
│  │  │  ├─ qa → diagnostic batch            │ ││
│  │  │  ├─ sourceLookup → React inspection  │ ││
│  │  │  └─ networkSourceLookup              │ ││
│  │  ├──────────────────────────────────────┤ ││
│  │  │  lib/runtime.ts (1,169 LOC)          │ ││
│  │  │  ├─ buildExecutionPlan()             │ ││
│  │  │  ├─ Session planning (auto/fresh)    │ ││
│  │  │  ├─ Argv redaction                   │ ││
│  │  │  └─ Command discovery                │ ││
│  │  ├──────────────────────────────────────┤ ││
│  │  │  lib/results/ (3,856 LOC)            │ ││
│  │  │  ├─ presentation.ts (2,250 LOC)      │ ││
│  │  │  ├─ shared.ts (626 LOC)              │ ││
│  │  │  ├─ snapshot.ts (719 LOC)            │ ││
│  │  │  ├─ envelope.ts (185 LOC)            │ ││
│  │  │  └─ confirmation.ts (76 LOC)         │ ││
│  │  ├──────────────────────────────────────┤ ││
│  │  │  lib/process.ts (355 LOC)             │ ││
│  │  │  └─ Child process management         │ ││
│  │  └──────────────────────────────────────┘ ││
│  └──────────────────────────────────────────┘│
│                    │                          │
│                    ▼ subprocess                │
│          agent-browser CLI (upstream)          │
│                    │                          │
│                    ▼                          │
│              Chromium (Playwright)             │
└──────────────────────────────────────────────┘
```

**Stack:** TypeScript, ESM, TypeBox schemas, Pi Extension API  
**LOC:** ~8,800 (extension) + ~9,800 (tests) + ~2,200 (docs) = **~20,800 total**  
**Upstream:** `agent-browser` by Vercel Labs — installed separately, not bundled  

---

## Key Design Patterns Worth Studying

### 1. Result Category System (Brilliant)

Every tool result includes machine-readable categories:

```typescript
details: {
  resultCategory: "success" | "failure",
  successCategory?: "navigation" | "mutation" | "inspection" | "artifact" | ...,
  failureCategory?: "stale-ref" | "timeout" | "no-session" | "invalid-args" | ...,
  nextActions?: [...],           // Structured recovery suggestions
  pageChangeSummary?: {...},     // Compact navigation/mutation summary
  artifactVerification?: {...},  // File existence checks
}
```

**Why this matters:** Agents can branch on structured enums instead of parsing prose. No regex on error messages. Deterministic failure recovery.

### 2. Secret Redaction (Production-Grade)

Multi-layer redaction pipeline:
- `redactInvocationArgs()` — masks `--password`, `--body`, `--headers`, `--proxy` values in echoed argv
- `redactPresentationData()` — recursively scrubs tokens, passwords, authorization headers from JSON
- `redactStatefulValues()` — field-aware cookie/storage value redaction
- `redactSensitiveText()` — URL and free-text secret scrubbing

**Why this matters:** Prevents credential leakage into LLM context windows. We have zero equivalent.

### 3. Stale Ref Recovery

When an `@eN` element ref goes stale:
1. Error classified as `stale-ref` via `failureCategory`
2. `nextActions` suggests `refresh-interactive-refs` → re-run `snapshot -i`
3. For `semanticAction` calls, appends `retry-semantic-action-after-stale-ref` with the same compiled `find` argv

**Why this matters:** Self-healing interaction loops. Agents don't get stuck.

### 4. Session Management (Sophisticated)

Three modes:
- **`auto`** (default): Extension generates implicit session name from Pi session ID + cwd hash
- **`fresh`**: Force new browser, replacing the managed session
- **Explicit `--session`**: Caller takes ownership

Session persistence across `/reload` and `/resume`. Idle timeout for cleanup. Tab-correction when restored profile tabs steal focus.

### 5. Input Compilation Pipeline

Multiple input modes compile to the same `batch` argv:

| Input | Compilation Target |
|:------|:-------------------|
| `args: [...]` | Direct upstream argv |
| `semanticAction: {...}` | → `find` argv |
| `job: {steps: [...]}` | → `batch` stdin JSON |
| `qa: {url, ...}` | → diagnostic batch |
| `sourceLookup: {...}` | → React inspection batch |
| `networkSourceLookup: {...}` | → network analysis batch |

All mutually exclusive per call. All echo compiled form for auditability.

### 6. Page Change Summaries

After navigation/mutation commands, compact summaries:
```typescript
{
  changeType: "navigation" | "mutation" | "confirmation" | "artifact",
  summary: "Navigated to https://example.com",
  title?: "Example Domain",
  url?: "https://example.com",
  nextActionIds: [...]
}
```

**Why this matters:** Agents don't need to re-snapshot to know what changed. Saves context tokens.

### 7. Deterministic Efficiency Benchmark

`scripts/agent-browser-efficiency-benchmark.mjs` models representative workflows without launching a browser:
- Tool call counts
- Model-visible output bytes
- Stale-ref failure/recovery counts
- Artifact success rates
- Failure-category coverage
- Elapsed-time estimates

Can save JSON baselines and compare: `--compare /tmp/baseline.json`

---

## Code Quality Assessment

| Aspect | Grade | Evidence |
|:-------|:------|:---------|
| Architecture | A+ | Clean separation: index → runtime → results → process |
| Type safety | A+ | TypeBox schemas, full TypeScript strict |
| Documentation | A+ | 2,200 LOC of docs (TOOL_CONTRACT, ARCHITECTURE, COMMAND_REFERENCE, REQUIREMENTS, SUPPORT_MATRIX, RELEASE) |
| Test coverage | A | 9,800 LOC tests (extension-validation, presentation, runtime, resume-state, real-upstream) |
| Error handling | A+ | Structured categories, recovery hints, redaction |
| Secret handling | A+ | Multi-layer redaction, stdin-only password input |
| Maintainability | A+ | Generated docs from canonical source, drift checks, baseline verification |
| Stealth/Anti-detection | F | Zero. None. No fingerprint defense whatsoever. |

---

## Comparison: pi-agent-browser-native vs Super Browser

| Dimension | Pi Agent Browser Native | Super Browser | Verdict |
|:----------|:------------------------|:--------------|:--------|
| **Anti-detection** | Zero | Full ejecta stack (5 ejectors, 12 surfaces) | **We win** |
| **Tool interface** | Native Pi tool (JSON) | Python API + CLI | Different hosts |
| **Browser engine** | Playwright (via agent-browser) | Patchright (CDP) | Comparable |
| **Session management** | Sophisticated (auto/fresh/explicit) | Basic (CloakBrowser sessions) | **They win** |
| **Secret redaction** | Production-grade (4 layers) | None | **They win** |
| **Error recovery** | Structured categories + nextActions | Basic error types | **They win** |
| **Result formatting** | Compact summaries, page change detection | Raw CDP results | **They win** |
| **Stale ref handling** | Self-healing with retry guidance | None | **They win** |
| **Benchmarking** | Deterministic efficiency benchmark | No agent-facing benchmark | **They win** |
| **Documentation** | 6 docs (2,200 LOC) | User docs only | **They win** |
| **Test quality** | 9,800 LOC tests, real-upstream harness | 1,931 unit tests | Comparable |
| **License** | MIT | MIT | Tie |

---

## Takeaways for Super Browser

### Patterns to Adopt (HIGH priority)

1. **Result Category System** — Add `resultCategory` + `successCategory`/`failureCategory` to all tool returns. Agents should never parse prose for branching.

2. **Page Change Summaries** — After navigation, return compact `{changeType, summary, title?, url?}` instead of forcing agents to re-snapshot.

3. **Stale Ref Recovery** — When element refs expire, return structured recovery guidance (`nextActions`) instead of generic errors.

4. **Deterministic Agent Benchmark** — Model representative workflows, measure call counts and token usage, compare baselines across changes.

### Patterns to Study (MEDIUM priority)

5. **Secret Redaction Pipeline** — Multi-layer approach to prevent credential leakage into LLM context. Critical for production use.

6. **Input Compilation** — Multiple input modes (`semanticAction`, `job`, `qa`) compiling to the same execution path. Elegant API design.

7. **Generated Docs from Canonical Source** — Playbook text in TypeScript, generated into Markdown, drift-checked on verify. Prevents doc rot.

### What They Lack (Our Moat — MAINTAIN)

8. **Zero stealth** — No fingerprint defense, no consistency engine, no ejectors. Their Chromium sessions are trivially detectable.

9. **No deterministic profiles** — No seed-based consistency, no cross-surface coherence.

10. **No behavioral synthesis** — No Bézier/Fitts/QWERTY/scroll patterns. Their clicks look robotic.

---

## Strategic Assessment

**This is NOT a competitor.** It's a complementary project in a different ecosystem (Pi coding agent vs standalone Python library). However, their **agent-facing UX patterns are best-in-class** and directly applicable to our v2.0 desktop agent plans.

```
pi-agent-browser-native:  Agent UX champion (redaction, categories, recovery, benchmarks)
Super Browser:            Stealth champion (ejectors, profiles, consistency, behavior)

Together they represent the ideal: undetectable + agent-friendly.
```

**Recommendation:** Study their result category system, page change summaries, stale ref recovery, and benchmark patterns. These translate directly to any agent-facing API surface we build.

---

Lead Sign: Lead, 2026-05-14
