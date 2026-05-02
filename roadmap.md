## Project: Super Browser — Comprehensive Browser Control

---

## Phase 0: Foundation & Tool Contracts (Week 1)

**Goal**: Establish the substrate everything else builds on.

| Task | Deliverable | Key Decision |
|------|-------------|--------------|
| Patchright integration | `BrowserSession` launches Patchright (not vanilla Playwright) | Stealth is non-negotiable — Patchright patches CDP leaks that expose automation  |
| CDP session bridge | `CDPBridge` class via `context.new_cdp_session(page)` | Raw CDP alongside Patchright — no separate browser launch |
| Protocol methods | `compositor_click()`, `compositor_type()`, `capture_screenshot()`, `evaluate()` | Coordinate clicks bypass shadow DOM / iframes at compositor level |
| Tool result envelope | `{ok, data, error, meta}` with duration, method used, screenshot hash | Follows 2026 production agent patterns — structured outputs enable tracing and evals  |

**Validation**: `python -c "from src.SUPER-BROWSER.browser.session import BrowserSession; s = BrowserSession(); p = s.new_page(); p.goto('https://example.com'); print(p.title())"`

---

## Phase 1: Core Control — The Three-Tier Engine (Weeks 2–3)

**Goal**: The browser can actually interact with any page.

| Component | File | Lines | What It Does |
|-----------|------|-------|--------------|
| **MultimodalController** | `control/multimodal.py` | ~180 | Three-tier fallback: selector → coordinate → vision |
| **SuperBrowser facade** | `super_browser.py` | ~250 | `navigate()`, `click()`, `fill()`, `act()`, `extract()`, `observe()` |
| **SuperBrowserTool** | `integration/browser_tool.py` | ~180 | ToolExecutor with 15 actions; falls back to legacy BrowserTool |
| **Tests** | `tests/browser/test_super_browser.py` | ~40 | Core functionality coverage |

### Three-Tier Fallback Logic

```
click(target):
    try:
        page.click(target)                    # Tier 1: DOM selector (fast, deterministic)
        return ActionResult(method="selector")
    except:
        box = cdp.get_bounding_box(target)    # Tier 2: CDP coordinate (robust)
        if box: cdp.compositor_click(box.x, box.y); return ActionResult(method="coordinate")
    except:
        screenshot = cdp.capture_screenshot() # Tier 3: Vision (handles everything)
        coords = llm_vision("Find '{target}' and return x,y", screenshot)
        cdp.compositor_click(coords.x, coords.y)
        return ActionResult(method="vision")
```

**Key Design Decision**: Each result records which method succeeded. Over time, the system learns the optimal method per site/element type — a lightweight form of the "model cascade" pattern for cost optimization .

**Validation**: Live test against `https://example.com` → click link → screenshot. Then test shadow DOM on `https://threads.net`.

---

## Phase 2: Visual Verification — The Look-Act-Look Loop (Week 4)

**Goal**: The browser knows whether its actions worked.

| Component | File | Lines | What It Does |
|-----------|------|-------|--------------|
| **VisualVerifier** | `verification/visual_check.py` | ~100 | Perceptual hashing for pre/post screenshot comparison |
| **Integration** | Update `super_browser.py` | +30 | `look_act_look()` method; optional verify on critical actions |

### Verification Flow

```
look_act_look(action):
    pre_hash = verifier.snapshot(page)
    execute(action)
    post_result = verifier.verify(page, pre_hash)
    if not post_result.changed:
        # Action had no visible effect — retry or escalate
        return ActionResult(success=False, error="No visual change detected")
    return ActionResult(success=True, similarity=post_result.similarity)
```

**Key Design Decision**: Not every click needs verification — only navigation, form submissions, and state-changing actions. This balances reliability against speed/cost.

**Validation**: Test against a page where clicking a broken button produces no visual change. Verify the system detects the failure.

---

## Phase 3: Self-Healing — Recovery from Failure (Weeks 5–6)

**Goal**: The browser doesn't break when sites change.

| Component | File | Lines | What It Does |
|-----------|------|-------|--------------|
| **SessionRecovery** | `healing/session_recovery.py` | ~120 | Stale session, selector failure, navigation recovery |
| **Integration** | Update `super_browser.py` | +20 | Auto-recovery hooks in `click()`, `navigate()`, `fill()` |

### Recovery Strategies

| Failure | Recovery Action |
|---------|-----------------|
| Stale element reference | Detect → re-locate element → retry with same or fallback method |
| Selector not found | Try similar selectors (aria-label, text content, partial match) |
| Navigation timeout | Check for redirects, auth walls, 404s; retry with wait |
| Browser crash | Daemon detects WebSocket disconnect → respawn → resume task |
| CDP session stale | Close page → acquire new page → replay last action |

**Key Design Decision**: The "Ralph Wiggum Loop" pattern — try increasingly creative approaches until success or budget exhaustion . Each recovery attempt costs tokens; cap at 3 attempts before escalating to human.

**Validation**: Intentionally break a selector on a live page. Watch recovery try similar selectors, then coordinate, then vision.

---

## Phase 4: Domain Skills — Learning Over Time (Weeks 7–8)

**Goal**: The browser gets smarter about specific sites.

| Component | File | Lines | What It Does |
|-----------|------|-------|--------------|
| **DomainSkillRegistry** | `skills/domain_knowledge.py` | ~150 | Site-specific knowledge with ACT-R activation (access frequency) |
| **Auto-discovery** | Update `super_browser.py` | +15 | Load skills for hostname on `navigate()` |

### Skill Structure

```python
@dataclass(frozen=True)
class DomainSkill:
    skill_id: str
    domain: str           # "github.com"
    name: str             # "login", "create_issue"
    selectors: dict       # semantic_name → CSS selector
    actions: dict         # action_name → JS or instruction
    provenance: str       # "discovered" | "learned" | "manual"
    access_count: int = 0
    last_used: float = 0.0
```

### Storage & Lifecycle

- **Location**: `~/.SUPER-BROWSER/browser-skills/<domain>/` as JSON
- **Discovery**: Agent generates skills by running tasks; human review optional
- **Activation**: Frequently used skills promoted to "hot" memory; rarely used skills archived

**Key Design Decision**: Follow browser-harness's rule — **agent-generated skills only**. The agent records what actually worked, not what a human guessed would work .

**Validation**: Navigate to GitHub → perform login → check that `github.com/login` skill was auto-generated. Navigate again → verify skill accelerates execution.

---

## Phase 5: Vision & Advanced Control (Weeks 9–10)

**Goal**: Handle pages that defy DOM entirely.

| Component | File | Lines | What It Does |
|-----------|------|-------|--------------|
| **VisionController** | `control/vision.py` | ~80 | LLM-based screenshot analysis for element location |
| **Full integration** | Update `multimodal.py` | +20 | Complete three-tier cascade with vision as final fallback |

### Vision Capabilities

- **Element location**: "Find the blue 'Submit' button and return x,y coordinates"
- **CAPTCHA solving**: "Read the distorted text in the image"
- **State inference**: "What page am I on? Is there an error message?"
- **Canvas interaction**: "Identify the drawing toolbar; where is the pen tool?"

**Key Design Decision**: Vision is the **most expensive** tier. Use the model cascade: GPT-4o Mini for simple location, Claude Sonnet for complex reasoning, Claude Opus for ambiguous judgment calls . Cache vision results to avoid re-analyzing static layouts.

**Validation**: Test against `https://excalidraw.com` (canvas UI), `https://google.com/recaptcha/api2/demo` (CAPTCHA), and a page with SVG icon buttons.

---

## Phase 6: Production Hardening (Weeks 11–12)

**Goal**: The system is safe, observable, and cost-controlled.

| Component | What It Does |
|-----------|--------------|
| **Token Budget Governor** | Daily spend caps, per-action cost limits, alerts at 80% threshold  |
| **Circuit Breakers** | If Cloudflare blocks 5 consecutive requests, switch to Browser Use cloud or pause  |
| **Security Envelope** | Human-in-the-loop for: form submissions with payment, account deletion, external emails  |
| **Tracing** | Every action logged with traceId, stepId, method, duration, token cost, screenshot hash  |
| **Eval Harness** | 50+ test trajectories covering each tier and recovery path |

### Cost Architecture

| Tier | Method | Relative Cost | When Used |
|------|--------|---------------|-----------|
| 1 | DOM selector | 1x (near zero) | Stable, known pages |
| 2 | CDP coordinate | 1.2x (CDP overhead) | Shadow DOM, iframes, dynamic IDs |
| 3 | Vision (Mini) | 10x | Simple element location |
| 3 | Vision (Sonnet) | 50x | Complex reasoning, CAPTCHA |
| 3 | Vision (Opus) | 200x | Ambiguous judgment calls |

**Target**: 85%+ of actions resolve at Tier 1 or 2. Vision usage <10% of actions.

---

## Phase 7: Stress Testing — The Gauntlet (Week 13)

Run the challenging scenarios from the previous analysis:

| Tier | Scenario | What It Validates |
|------|----------|-----------------|
| 1 | Dynamic ID soup, shadow DOM login, nested iframes | Multimodal fallback chain |
| 2 | Cloudflare Turnstile, DataDome slider, Fingerprint.com | Patchright stealth + cloud fallback |
| 3 | Canvas UI, SVG icons, CAPTCHA grid | Vision accuracy |
| 4 | Auth expiry mid-task, browser crash, A/B test variants | Session recovery + skill variants |
| 5 | Honeypot fields, clickjacking, memory exhaustion | Security envelope + health monitoring |
| 6 | Book flight end-to-end, cross-site price comparison | Domain skills + full integration |

---

## Architecture Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    SUPERVISOR (SUPER-BROWSER)                  │
│              Goal: "Book me a flight to Tokyo"                │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                  SUPER BROWSER FACADE                         │
│  navigate()  act()  extract()  observe()  look_act_look()   │
└─────────────────────┬───────────────────────────────────────┘
                      │
    ┌─────────────────┼─────────────────┐
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌─────────────┐
│  TIER 1 │    │   TIER 2    │    │   TIER 3    │
│ Selector│───►│ Coordinate  │───►│   Vision    │
│(Patchright)│  │  (CDP)      │    │  (LLM)      │
└─────────┘    └─────────────┘    └─────────────┘
    │                 │                 │
    ▼                 ▼                 ▼
┌─────────┐    ┌─────────────┐    ┌─────────────┐
│Domain   │    │ Visual      │    │ Token Budget │
│Skills   │    │ Verifier    │    │ Governor     │
│(ACT-R)  │    │ (hash diff) │    │ (cost caps)  │
└─────────┘    └─────────────┘    └─────────────┘
    │                 │                 │
    └─────────────────┴─────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│              STEALTH LAYER (Patchright / Cloud)               │
│  CDP leak patching • Proxy rotation • CAPTCHA solving         │
│  Real Chrome profile • TLS fingerprint matching               │
└─────────────────────────────────────────────────────────────┘
```

---

## Key Milestones & Deliverables

| Week | Milestone | Deliverable |
|------|-----------|-------------|
| 1 | Foundation | Patchright session + CDP bridge working |
| 3 | Core Control | Three-tier fallback; 40 tests passing |
| 4 | Verification | Look-act-look loop; visual diff working |
| 6 | Self-Healing | Auto-recovery from stale sessions, broken selectors |
| 8 | Domain Skills | Skill registry; auto-discovery on GitHub, LinkedIn |
| 10 | Vision | Canvas, CAPTCHA, SVG icon handling |
| 12 | Production | Budget governor, circuit breakers, security envelope |
| 13 | Gauntlet | All 6 challenge tiers completed; eval dataset >50 cases |

---

## Critical Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Action success rate | >95% | `success=True` in ActionResult |
| Tier 1/2 resolution | >85% | `method in ("selector", "coordinate")` |
| Average action cost | <$0.01 | Token spend / action count |
| Recovery success rate | >70% | Failed first attempt → succeeds after recovery |
| Anti-bot pass rate | >90% | nowsecure.nl, datadome.co, fingerprint.com |
| Test suite coverage | >90% | pytest coverage report |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Patchright breaks with Chrome update | Pin Chrome version; monitor Patchright releases |
| Vision costs explode | Hard cap at 10% of actions; cache static layouts |
| Site redesign invalidates all skills | Store multiple variants; A/B test detection |
| Cloudflare evolves beyond Patchright | Browser Use cloud as circuit-breaker fallback |
| Agent writes bad helper code | Sandbox file writes; review before execution |

This roadmap transforms the design document into a 13-week execution plan with clear milestones, measurable outcomes, and production-grade guardrails.
