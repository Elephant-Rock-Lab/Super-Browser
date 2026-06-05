# API Reference

> **Super Browser** v1.9.3 — Complete public API documentation.

This reference covers every public class, method, and function in Super Browser. Classes are grouped by subsystem.

---

## Table of Contents

- [SuperBrowser (Facade)](#superbrowser-facade)
- [AgentLoop](#agentloop)
- [Config](#config)
- [LLMClient Protocol](#llmclient-protocol)
- [create_llm Factory](#create_llm-factory)
- [BudgetAwareLLMClient](#budgetawarellmclient)
- [StealthManager](#stealthmanager)
- [TokenBudgetGovernor](#tokenbudgetgovernor)
- [CheckpointManager](#checkpointmanager)
- [Result Types](#result-types)
- [Configuration Sub-types](#configuration-sub-types)
- [EventBus](#eventbus)
- [SessionRecorder](#sessionrecorder)
- [RecordingReplayer](#recordingreplayer)
- [MemoryStore](#memorystore)
- [Plugin System](#plugin-system)
- [HumanBehaviorAdapter](#humanbehavioradapter)
- [HumanConfig](#humanconfig)
- [FingerprintScanner](#fingerprintscanner)
- [FingerprintScorer](#fingerprintscorer)
- [FingerprintScore & FingerprintCheck](#fingerprintscore--fingerprintcheck)

---

## SuperBrowser (Facade)

**Module:** `super_browser.agent.facade`

The primary entry point for all browser automation. Wraps the agent loop, stealth stack, budget system, recovery coordinator, and browser session behind a single async API.

### Constructor

```python
class SuperBrowser(
    config: Optional[SuperBrowserConfig] = None,
    *,
    tool_registry: Optional[ToolRegistry] = None,
    llm_client: Optional[LLMClient] = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `config` | `SuperBrowserConfig \| None` | `None` | Agent configuration. Uses defaults when `None`. |
| `tool_registry` | `ToolRegistry \| None` | `None` | Custom tool registry. Creates a default registry when `None`. |
| `llm_client` | `LLMClient \| None` | `None` | LLM client for `act()` calls. **Required** for `act()`. |

### Lifecycle Methods

#### `start() → None` *(async)*

Launches the browser session and initialises all configured subsystems (recovery, budget, tracing, security, stealth, vision, skills).

```python
sb = SuperBrowser(config)
await sb.start()
# ... use sb ...
await sb.stop()
```

#### `stop() → None` *(async)*

Gracefully shuts down all subsystems and closes the browser session.

#### `__aenter__() → SuperBrowser` / `__aexit__(*exc) → None`

Async context manager for automatic lifecycle management:

```python
async with SuperBrowser(config) as sb:
    await sb.navigate("https://example.com")
```

### Navigation

#### `navigate(url, *, wait_until="domcontentloaded") → ActionResult`

Navigate the browser to a URL.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `url` | `str` | *(required)* | The URL to navigate to. |
| `wait_until` | `str` | `"domcontentloaded"` | Playwright load event to wait for (`"load"`, `"domcontentloaded"`, `"networkidle"`). |

**Returns:** `ActionResult` with `NavigateResult` data containing `url`, `final_url`, and `title`.

```python
result = await sb.navigate("https://example.com")
if result.ok:
    print(result.data.title)  # "Example Domain"
    print(result.data.final_url)  # "https://example.com/"
```

### Interaction

#### `click(target, *, description=None) → ActionResult`

Click an element identified by CSS selector, text, or accessibility role.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `target` | `str` | *(required)* | Element selector or description. |
| `description` | `str \| None` | `None` | Human-readable description for logging. |

```python
result = await sb.click("#login-button", description="Submit login form")
```

#### `fill(target, value, *, clear_first=True, description=None) → ActionResult`

Fill a form field with a value.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `target` | `str` | *(required)* | Element selector. |
| `value` | `str` | *(required)* | The value to type. |
| `clear_first` | `bool` | `True` | Clear existing content before typing. |
| `description` | `str \| None` | `None` | Human-readable description. |

```python
await sb.fill("#email", "user@example.com")
await sb.fill("#password", "s3cret", clear_first=False)
```

### Agent

#### `act(instruction, *, max_steps=50) → ActionResult`

Execute a natural-language instruction using the LLM-powered agent loop. Requires `llm_client` to be configured.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `instruction` | `str` | *(required)* | Natural-language instruction (e.g., "Find the cheapest flight"). |
| `max_steps` | `int` | `50` | Maximum agent loop iterations. |

**Returns:** `ActionResult` with `DelegatedResult` data containing `instruction`, `completion_reason`, `steps_executed`, `budget_remaining`, and `execution_history`.

```python
result = await sb.act("Search for 'python automation' and open the first result")
if result.ok:
    print(f"Completed in {result.data.steps_executed} steps")
```

**Raises:** `ConfigurationError` if no `llm_client` was provided.

#### `act_stream(instruction, *, max_steps=50) → AsyncIterator[StreamEvent]`

Streaming variant of :meth:`act`. Yields ``StreamEvent`` for each step lifecycle event, allowing callers to observe progress in real time. The final event is ``StepEvent.DONE`` with ``completion_reason``, ``total_steps``, and ``total_duration_ms``.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `instruction` | `str` | *(required)* | Natural-language instruction. |
| `max_steps` | `int` | `50` | Maximum agent loop iterations. |

**Yields:** `StreamEvent` — frozen dataclass ``(type: StepEvent, data: dict)`` for each lifecycle event. The ``data`` dict should be treated as read-only by callers.

```python
async for event in sb.act_stream("Fill the form"):
    if event.type == "step_complete":
        print(f"Step done: {event.data}")
    if event.type == "done":
        print(f"Finished: {event.data['completion_reason']}")
```

**Raises:** `ConfigurationError` if no `llm_client` was provided. Yields a single ``ABORT`` event if the browser is not started.

### Extraction

#### `extract(query, *, selector=None, schema=None) → ActionResult`

Extract data from the current page. Supports CSS-selector-based extraction or accessibility-tree snapshot.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `query` | `str` | *(required)* | Description of what to extract. |
| `selector` | `str \| None` | `None` | CSS selector for targeted extraction. |
| `schema` | `dict \| None` | `None` | *(Reserved for v2.0)* JSON Schema for structured extraction. |

```python
# Extract via selector
result = await sb.extract("product price", selector=".price-tag")
print(result.data.extracted)

# Extract full page accessibility snapshot
result = await sb.extract("page content")
print(result.data.extracted)
```

#### `observe() → ActionResult`

Capture a snapshot of the current page state: URL, title, and interactive element count.

```python
obs = await sb.observe()
print(obs.data)
# {"url": "https://example.com", "title": "...", "interactive_elements": 5, "total_elements": 42}
```

### Delegation

#### `delegate(tasks, *, max_concurrency=4) → DelegationResult`

Spawn parallel sub-agents to execute multiple tasks concurrently.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `tasks` | `list[str]` | *(required)* | List of natural-language instructions. |
| `max_concurrency` | `int` | `4` | Maximum parallel sub-agents. |

```python
result = await sb.delegate([
    "Find the CEO's name",
    "Get the company address",
    "List the top 3 products",
])
print(f"Completed: {result.completed_count}, Failed: {result.failed_count}")
```

### Tool Management

#### `tools(*, toolset=None) → str`

Get the API description of registered tools. Optionally filter by toolset name.

#### `register_tool(func, *, toolsets=()) → None`

Register a custom tool function. The function's docstring becomes the tool description.

```python
def my_scroll_tool(direction: str, pixels: int = 500) -> dict:
    """Scroll the page in a direction by a number of pixels."""
    ...

sb.register_tool(my_scroll_tool, toolsets=("navigation",))
```

### Other

#### `abort() → None`

Signal the agent loop to stop at the next step boundary.

#### `configure_verification(config=None) → None`

Configure the visual verification system for action confirmations.

#### `learn_from_trajectory(domain, task_description, actions_taken, selectors_used, *, preferred_tier=None) → Any`

Teach the skill registry from a recorded interaction trajectory.

#### `is_running` *(property)* → `bool`

Whether the browser session is currently active.

### Tab Management

#### `open_tab(url=None) → ActionResult`

Open a new browser tab, optionally navigating to a URL.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `url` | `str \| None` | `None` | URL to navigate to. Opens a blank tab if omitted. |

```python
result = await sb.open_tab("https://example.com")
```

#### `switch_tab(tab_id) → ActionResult`

Switch to a different tab by its integer ID.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `tab_id` | `int` | *required* | Tab ID to switch to. |

```python
await sb.switch_tab(1)
```

#### `close_tab(tab_id) → ActionResult`

Close a tab by its ID.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `tab_id` | `int` | *required* | Tab ID to close. |

```python
await sb.close_tab(2)
```

#### `list_tabs() → ActionResult`

List all open tabs.

```python
tabs = await sb.list_tabs()
for t in tabs.data:
    print(t["title"])
```

### File Operations

#### `upload_file(selector, file_path) → ActionResult`

Upload a file to an `<input type="file">` element.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `selector` | `str` | *required* | CSS selector for the file input. |
| `file_path` | `str` | *required* | Path to the file to upload. |

```python
await sb.upload_file("#resume", "/path/to/resume.pdf")
```

#### `download(url_or_selector, *, save_path=None) → ActionResult`

Download a file by clicking a link or navigating to a URL.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `url_or_selector` | `str` | *required* | URL or CSS selector to trigger download. |
| `save_path` | `str \| None` | `None` | Where to save the file. Uses temp dir if omitted. |

```python
result = await sb.download("a.download-link", save_path="./report.pdf")
```

### Frame Scoping

#### `enter_frame(selector) → ActionResult`

Enter an iframe, scoping subsequent interactions to it.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `selector` | `str` | *required* | CSS selector for the iframe. |

```python
await sb.enter_frame("iframe#payment")
await sb.fill("#card", "4242...")
await sb.exit_frame()
```

#### `exit_frame() → ActionResult`

Exit the current iframe, returning to the parent frame.

### Shadow DOM

#### `query_shadow(host_selector, inner_selector) → ActionResult`

Query an element inside a Shadow DOM.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `host_selector` | `str` | *required* | CSS selector for the shadow host. |
| `inner_selector` | `str` | *required* | CSS selector inside the shadow root. |

```python
result = await sb.query_shadow("my-widget", "#value")
print(result.data.text)
```

### Network Interception

#### `intercept_requests(pattern="*", *, action="log") → ActionResult`

Enable network request interception.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `pattern` | `str` | `"*"` | URL pattern to match. |
| `action` | `str` | `"log"` | Interception action (`"log"`, `"block"`, `"modify"`). |

```python
await sb.intercept_requests("*/api/*", action="log")
```

#### `block_requests(pattern="*") → ActionResult`

Block all requests matching a URL pattern.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `pattern` | `str` | `"*"` | URL pattern to block. |

```python
await sb.block_requests("*.tracking.*")
```

#### `mock_response(pattern, body, *, content_type="application/json", status=200) → ActionResult`

Mock a network response for matching requests.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `pattern` | `str` | *required* | URL pattern to match. |
| `body` | `str` | *required* | Response body. |
| `content_type` | `str` | `"application/json"` | Content-Type header. |
| `status` | `int` | `200` | HTTP status code. |

```python
await sb.mock_response("*/api/config", '{"theme":"dark"}')
```

#### `clear_interceptions() → ActionResult`

Remove all network request interceptions.

```python
await sb.clear_interceptions()
```

### Session Persistence

#### `save_session(path) → ActionResult`

Save cookies and session state to a JSON file.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `path` | `str` | *required* | File path to save session data. |

```python
await sb.save_session("session.json")
```

#### `load_session(path) → ActionResult`

Load cookies and session state from a JSON file.

| Parameter | Type | Default | Description |
|:----------|:-----|:--------|:------------|
| `path` | `str` | *required* | File path to load session data from. |

```python
await sb.load_session("session.json")
```

---

## AgentLoop

**Module:** `super_browser.agent.loop`

The step-based LLM interaction cycle that powers `SuperBrowser.act()`. Handles planning, loop detection, stagnation recovery, and action dispatch.

### Constructor

```python
class AgentLoop(
    controller: Any,
    registry: ToolRegistry,
    llm_client: Any,
    *,
    max_steps: int = 50,
    loop_detector: Optional[ActionLoopDetector] = None,
    abort_signal: Optional[asyncio.Event] = None,
    event_callback: Optional[Callable[[StepEvent, dict], Awaitable[None]]] = None,
    stagnation_threshold: int = 3,
    recovery_coordinator: Optional[Any] = None,
    budget_client: Optional[Any] = None,
    flow_logger: Optional[Any] = None,
    security_manager: Optional[Any] = None,
    stealth_manager: Optional[Any] = None,
    debug_config: Optional[DebugConfig] = None,
    retry_budget: Optional[RetryBudget] = None,
    timeout_config: Optional[ActionTimeoutConfig] = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `controller` | `Any` | *(required)* | `MultimodalController` for browser interaction. |
| `registry` | `ToolRegistry` | *(required)* | Tool registry for action dispatch. |
| `llm_client` | `Any` | *(required)* | LLM client implementing `LLMClient` protocol. |
| `max_steps` | `int` | `50` | Maximum loop iterations before forced stop. |
| `loop_detector` | `ActionLoopDetector \| None` | `None` | Custom loop detector instance. |
| `abort_signal` | `asyncio.Event \| None` | `None` | External signal to abort the loop. |
| `event_callback` | `Callable \| None` | `None` | Callback invoked on each `StepEvent`. |
| `stagnation_threshold` | `int` | `3` | Consecutive stagnant steps before auto-replan. |
| `recovery_coordinator` | `Any` | `None` | Recovery coordinator for error resilience. |
| `budget_client` | `Any` | `None` | Budget-aware LLM client wrapper. |
| `flow_logger` | `Any` | `None` | Tracing/observability logger. |
| `security_manager` | `Any` | `None` | Security policy enforcer. |
| `stealth_manager` | `Any` | `None` | Stealth policy enforcer. |
| `debug_config` | `DebugConfig \| None` | `None` | Debug artifact capture settings. |
| `retry_budget` | `RetryBudget \| None` | `None` | Per-action retry limits. |
| `timeout_config` | `ActionTimeoutConfig \| None` | `None` | Per-action timeout settings. |

### Methods

#### `run(instruction, *, abort_signal=None, initial_plan=None) → LoopResult` *(async)*

Execute the agent loop for the given instruction.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `instruction` | `str` | *(required)* | Natural-language instruction. |
| `abort_signal` | `asyncio.Event \| None` | `None` | Override the constructor abort signal. |
| `initial_plan` | `list[PlanItem] \| None` | `None` | Pre-built plan (skips LLM planning). |

**Returns:** `LoopResult` with `instruction`, `steps`, `plan`, `completion_reason`, `total_duration_ms`, `total_steps`, `loop_detections`, `replan_count`.

**Completion reasons:** `"success"`, `"max_steps"`, `"abort"`, `"loop_detected"`.

```python
loop = AgentLoop(controller, registry, llm_client, max_steps=20)
result = await loop.run("Click the submit button")
print(result.completion_reason)  # "success"
print(result.total_steps)        # 3
```

---

## Config

**Module:** `super_browser.config`

Top-level frozen dataclass that composes all sub-configurations. The recommended way to configure Super Browser.

### Constructor

```python
@dataclass(frozen=True)
class Config(
    browser: SessionConfig = SessionConfig(),
    agent: AgentConfig = AgentConfig(),
    stealth: StealthConfig = StealthConfig(),
    budget: BudgetConfig = BudgetConfig(),
    security: SecurityConfig = SecurityConfig(),
    tracing: TracingConfig = TracingConfig(),
)
```

### Class Methods

#### `Config.from_env() → Config`

Build from `SB_*` environment variables.

| Env Variable | Target Field |
|---|---|
| `SB_LLM_PROVIDER` | `agent.llm_provider` |
| `SB_LLM_MODEL` | `agent.llm_model` |
| `SB_LLM_API_KEY` | `agent.llm_api_key` |
| `SB_HEADLESS` | `browser.headless` |
| `SB_PROXY_URL` | `stealth.proxy_url` |
| `SB_DAILY_BUDGET` | `budget.daily_cap_usd` |
| `SB_STEALTH_TIER` | `stealth.proxy_tier` |
| `SB_TRACING_ENABLED` | `tracing.enabled` |
| `SB_TRACING_SINK` | `tracing.sink_type` |

```python
import os
os.environ["SB_LLM_PROVIDER"] = "anthropic"
os.environ["SB_LLM_API_KEY"] = "sk-ant-..."
config = Config.from_env()
```

#### `Config.from_yaml(path) → Config`

Load from a YAML file. Requires `pyyaml`.

```yaml
# config.yaml
browser:
  headless: true
agent:
  llm_provider: anthropic
  llm_model: claude-sonnet-4-20250514
  llm_api_key: sk-ant-...
stealth:
  proxy_tier: standard_residential
  proxy_url: "http://proxy:8080"
budget:
  daily_cap_usd: 15.0
tracing:
  enabled: true
  sink_type: file
```

```python
config = Config.from_yaml("config.yaml")
```

#### `Config.from_dict(d) → Config`

Build from a nested dictionary. Unknown keys are silently ignored.

```python
config = Config.from_dict({
    "agent": {"llm_provider": "openai", "llm_model": "gpt-4o"},
    "budget": {"daily_cap_usd": 5.0},
})
```

#### `validate() → list[str]`

Returns a list of validation error strings. An empty list means the config is valid.

```python
errors = config.validate()
if errors:
    for e in errors:
        print(f"Config error: {e}")
```

### Sub-Configs

#### `AgentConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `llm_provider` | `str` | `"anthropic"` | LLM provider: `"anthropic"` or `"openai"`. |
| `llm_model` | `str` | `"claude-sonnet-4-20250514"` | Model identifier. |
| `llm_api_key` | `str` | `""` | API key for the chosen provider. |
| `core` | `SuperBrowserConfig` | defaults | Nested agent-level settings. |

#### `TracingConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `enabled` | `bool` | `False` | Enable tracing/observability. |
| `sink_type` | `str` | `"console"` | Sink type: `"console"`, `"file"`, or `"otlp"`. |

#### `BudgetConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `daily_cap_usd` | `float` | `10.0` | Maximum daily spend in USD. |
| `per_action_cap_usd` | `float` | `0.50` | Maximum spend per action in USD. |
| `per_turn_token_limit` | `int` | `100,000` | Maximum tokens per agent turn. |
| `warning_threshold` | `float` | `0.80` | Fraction of cap for warning alerts. |
| `critical_threshold` | `float` | `0.95` | Fraction of cap for critical alerts. |
| `context_compress_threshold` | `float` | `0.75` | Fraction for context compression trigger. |

#### `StealthConfig`

| Field | Type | Default | Description |
|---|---|---|---|
| `headless` | `bool` | `False` | Run browser in headless mode. |
| `proxy_tier` | `ProxyTier` | `DIRECT` | Default proxy escalation tier. |
| `proxy_url` | `str \| None` | `None` | Proxy URL. |
| `captcha_detection_enabled` | `bool` | `True` | Enable CAPTCHA detection. |
| `captcha_blocking_timeout` | `float` | `120.0` | Seconds to wait for CAPTCHA resolution. |
| `stealth_check_urls` | `tuple[str, ...]` | *(built-in list)* | URLs for stealth validation. |
| `custom_init_scripts` | `tuple[str, ...]` | `()` | JavaScript to inject via route interception. |
| `locale` | `str` | `"en-US"` | Browser locale. |
| `timezone` | `str` | `"America/New_York"` | Browser timezone. |
| `viewport_width` | `int` | `1920` | Viewport width in pixels. |
| `viewport_height` | `int` | `1080` | Viewport height in pixels. |
| `httpmorph_enabled` | `bool` | `True` | Use httpmorph for TLS fingerprinting. |
| `policy_file` | `str \| None` | `None` | Path to stealth action policy file. |
| `confirm_callback` | `Callable \| None` | `None` | Callback for confirm-required actions. |

---

## LLMClient Protocol

**Module:** `super_browser.agent.llm.protocol`

A `@runtime_checkable` async protocol that every LLM backend must implement.

```python
@runtime_checkable
class LLMClient(Protocol):
    async def propose_action(self, prompt: str, *, tools: list[dict] | None = None) -> dict: ...
    async def create_plan(self, instruction: str, *, tools: list[dict]) -> list[dict]: ...
    async def replan(self, *, instruction: str, original_plan: list[dict], failed_step: int, error: str) -> list[dict]: ...
```

### Methods

#### `propose_action(prompt, *, tools=None) → dict` *(async)*

Ask the LLM for its next action.

**Returns:** `{"action": str, "params": dict}` for a tool invocation, or `{"done": True, "summary": str}` when complete.

#### `create_plan(instruction, *, tools) → list[dict]` *(async)*

Generate an ordered plan of steps.

**Returns:** List of dicts with at least `"step"` key. Example: `[{"step": "Open the page", "tool": "navigate", "params": {"url": "..."}}]`

#### `replan(*, instruction, original_plan, failed_step, error) → list[dict]` *(async)*

Revise a plan after a step failure.

**Returns:** A new list of step dicts (same schema as `create_plan`).

### Implementing a Custom Client

```python
from super_browser.agent.llm.protocol import LLMClient

class MyMockClient:
    """A mock LLM client that always returns 'done'."""

    async def propose_action(self, prompt: str, *, tools=None) -> dict:
        return {"done": True, "summary": "Mock completed"}

    async def create_plan(self, instruction: str, *, tools) -> list[dict]:
        return [{"step": "Complete task", "tool": "done"}]

    async def replan(self, *, instruction, original_plan, failed_step, error) -> list[dict]:
        return original_plan

# Runtime type-check works:
assert isinstance(MyMockClient(), LLMClient)  # True
```

---

## create_llm Factory

**Module:** `super_browser.agent.llm.factory`

```python
def create_llm(
    provider: Optional[str] = None,
    model: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LLMClient
```

Create a concrete `LLMClient` for the given provider. Falls back to environment variables when arguments are `None`.

| Parameter | Env Fallback | Description |
|---|---|---|
| `provider` | `SB_LLM_PROVIDER` | `"anthropic"` or `"openai"`. |
| `model` | `SB_LLM_MODEL` | Model identifier (e.g., `"claude-sonnet-4-20250514"`, `"gpt-4o"`). |
| `api_key` | `SB_LLM_API_KEY` | Provider API key. |

**Raises:**
- `ValueError` — Unknown provider name.
- `EnvironmentError` — Required value missing from both argument and env.

```python
from super_browser.agent.llm.factory import create_llm

# Explicit parameters
client = create_llm(provider="anthropic", model="claude-sonnet-4-20250514", api_key="sk-ant-...")

# From environment variables
import os
os.environ["SB_LLM_PROVIDER"] = "openai"
os.environ["SB_LLM_MODEL"] = "gpt-4o"
os.environ["SB_LLM_API_KEY"] = "sk-..."
client = create_llm()
```

---

## BudgetAwareLLMClient

**Module:** `super_browser.agent.llm.budget_aware`

Wraps any `LLMClient` and automatically records token usage and estimated USD cost in a `TokenBudgetGovernor` after every call.

### Constructor

```python
class BudgetAwareLLMClient(
    client: LLMClient,
    governor: TokenBudgetGovernor,
    model: str,
)
```

| Parameter | Type | Description |
|---|---|---|
| `client` | `LLMClient` | The underlying LLM client to delegate to. |
| `governor` | `TokenBudgetGovernor` | Governor that receives usage records. |
| `model` | `str` | Model identifier for cost estimation. |

### Methods

Implements the full `LLMClient` protocol transparently:

- `propose_action(prompt, *, tools=None) → dict` *(async)* — Delegates and records cost.
- `create_plan(instruction, *, tools) → list[dict]` *(async)* — Delegates and records cost.
- `replan(*, instruction, original_plan, failed_step, error) → list[dict]` *(async)* — Delegates and records cost.

#### `record_raw_usage(*, input_tokens, output_tokens, action_name="compress") → None`

Record usage directly, outside the LLM protocol. Useful for components like `ContextCompressor`.

```python
from super_browser.agent.llm.budget_aware import BudgetAwareLLMClient
from super_browser.budget.governor import TokenBudgetGovernor

governor = TokenBudgetGovernor()
client = create_llm(provider="anthropic", model="claude-sonnet-4-20250514", api_key="sk-...")
budget_client = BudgetAwareLLMClient(client, governor, model="claude-sonnet-4-20250514")

# All LLM calls automatically tracked:
result = await budget_client.propose_action("Click the button")
print(f"Daily spend: ${governor.daily_spend:.4f}")
print(f"Remaining: ${governor.daily_remaining:.4f}")
```

### Supported Models for Cost Estimation

| Model | Input / 1K tokens | Output / 1K tokens |
|---|---|---|
| `claude-haiku-4-20250414` | $0.0008 | $0.004 |
| `claude-sonnet-4-20250514` | $0.003 | $0.015 |
| `claude-opus-4-20250514` | $0.015 | $0.075 |
| `gpt-4o` | $0.0025 | $0.01 |
| `gpt-4o-mini` | $0.00015 | $0.0006 |
| `gpt-4-turbo` | $0.01 | $0.03 |
| `o3` | $0.002 | $0.008 |
| `o3-mini` | $0.0011 | $0.0044 |
| `o4-mini` | $0.0011 | $0.0044 |

---

## StealthManager

**Module:** `super_browser.stealth.manager`

Top-level orchestrator for the multi-layer stealth stack. Manages UA rotation, header randomization, proxy escalation, CAPTCHA detection, and stealth diagnostics.

### Constructor

```python
class StealthManager(
    config: Optional[StealthConfig] = None,
    cdp: Any = None,
    event_bus: Any = None,
    page: Any = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `config` | `StealthConfig \| None` | `None` | Stealth configuration. |
| `cdp` | `Any` | `None` | CDP session for browser control. |
| `event_bus` | `Any` | `None` | Event bus for CAPTCHA watchdog. |
| `page` | `Any` | `None` | Patchright page handle. |

### Lifecycle

#### `initialize(session=None) → None` *(async)*

Initialise stealth scripts, CAPTCHA watchdog, and route interception. Call after the browser session is created.

#### `shutdown() → None` *(async)*

Stop CAPTCHA watchdog and clean up.

#### `__aenter__()` / `__aexit__(*exc)`

Async context manager support.

### Header & UA Methods

#### `randomize_headers(*, is_json=False) → dict[str, str]`

Return a fresh set of randomised HTTP headers. Call before each navigation to vary the fingerprint.

```python
headers = stealth.randomize_headers(is_json=True)
```

#### `get_user_agent() → str`

Get the next user-agent string from the rotating UA pool. Pool is lazily initialised on first call.

```python
ua = stealth.get_user_agent()
print(ua)  # "Mozilla/5.0 (Windows NT 10.0; Win64; x64) ..."
```

#### `ua_pool` *(property)* → `UserAgentPool | None`

Access the underlying UA pool. `None` until first `get_user_agent()` call.

### CAPTCHA Methods

#### `current_captcha() → CAPTCHADetection | None`

Get the current CAPTCHA detection, if any.

#### `wait_for_captcha_resolution(timeout=None) → CAPTCHADetection` *(async)*

Block until the current CAPTCHA is resolved or timeout expires.

**Raises:** `CaptchaTimeoutError` if timeout expires or no watchdog is configured.

#### `captcha_encounter_count` *(property)* → `int`

Total CAPTCHA encounters in the current session.

### Proxy Methods

#### `current_proxy_tier(domain=None) → ProxyTier`

Get the current or domain-specific recommended proxy tier.

#### `escalation_history(domain=None) → list[EscalationRecord]`

Get proxy escalation history, optionally filtered by domain.

### Diagnostics

#### `run_diagnostics() → StealthHealthReport` *(async)*

Run a full stealth health check. Returns a report with pass/fail for each check.

#### `validate_stealth_site(url) → StealthDiagnostic` *(async)*

Navigate to a URL and check `navigator.webdriver` exposure.

### Action Policy

#### `evaluate_action(action, url) → Any`

Evaluate whether an action is allowed under the current stealth policy. Returns a verdict (`"allow"`, `"deny"`, or `"confirm"`).

### HTTP Requests

#### `http_request(config) → HTTPMorphResponse` *(async)*

Execute an HTTP request through the stealth stack with automatic proxy escalation on failure.

```python
from super_browser.stealth.types import HTTPMorphRequestConfig

response = await stealth.http_request(HTTPMorphRequestConfig(
    url="https://example.com/api/data",
    method="GET",
))
print(response.status_code, response.timing_ms)
```

### Properties

| Property | Type | Description |
|---|---|---|
| `config` | `StealthConfig` | The active stealth configuration. |
| `proxy_escalator` | `ProxyEscalator` | The proxy escalation engine. |
| `action_policy` | `StealthActionPolicy` | The action policy evaluator. |

---

## TokenBudgetGovernor

**Module:** `super_browser.budget.governor`

Three-scope budget enforcement: daily, per-action, and per-turn. Thread-safe with automatic daily reset and optional persistence.

### Constructor

```python
class TokenBudgetGovernor(
    config: BudgetConfig = BudgetConfig(),
    cost_estimator: Optional[CostEstimator] = None,
    state_dir: Optional[Path] = None,
    alert_callback: Optional[Callable[[BudgetAlert], None]] = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `config` | `BudgetConfig` | defaults | Budget thresholds and caps. |
| `cost_estimator` | `CostEstimator \| None` | `None` | Custom cost estimator. |
| `state_dir` | `Path \| None` | `None` | Directory for state persistence. |
| `alert_callback` | `Callable \| None` | `None` | Callback for budget alerts. |

### Budget Checks

#### `check_budget(scope, estimated_cost_usd=0.0, estimated_tokens=0) → Optional[BudgetBlock]`

Check if spending is within limits for the given scope. Returns `None` if OK, or a `BudgetBlock` if the budget would be exceeded.

| Parameter | Type | Description |
|---|---|---|
| `scope` | `BudgetScope` | `DAILY`, `PER_ACTION`, or `PER_TURN`. |
| `estimated_cost_usd` | `float` | Estimated cost of the pending operation. |
| `estimated_tokens` | `int` | Estimated token count (for `PER_TURN` scope). |

#### `can_spend(estimated_cost_usd) → bool`

Simple boolean check: `True` if the estimated cost fits within the daily cap.

### Recording Usage

#### `record_usage(record) → Optional[BudgetAlert]`

Record a `TokenUsageRecord` and return an alert if a threshold was crossed.

### Scopes

#### `new_action() → None`

Reset the per-action spend counter. Call at the start of each new action.

#### `new_turn() → None`

Reset the per-turn token counter. Call at the start of each new agent turn.

#### `reset_daily() → None`

Force-reset the daily spend counter and clear all records.

### Properties

| Property | Type | Description |
|---|---|---|
| `daily_spend` | `float` | Current daily spend in USD. |
| `daily_remaining` | `float` | Remaining daily budget in USD. |
| `turn_tokens_used` | `int` | Tokens used in the current turn. |
| `turn_tokens_remaining` | `int` | Tokens remaining in the current turn. |
| `action_spend` | `float` | Spend in the current action scope. |
| `records` | `list[TokenUsageRecord]` | All recorded usage entries (copy). |

```python
from super_browser.budget.governor import TokenBudgetGovernor
from super_browser.budget.types import BudgetConfig, TokenUsageRecord

governor = TokenBudgetGovernor(config=BudgetConfig(daily_cap_usd=5.0))
governor.new_action()

# Check before spending
if governor.can_spend(0.10):
    print(f"OK — ${governor.daily_remaining:.2f} remaining")

# Record actual usage
record = TokenUsageRecord(
    model="claude-sonnet-4-20250514",
    input_tokens=1500,
    output_tokens=300,
    estimated_cost_usd=0.009,
    action_name="propose_action",
)
alert = governor.record_usage(record)
if alert:
    print(f"Budget alert: {alert.level} ({alert.usage_pct:.1f}%)")
```

---

## CheckpointManager

**Module:** `super_browser.recovery.checkpoint`

Save and restore browser page state (URL, scroll position, form values, cookies) to JSON files for crash recovery.

### Constructor

```python
class CheckpointManager(
    workspace: Path,
    checkpoint_dir: Optional[Path] = None,
    *,
    session_id: str = "default",
    cdp: Optional[Any] = None,
    page: Optional[Any] = None,
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `workspace` | `Path` | *(required)* | Workspace root directory. |
| `checkpoint_dir` | `Path \| None` | `None` | Override checkpoint storage directory. Defaults to `~/.config/super-browser/checkpoints/{session_id}/`. |
| `session_id` | `str` | `"default"` | Unique session identifier. |
| `cdp` | `Any` | `None` | CDP session for state extraction. |
| `page` | `Any` | `None` | Page handle for URL access. |

### Methods

#### `initialize() → None` *(async)*

Ensure the checkpoint directory exists. Call once after construction.

#### `save(label="") → Checkpoint` *(async)*

Capture the current page state (URL, scroll, form values, cookies) and persist to a JSON file.

```python
checkpoint = await manager.save("before-form-submit")
print(checkpoint.checkpoint_id)  # "a1b2c3d4e5f6"
```

#### `restore(checkpoint_id) → bool` *(async)*

Restore page to a previously saved checkpoint. Navigates to URL, restores cookies, fills form values, and scrolls to position.

```python
success = await manager.restore("a1b2c3d4e5f6")
```

#### `list_checkpoints(limit=20) → list[Checkpoint]`

Return metadata for saved checkpoints, newest first.

```python
for cp in manager.list_checkpoints(limit=5):
    print(f"{cp.checkpoint_id}: {cp.message} @ {cp.created_at}")
```

#### `delete(checkpoint_id) → bool`

Remove a checkpoint file. Returns `True` if the file existed and was deleted.

### Legacy Aliases

- `create_checkpoint(message) → Checkpoint` — Alias for `save(label=message)`.
- `rollback(checkpoint_id) → bool` — Alias for `restore(checkpoint_id)`.

---

## Result Types

**Module:** `super_browser.results.types`

### ActionResult

The standard envelope for every browser action.

```python
@dataclass
class ActionResult:
    ok: bool                           # True = success, False = error
    data: Any = None                   # Action-specific payload
    error: Optional[ActionError] = None
    meta: ResultMeta = ...             # Trace ID, duration, method
```

**Invariants:**
- `ok=True` ⟹ `error` is `None`
- `ok=False` ⟹ `error` is not `None`
- `meta` is always present

Methods: `to_json() → str`, `to_dict() → dict`, `from_dict(d) → ActionResult`.

### ActionError

```python
@dataclass
class ActionError:
    category: ErrorCategory
    message: str
    selector: Optional[str] = None
    recoverable: bool = True
    retry_hint: Optional[str] = None
```

### ErrorCategory

`"timeout"` | `"selector_not_found"` | `"navigation"` | `"security"` | `"browser_crash"` | `"validation"` | `"context_overflow"` | `"unknown"`

### CompletionReason

`"success"` | `"budget_exhausted"` | `"error"` | `"cancelled"` | `"max_steps"`

### ActionMethod

`"selector"` | `"coordinate"` | `"vision"`

### Typed Result Data Classes

These appear in `ActionResult.data` for specific operations:

- **`NavigateResult`** — `url`, `final_url`, `title`
- **`ExtractResult`** — `selector`, `extracted`, `element_count`
- **`DelegatedResult`** — `instruction`, `completion_reason`, `summary`, `steps_executed`, `budget_remaining`, `execution_history`

---

## Configuration Sub-Types

### AgentLoop Types (`super_browser.agent.types`)

| Type | Description |
|---|---|
| `PlanItem` | A single plan step with status, timing, and result. |
| `PlanStatus` | `"pending"` \| `"in_progress"` \| `"done"` \| `"failed"` \| `"skipped"` |
| `StepEvent` | `"step_start"` \| `"step_complete"` \| `"step_error"` \| `"loop_detected"` \| `"plan_updated"` \| `"abort"` \| `"max_steps_reached"` |
| `LoopResult` | Complete result from an `AgentLoop.run()` call. |
| `StepResult` | Single step outcome: `step_number`, `action_name`, `action_params`, `action_result`, `duration_ms`, `page_changed`, `error`. |
| `LoopNudge` | Loop detection nudge: `level`, `message`, `repetition_count`, `repeated_action`. |
| `DebugConfig` | Debug artifact settings: `enabled`, `screenshot_dir`, `capture_dom`. |
| `ActionTimeoutConfig` | Per-action timeouts: `default_action_timeout`, `navigation_timeout`, `per_action_overrides`. |
| `RetryBudget` | Per-action retry limits: `click`, `type`, `navigate`, `scroll`, `extract`. |
| `DelegationResult` | Parallel task outcomes: `tasks`, `total_duration_ms`, `completed_count`, `failed_count`, `cancelled_count`. |

### Budget Types (`super_browser.budget.types`)

| Type | Description |
|---|---|
| `BudgetScope` | `"daily"` \| `"per_action"` \| `"per_turn"` |
| `AlertLevel` | `"warning"` \| `"critical"` \| `"exhausted"` |
| `CostTier` | `"tier_1"` \| `"tier_2"` \| `"tier_3_mini"` \| `"tier_3_sonnet"` \| `"tier_3_opus"` |
| `BudgetAlert` | `level`, `scope`, `current_spend`, `cap`, `remaining`, `usage_pct` |
| `BudgetBlock` | `exhausted_scope`, `current_spend`, `cap`, `alert` |
| `TokenUsageRecord` | `model`, `input_tokens`, `output_tokens`, `estimated_cost_usd`, `action_name`, `to_dict()` |
| `BudgetConfig` | See [Config section](#config) above. |

### Stealth Types (`super_browser.stealth.types`)

| Type | Description |
|---|---|
| `ProxyTier` | `"direct"` \| `"standard_residential"` \| `"premium_residential"` \| `"datacenter_tls"` |
| `CAPTCHAProvider` | `"cloudflare_turnstile"` \| `"hcaptcha"` \| `"recaptcha_v2"` \| `"recaptcha_v3"` \| `"datadome"` \| `"kasada"` \| `"akamai"` \| `"generic"` |
| `StealthHealthItem` | Individual stealth check identifiers (webdriver, TLS, etc.) |
| `CAPTCHADetection` | `captcha_type`, `detected_at`, `selector`, `iframe_url`, `resolved`, `age_seconds` |
| `EscalationRecord` | `domain`, `from_tier`, `to_tier`, `trigger_status`, `escalated_at` |
| `StealthDiagnostic` | `check`, `passed`, `detail` |
| `StealthHealthReport` | `checks`, `overall_passed`, `pass_count`, `fail_count` |
| `HTTPMorphRequestConfig` | `url`, `method`, `headers`, `body`, `timeout`, `proxy_url` |
| `HTTPMorphResponse` | `status_code`, `headers`, `body`, `url`, `timing_ms`, `proxy_tier_used` |

### Recovery Types (`super_browser.recovery.types`)

| Type | Description |
|---|---|
| `Checkpoint` | `checkpoint_id`, `message`, `created_at`, `file_count` |
| `ErrorType` | Error taxonomy: `"auth"` \| `"rate_limit"` \| `"timeout"` \| `"captcha_blocked"` \| etc. |
| `RecoveryStrategy` | `"retry"` \| `"reattach_session"` \| `"respawn_browser"` \| `"checkpoint_rollback"` \| etc. |
| `RecoveryHint` | `strategy`, `retryable`, `max_attempts`, `should_rotate_credential` |
| `ClassifiedError` | `error_type`, `hint`, `original_error` |

---

## EventBus

**Module:** `super_browser.events.bus`

Typed pub/sub event bus with sync and async handler support. Handler errors are caught and logged — `emit()` never raises.

### Constructor

```python
class EventBus()
```

No parameters. Creates an empty handler registry.

### Methods

#### `subscribe(event_type: str, handler: Handler) → str`

Register *handler* for *event_type*. Returns a subscription ID for later unsubscription.

```python
bus = EventBus()
sub_id = bus.subscribe("before_navigate", lambda ctx: print(ctx["url"]))
```

#### `unsubscribe(subscription_id: str) → None`

Remove a previously registered handler by its subscription ID.

#### `emit(event_type: str, context: dict) → None`

Emit *event_type* synchronously. **Never raises.** The context dict is passed as read-only (`MappingProxyType`). Async handlers receive a warning but are not awaited.

```python
bus.emit("before_navigate", {"url": "https://example.com"})
```

#### `emit_async(event_type: str, context: dict) → None` *(async)*

Emit *event_type* asynchronously. Both sync and async handlers are supported; async handlers are properly awaited.

### Event Types (`super_browser.events.types`)

| Constant | Value | Context Keys |
|---|---|---|
| `BEFORE_NAVIGATE` | `"before_navigate"` | `url` |
| `AFTER_NAVIGATE` | `"after_navigate"` | `url`, `final_url`, `title`, `ok` |
| `BEFORE_ACTION` | `"before_action"` | `action`, `target`, `step` |
| `AFTER_ACTION` | `"after_action"` | `action`, `target`, `step`, `ok`, `duration_ms` |
| `ON_ERROR` | `"on_error"` | `action`, `error`, `category`, `step` |
| `ON_LOOP_DETECTED` | `"on_loop_detected"` | `level`, `message`, `repetition_count`, `repeated_action` |
| `ON_BUDGET_ALERT` | `"on_budget_alert"` | `level`, `usage_pct`, `remaining` |

---

## SessionRecorder

**Module:** `super_browser.recording.recorder`

Records browser lifecycle events into an `ActionRecord` list. Subscribes to all lifecycle events on an `EventBus`.

### Constructor

```python
class SessionRecorder(
    event_bus: EventBus,
    cdp_bridge: Optional[CDPBridge] = None,
    *,
    max_screenshots: int = 100,
)
```

### Methods

#### `start() → None`

Begin recording. Subscribes to `before_navigate`, `after_navigate`, `before_action`, `after_action`, and `on_error` events.

#### `stop() → RecordingSession`

Stop recording, unsubscribe from all events, and return the captured session.

#### `export_json() → str`

Export the current recording as a JSON string.

### Recording Types (`super_browser.recording.types`)

#### `ActionRecord`

```python
@dataclass
class ActionRecord:
    index: int
    timestamp: float
    action: str
    params: dict[str, Any]
    url: str = ""
    title: str = ""
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None
    ok: bool = True
    error: Optional[str] = None
    duration_ms: float = 0.0
```

#### `RecordingSession`

```python
@dataclass
class RecordingSession:
    session_id: str
    started_at: float
    actions: list[ActionRecord]
    schema_version: str = "1.0"
```

Methods: `to_dict()`, `from_dict(data)`, `metadata` (computed property with `action_count`, `error_count`, `duration_ms`).

### Persistence (`super_browser.recording.persistence`)

| Function | Signature | Description |
|---|---|---|
| `save` | `(recording, path) → None` | Write recording to JSON file |
| `load` | `(path) → RecordingSession` | Load recording from JSON file |

---

## RecordingReplayer

**Module:** `super_browser.recording.replayer`

Replays a recorded session against a live `SuperBrowser` instance, producing a `ReplayReport` with mismatch detection.

### Constructor

```python
class RecordingReplayer(sb: SuperBrowser)
```

### Methods

#### `replay(recording, *, delay_ms=100) → ReplayReport` *(async)*

Replay all actions in *recording* with a configurable delay between actions.

### ReplayReport

```python
@dataclass
class ReplayReport:
    total_actions: int = 0
    matched: int = 0
    mismatches: list[MismatchRecord] = []
    duration_ms: float = 0.0
```

### MismatchRecord

```python
@dataclass
class MismatchRecord:
    index: int
    action: str
    expected: dict[str, Any]
    actual: dict[str, Any]
    reason: str
```

---

## MemoryStore

**Module:** `super_browser.memory.store`

Per-domain JSON memory store with TTL-based pruning and credential filtering.

### Constructor

```python
class MemoryStore(memory_dir: Path, ttl_days: int = 30)
```

### Core Methods

| Method | Description |
|---|---|
| `save(domain, memory) → None` | Persist domain memory to JSON file |
| `load(domain) → DomainMemory` | Load domain memory (returns empty if not found) |
| `list_domains() → list[str]` | List domains with stored memory |
| `clear(domain) → None` | Delete memory for a domain |
| `prune() → int` | Remove expired entries, return count removed |

### High-Level Helpers

| Method | Description |
|---|---|
| `record_sequence(domain, task, actions, success) → None` | Record an action sequence (success only) |
| `record_selector(domain, element, selector) → None` | Record a working CSS selector |
| `get_context_for_prompt(domain) → str` | Generate advisory text for LLM prompt injection |

### Memory Types (`super_browser.memory.types`)

#### `DomainMemory`

```python
@dataclass
class DomainMemory:
    domain: str
    sequences: list[ActionSequence] = []
    selectors: dict[str, str] = {}
    preferences: dict[str, Any] = {}
    created_at: float
    updated_at: float
```

#### `ActionSequence`

```python
@dataclass
class ActionSequence:
    task: str
    actions: list[dict[str, Any]] = []
    success: bool = True
    created_at: float
    used_count: int = 0
```

### Integration (`super_browser.memory.integration`)

| Function | Description |
|---|---|
| `create_memory_store(*, memory_enabled, memory_dir, ttl_days) → MemoryStore \| None` | Factory used by `SuperBrowser` |
| `extract_domain_from_url(url) → str` | Extract domain key from URL |
| `build_memory_context(store, url) → str` | Build memory context for LLM prompt |
| `record_task_result(store, url, task, actions, success) → None` | Record a task result to memory |
| `record_selector_result(store, url, element, selector) → None` | Record a working selector |

---

## Plugin System

**Module:** `super_browser.plugins`

Global hook registry and decorator API for lifecycle event registration.

### Decorator

#### `@hook(event_type: str)`

Decorator that registers a function as a lifecycle hook handler. Defined in `super_browser.plugins.decorators`.

```python
from super_browser.plugins import hook

@hook("after_action")
def my_hook(ctx):
    print(f"Action: {ctx['action']}")
```

### Functions

| Function | Module | Description |
|---|---|---|
| `register_hook(event_type, handler) → None` | `plugins.hooks` | Add handler to the global registry |
| `get_registered_hooks() → dict[str, list[Handler]]` | `plugins.hooks` | Return a copy of the global registry |
| `clear_registry() → None` | `plugins.hooks` | Clear the global registry (testing) |

### SuperBrowser Integration Methods

#### `enable_recording(*, max_screenshots=100) → None`

Enable session recording on the `SuperBrowser` instance.

#### `enable_memory(*, memory_dir="~/.config/super-browser/memory", ttl_days=30) → None`

Enable per-domain memory persistence (opt-in).

#### `replay(path, *, delay_ms=100) → ActionResult` *(async)*

Load and replay a recording file against this browser.

#### Properties

| Property | Type | Description |
|---|---|---|
| `event_bus` | `EventBus \| None` | Access the internal EventBus |
| `recording` | `SessionRecorder \| None` | Access the active recorder |
| `memory` | `MemoryStore \| None` | Access the active memory store |

---

## HumanBehaviorAdapter

**Module:** `super_browser.stealth.human`

Abstracts human simulation across CloakBrowser and Patchright backends. Introduces mouse jitter, per-character typing delays, typo simulation, random pauses, and realistic scrolling.

### Constructor

```python
class HumanBehaviorAdapter(
    config: Optional[HumanConfig] = None,
    backend: str = "patchright",
)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `config` | `HumanConfig \| None` | `HumanConfig()` | Behavioral configuration. |
| `backend` | `str` | `"patchright"` | Stealth backend: `"patchright"` or `"cloak"`. |

### Methods

#### `humanize_click(page, selector) → None` *(async)*

Click an element with human-like mouse movement and hold time.

#### `humanize_type(page, selector, text) → None` *(async)*

Type `text` into `selector` with per-character delays and optional typo simulation.

#### `humanize_scroll(page, direction="down", amount=1) → None` *(async)*

Scroll the page with human-like behavior.

#### `random_pause() → None` *(async)*

Sleep for a random duration within `config.pause_between_actions`.

### Properties

| Property | Type | Description |
|---|---|---|
| `config` | `HumanConfig` | The active behavioral configuration. |
| `backend` | `str` | The stealth backend name. |

---

## HumanConfig

**Module:** `super_browser.stealth.human_config`

Frozen dataclass controlling all human behavior parameters.

```python
@dataclass(frozen=True)
class HumanConfig(
    typing_delay_ms: tuple[int, int] = (50, 150),
    mouse_jitter_px: float = 3.0,
    click_hold_ms: tuple[int, int] = (50, 200),
    scroll_step_px: int = 300,
    pause_between_actions: tuple[float, float] = (0.3, 1.5),
    typo_chance: float = 0.02,
    preset: str = "default",
)
```

When `preset` is set to `"careful"` or `"fast"`, individual field values are overridden with curated preset values.

| Preset | Typing Delay | Jitter | Click Hold | Typo Chance |
|---|---|---|---|---|
| `default` | 50-150ms | 3px | 50-200ms | 2% |
| `careful` | 80-250ms | 5px | 80-350ms | 1% |
| `fast` | 20-60ms | 1.5px | 30-80ms | 0.5% |

---

## FingerprintScanner

**Module:** `super_browser.stealth.fingerprint_scanner`

Scans browser fingerprints against detection sites. Supports offline (default) and online modes.

### Constructor

```python
class FingerprintScanner(scanner_config: Optional[dict] = None)
```

| Config Key | Type | Default | Description |
|---|---|---|---|
| `offline` | `bool` | `True` | Force offline mode. |
| `backend` | `str` | `"patchright"` | Backend name for reports. |
| `custom_checks` | `list[FingerprintCheck] \| None` | `None` | Override offline checks. |

### Methods

#### `scan(browser_page=None) → FingerprintScore` *(async)*

Run a fingerprint scan. In offline mode, returns deterministic mock scores. In online mode, visits detection sites and parses results.

#### `scan_site(browser_page, url) → FingerprintCheck` *(async)*

Visit a single detection site and return a check result.

#### `format_report(score) → str` *(static)*

Produce a Markdown report from a `FingerprintScore`.

### Properties

| Property | Type | Description |
|---|---|---|
| `offline` | `bool` | Whether the scanner is in offline mode. |

---

## FingerprintScorer

**Module:** `super_browser.stealth.fingerprint_score`

Computes a weighted 0-100 composite score from individual check categories.

### Methods

#### `score_from_checks(checks) → FingerprintScoreResult`

Compute composite score and grade from a dict of check results.

| Category | Weight |
|---|---|
| `webdriver` | 25% |
| `headers` | 20% |
| `plugins_mimetypes` | 15% |
| `user_agent` | 15% |
| `tls` | 15% |
| `misc` | 10% |

### FingerprintScoreResult

```python
@dataclass(frozen=True)
class FingerprintScoreResult:
    score: int                          # 0-100 composite score
    grade: FingerprintGrade             # A/B/C/D
    deductions: list[str]               # Failed check descriptions
    category_scores: dict[str, int]     # Per-category scores
```

### FingerprintGrade

```python
class FingerprintGrade(StrEnum):
    A = "A"   # 90-100
    B = "B"   # 75-89
    C = "C"   # 60-74
    D = "D"   # 0-59
```

---

## FingerprintScore & FingerprintCheck

**Module:** `super_browser.stealth.scoring`

### FingerprintScore

```python
@dataclass(frozen=True)
class FingerprintScore:
    overall: int                        # Composite score (0-100)
    checks: list[FingerprintCheck]      # Individual check results
    timestamp: float                    # Unix timestamp
    backend: str                        # "patchright" or "cloak"
```

### FingerprintCheck

```python
@dataclass(frozen=True)
class FingerprintCheck:
    name: str       # Check identifier
    passed: bool    # Whether the check passed
    score: int      # Numeric score (0-100)
    detail: str     # Human-readable description
```
