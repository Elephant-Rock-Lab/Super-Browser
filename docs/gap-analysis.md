# Super Browser — Gap Analysis

> **Version analyzed:** 1.0.2 (2026-05-03)  
> **Date:** 2026-05-07  
> **Analyst:** Product Strategy Review

---

## Executive Summary

Super Browser is a **well-architected, depth-over-breadth** browser automation library for AI agents. Its core value — a three-tier cascade (LLM → Skills → Raw Browser), stealth stack, budget governance, and recovery system — is **genuinely differentiated** and production-quality (1,370 tests, structured result types, frozen config). However, it is still fundamentally a **library, not a platform**. The gaps cluster around **surface area** (features users expect from any browser tool) and **distribution** (how users discover, install, and operate it at scale).

The single highest-leverage investment is **cloud browser integration** — without it, Super Browser cannot compete for the enterprise/production use cases that drive adoption and revenue.

---

## 1. Feature Gaps

### 1.1 Multi-Tab / Multi-Window Support

| Dimension | Assessment |
|-----------|------------|
| **Current state** | `BrowserSession.new_page()` creates pages within a single browser context. `SubagentDelegator` spawns concurrent pages. No explicit tab management API (switch, close by ID, window handles). |
| **Impact** | 🔴 **High** — Every real workflow involves multiple tabs. Users expect `sb.switch_tab(2)`, `sb.close_tab()`, popup handling. |
| **Effort** | **S** — Patchright exposes `context.pages()` and page event listeners. A thin `TabManager` wrapper with switch/close/listen would take ~1 sprint. |
| **Priority** | **P0** |

**Gap:** No public API for tab lifecycle (list, switch, close, wait for popup). Window management (move, resize, multi-monitor) is absent. Popup/`target="_blank"` handling is implicit at best.

---

### 1.2 File Upload / Download Handling

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Not implemented. The `StealthActionPolicy` has a `file_upload` rule requiring confirmation, but no upload/download logic exists. |
| **Impact** | 🔴 **High** — File upload is essential for form completion (resumes, documents, images). File download is needed for data extraction workflows. |
| **Effort** | **S** — Patchright provides `page.set_input_files()` for uploads and `download` event listeners. A thin wrapper is straightforward. |
| **Priority** | **P0** |

**Gap:** No `sb.upload(selector, file_path)`, no `sb.download(url) → path`, no download event interception.

---

### 1.3 iframe Navigation

| Dimension | Assessment |
|-----------|------------|
| **Current state** | CAPTCHA detection can find iframes by selector, but there's no general-purpose frame API. The `extract()` and `click()` methods do not traverse into iframes. |
| **Impact** | 🔴 **High** — Many enterprise apps (Salesforce, SAP, old government sites) rely heavily on iframes. CAPTCHA itself lives in iframes. |
| **Effort** | **M** — Patchright provides `page.frame()` and `frame_locator()`. Need to extend `MultimodalController` to accept frame context and update `extract()`/`click()`/`fill()` to operate within frames. |
| **Priority** | **P0** |

**Gap:** No `sb.within_frame(selector).click(...)`, no frame enumeration, no recursive DOM access across frames.

---

### 1.4 Shadow DOM Support

| Dimension | Assessment |
|-----------|------------|
| **Current state** | `document.querySelector()` in `extract()` cannot pierce Shadow DOM. Accessibility snapshots may or may not include shadow-pierced elements depending on Patchright version. |
| **Impact** | 🟡 **Medium** — Modern web components (YouTube, GitHub, many design systems) use Shadow DOM. Growing in importance. |
| **Effort** | **M** — Need to switch from `querySelector` to `querySelectorAll` with `>>>` piercing selector, or use CDP `DOM.describeNode` for shadow traversal. |
| **Priority** | **P1** |

**Gap:** No shadow-piercing selectors, no `sb.shadow_root(selector)`, no automatic shadow DOM traversal in extract/observe.

---

### 1.5 PDF Generation / Screenshot Annotation

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Screenshots exist (vision controller, debug mode). No PDF generation. No annotation/overlay on screenshots. |
| **Impact** | 🟡 **Medium** — PDF export is a common workflow output. Annotated screenshots are useful for debugging and compliance. |
| **Effort** | **S** — Patchright provides `page.pdf()`. Screenshot annotation can use Pillow (already a dependency). |
| **Priority** | **P2** |

**Gap:** No `sb.screenshot(path, annotate=True)`, no `sb.pdf(path)`, no visual diff output.

---

### 1.6 Session Recording / Replay

| Dimension | Assessment |
|-----------|------------|
| **Current state** | `CheckpointManager` saves/restores state snapshots. `FlowLogger` records trace events. But no video recording, no HAR capture, no replay engine. |
| **Impact** | 🔴 **High** — Critical for debugging failed agents, compliance audit trails, and demo/replay scenarios. Competitors (Playwright, Browserbase) ship this out of the box. |
| **Effort** | **M** — Patchright supports HAR recording natively. Video recording via `context.new_context(record_video=...)`. Replay engine is a separate ~L effort. |
| **Priority** | **P1** |

**Gap:** No `sb.start_recording()`, no `sb.stop_recording() → video_path`, no HAR export, no action replay.

---

### 1.7 Visual Regression Testing

| Dimension | Assessment |
|-----------|------------|
| **Current state** | `VisualVerifier` exists for action confirmation. `FingerprintScorer` exists for stealth. Neither does pixel-level comparison or baseline management. |
| **Impact** | 🟡 **Medium** — Important for testing/CI use cases, but Super Browser is positioned as an agent library, not a testing framework. |
| **Effort** | **M** — Would need baseline storage, diff algorithm (pixelmatch/SSIM), threshold config, and reporting. |
| **Priority** | **P2** |

**Gap:** No `sb.assert_visual(baseline)`, no screenshot diff, no baseline management.

---

### 1.8 Network Interception / Mocking

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Stealth mode uses route interception for script injection and CSP stripping. But there's no public API for request/response mocking, throttling, or blocking. |
| **Impact** | 🔴 **High** — Network mocking is essential for reliable testing, offline development, and simulating error conditions. |
| **Effort** | **S** — Patchright's `page.route()` already used internally. Just need to expose it: `sb.route("**/api/*", handler)`, `sb.mock(url, response)`. |
| **Priority** | **P1** |

**Gap:** No `sb.intercept(pattern, handler)`, no `sb.mock_api(url, response)`, no throttle/offline mode.

---

### 1.9 Geolocation Spoofing

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Not implemented. `SessionConfig` has locale and timezone but no geolocation override. |
| **Impact** | 🟡 **Medium** — Important for location-based testing (maps, local search, geo-restricted content). |
| **Effort** | **XS** — Patchright provides `context.grant_permissions(["geolocation"])` + `page.set_geolocation(lat, lng)`. One afternoon of work. |
| **Priority** | **P1** |

**Gap:** No `sb.set_location(lat, lng)`, no location override in config.

---

### 1.10 Multi-Browser Support (Firefox, Safari, Edge)

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Built exclusively on Patchright (Chromium fork). Architecture doc mentions Firefox as a v2.0 extension point. |
| **Impact** | 🟡 **Medium** — Most agent use cases work with Chromium. Firefox/Safari support matters for testing and compliance, not for general automation. |
| **Effort** | **XL** — Requires abstracting the browser layer, testing against Firefox (Playwright backend), WebKit. Significant surface area changes in `BrowserSession`, `MultimodalController`, and stealth stack. |
| **Priority** | **P2** |

**Gap:** Chromium only. No Firefox, no WebKit/Safari, no mobile emulation beyond viewport resizing.

---

### 1.11 Cloud Browser Integration (Browserbase, Browserless)

| Dimension | Assessment |
|-----------|------------|
| **Current state** | Not implemented. `BrowserSession` creates a local Patchright instance only. No CDP-over-WebSocket connection, no cloud provider abstraction. |
| **Impact** | 🔴 **High** — This is the **#1 blocker for production adoption**. Users who want to run 100+ concurrent agents or avoid managing browser infrastructure need this. Every major competitor supports it. |
| **Effort** | **M** — Patchright supports `connect_over_cdp(ws_endpoint)`. Need: (1) a `BrowserProvider` abstraction, (2) connectors for Browserbase/Browserless/Steel, (3) session lifecycle management. |
| **Priority** | **P0** |

**Gap:** No `Config(browser_provider="browserbase", api_key="...")`, no remote session management, no provider abstraction layer.

---

### 1.12 Streaming / Real-Time Results

| Dimension | Assessment |
|-----------|------------|
| **Current state** | `AgentLoop` emits `StepEvent` callbacks per step. `act()` returns only after completion. No streaming API, no SSE/WebSocket output, no incremental result delivery. |
| **Impact** | 🟡 **Medium** — Important for UX (show progress while agent works) and for integration with chat/streaming frameworks. |
| **Effort** | **S** — `AgentLoop` already has `event_callback`. Just need `act_stream()` that yields `StepEvent` as an async generator. |
| **Priority** | **P1** |

**Gap:** No `sb.act_stream(instruction) → AsyncIterator[StepEvent]`, no partial result delivery, no progress hooks for UI integration.

---

### 1.13 Webhook / Event System

| Dimension | Assessment |
|-----------|------------|
| **Current state** | `FlowLogger` and `event_callback` provide in-process event emission. No external webhook delivery, no message queue integration, no event bus beyond the callback. |
| **Impact** | 🟡 **Medium** — Important for production monitoring, alerting, and integration with external systems (Slack, PagerDuty). |
| **Effort** | **M** — Need an `EventBus` abstraction with pluggable sinks (webhook, Kafka, SQS). The `FlowLogger` sink pattern already provides a template. |
| **Priority** | **P2** |

**Gap:** No `Config(webhook_url="...")`, no event bus, no integration with external observability systems.

---

### 1.14 Plugin / Extension System

| Dimension | Assessment |
|-----------|------------|
| **Current state** | `PluginSlot` / `PluginRegistry` classes exist with `slot_key`, `initialize`, `shutdown` methods. `ToolRegistry` supports custom tool registration. But there's no plugin discovery, no plugin manifest, no community plugin infrastructure. |
| **Impact** | 🟡 **Medium** — Plugins enable community contributions and vertical-specific extensions. Not blocking for v1, but critical for ecosystem growth. |
| **Effort** | **L** — Need plugin manifest spec, discovery (entry points / directory scan), dependency resolution, versioning, and documentation. |
| **Priority** | **P2** |

**Gap:** Skeleton exists (`PluginSlot` ABC), but no plugin discovery, no packaging standard, no plugin marketplace, no community examples.

---

### Feature Gap Summary Table

| # | Feature | Impact | Effort | Priority |
|---|---------|--------|--------|----------|
| 1.1 | Multi-tab / multi-window | 🔴 High | S | **P0** |
| 1.2 | File upload / download | 🔴 High | S | **P0** |
| 1.3 | iframe navigation | 🔴 High | M | **P0** |
| 1.4 | Shadow DOM support | 🟡 Medium | M | P1 |
| 1.5 | PDF generation / screenshot annotation | 🟡 Medium | S | P2 |
| 1.6 | Session recording / replay | 🔴 High | M | P1 |
| 1.7 | Visual regression testing | 🟡 Medium | M | P2 |
| 1.8 | Network interception / mocking | 🔴 High | S | P1 |
| 1.9 | Geolocation spoofing | 🟡 Medium | XS | P1 |
| 1.10 | Multi-browser (Firefox/Safari) | 🟡 Medium | XL | P2 |
| 1.11 | Cloud browser integration | 🔴 High | M | **P0** |
| 1.12 | Streaming / real-time results | 🟡 Medium | S | P1 |
| 1.13 | Webhook / event system | 🟡 Medium | M | P2 |
| 1.14 | Plugin / extension system | 🟡 Medium | L | P2 |

---

## 2. Architecture Gaps

### 2.1 Scaling: Can It Run 100 Parallel Sessions?

**Current state:** ❌ **Not designed for multi-process scaling.**

- `SuperBrowser` is a single-process, single-browser-context class. Each instance owns one Patchright browser.
- `SubagentDelegator` supports up to `max_concurrency=4` parallel sub-agents within a single context — limited by the hard tab cap.
- No process pooling, no session serialization, no distributed coordination.
- `TokenBudgetGovernor` is thread-safe (uses `threading.Lock`) but not multi-process safe.
- State persistence (`CheckpointManager`, `TokenBudgetGovernor`) uses local filesystem JSON — no shared state backend.

**What's needed:**
1. **Browser Provider abstraction** — decouple from local Patchright, connect to remote browser grids
2. **Session Manager** — pool of `SuperBrowser` instances with lifecycle management, health checks, and recycling
3. **Shared state backend** — Redis/Postgres for budget state, checkpoints, and cost records
4. **Rate limiter** — per-domain and global concurrency controls to avoid triggering anti-bot defenses

**Effort:** L — This is a fundamental architecture change, not a feature addition.

---

### 2.2 Persistence: Can Sessions Survive Restart?

**Current state:** ⚠️ **Partial.**

- `CheckpointManager` persists page state (URL, scroll, cookies, form values) to JSON files.
- `TokenBudgetGovernor` supports `state_dir` for persistence to disk.
- But: **no session resumption API** — there's no `SuperBrowser.resume(session_id)` that reconnects to an existing browser and restores full agent state (plan, history, budget).
- Checkpoint restore only handles browser-level state, not agent-level state (running plans, loop detector history, retry budgets).

**What's needed:**
1. **Session serialization** — serialize `AgentLoop` state (plan, step history, loop detector, retry budgets)
2. **Session resumption API** — `SuperBrowser.resume(session_id)` that reconnects browser + restores agent state
3. **Cloud checkpoint storage** — S3/GCS for cross-machine recovery (mentioned in architecture doc as v2.0)

**Effort:** M — The building blocks exist; this is a matter of composing them into a resumption workflow.

---

### 2.3 Observability: Tracing, Metrics, Dashboards

**Current state:** ⚠️ **Foundation exists, not production-ready.**

| Capability | Status | Notes |
|-----------|--------|-------|
| **Structured tracing** | ✅ | `FlowLogger` with console + file + OTLP sinks |
| **Span-based timing** | ✅ | Every `ActionResult` includes `duration_ms` |
| **Cost tracking** | ✅ | `TokenBudgetGovernor` + `CostAnalytics` + SQLite `SessionDB` |
| **OpenTelemetry** | ⚠️ | OTLP sink type declared but no actual OTLP export implementation |
| **Metrics endpoint** | ❌ | No Prometheus `/metrics` endpoint |
| **Dashboard** | ❌ | No built-in dashboard for sessions, costs, errors |
| **Distributed tracing** | ❌ | No trace propagation across sub-agents |

**What's needed:**
1. **OTLP exporter** — wire the declared OTLP sink to `opentelemetry-sdk`
2. **Prometheus metrics** — `sb_sessions_active`, `sb_steps_total`, `sb_cost_usd_total`, `sb_errors_total`
3. **Built-in dashboard** — even a simple HTML page that reads the SQLite `SessionDB`
4. **Trace correlation** — propagate `trace_id` across sub-agent delegations

**Effort:** M for OTLP + Prometheus, L for dashboard.

---

### 2.4 Testing: How Easy Is It to Test Agents?

**Current state:** ✅ **Good for unit tests, limited for integration.**

| Capability | Status | Notes |
|-----------|--------|-------|
| **MockLLMClient** | ✅ | Built-in mock in `super_browser.testing` |
| **Frozen config** | ✅ | Immutable configs prevent test pollution |
| **ActionResult typing** | ✅ | Every result is typed and inspectable |
| **139 test files** | ✅ | Comprehensive unit test coverage |
| **Integration tests** | ⚠️ | 67 E2E tests but require real browser |
| **VCR/replay testing** | ❌ | No HTTP or browser response recording/replay |
| **Snapshot testing** | ❌ | No DOM/AX snapshot baselines |
| **Test fixtures** | ⚠️ | No shared page fixtures (login state, common pages) |

**What's needed:**
1. **HAR replay mode** — record real browser sessions, replay offline in CI
2. **Page fixtures** — pre-built authenticated sessions for common sites
3. **Snapshot assertions** — `assert_snapshot(result)` for DOM/AX tree comparison
4. **Test utilities** — `create_test_sb()` helper with sensible test defaults

**Effort:** S for test utilities, M for HAR replay.

---

## 3. Distribution Gaps

### 3.1 PyPI Package

| Status | Assessment |
|--------|------------|
| ⚠️ **Badge says published, no evidence** | README shows a PyPI badge (`1.0.0`) and `pip install super-browser` instructions, but `pyproject.toml` has no `[project.urls]` and no evidence of actual PyPI publication. The package name `super-browser` may not be registered. |

**Action items:**
- Register `super-browser` on PyPI (or choose a unique name if taken)
- Add `[project.urls]` (Homepage, Documentation, Repository, Changelog)
- Set up trusted publishing via GitHub Actions OIDC
- Publish 1.0.2 to match `pyproject.toml` version

**Effort:** S — One-time setup, automated thereafter.

---

### 3.2 Docker Image

| Status | Assessment |
|--------|------------|
| ❌ **Not available** | No `Dockerfile`, no `docker-compose.yml`, no container registry references. |

**Why it matters:** Docker is the standard deployment mechanism for production automation. Users want `docker run super-browser` with Chromium pre-installed, not `pip install + python -m patchright install chromium`.

**Action items:**
- Multi-stage `Dockerfile`: Python 3.11 + Chromium + Patchright binary
- `docker-compose.yml` for development (with Anthropic API key injection)
- Publish to GitHub Container Registry (`ghcr.io`)
- Slim image for cloud browser mode (no Chromium needed)

**Effort:** S — Standard Docker packaging.

---

### 3.3 Hosted / Cloud Version

| Status | Assessment |
|--------|------------|
| ❌ **Not available** | No SaaS offering, no managed service, no API gateway. |

**Why it matters:** Browserbase, Browserless, and Steel all offer hosted browser-as-a-service. Super Browser's agent intelligence layered on a hosted browser grid would be a compelling product.

**Action items:**
- Cloud browser provider abstraction (prerequisite for §1.11)
- REST API gateway: `POST /sessions`, `POST /sessions/{id}/act`, `GET /sessions/{id}/status`
- WebSocket API for streaming results
- Usage-based billing (already have budget tracking infrastructure)
- Session isolation and multi-tenancy

**Effort:** XL — Full product build.

---

### 3.4 CLI Tool

| Status | Assessment |
|--------|------------|
| ❌ **Not available** | No `[project.scripts]` entry in `pyproject.toml`. No CLI module. |

**Why it matters:** CLI is the fastest path from install to value. `super-browser act "search for flights to Tokyo"` would be a powerful demo and debugging tool.

**Action items:**
```toml
[project.scripts]
super-browser = "super_browser.cli:main"
```
- `super-browser run "instruction"` — run a single agent task
- `super-browser config` — validate/show current config
- `super-browser doctor` — run diagnostics (stealth, browser, LLM connectivity)
- `super-browser cost` — show budget usage
- `super-browser replay <trace-file>` — replay a recorded trace

**Effort:** S — Thin wrapper over existing `SuperBrowser` API using `click` or `typer`.

---

### 3.5 VS Code Extension

| Status | Assessment |
|--------|------------|
| ❌ **Not available** | No extension code, no marketplace listing. |

**Why it matters:** VS Code integration (agent output panel, live browser preview, cost tracker sidebar) would dramatically improve the developer experience. This is a **differentiation opportunity** — no major competitor has a good VS Code extension.

**Action items:**
- WebView panel for live browser + agent status
- Sidebar for budget tracking and session history
- Command palette: "Run Agent Task", "Validate Stealth", "Show Cost Report"
- Integrated terminal for CLI commands

**Effort:** L — Full extension development, but high impact.

---

### Distribution Gap Summary

| Channel | Status | Effort | Impact |
|---------|--------|--------|--------|
| PyPI package | ⚠️ Claimed but unverified | S | 🔴 Must-have |
| Docker image | ❌ | S | 🔴 Must-have |
| CLI tool | ❌ | S | 🟡 Nice-to-have |
| Hosted/cloud version | ❌ | XL | 🟡 Future |
| VS Code extension | ❌ | L | 🟡 Differentiator |

---

## 4. Documentation Gaps

### 4.1 What Exists

| Document | Quality | Coverage |
|----------|---------|----------|
| `README.md` | ✅ Good | Installation, quickstart, architecture summary |
| `docs/quickstart.md` | ✅ Good | 5-minute tutorial, mock mode, config options, debug mode |
| `docs/architecture.md` | ✅ Excellent | Full subsystem diagrams, data flows, component inventory, extension points |
| `docs/api-reference.md` | ✅ Excellent | Every public class, method, parameter, return type, code examples |
| `CHANGELOG.md` | ✅ Excellent | Detailed batch-by-batch history with test counts |
| `examples/basic_usage.py` | ✅ Adequate | Basic navigate/click/extract/act flow |
| `examples/budget_tracking.py` | ✅ Adequate | Budget governor usage |
| `examples/stealth_mode.py` | ✅ Adequate | Stealth configuration |

### 4.2 What's Missing

| Gap | Impact | Priority |
|-----|--------|----------|
| **Migration guide** (Playwright → Super Browser) | High — most users come from Playwright/Selenium | P1 |
| **Recipe book** (common tasks: login, scrape, form fill, search) | High — copy-paste examples drive adoption | P0 |
| **Stealth guide** (what each layer does, when to enable, fingerprint scoring interpretation) | Medium — stealth is the differentiator but users need to understand it | P1 |
| **Budget management guide** (daily caps, model cascade, cost optimization strategies) | Medium — users need to control costs before trusting the tool | P1 |
| **Recovery & reliability guide** (checkpoint strategies, error classification, retry configuration) | Medium — production users need reliability story | P1 |
| **Security hardening guide** (credential vault, safety gate tiers, action policies) | Medium — enterprise users need security story | P2 |
| **Contributing guide** (CONTRIBUTING.md is referenced but content unknown) | Low — needed for open source growth | P2 |
| **Changelog website** (auto-generated from CHANGELOG.md) | Low — discoverability | P2 |
| **TypeScript / JavaScript bindings** | High — Python-only limits addressable market | P2 |
| **Interactive API playground** | Medium — try.superbrowser.dev | P2 |
| **Video tutorials / walkthroughs** | Medium — high conversion for visual learners | P2 |

### 4.3 API Reference Gaps

These modules are implemented but **not documented** in `api-reference.md`:

| Module | Classes/Functions Missing from API Reference |
|--------|----------------------------------------------|
| `recovery/coordinator.py` | `RecoveryCoordinator` |
| `recovery/types.py` | `ErrorType`, `RecoveryStrategy`, `RecoveryHint`, `ClassifiedError` |
| `interaction/controller.py` | `MultimodalController` |
| `vision/controller.py` | `VisionController`, `VisionCache`, `VisionProviderFactory` |
| `verification/verifier.py` | `VisualVerifier`, `VerifierConfig` |
| `skills/registry.py` | `SkillRegistry` |
| `tracing/flow_logger.py` | `FlowLogger` |
| `tracing/session_db.py` | `SessionDB` |
| `tracing/cost_analytics.py` | `CostAnalytics` |
| `agent/router.py` | `DeterministicRouter` |
| `security/gate.py` | `SafetyGate.evaluate()` |
| `agent/plugins.py` | `PluginSlot`, `PluginRegistry` |
| `testing.py` | `MockLLMClient` |
| `browser/session.py` | `BrowserSession`, `PageHandle` |

---

## 5. Competitive Positioning

### 5.1 Competitive Landscape

| Tool | Type | Focus | Stealth | Budget | Agent | Scale |
|------|------|-------|---------|--------|-------|-------|
| **Super Browser** | Library | AI agent browser control | ✅ Best-in-class | ✅ 3-scope governor | ✅ LLM + skills cascade | ❌ Single-process |
| **Playwright** | Library | Test automation | ❌ None | ❌ None | ❌ None | ✅ Multi-browser |
| **Patchright** | Library | Stealth browser control | ✅ Good (detection evasion) | ❌ None | ❌ None | ⚠️ Single-process |
| **Browser Use** | Library | AI agent browser control | ❌ Basic | ❌ None | ✅ LLM-driven | ⚠️ Basic |
| **Stagehand** | Library | AI web extraction | ❌ None | ❌ None | ✅ LLM-driven | ⚠️ Single-process |
| **Browserbase** | Platform | Cloud browser infra | ⚠️ Basic | ❌ None | ❌ None (provides infra) | ✅ Cloud-scale |
| **Browserless** | Platform | Cloud browser infra | ❌ None | ❌ None | ❌ None (provides infra) | ✅ Cloud-scale |
| **Steel** | Platform | Cloud browser for agents | ⚠️ Basic | ❌ None | ❌ None (provides infra) | ✅ Cloud-scale |
| **Selenium** | Library | Test automation | ❌ None | ❌ None | ❌ None | ✅ Multi-browser |
| **Puppeteer** | Library | Browser automation | ❌ None | ❌ None | ❌ None | ⚠️ Single-process |

### 5.2 Super Browser's Unique Value Proposition

**"The only browser automation library that combines stealth, budget control, and AI agent intelligence in a single facade."**

Specifically, no other tool offers **all four** of:

1. **Stealth stack** — header randomization, UA rotation, TLS fingerprinting, proxy escalation, CAPTCHA detection, fingerprint scoring
2. **Budget governance** — daily/action/turn caps, model cascade, credential rotation, circuit breaker, context compression
3. **Agent intelligence** — three-tier cascade (LLM → skills → raw browser), self-healing selectors, loop detection, stagnation recovery
4. **Security guardrails** — tier-based action evaluation, credential vault, URL allow/deny lists, prompt injection defense

This combination is genuinely unique. The closest competitor is **Browser Use** (agent + browser), but it lacks stealth and budget management entirely.

### 5.3 Where Super Browser Wins

| Scenario | Why Super Browser Wins |
|----------|----------------------|
| **Web scraping at scale** | Stealth stack avoids detection, budget caps prevent cost overruns, self-healing selectors handle DOM changes |
| **AI agent workflows** | Three-tier cascade means simple tasks are free (skills tier), complex tasks use LLM efficiently |
| **Production automation** | Recovery system, checkpoint manager, and budget governance provide reliability guarantees |
| **Cost-sensitive deployments** | Model cascade + credential pool + context compression = lowest possible LLM cost per task |
| **Anti-detection scenarios** | Most complete stealth stack of any Python browser library (TLS, headers, UA, proxy escalation, CAPTCHA) |

### 5.4 Where Super Browser Loses

| Scenario | Why Super Browser Loses | To Whom |
|----------|------------------------|----------|
| **Test automation** | No multi-browser, no visual regression, no test runner integration | Playwright, Selenium |
| **Cloud / hosted deployment** | No cloud browser, no SaaS, no REST API | Browserbase, Browserless, Steel |
| **Enterprise features** | No SSO, no RBAC, no audit logging, no SOC2 | Commercial platforms |
| **Developer onboarding** | Python-only, no JS/TS bindings, no CLI | Playwright, Puppeteer |
| **Ecosystem / community** | New project, no plugins, no marketplace, small community | Playwright (30k+ GitHub stars) |
| **Simple automation** | Heavy dependency footprint (LLM client, Patchright, stealth stack) for users who just need `page.click()` | Playwright, Puppeteer |
| **Mobile testing** | No mobile emulation beyond viewport resize | Playwright, Appium |

### 5.5 Strategic Recommendations

#### Immediate (P0 — Next 2 Sprints)

1. **Cloud browser integration** — This unlocks the production use case. Start with CDP-over-WebSocket support and a Browserbase connector. The `BrowserSession` abstraction makes this a clean extension.

2. **Tab management + file upload/download + iframe support** — These three P0 features address the "I can't do basic browser things" feedback. Each is small effort, high impact.

3. **PyPI publication + Docker image** — Without these, the project doesn't exist for most potential users. One-time setup effort.

4. **Recipe book** — 10-15 copy-paste examples for the most common tasks. This is what drives "5-minute evaluation" adoption.

#### Near-Term (P1 — Next Quarter)

5. **Network interception API** — Expose the internal route interception as a public API. Small effort, enables testing and mocking workflows.

6. **Geolocation spoofing** — Trivially small effort, completes the "browser emulation" story alongside stealth.

7. **Streaming API** — `act_stream()` as an async generator. Critical for UI integration and progressive result delivery.

8. **Session recording (HAR + video)** — Essential for debugging and compliance. Patchright supports both natively.

9. **Shadow DOM support** — Growing importance as web components adoption increases.

#### Medium-Term (P2 — Next 2 Quarters)

10. **CLI tool** — Low effort, high discoverability.

11. **OTLP + Prometheus observability** — Required for production monitoring.

12. **Plugin system** — Flesh out `PluginSlot` with discovery, packaging, and community infrastructure.

13. **Multi-browser support** — Firefox and WebKit backends via Playwright.

14. **VS Code extension** — Differentiation opportunity; no competitor has a good one.

15. **TypeScript bindings** — Expands addressable market significantly.

---

## Appendix A: Effort Scale Reference

| Code | Meaning | Typical Scope |
|------|---------|---------------|
| **XS** | Extra Small | < 1 day, < 50 lines changed |
| **S** | Small | 1–3 days, 50–300 lines changed |
| **M** | Medium | 1–2 weeks, 300–1,000 lines changed |
| **L** | Large | 2–4 weeks, 1,000–5,000 lines changed |
| **XL** | Extra Large | 1–3 months, major architecture or product work |

## Appendix B: Priority Scale Reference

| Code | Meaning | Action |
|------|---------|--------|
| **P0** | Critical | Block next release. Must have. |
| **P1** | Important | Needed within one quarter. Should have. |
| **P2** | Desirable | Needed within two quarters. Nice to have. |
