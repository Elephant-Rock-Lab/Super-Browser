# Architecture

> **Super Browser** v1.9.3 — System architecture, data flow, and extension points.

---

## Table of Contents

- [System Overview](#system-overview)
- [Architecture Diagram](#architecture-diagram)
- [Major Subsystems](#major-subsystems)
- [Data Flow](#data-flow)
- [Component Inventory](#component-inventory)
- [Extension Points for v2.0](#extension-points-for-v20)

---

## System Overview

Super Browser is a **browser-control library for AI agents**. It provides a three-tier action cascade (LLM client → built-in skills → raw browser), self-healing selectors, stealth-mode navigation, token-budget management, and security guardrails — all behind a single `SuperBrowser` façade.

The architecture is designed around these principles:

1. **Façade Pattern** — `SuperBrowser` is the single entry point; all subsystems are composed internally.
2. **Protocol-Based LLM** — Any LLM provider can be used by implementing the `LLMClient` protocol.
3. **Defence in Depth** — Stealth, security, and budget checks are layered; no single bypass compromises the system.
4. **Recovery by Default** — Every action can be retried, rolled back, or escalated.
5. **Observability First** — Every action produces a traceable `ActionResult` with timing, method, and error metadata.

---

## Architecture Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                            USER CODE                                     │
│                         (async Python)                                   │
└──────────────────────────────┬───────────────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        SuperBrowser (Facade)                             │
│                                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │navigate()│  │  click() │  │  fill()  │  │  act()   │  │extract() │ │
│  └──────────┘  └──────────┘  └──────────┘  └────┬─────┘  └──────────┘ │
│                                                  │                       │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │                       │
│  │observe() │  │delegate()│  │  abort() │       │                       │
│  └──────────┘  └──────────┘  └──────────┘       │                       │
└──────────────────────────────────────────────────┼───────────────────────┘
                                                   │
                    ┌──────────────────────────────┘
                    ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          AgentLoop                                       │
│                                                                          │
│   ┌─────────────┐    ┌──────────────┐    ┌───────────────────┐         │
│   │ Plan Mgmt   │    │ Loop Detector│    │ Action Dispatcher │         │
│   │ (create/    │    │ (stagnation  │    │ (security +       │         │
│   │  replan)    │    │  detection)  │    │  stealth checks)  │         │
│   └──────┬──────┘    └──────┬───────┘    └────────┬──────────┘         │
│          │                  │                      │                     │
│          ▼                  ▼                      ▼                     │
│   ┌──────────────────────────────────────────────────────┐              │
│   │              LLMClient (Protocol)                    │              │
│   │  ┌───────────────┐  ┌───────────────┐               │              │
│   │  │ AnthropicLLM  │  │ OpenAILLM     │               │              │
│   │  │ Client        │  │ Client        │               │              │
│   │  └───────────────┘  └───────────────┘               │              │
│   └──────────────────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────────────────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────┐  ┌──────────────────┐  ┌────────────────────────┐
│  Stealth    │  │     Budget       │  │     Recovery           │
│  Manager    │  │     System       │  │     System             │
│             │  │                  │  │                        │
│ ┌─────────┐ │  │ ┌──────────────┐│  │ ┌────────────────────┐ │
│ │Header   │ │  │ │ Budget       ││  │ │ CheckpointManager  │ │
│ │Randomiz.│ │  │ │ Governor     ││  │ │ (save/restore      │ │
│ └─────────┘ │  │ │ (3-scope)    ││  │ │  page state)       │ │
│ ┌─────────┐ │  │ └──────────────┘│  │ └────────────────────┘ │
│ │UA Pool  │ │  │ ┌──────────────┐│  │ ┌────────────────────┐ │
│ │(rotation│ │  │ │ Model Cascade││  │ │ RecoveryCoord.     │ │
│ └─────────┘ │  │ │ (cost-tier   ││  │ │ (error classify,   │ │
│ ┌─────────┐ │  │ │  fallback)   ││  │ │  auto-retry)       │ │
│ │CAPTCHA  │ │  │ └──────────────┘│  │ └────────────────────┘ │
│ │Watchdog │ │  │ ┌──────────────┐│  │ ┌────────────────────┐ │
│ └─────────┘ │  │ │ Cred. Pool   ││  │ │ Watchdog           │ │
│ ┌─────────┐ │  │ │ + Circuit    ││  │ │ (health monitor)   │ │
│ │Proxy    │ │  │ │   Breaker    ││  │ └────────────────────┘ │
│ │Escalator│ │  │ └──────────────┘│  └────────────────────────┘
│ └─────────┘ │  │ ┌──────────────┐│
│ ┌─────────┐ │  │ │ Context      ││
│ │Action   │ │  │ │ Compressor   ││
│ │Policy   │ │  │ └──────────────┘│
│ └─────────┘ │  └──────────────────┘
└─────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                        Browser Layer                                     │
│                                                                          │
│   ┌─────────────────┐  ┌─────────────────┐  ┌────────────────────┐     │
│   │ BrowserSession  │  │ MultimodalCtrl  │  │ Tool Registry      │     │
│   │ (Patchright)    │  │ (click/fill/    │  │ (action dispatch)  │     │
│   │                 │  │  observe)       │  │                    │     │
│   └────────┬────────┘  └─────────────────┘  └────────────────────┘     │
│            │                                                            │
│            ▼                                                            │
│   ┌────────────────────────────────────────────┐                       │
│   │        Chromium (via CDP / Patchright)      │                       │
│   └────────────────────────────────────────────┘                       │
└──────────────────────────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      Cross-Cutting Concerns                              │
│                                                                          │
│   ┌─────────────┐  ┌──────────────┐  ┌───────────────┐                 │
│   │  Tracing     │  │  Security    │  │  Skills       │                 │
│   │  (FlowLogger)│  │  (SecMgr)    │  │  (SkillReg.)  │                 │
│   └─────────────┘  └──────────────┘  └───────────────┘                 │
│                                                                          │
│   ┌─────────────┐  ┌──────────────┐  ┌───────────────┐                 │
│   │  Vision     │  │  Verification│  │  Config       │                 │
│   │  (VisionCtrl│  │  (VisualVfr) │  │  (unified)    │                 │
│   └─────────────┘  └──────────────┘  └───────────────┘                 │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Major Subsystems

### 1. Agent (SuperBrowser + AgentLoop)

**Purpose:** Orchestrate LLM-driven browser automation with planning, loop detection, and error recovery.

**Key Classes:**
- `SuperBrowser` — Facade that composes all subsystems. Public API: `navigate()`, `click()`, `fill()`, `act()`, `extract()`, `observe()`, `delegate()`.
- `AgentLoop` — Step-based interaction cycle. Manages plan lifecycle, stagnation detection, retry budgets, and per-action timeouts.
- `ToolRegistry` — Registers and dispatches tool functions. Tools are Python callables with optional security levels and toolset membership.
- `SubagentDelegator` — Spawns parallel sub-agent sessions for concurrent task execution.

**Design Decisions:**
- The agent loop builds a prompt containing the current plan, recent step history, available tool API, and any loop-detection nudges.
- Stagnation (no page change for N steps) triggers automatic replanning.
- Loop detection uses action fingerprinting with configurable nudge levels (1–3). Level 3 aborts the loop.

### 2. Stealth

**Purpose:** Make browser automation resistant to common anti-bot detection vectors.

**Key Classes:**
- `StealthManager` — Orchestrator for the multi-layer stealth stack.
- `HeaderRandomizer` — Generates unique HTTP header sets per request.
- `UserAgentPool` — Rotating pool of realistic user-agent strings.
- `CAPTCHAWatchdog` — Detects CAPTCHA challenges via DOM selector monitoring.
- `ProxyEscalator` — Automatic proxy tier escalation (direct → residential → datacenter) based on HTTP status codes.
- `StealthActionPolicy` — Rule-based policy for allowing/denying/confirming actions on sensitive domains.
- `FingerprintScorer` — Weighted composite stealth score (0–100) with letter grades.

**Detection Layers:**
1. **JavaScript Injection** — Override `navigator.webdriver`, plugins, mimetypes via Patchright route interception.
2. **HTTP Headers** — Randomised per-request headers with realistic browser fingerprints.
3. **TLS Fingerprinting** — httpmorph integration for JA4 hash matching.
4. **Proxy Rotation** — Multi-tier proxy escalation with domain-specific caching.
5. **CAPTCHA Monitoring** — Continuous DOM scanning for known CAPTCHA iframes/elements.

### 3. Budget

**Purpose:** Prevent runaway LLM costs with three-scope budget enforcement.

**Key Classes:**
- `TokenBudgetGovernor` — Thread-safe governor with daily, per-action, and per-turn scopes. Auto-resets daily. Supports state persistence to disk.
- `BudgetAwareLLMClient` — Decorator that wraps any `LLMClient` and records token usage + estimated USD cost after every call.
- `ModelCascade` — Cost-optimised model selection: starts with cheapest tier, escalates to more capable (and expensive) models only when needed.
- `ContextCompressor` — Reduces token usage by pruning tool output, summarising turns, or head-tail protection.
- `CredentialPool` — Rotates API keys to distribute load across multiple credentials.
- `CircuitBreaker` — Trips after consecutive failures, preventing cascading errors.

**Budget Flow:**
```
LLM Call → BudgetAwareLLMClient → TokenBudgetGovernor
                │                        │
                │                        ├─ Check daily cap
                │                        ├─ Check per-action cap
                │                        ├─ Check per-turn tokens
                │                        │
                │                        └─ Emit BudgetAlert if threshold crossed
                │
                └─ Propagate alert to callback / log
```

### 4. Recovery

**Purpose:** Automatically recover from browser errors, crashes, and unexpected page states.

**Key Classes:**
- `RecoveryCoordinator` — Top-level coordinator that classifies errors and selects recovery strategies.
- `CheckpointManager` — Persists page state (URL, scroll, forms, cookies) to JSON. Supports save/restore/list/delete.
- `Watchdog` — Health monitor that detects crashes, stale elements, navigation timeouts, and security violations.
- `ErrorClassifier` — Maps exceptions to `ErrorType` + `RecoveryHint` pairs.

**Recovery Strategies:**
| Strategy | Trigger |
|---|---|
| `retry` | Transient errors (timeout, rate limit) |
| `retry_similar_selector` | `selector_not_found` |
| `reattach_session` | CDP session stale |
| `respawn_browser` | Browser crash |
| `checkpoint_rollback` | Corrupted state |
| `re_prompt_llm` | Context overflow |
| `nudge_agent` | Loop detected |

### 5. Security

**Purpose:** Enforce safety guardrails on all browser actions.

**Key Classes:**
- `SecurityManager` — Centralised security policy enforcer.
- `CredentialVault` — Encrypted local credential storage (Fernet AES-128-CBC + HMAC-SHA256).

**Security Levels:**
- `safe` — Read-only actions (navigate, observe, extract)
- `sensitive` — Data-modifying actions (fill, click)
- `dangerous` — Destructive actions (delete, submit forms)

Every action dispatched through `AgentLoop` passes through the security manager before execution.

---

## Data Flow

### Typical Agent Action Flow

```
User: sb.act("Search for 'python books'")
         │
         ▼
   SuperBrowser.act()
         │
         ▼
   AgentLoop.run(instruction)
         │
         ├─ 1. Request initial plan from LLM
         │     LLMClient.create_plan() → [PlanItem, ...]
         │
         ├─ 2. Step loop (max_steps iterations):
         │     │
         │     ├─ Build prompt (plan + history + tools + nudge)
         │     │
         │     ├─ LLMClient.propose_action(prompt) → {action, params} | {done}
         │     │
         │     ├─ Loop detector: record_and_check(action)
         │     │   └─ If repeated: emit nudge, may abort
         │     │
         │     ├─ Security check: SecurityManager.check_action()
         │     │   └─ If denied: return error ActionResult
         │     │
         │     ├─ Stealth check: StealthManager.evaluate_action()
         │     │   └─ If denied: return error ActionResult
         │     │
         │     ├─ Dispatch action: ToolRegistry.get(name).handler(**params)
         │     │
         │     ├─ Compute page fingerprint (URL + title hash)
         │     │
         │     ├─ Detect page change → reset stagnation counter
         │     │
         │     └─ Emit StepEvent via callback
         │
         └─ 3. Return LoopResult
               (steps, plan, completion_reason, timing)
```

### Budget Tracking Flow

```
AgentLoop calls LLM
         │
         ▼
BudgetAwareLLMClient.propose_action()
         │
         ├─ Delegate to underlying LLMClient
         │
         ├─ Extract token counts from response
         │
         ├─ Estimate USD cost (_estimate_cost_usd)
         │
         ├─ Create TokenUsageRecord
         │
         └─ TokenBudgetGovernor.record_usage(record)
               │
               ├─ Update daily_spend_usd
               ├─ Update action_spend_usd
               ├─ Update turn_tokens_used
               │
               ├─ Check thresholds:
               │   ├─ 80% → WARNING alert
               │   ├─ 95% → CRITICAL alert
               │   └─ 100% → EXHAUSTED alert
               │
               └─ Invoke alert_callback if alert generated
```

### Recovery Flow

```
Action fails with exception
         │
         ▼
RecoveryCoordinator.execute_with_recovery()
         │
         ├─ Classify error → ErrorType + RecoveryHint
         │
         ├─ Select strategy:
         │   ├─ retry (up to max_attempts)
         │   ├─ retry_similar_selector (self-healing)
         │   ├─ reattach_session (CDP stale)
         │   ├─ respawn_browser (crash)
         │   ├─ checkpoint_rollback (corruption)
         │   └─ abort (unrecoverable)
         │
         ├─ Execute recovery strategy
         │
         └─ Emit RecoveryEvent
```

---

## Component Inventory

| Package | Module | Primary Class | Purpose |
|---|---|---|---|
| `agent` | `facade.py` | `SuperBrowser` | Main entry point |
| `agent` | `loop.py` | `AgentLoop` | Step-based LLM cycle |
| `agent` | `registry.py` | `ToolRegistry` | Tool dispatch |
| `agent` | `delegator.py` | `SubagentDelegator` | Parallel sub-agents |
| `agent` | `loop_detector.py` | `ActionLoopDetector` | Stagnation detection |
| `agent.llm` | `protocol.py` | `LLMClient` | Async LLM protocol |
| `agent.llm` | `factory.py` | `create_llm()` | LLM client factory |
| `agent.llm` | `budget_aware.py` | `BudgetAwareLLMClient` | Cost-tracking wrapper |
| `agent.llm` | `anthropic_client.py` | `AnthropicLLMClient` | Anthropic provider |
| `agent.llm` | `openai_client.py` | `OpenAILLMClient` | OpenAI provider |
| `budget` | `governor.py` | `TokenBudgetGovernor` | 3-scope budget |
| `budget` | `cost_estimator.py` | `CostEstimator` | Token → USD |
| `stealth` | `manager.py` | `StealthManager` | Stealth orchestrator |
| `stealth` | `headers.py` | `HeaderRandomizer` | Header variation |
| `stealth` | `user_agent_pool.py` | `UserAgentPool` | UA rotation |
| `stealth` | `captcha.py` | `CAPTCHAWatchdog` | CAPTCHA monitoring |
| `stealth` | `proxy.py` | `ProxyEscalator` | Proxy tier escalation |
| `stealth` | `action_policy.py` | `StealthActionPolicy` | Action rules |
| `stealth` | `diagnostics.py` | `run_diagnostics()` | Health checks |
| `recovery` | `checkpoint.py` | `CheckpointManager` | State persistence |
| `recovery` | `coordinator.py` | `RecoveryCoordinator` | Error recovery |
| `security` | `manager.py` | `SecurityManager` | Safety guardrails |
| `security` | `credential_vault.py` | `CredentialVault` | Encrypted storage |
| `browser` | `session.py` | `BrowserSession` | Patchright wrapper |
| `browser` | `config.py` | `SessionConfig` | Browser settings |
| `interaction` | `controller.py` | `MultimodalController` | Click/fill/observe |
| `tracing` | `flow_logger.py` | `FlowLogger` | Trace spans |
| `vision` | `controller.py` | `VisionController` | Screenshot analysis |
| `verification` | `verifier.py` | `VisualVerifier` | Visual validation |
| `skills` | `registry.py` | `SkillRegistry` | Skill auto-discovery |
| `config.py` | — | `Config` | Unified configuration |

---

## Extension Points for v2.0

### Configuration

`Config` (in `super_browser.config`) is the **composition root** — the single entry point for all configuration. Subsystem configs (`SessionConfig`, `BudgetConfig`, `StealthConfig`, etc.) are composed into `Config` and passed through explicit constructors only.

`SuperBrowserConfig` (in `agent/config.py`) is a legacy alias that still works but is not the recommended path for new code. See `docs/api-stability.md` for the full contract.

### 1. Custom LLM Providers

The `LLMClient` protocol is `@runtime_checkable`. Any class implementing `propose_action()`, `create_plan()`, and `replan()` is accepted. Future providers:

```python
# Example: Gemini provider
class GeminiLLMClient:
    async def propose_action(self, prompt, *, tools=None): ...
    async def create_plan(self, instruction, *, tools): ...
    async def replan(self, *, instruction, original_plan, failed_step, error): ...
```

### 2. Tool Plugins

Tools are registered via `register_tool()`. Future extensions:

- **Tool annotations** — Security level, cost estimate, idempotency flag
- **Tool versioning** — Multiple versions of the same tool with automatic migration
- **Streaming tools** — Async generators that yield intermediate results

### 3. Stealth Plugins

The stealth stack is modular. New detection/prevention layers can be added:

- **Canvas fingerprint protection** — Inject noise into canvas rendering
- **WebGL fingerprint randomisation** — Override WebGL renderer strings
- **Audio context fingerprinting** — Normalise AudioContext behaviour

### 4. Budget Strategies

Current model cascade is cost-tier based. Future strategies:

- **Quality-optimised cascade** — Start with capable model, downgrade only when budget is tight
- **Task-aware routing** — Use different models for planning vs. execution
- **Multi-provider arbitrage** — Route to whichever provider has the lowest cost for each model tier

### 5. Recovery Extensions

- **Cross-session recovery** — Persist checkpoints to cloud storage for multi-machine recovery
- **Replay-based testing** — Record and replay action trajectories for regression testing
- **Self-healing selectors** — AI-powered selector repair when DOM changes

### 6. Observability

- **OpenTelemetry integration** — Export traces to Jaeger/Zipkin via OTLP sink
- **Metrics export** — Prometheus-compatible metrics endpoint for budget, latency, and error rates
- **Session recording** — Full video recording of browser sessions for debugging

### 7. Multi-Browser Support

Currently built on Patchright (Chromium). Future:

- **Firefox support** — Via Playwright Firefox backend
- **Mobile emulation** — Device mode with touch events
- **Network interception** — Request/response mocking for testing

---

## Configuration Hierarchy

```
Config (unified)
 ├── browser: SessionConfig         Headless, viewport, browser args
 ├── agent: AgentConfig             LLM provider, model, API key
 │    └── core: SuperBrowserConfig  Max steps, stagnation, features
 ├── stealth: StealthConfig         Proxy, CAPTCHA, UA, init scripts
 ├── budget: BudgetConfig           Daily cap, action cap, turn limit
 ├── security: SecurityConfig       Action security levels
 └── tracing: TracingConfig         Sink type, enabled flag
```

All configs are **frozen dataclasses** (immutable after creation). Construct via:

```
Config.from_env()   ← SB_* environment variables
Config.from_yaml()  ← YAML file
Config.from_dict()  ← Python dictionary
Config()            ← All defaults
```
