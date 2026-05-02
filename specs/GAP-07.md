# GAP-07: Agent Orchestration & Facade

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap          | #7                                                           |
| Title        | Agent Orchestration & Facade                                 |
| Phase        | Phase 1 (Core Control)                                       |
| Status       | Covered -- 8 sources                                         |
| Depends-On   | GAP-01 (Browser Session & CDP), GAP-02 (Three-Tier Interaction Engine), GAP-12 (Structured Action Results) |
| Enables      | GAP-04 (Self-Healing), GAP-09 (Token Budget), GAP-10 (Security), GAP-11 (Tracing) |
| Effort       | Medium                                                       |
| Build Order  | Week 4-5                                                     |

---

## 1. Problem

Super Browser needs a single, unified entry point that external callers -- human operators, LLM agents, scripted workflows -- use to interact with a browser session. Today, every reference project exposes browser capabilities differently: Hermes auto-discovers tools via AST parsing, Stagehand provides 16+ tools through a v3AgentHandler, browser-use runs a step loop with loop detection, and Agent-S uses an `@agent_action` decorator for zero-drift API documentation. None of these projects compose all of these patterns into a coherent facade.

Without a facade layer, every consumer must understand the internal architecture: which object handles clicks, which handles extraction, how to register new tools, and how to detect when the agent is stuck in a loop. The orchestration layer must unify tool registration (auto-discovery), agent loop execution (with step counting, abort signals, and loop detection), and a clean public API (the SuperBrowser facade) that hides all internal complexity behind six primary methods: `navigate()`, `click()`, `fill()`, `act()`, `extract()`, `observe()`.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                                    |
|-------|--------------------------------------------------------------------------------------------------------------------------------|
| R1    | Provide a `SuperBrowser` facade class as the primary entry point with six methods: `navigate()`, `click()`, `fill()`, `act()`, `extract()`, `observe()` |
| R2    | Each facade method delegates to the `MultimodalController` (GAP-02) for three-tier cascade execution and returns an `ActionResult` (GAP-12) |
| R3    | Implement a `ToolRegistry` that auto-discovers `@agent_action`-decorated functions via AST parsing at startup and registers them as callable tools |
| R4    | The `ToolRegistry` supports toolset composition: named groups of tools (e.g., `navigation`, `form_interaction`, `extraction`) that can be included or excluded per session |
| R5    | The `ToolRegistry` is thread-safe: concurrent reads during agent execution must never see partial state                       |
| R6    | Implement an `AgentLoop` that executes a step-based LLM interaction cycle: capture page state, prompt LLM, parse action, execute action, observe result |
| R7    | The `AgentLoop` tracks step count with a configurable `max_steps` limit (default 50) and aborts when exceeded                  |
| R8    | The `AgentLoop` supports an `AbortSignal` (asyncio.Event) that external callers can set to cancel the loop at any point        |
| R9    | Implement `ActionLoopDetector` using SHA-256 action hashing in a rolling window (default 20 entries) to detect when the agent repeats the same action |
| R10   | On loop detection, escalate nudges to the LLM: soft nudge at repetition count 5, stronger nudge at 8, critical nudge at 12   |
| R11   | On 3 consecutive stalled steps (no page change), trigger auto-replan by sending the current plan state to the LLM for revision |
| R12   | Maintain a `PlanItem` list that tracks the agent's task decomposition, current step index, and completion status for each planned action |
| R13   | Implement a `SubagentDelegator` that spawns child agent contexts with isolated browser state, executes tasks in parallel, and collects `DelegatedResult` from each child |
| R14   | The `SubagentDelegator` supports a maximum concurrency limit (default 4) and returns results as a `DelegationResult` aggregate |
| R15   | Every tool registered in the `ToolRegistry` has a JSON Schema parameter description auto-generated from `inspect.signature()`, ensuring zero-drift between code and LLM-facing tool descriptions |
| R16   | The `SuperBrowser` facade exposes a `tools()` method that returns the current tool API description formatted for LLM system prompts |
| R17   | Support plugin slots for future extensibility: an abstract `PluginSlot` interface with exclusive occupancy (only one plugin per capability slot), deferred to a later phase |
| R18   | The `AgentLoop` emits step events (step_start, step_complete, step_error, loop_detected, plan_updated) for consumption by GAP-11 (Tracing) |
| R19    | Validate end-to-end: a single `SuperBrowser.act("search for flights to Tokyo")` call navigates, fills forms, clicks buttons, and returns a structured result |

### Non-Functional

| ID    | Requirement                                                                                                                    |
|-------|--------------------------------------------------------------------------------------------------------------------------------|
| NFR1  | Tool registration (AST scanning + decorator introspection) completes in under 500 ms at startup                               |
| NFR2  | The `SuperBrowser` facade methods add under 2 ms of overhead beyond the underlying `MultimodalController` execution time       |
| NFR3  | Loop detection (SHA-256 hash computation + rolling window check) adds under 0.1 ms per step                                    |
| NFR4  | The `ToolRegistry` snapshot operation (return all registered tools) is lock-free and O(1) for concurrent readers               |
| NFR5  | `SubagentDelegator` child isolation must be complete: a child crash or exception must never corrupt the parent's browser state |
| NFR6  | `AgentLoop` abort via `AbortSignal` must take effect within one step (max 30 seconds from signal set to loop termination)      |

### Out of Scope

- Programmatic Tool Calling (PTC) where the LLM writes Python code that calls tools -- deferred to a future iteration (high effort, requires sandbox infrastructure)
- Behavior Best-of-N (bBoN) multi-rollout trajectory comparison -- deferred to a future iteration (high effort, requires VLM infrastructure)
- Plugin slot implementation with manifest-driven loading -- deferred to Week 11 (OpenClaw pattern, interface defined now but not implemented)
- Vision-based plan verification using screenshot comparison -- deferred to GAP-03 (Visual Verification)

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | Tool Registry with AST Auto-Discovery | Hermes `tools/registry.py`, `toolsets.py` | 4.80 | Medium | Tool registration and composition |
| P2 | @agent_action Decorator + Dynamic Prompts | Agent-S `grounding.py:25-28`, `procedural_memory.py:78-89` | 4.12 | Low | Zero-drift tool API descriptions |
| P3 | v3AgentHandler Step Loop | Stagehand `handlers/v3AgentHandler.ts` (727 lines) | 4.25 | Medium | Agent loop with step counting |
| P4 | Action Loop Detection via SHA-256 Hashing | browser-use `agent/views.py` (ActionLoopDetector) | 4.20 | Low | Stuck-state detection |
| P5 | Planning with PlanItem Tracking | browser-use `agent/service.py` (PlanItem) | 4.20 | Low | Task decomposition and replanning |
| P6 | Subagent Delegation with Isolated Context | Hermes `tools/delegate_tool.py` | 4.20 | Medium | Parallel child task execution |
| P7 | 16+ Tool Agent Handler (DOM/hybrid modes) | Stagehand `handlers/v3AgentHandler.ts` | 4.25 | Medium | Tool dispatch for agent actions |
| P8 | Plugin Slots with Exclusive Occupancy | OpenClaw `plugins/slots.ts`, `plugins/registry.ts` | 4.80 | Medium | Extensible capability registration |
| P9 | Error Classifier with Recovery Hints | Hermes `agent/error_classifier.py` | 4.50 | Low | Step-level error routing |
| P10 | Pluggable ToolCallEngine for Function-Calling and Text-Based Models | UI-TARS-Desktop `PromptEngineeringToolCallEngine.ts` (780), `ToolCallEngine.ts` (237) | 4.47 | Medium | Non-function-calling model bridge |

### Per-Pattern Adoption Notes

**P1 -- Tool Registry with AST Auto-Discovery (Hermes)**
Adopt Hermes's pattern of scanning Python source files at startup, parsing their ASTs, and identifying modules containing tool registration calls. In Hermes, `_module_registers_tools()` reads each `.py` file, calls `ast.parse()`, and searches for `registry.register()` calls. Super Browser adapts this to search for `@agent_action` decorated functions: parse each module's AST, find `FunctionDef` nodes whose `decorator_list` contains a Name or Call node matching `agent_action`, and register those functions as tools. Each tool carries its name, function reference, parameter schema (from `inspect.signature()`), description (from `__doc__`), and toolset membership. Toolsets are declarative compositions (e.g., `_CORE_TOOLS` includes navigate, click, fill, observe). Thread-safe snapshots via `threading.RLock` for write operations and copy-on-read for concurrent access. Source files: `tools/registry.py`, `toolsets.py`.

**P2 -- @agent_action Decorator + Dynamic Prompts (Agent-S)**
Adopt Agent-S's minimal decorator pattern: `func.is_agent_action = True` marks action methods. At registration time, the system iterates all registered tools, extracts `inspect.signature()` for parameter names/types and `__doc__` for descriptions, and assembles a formatted API description for the agent's system prompt. This eliminates documentation drift -- the LLM always sees an API that exactly matches the available actions. The decorator is defined in GAP-02 for the `MultimodalController` methods; GAP-07 extends it to any function registered in the `ToolRegistry`. Source files: `s3/agents/grounding.py:25-28`, `s3/memory/procedural_memory.py:78-89`.

**P3 -- v3AgentHandler Step Loop (Stagehand)**
Adopt Stagehand's agent loop pattern from `v3AgentHandler.ts`. The handler manages a full step loop: capture page snapshot, build action prompt with available tools, call LLM for action proposal, parse action from LLM response, execute action, observe result, and repeat. The loop tracks step count with `maxSteps` enforcement, supports abort signals, and handles CAPTCHA blocking waits. Super Browser adapts this as the `AgentLoop` class: each step follows the same capture-prompt-parse-execute-observe cycle. The loop integrates with the `ToolRegistry` for action dispatch and the `ActionLoopDetector` for stuck-state handling. Source file: `handlers/v3AgentHandler.ts` (727 lines).

**P4 -- Action Loop Detection via SHA-256 Hashing (browser-use)**
Adopt browser-use's `ActionLoopDetector` pattern: compute a SHA-256 hash of each action's normalized representation (action name + parameters), maintain a rolling window of recent hashes (default 20), and detect when the same hash appears multiple times. When repetition is detected, escalate nudges to the LLM with increasing urgency: soft nudge at count 5 ("You seem to be repeating actions. Consider a different approach."), stronger nudge at count 8 ("You are in a loop. Try a completely different strategy."), critical nudge at count 12 (abort with loop error). The normalization strips volatile parameters (timestamps, random IDs) to ensure meaningful hash comparison. Source file: `browser_use/agent/views.py`.

**P5 -- Planning with PlanItem Tracking (browser-use)**
Adopt browser-use's `PlanItem` pattern for task decomposition tracking. The LLM produces an initial plan as a list of `PlanItem` objects, each with a description, status (pending, in_progress, done, failed), and step index. The `AgentLoop` tracks the current plan, marks steps as done on success, and triggers auto-replan when 3 consecutive steps produce no page change (stagnation). Auto-replan sends the current plan state, the last N actions, and a replan prompt to the LLM, which revises the remaining plan. This prevents the agent from persisting with a failed strategy. Source file: `browser_use/agent/service.py`.

**P6 -- Subagent Delegation with Isolated Context (Hermes)**
Adopt Hermes's `delegate_tool.py` pattern for child agent spawning. A `SubagentDelegator` creates child agent contexts with isolated browser state (separate page/tab), executes tasks in parallel via `asyncio.TaskGroup`, and collects `DelegatedResult` from each child. Maximum concurrency is enforced (default 4 children). Each child inherits the parent's tool registry (read-only snapshot) but has its own `AgentLoop` state, preventing cross-contamination. If a child fails, its `DelegatedResult` records the error while other children continue. Source file: `tools/delegate_tool.py`.

**P7 -- 16+ Tool Agent Handler (Stagehand)**
Adopt Stagehand's tool dispatch pattern. The `v3AgentHandler` defines 16+ tools (act, fill_form, goto, scroll, wait, navback, keys, etc.) that the LLM can invoke. Each tool has a JSON Schema parameter definition and a handler function. Super Browser's `ToolRegistry` provides the same structure: registered tools with parameter schemas, dispatched by name when the LLM proposes an action. The handler validates parameters against the schema before execution. Source file: `handlers/v3AgentHandler.ts`.

**P8 -- Plugin Slots with Exclusive Occupancy (OpenClaw)**
Adopt OpenClaw's plugin slot architecture for future extensibility. Define an abstract `PluginSlot` interface with named capability slots (e.g., `memory`, `context_engine`, `skill_provider`). Only one plugin may occupy each slot. The `PluginRegistry` manages slot assignments and enforces exclusivity. The actual plugin loading (manifest parsing, security scanning) is deferred to Week 11 -- the interface is defined now to ensure the `ToolRegistry` architecture accommodates future plugin-based tool registration. Source files: `plugins/slots.ts`, `plugins/registry.ts`.

**P9 -- Error Classifier with Recovery Hints (Hermes)**
Adopt Hermes's error classifier pattern for step-level error routing. The `error_classifier.py` defines a `ClassifiedError` with fields: `reason` (auth, billing, rate_limit, overloaded, context_overflow, timeout, selector_not_found, etc.), `retryable`, `should_compress`, `should_rotate_credential`, `should_fallback`. The `AgentLoop` uses this classifier after each failed step to determine the recovery action: retry the same step, replan, compress context, or abort. This replaces ad-hoc error handling with a structured taxonomy. Source file: `agent/error_classifier.py`.

**P10 -- Pluggable ToolCallEngine (UI-TARS-Desktop)**
Adopt the Tarko framework's pluggable `ToolCallEngine` pattern. The original provides two engines: (1) `NativeToolCallEngine` for models that support function calling natively (Claude, GPT-4o), and (2) `PromptEngineeringToolCallEngine` (780 lines) for models that do not. The prompt-engineering engine parses VLM text output (which may contain `Thought:... Action:...` or XML tags) into structured tool calls that the agent framework can dispatch. This enables any LLM -- including local models and VLMs without function-calling support -- to work with the tool system. Super Browser's `AgentLoop` should use this pattern: the default engine assumes native function calling, but a fallback engine extracts tool calls from free-text responses using the 6-format action parser chain from GAP-06 (P11). This is critical for the vision tier where VLMs like UI-TARS output actions as structured text rather than function calls. Source files: `tarko/agent/src/agent/PromptEngineeringToolCallEngine.ts`, `agent-sdk/src/ToolCallEngine.ts`.

---

## 4. Interface Contract

```python
"""
Agent Orchestration & Facade -- Super Browser
Gap #07 Interface Contract

All classes are dataclasses for deterministic serialization.
All enums are string enums for JSON compatibility.
"""

from __future__ import annotations

import abc
import ast
import asyncio
import hashlib
import inspect
import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Callable, Optional, Awaitable


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class PlanStatus(StrEnum):
    """Status of a single plan item."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class StepEvent(StrEnum):
    """Events emitted by the AgentLoop during execution."""
    STEP_START = "step_start"
    STEP_COMPLETE = "step_complete"
    STEP_ERROR = "step_error"
    LOOP_DETECTED = "loop_detected"
    PLAN_UPDATED = "plan_updated"
    ABORT = "abort"
    MAX_STEPS_REACHED = "max_steps_reached"


class DelegationStatus(StrEnum):
    """Status of a subagent delegation."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PluginSlotKey(StrEnum):
    """Named capability slots for plugin registration."""
    MEMORY = "memory"
    CONTEXT_ENGINE = "context_engine"
    SKILL_PROVIDER = "skill_provider"
    VISION_PROVIDER = "vision_provider"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Plan Items
# ---------------------------------------------------------------------------

@dataclass
class PlanItem:
    """A single step in the agent's task decomposition."""
    index: int
    description: str
    status: PlanStatus = PlanStatus.PENDING
    action_taken: Optional[str] = None           # actual action executed
    result_summary: Optional[str] = None          # brief result description
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return None


# ---------------------------------------------------------------------------
# Loop Detection
# ---------------------------------------------------------------------------

@dataclass
class LoopNudge:
    """A nudge injected into the LLM context when a loop is detected."""
    level: int                                   # 1=soft, 2=strong, 3=critical
    message: str
    repetition_count: int
    repeated_action: str                         # description of the repeated action


class ActionLoopDetector:
    """
    Detects when the agent is repeating the same action in a loop.
    Uses SHA-256 hashing of normalized action representations in a
    rolling window.

    Adopted from: browser-use ActionLoopDetector
    """

    def __init__(self, window_size: int = 20) -> None:
        self._window_size = window_size
        self._recent_hashes: deque[str] = deque(maxlen=window_size)
        self._recent_actions: deque[dict] = deque(maxlen=window_size)

    def compute_hash(self, action: dict) -> str:
        """
        Compute a SHA-256 hash of a normalized action representation.
        Strips volatile parameters (timestamps, random IDs) before hashing.
        """
        normalized = self._normalize(action)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]

    def record_and_check(self, action: dict) -> Optional[LoopNudge]:
        """
        Record an action and check for loops.

        Returns a LoopNudge if a loop is detected, None otherwise.
        Nudge escalation:
          - repetition count 5:  soft nudge (level 1)
          - repetition count 8:  strong nudge (level 2)
          - repetition count 12: critical nudge (level 3 -- abort)
        """
        ...

    def _normalize(self, action: dict) -> str:
        """
        Normalize an action dict for hashing.
        Strips volatile fields: timestamp, trace_id, step_id, random seeds.
        Sorts remaining keys for deterministic serialization.
        """
        ...

    def reset(self) -> None:
        """Clear the rolling window (e.g., after a successful replan)."""
        ...


# ---------------------------------------------------------------------------
# Tool Registration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ToolParameter:
    """A single parameter in a tool's signature."""
    name: str
    type_name: str                               # e.g., "str", "int", "bool"
    required: bool
    default: Optional[str] = None                # string representation of default value
    description: str = ""                        # from docstring or type annotation


@dataclass(frozen=True)
class ToolDefinition:
    """Immutable description of a registered tool."""
    name: str                                    # function name
    description: str                             # from __doc__
    parameters: tuple[ToolParameter, ...]
    toolsets: tuple[str, ...] = ()               # which toolset groups this belongs to
    handler: Callable = field(repr=False, compare=False)  # the actual callable
    max_result_chars: int = 50_000               # per-tool output cap (GAP-12 OutputDefender)

    def to_json_schema(self) -> dict:
        """Generate a JSON Schema description for LLM tool calling."""
        ...

    def to_prompt_description(self) -> str:
        """
        Generate a human-readable description for the LLM system prompt.
        Format:
            def tool_name(param1: str, param2: int = 0) -> ActionResult:
                '''Tool description from docstring.'''
        """
        ...


@dataclass(frozen=True)
class Toolset:
    """A named group of tools."""
    name: str
    description: str
    tool_names: frozenset[str]


class ToolRegistry:
    """
    Thread-safe registry of browser action tools.
    Auto-discovers @agent_action-decorated functions via AST parsing.

    Adopted from: Hermes tools/registry.py (AST auto-discovery),
                  Agent-S procedural_memory.py (decorator + signature).
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}
        self._toolsets: dict[str, Toolset] = {}
        self._lock = threading.RLock()

    # -- Registration -------------------------------------------------------

    def register(
        self,
        func: Callable,
        *,
        toolsets: tuple[str, ...] = (),
        max_result_chars: int = 50_000,
    ) -> None:
        """
        Register a function as a tool.

        Introspects inspect.signature() for parameters and __doc__
        for description. Thread-safe (acquires write lock).
        """
        ...

    def register_module(self, module_path: Path) -> int:
        """
        Scan a Python module file for @agent_action-decorated functions
        and register them. Returns the count of tools registered.

        Adopted from: Hermes _module_registers_tools() AST pattern.
        """
        ...

    def register_package(self, package_dir: Path) -> int:
        """
        Recursively scan a package directory for Python modules and
        register all @agent_action-decorated functions found.
        Returns total count of tools registered.
        """
        ...

    def define_toolset(self, name: str, description: str, tool_names: set[str]) -> None:
        """Define a named toolset (group of tools)."""
        ...

    # -- Lookup -------------------------------------------------------------

    def get(self, name: str) -> Optional[ToolDefinition]:
        """Get a tool by name. Lock-free (concurrent read on frozen dict)."""
        ...

    def snapshot(self, *, toolset: Optional[str] = None) -> dict[str, ToolDefinition]:
        """
        Return a snapshot of all registered tools (or filtered by toolset).
        The returned dict is a copy safe for concurrent iteration.
        """
        ...

    def list_tools(self, *, toolset: Optional[str] = None) -> list[ToolDefinition]:
        """List all tools, optionally filtered by toolset membership."""
        ...

    def list_toolsets(self) -> list[Toolset]:
        """List all defined toolsets."""
        ...

    # -- LLM-facing API ----------------------------------------------------

    def build_tool_api_description(self, *, toolset: Optional[str] = None) -> str:
        """
        Build a formatted string describing all available tools for
        the LLM system prompt. Each tool shows its signature and docstring.

        Adopted from: Agent-S build_action_api_description().
        """
        ...

    def build_tool_schemas(self, *, toolset: Optional[str] = None) -> list[dict]:
        """
        Build JSON Schema descriptions for all tools, suitable for
        LLM function calling APIs (OpenAI/Anthropic format).
        """
        ...

    # -- AST Auto-Discovery ------------------------------------------------

    def _scan_module_ast(self, source: str, filename: str) -> list[str]:
        """
        Parse source code AST and find function names decorated with
        @agent_action. Returns list of function names.

        Adopted from: Hermes _module_registers_tools().
        """
        tree = ast.parse(source, filename=filename)
        decorated = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                for decorator in node.decorator_list:
                    if self._is_agent_action_decorator(decorator):
                        decorated.append(node.name)
        return decorated

    @staticmethod
    def _is_agent_action_decorator(decorator: ast.expr) -> bool:
        """Check if an AST decorator node is @agent_action."""
        if isinstance(decorator, ast.Name) and decorator.id == "agent_action":
            return True
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Name) and func.id == "agent_action":
                return True
        return False

    # -- Stats --------------------------------------------------------------

    @property
    def tool_count(self) -> int: ...

    @property
    def toolset_count(self) -> int: ...


# ---------------------------------------------------------------------------
# SuperBrowser Facade
# ---------------------------------------------------------------------------

class SuperBrowser:
    """
    Primary entry point for all browser automation.
    Provides six high-level methods that external callers use.

    Delegates to:
      - MultimodalController (GAP-02) for action execution
      - ToolRegistry for tool management
      - AgentLoop for autonomous task execution

    Usage:
        browser = SuperBrowser(config=SuperBrowserConfig())
        await browser.start()

        # Single-action facade methods
        result = await browser.navigate("https://example.com")
        result = await browser.click("button.submit")
        result = await browser.fill("#email", "user@example.com")

        # Autonomous task execution
        result = await browser.act("search for flights to Tokyo")

        # Data extraction
        data = await browser.extract("all product names and prices")

        # Page observation
        obs = await browser.observe()

        await browser.stop()
    """

    def __init__(
        self,
        config: Optional[SuperBrowserConfig] = None,
        *,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None: ...

    # -- Lifecycle ----------------------------------------------------------

    async def start(self) -> None:
        """
        Initialize the browser session (GAP-01), MultimodalController (GAP-02),
        ToolRegistry, and AgentLoop. Scan for @agent_action tools.
        """
        ...

    async def stop(self) -> None:
        """Graceful shutdown: stop agent loop, close browser session."""
        ...

    async def __aenter__(self) -> SuperBrowser: ...
    async def __aexit__(self, *exc) -> None: ...

    # -- Facade Methods (primary API) ---------------------------------------

    async def navigate(self, url: str, *, wait_until: str = "domcontentloaded") -> ActionResult:
        """
        Navigate to a URL.

        Delegates to PageHandle.goto() (GAP-01).
        Returns NavigateResult with final URL, status code, and redirect chain.
        """
        ...

    async def click(
        self,
        target: str,
        *,
        description: Optional[str] = None,
    ) -> ActionResult:
        """
        Click on an element.

        Delegates to MultimodalController.click() (GAP-02).
        Three-tier cascade: selector -> coordinate -> vision.
        Returns ClickResult with method used and coordinates.
        """
        ...

    async def fill(
        self,
        target: str,
        value: str,
        *,
        clear_first: bool = True,
        description: Optional[str] = None,
    ) -> ActionResult:
        """
        Fill a text input with the given value.

        Delegates to MultimodalController.fill() (GAP-02).
        Returns FillResult with the value entered and method used.
        """
        ...

    async def act(self, instruction: str, *, max_steps: int = 50) -> ActionResult:
        """
        Execute an autonomous multi-step task.

        Starts the AgentLoop with the given instruction. The LLM decomposes
        the task, executes steps, and returns when the task is complete or
        max_steps is reached.

        Returns ActionResult with DelegatedResult containing the full
        execution trace, steps executed, and completion reason.
        """
        ...

    async def extract(
        self,
        query: str,
        *,
        selector: Optional[str] = None,
        schema: Optional[dict] = None,
    ) -> ActionResult:
        """
        Extract structured data from the current page.

        Uses CSS selector if provided, otherwise uses LLM-based extraction
        guided by the query and optional JSON Schema.

        Returns ExtractResult with the extracted data.
        """
        ...

    async def observe(self) -> ActionResult:
        """
        Capture the current page state.

        Returns an observation containing: URL, title, AX snapshot,
        screenshot hash, and interactive element summary.
        """
        ...

    # -- Subagent Delegation ------------------------------------------------

    async def delegate(
        self,
        tasks: list[str],
        *,
        max_concurrency: int = 4,
    ) -> DelegationResult:
        """
        Delegate multiple independent tasks to child agents.

        Each task runs in its own browser context (isolated tab/page).
        Results are collected as they complete.

        Adopted from: Hermes delegate_tool.py pattern.
        """
        ...

    # -- Tool Management ----------------------------------------------------

    def tools(self, *, toolset: Optional[str] = None) -> str:
        """Return the formatted tool API description for LLM prompts."""
        ...

    def register_tool(
        self,
        func: Callable,
        *,
        toolsets: tuple[str, ...] = (),
    ) -> None:
        """Register a custom tool at runtime."""
        ...

    # -- Abort --------------------------------------------------------------

    def abort(self) -> None:
        """Signal the running AgentLoop to stop after the current step."""
        ...

    @property
    def is_running(self) -> bool:
        """Whether an AgentLoop is currently executing."""
        ...


# ---------------------------------------------------------------------------
# Agent Loop
# ---------------------------------------------------------------------------

@dataclass
class StepResult:
    """Result from a single agent loop step."""
    step_number: int
    action_name: str                             # which tool was called
    action_params: dict[str, Any]
    action_result: Any                           # ActionResult from tool execution
    duration_ms: float
    page_changed: bool = False                   # detected by DOM/hash comparison
    error: Optional[str] = None


@dataclass
class LoopResult:
    """Complete result from an AgentLoop execution."""
    instruction: str
    steps: list[StepResult]
    plan: list[PlanItem]
    completion_reason: str                       # "success", "max_steps", "abort", "error"
    total_duration_ms: float
    total_steps: int
    loop_detections: int = 0
    replan_count: int = 0


class AgentLoop:
    """
    Step-based LLM interaction cycle with loop detection, planning,
    and abort signal support.

    Adopted from: Stagehand v3AgentHandler (step loop),
                  browser-use Agent (loop detection + planning).

    Usage:
        loop = AgentLoop(
            controller=controller,
            registry=registry,
            llm_client=llm,
            max_steps=50,
        )
        result = await loop.run("search for flights to Tokyo", abort_signal=signal)
    """

    def __init__(
        self,
        controller: Any,             # MultimodalController (GAP-02)
        registry: ToolRegistry,
        llm_client: Any,             # LLM provider (Anthropic/OpenAI)
        *,
        max_steps: int = 50,
        loop_detector: Optional[ActionLoopDetector] = None,
        abort_signal: Optional[asyncio.Event] = None,
        event_callback: Optional[Callable[[StepEvent, dict], Awaitable[None]]] = None,
    ) -> None: ...

    # -- Execution ----------------------------------------------------------

    async def run(
        self,
        instruction: str,
        *,
        abort_signal: Optional[asyncio.Event] = None,
        initial_plan: Optional[list[PlanItem]] = None,
    ) -> LoopResult:
        """
        Execute the agent loop for a given instruction.

        Steps per iteration:
          1. Check abort signal; if set, terminate.
          2. Capture page snapshot (via MultimodalController).
          3. Build prompt: instruction + plan + recent actions + tool API.
          4. Call LLM to propose next action.
          5. Parse action name and parameters from LLM response.
          6. Record action in loop detector; check for loops.
          7. If loop detected, inject nudge and continue (or abort at level 3).
          8. Dispatch action via ToolRegistry.
          9. Observe result, detect page change.
          10. Update plan: mark current step done if appropriate.
          11. If 3 consecutive stalled steps, trigger auto-replan.
          12. Emit step event.
          13. If LLM signals completion, terminate with success.
          14. If step count >= max_steps, terminate with max_steps reason.
          15. Repeat from step 1.
        """
        ...

    # -- Plan Management ----------------------------------------------------

    async def _request_initial_plan(self, instruction: str) -> list[PlanItem]:
        """Ask the LLM to decompose the instruction into plan items."""
        ...

    async def _auto_replan(self, reason: str) -> list[PlanItem]:
        """
        Trigger replan when the current plan is stalled.
        Sends current plan state, last N actions, and replan prompt.
        """
        ...

    def _advance_plan(self, step_result: StepResult) -> None:
        """Mark the current plan item based on the step result."""
        ...

    # -- Action Dispatch ----------------------------------------------------

    async def _dispatch_action(self, action_name: str, params: dict) -> ActionResult:
        """Look up tool in registry, validate params, execute handler."""
        ...

    # -- Page Change Detection ----------------------------------------------

    def _compute_page_fingerprint(self, snapshot: Any) -> str:
        """
        Compute a fingerprint of the current page state for stagnation
        detection. Combines URL, element count, and DOM text hash.
        """
        ...

    def _detect_page_change(self, before: str, after: str) -> bool:
        """Compare two page fingerprints to determine if a change occurred."""
        ...


# ---------------------------------------------------------------------------
# Subagent Delegation
# ---------------------------------------------------------------------------

@dataclass
class ChildTask:
    """A single task delegated to a child agent."""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    instruction: str = ""
    status: DelegationStatus = DelegationStatus.PENDING
    result: Optional[Any] = None                 # ActionResult or error
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at) * 1000
        return None


@dataclass
class DelegationResult:
    """Aggregate result from subagent delegation."""
    tasks: list[ChildTask]
    total_duration_ms: float
    completed_count: int
    failed_count: int
    cancelled_count: int

    @property
    def all_succeeded(self) -> bool:
        return self.failed_count == 0 and self.cancelled_count == 0


class SubagentDelegator:
    """
    Spawns child agents with isolated browser contexts for parallel execution.

    Adopted from: Hermes tools/delegate_tool.py.

    Usage:
        delegator = SubagentDelegator(browser_session, registry, llm_client)
        result = await delegator.delegate(
            tasks=["search for flights", "check hotel prices"],
            max_concurrency=2,
        )
    """

    def __init__(
        self,
        browser_session: Any,         # BrowserSession (GAP-01)
        registry: ToolRegistry,
        llm_client: Any,
        *,
        max_concurrency: int = 4,
    ) -> None: ...

    async def delegate(
        self,
        tasks: list[str],
        *,
        max_concurrency: Optional[int] = None,
        abort_signal: Optional[asyncio.Event] = None,
    ) -> DelegationResult:
        """
        Execute tasks in parallel using isolated child agents.

        Each child gets its own browser tab and AgentLoop.
        Uses asyncio.TaskGroup for structured concurrency.
        """
        ...

    async def _run_child(self, task: ChildTask) -> ChildTask:
        """
        Execute a single child task in an isolated browser context.

        Creates a new page/tab, runs an AgentLoop for the instruction,
        collects the result, and closes the page.
        """
        ...


# ---------------------------------------------------------------------------
# Plugin Slot Interface (deferred implementation)
# ---------------------------------------------------------------------------

class PluginSlot(abc.ABC):
    """
    Abstract interface for plugin capability slots.
    Only one plugin may occupy each slot.

    Adopted from: OpenClaw plugins/slots.ts.
    Implementation deferred to Week 11.
    """

    @abc.abstractmethod
    def slot_key(self) -> PluginSlotKey: ...

    @abc.abstractmethod
    async def initialize(self, context: dict) -> None: ...

    @abc.abstractmethod
    async def shutdown(self) -> None: ...


class PluginRegistry:
    """
    Manages plugin slot assignments. Enforces exclusive occupancy.
    Implementation deferred to Week 11.

    Adopted from: OpenClaw plugins/registry.ts.
    """

    def __init__(self) -> None:
        self._slots: dict[PluginSlotKey, PluginSlot] = {}

    def register(self, plugin: PluginSlot) -> None:
        """
        Register a plugin in its slot. Raises if slot is already occupied.
        """
        ...

    def get(self, key: PluginSlotKey) -> Optional[PluginSlot]: ...

    def unregister(self, key: PluginSlotKey) -> None: ...


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SuperBrowserConfig:
    """Immutable configuration for the SuperBrowser facade."""
    # Agent loop settings
    max_steps: int = 50
    loop_window_size: int = 20
    stagnation_threshold: int = 3                # consecutive stalled steps before replan
    nudge_levels: tuple[int, ...] = (5, 8, 12)   # repetition counts for nudge escalation

    # Delegation settings
    max_delegation_concurrency: int = 4

    # Tool discovery
    tool_scan_dirs: tuple[str, ...] = ()         # directories to scan for @agent_action tools

    # LLM settings
    default_model: str = "claude-sonnet-4-20250514"
    llm_temperature: float = 0.0
    llm_max_tokens: int = 4096

    # Tracing
    trace_enabled: bool = True
```

---

## 5. Data Flow

```
                          External Caller
                          (LLM agent / script / human)
                                    |
                                    v
                      +-------------+---------------+
                      |       SuperBrowser           |
                      |         (Facade)             |
                      +-------------+---------------+
                                    |
                 +------------------+------------------+
                 |                  |                   |
           navigate()         click()/fill()      act(instruction)
                 |                  |                   |
                 v                  v                   v
          PageHandle         MultimodalController   AgentLoop
          (GAP-01)           (GAP-02)               (orchestrator)
                                                       |
                                      +----------------+----------------+
                                      |                                 |
                                Step 1..N                          abort_signal
                                      |                                 |
                                      v                                 |
                            +---------+----------+                      |
                            | Capture Snapshot   |                      |
                            | Build Prompt       |                      |
                            | Call LLM           |                      |
                            | Parse Action       |                      |
                            +---------+----------+                      |
                                      |                                 |
                                      v                                 |
                            +---------+----------+                      |
                            | ActionLoopDetector |                      |
                            | (SHA-256 hash)     |                      |
                            | Rolling window     |                      |
                            +---------+----------+                      |
                                      |                                 |
                                No loop                         Loop detected
                                      |                                 |
                                      v                                 v
                            +---------+----------+            +---------+--------+
                            | ToolRegistry       |            | Inject nudge     |
                            | lookup(action_name)|            | into LLM context |
                            | validate(params)   |            | Escalate at 5/8/12|
                            +---------+----------+            +------------------+
                                      |                                 |
                                      v                                 |
                            +---------+----------+            Loop level 3?
                            | Dispatch Action    |                 |
                            | via handler()      |                 v
                            +---------+----------+            Abort loop
                                      |                     with LOOP_DETECTED
                                      v
                            +---------+----------+
                            | ActionResult       |
                            | (GAP-12)           |
                            | ok=True/False      |
                            | data=TypedResult   |
                            +---------+----------+
                                      |
                                      v
                            +---------+----------+
                            | Page Change?       |
                            | (fingerprint diff) |
                            +---------+----------+
                             |                  |
                        Changed            Unchanged
                             |                  |
                        Mark step done    Increment stall count
                             |                  |
                             v                  v
                        Continue loop    3 consecutive stalls?
                                             |
                                        Yes: auto-replan
                                        (send plan state to LLM
                                         for revision)
                                             |
                                             v
                                        Updated PlanItem list
                                        (PLAN_UPDATED event emitted)


    Tool Registration Flow (at startup):

    Python Module Files (*.py)
            |
            v
    ToolRegistry.register_module()
            |
            v
    AST Parse --> Find @agent_action decorators
            |
            v
    For each decorated function:
      - inspect.signature() -> ToolParameter list
      - __doc__ -> description
      - Assign to toolsets
            |
            v
    ToolRegistry._tools: Dict[str, ToolDefinition]
    (thread-safe, RLock for writes, copy-on-read for reads)
            |
            v
    build_tool_api_description() -> formatted string for LLM prompt
    build_tool_schemas() -> JSON Schema list for function calling


    Subagent Delegation Flow:

    SuperBrowser.delegate(["task1", "task2", "task3"])
            |
            v
    SubagentDelegator.delegate()
            |
            v
    asyncio.TaskGroup (max_concurrency=4)
      |
      +---> Child 1: new tab -> AgentLoop("task1") -> result1
      +---> Child 2: new tab -> AgentLoop("task2") -> result2
      +---> Child 3: new tab -> AgentLoop("task3") -> result3
            |
            v
    DelegationResult(tasks=[ChildTask...], completed_count=3, failed_count=0)
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| GAP-01 (Browser Session & CDP) | -- | `BrowserSession` for session lifecycle, `PageHandle` for navigation, `CDPBridge` for compositor operations |
| GAP-02 (Three-Tier Interaction Engine) | -- | `MultimodalController` for `click()`, `fill()`, `select()`, `hover()`, `drag()` three-tier cascade execution |
| GAP-12 (Structured Action Results) | -- | `ActionResult`, `ResultMeta`, `ActionError`, `ActionMethod`, typed result payloads (`ClickResult`, `NavigateResult`, etc.) |
| `patchright` | >= 1.0 | Stealth browser (consumed via GAP-01) |
| Python | >= 3.11 | `asyncio.TaskGroup`, `enum.StrEnum`, `threading.RLock` |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| LLM Provider SDK (`anthropic` / `openai`) | `AgentLoop.run()` needs an LLM client for action proposal and planning | No autonomous `act()` without LLM; manual facade methods (`click`, `fill`, `navigate`) still work |
| GAP-11 (Tracing & Observability) | `AgentLoop` emits `StepEvent` for trace correlation | Events are silently dropped if no tracing is configured |
| `pydantic` | JSON Schema generation for tool parameters | Manual schema construction from `inspect.signature()` |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-07 |
|-----|--------------------------|
| GAP-04 (Self-Healing & Session Recovery) | `ActionLoopDetector` feeds into watchdog error classification; `StepResult.error` drives recovery strategy selection; `PlanItem` status enables retry-from-failure |
| GAP-09 (Token Budget & Cost Control) | `AgentLoop` step count drives per-step token budget allocation; `LoopResult.total_steps` feeds into cost analytics; `ToolDefinition.max_result_chars` feeds into `OutputDefender` (GAP-12) |
| GAP-10 (Security Envelope) | `ToolRegistry` is the enforcement point for action policy evaluation before tool dispatch; `SuperBrowser` facade is the boundary for security checks |
| GAP-11 (Tracing & Observability) | `StepEvent` emissions provide the primary trace events for agent loop observability; `LoopResult` is the aggregate session trace |

---

## 7. Acceptance Criteria

### AC1: SuperBrowser Facade -- navigate()

Calling `browser.navigate("https://example.com")` returns `ActionResult(ok=True, data=NavigateResult)` with `data.url` containing the final URL, `data.title` containing "Example Domain", and `data.status_code` set. The method delegates to `PageHandle.goto()` from GAP-01.

### AC2: SuperBrowser Facade -- click()

Calling `browser.click("a")` on example.com returns `ActionResult(ok=True, data=ClickResult)` with `data.method` set to `ActionMethod.SELECTOR` (Tier 1). The method delegates to `MultimodalController.click()` from GAP-02.

### AC3: SuperBrowser Facade -- fill()

Calling `browser.fill("#email", "user@example.com")` on a page with an email input returns `ActionResult(ok=True, data=FillResult)` with `data.value_entered="user@example.com"`. The method delegates to `MultimodalController.fill()` from GAP-02.

### AC4: SuperBrowser Facade -- act()

Calling `browser.act("click the 'More information' link on example.com", max_steps=10)` returns `ActionResult(ok=True, data=DelegatedResult)` with `data.completion_reason="success"`, `data.steps_executed >= 1`, and the page navigated away from example.com. The `AgentLoop` autonomously planned and executed the required steps.

### AC5: SuperBrowser Facade -- extract()

Calling `browser.extract("the main heading and first paragraph")` on example.com returns `ActionResult(ok=True, data=ExtractResult)` with `data.extracted` containing a dict with the heading text and paragraph text. The method uses LLM-based extraction guided by the query.

### AC6: SuperBrowser Facade -- observe()

Calling `browser.observe()` returns `ActionResult(ok=True)` with data containing: the current URL, page title, an AX snapshot summary (element count and interactive element list), and a screenshot hash. No DOM modifications occur.

### AC7: ToolRegistry AST Auto-Discovery

Given a Python module containing three `@agent_action`-decorated functions, calling `registry.register_module(path)` returns 3. The registry contains three `ToolDefinition` entries, each with the correct function name, parameter list (from `inspect.signature()`), and description (from `__doc__`). Registration completes in under 500 ms.

### AC8: ToolRegistry Thread Safety

When 10 concurrent tasks call `registry.snapshot()` while another task calls `registry.register()` 100 times, no task observes partial state: every snapshot either includes all tools registered before it started, or none registered after. No race conditions or deadlocks occur.

### AC9: ToolRegistry Toolset Composition

After defining toolsets `navigation` (navigate, click, fill) and `extraction` (extract, observe), calling `registry.list_tools(toolset="navigation")` returns exactly 3 tools. Calling `registry.build_tool_api_description(toolset="extraction")` returns a string containing only the extract and observe signatures.

### AC10: AgentLoop Step Count and Max Steps

Running an `AgentLoop` with `max_steps=5` on a task that would require 10 steps terminates after exactly 5 steps with `LoopResult.completion_reason="max_steps"` and `LoopResult.total_steps=5`. No step beyond the limit is executed.

### AC11: AgentLoop Abort Signal

When an `asyncio.Event` is set as the `abort_signal` during an `AgentLoop.run()` execution, the loop terminates within one step (at most 30 seconds from signal set). The `LoopResult.completion_reason="abort"` and the loop emits a `StepEvent.ABORT` event.

### AC12: ActionLoopDetector SHA-256 Loop Detection

When the same action (name + parameters) is recorded 5 times within the rolling window of 20, `ActionLoopDetector.record_and_check()` returns a `LoopNudge` with `level=1` and `repetition_count=5`. At 8 repetitions, `level=2`. At 12 repetitions, `level=3`. Different actions with different parameters do not trigger false positives.

### AC13: AgentLoop Planning and Auto-Replan

When the `AgentLoop` executes 3 consecutive steps that produce no page change (stagnation), it triggers an auto-replan: the current `PlanItem` list is sent to the LLM for revision, a new plan is received, and execution continues with the revised plan. The `LoopResult.replan_count` is incremented.

### AC14: Subagent Delegation with Parallel Execution

Calling `browser.delegate(["task A", "task B", "task C"], max_concurrency=2)` creates 3 child agents that execute in parallel (2 concurrent). The `DelegationResult` contains 3 `ChildTask` entries, each with `status=COMPLETED` and its own result. The total wall-clock time is less than the sum of individual task durations (demonstrating parallelism).

### AC15: Subagent Delegation Child Isolation

When a child agent raises an unhandled exception, it does not corrupt the parent's browser state. The parent's current page URL, title, and DOM remain unchanged. The failed child's `ChildTask.status=FAILED` and `ChildTask.result` contains the error, while other children continue executing.

### AC16: Tool API Description for LLM Prompt

Calling `browser.tools()` returns a formatted string containing function signatures and docstrings for all registered tools. The string is parseable by an LLM and exactly matches the available methods (zero drift). After registering a new tool at runtime, the description is updated to include it.

### AC17: Step Event Emission

During `AgentLoop.run()`, each step emits `StepEvent.STEP_START` before action dispatch and `StepEvent.STEP_COMPLETE` after the action result is received. On error, `StepEvent.STEP_ERROR` is emitted. On loop detection, `StepEvent.LOOP_DETECTED` is emitted. The event callback receives the event type and a dict with step_number, action_name, and duration_ms.

---

## 8. Test Scenarios

| ID  | Scenario | Steps | Expected Outcome | AC |
|-----|----------|-------|------------------|----|
| T1  | Navigate to example.com | `browser.start()`, `browser.navigate("https://example.com")` | `ActionResult(ok=True, data=NavigateResult(url="https://example.com/", title="Example Domain"))` | AC1 |
| T2  | Click link on example.com | Navigate to example.com, `browser.click("a")` | `ActionResult(ok=True, data=ClickResult(method=SELECTOR))`, page navigates | AC2 |
| T3  | Fill text input | Navigate to page with input, `browser.fill("#search", "hello")` | `ActionResult(ok=True, data=FillResult(value_entered="hello"))` | AC3 |
| T4  | Autonomous act | `browser.act("click the 'More information' link", max_steps=5)` | `ActionResult(ok=True, data=DelegatedResult(completion_reason="success", steps_executed >= 1))` | AC4 |
| T5  | Extract data | Navigate to example.com, `browser.extract("the main heading")` | `ActionResult(ok=True, data=ExtractResult)` with heading text present | AC5 |
| T6  | Observe page state | Navigate to example.com, `browser.observe()` | `ActionResult(ok=True)` with URL, title, element count, screenshot hash | AC6 |
| T7  | AST auto-discovery of 3 tools | Create module with 3 `@agent_action` functions, `registry.register_module()` | Returns 3, `registry.tool_count == 3`, each has correct signature and docstring | AC7 |
| T8  | AST discovery under 500ms | Scan a package with 10 modules, 50 tools | Registration completes in under 500 ms | AC7 |
| T9  | Concurrent read/write safety | 10 readers + 1 writer running simultaneously | No exceptions, every snapshot is internally consistent | AC8 |
| T10 | Toolset filtering | Define `nav` toolset with 3 tools, `registry.list_tools(toolset="nav")` | Returns exactly 3 tools, `build_tool_api_description(toolset="nav")` contains only those 3 | AC9 |
| T11 | Max steps enforcement | Run loop with `max_steps=3` on a task needing 10 steps | `LoopResult.completion_reason="max_steps", total_steps=3` | AC10 |
| T12 | Abort signal | Start loop, set `abort_signal` after 2 seconds | Loop terminates within one step, `completion_reason="abort"`, `StepEvent.ABORT` emitted | AC11 |
| T13 | Loop detection at level 1 | Record same action 5 times | `LoopNudge(level=1, repetition_count=5)` returned | AC12 |
| T14 | Loop detection at level 3 | Record same action 12 times | `LoopNudge(level=3, repetition_count=12)` returned | AC12 |
| T15 | No false positives | Record 10 different actions | No `LoopNudge` returned | AC12 |
| T16 | Auto-replan on stagnation | Run loop, simulate 3 consecutive stalled steps | Auto-replan triggered, `LoopResult.replan_count >= 1` | AC13 |
| T17 | Parallel delegation | `browser.delegate(["task A", "task B", "task C"], max_concurrency=2)` | `DelegationResult(completed_count=3, failed_count=0)`, total time < sum of individual times | AC14 |
| T18 | Child isolation on failure | Delegate 3 tasks, force child 2 to crash | Child 2 `status=FAILED`, children 1 and 3 `status=COMPLETED`, parent state unchanged | AC15 |
| T19 | Tool API description | `browser.tools()` after registering 6 core tools | Formatted string with all 6 signatures and docstrings, parseable by LLM | AC16 |
| T20 | Tool API updates dynamically | `browser.register_tool(new_func)`, then `browser.tools()` | New tool appears in description | AC16 |
| T21 | Step events emitted | Run loop for 5 steps with event callback | Receives 5 `STEP_START` + 5 `STEP_COMPLETE` events, each with step_number and action_name | AC17 |
| T22 | Full end-to-end autonomous task | `browser.act("go to example.com and click the 'More information' link")` | Page navigates to iana.org, `ActionResult(ok=True, completion_reason="success")` | AC4 |

---

## 9. Novel Work

None. All patterns are adopted from reference sources:

- Tool registry with AST auto-discovery: Hermes `tools/registry.py`
- @agent_action decorator + dynamic prompts: Agent-S `grounding.py`, `procedural_memory.py`
- Agent loop step execution: Stagehand `v3AgentHandler.ts`
- Action loop detection via SHA-256 hashing: browser-use `agent/views.py`
- Planning with PlanItem tracking: browser-use `agent/service.py`
- Subagent delegation with isolated context: Hermes `tools/delegate_tool.py`
- Plugin slot architecture: OpenClaw `plugins/slots.ts`, `plugins/registry.ts`
- Error classifier with recovery hints: Hermes `agent/error_classifier.py`

The integration value is composing Hermes's AST-based tool discovery with Agent-S's ergonomic decorator pattern, browser-use's loop detection and planning into Stagehand's agent loop structure, and exposing everything through a clean SuperBrowser facade with six primary methods that hide all internal complexity from the caller.

---

## 10. Adoption Timeline

| Week | Deliverable | Source Pattern |
|------|-------------|----------------|
| 4 | `ToolRegistry` with AST auto-discovery and `@agent_action` decorator integration | P1, P2 |
| 4 | `ToolDefinition`, `ToolParameter`, `Toolset` dataclasses | P1 |
| 4 | `ActionLoopDetector` with SHA-256 hashing and rolling window | P4 |
| 4 | `SuperBrowser` facade with `navigate()`, `click()`, `fill()` (manual delegation to GAP-02) | -- |
| 4 | `LoopNudge` escalation levels (5, 8, 12) | P4 |
| 5 | `AgentLoop` with step-based LLM interaction cycle | P3 |
| 5 | `PlanItem` tracking and auto-replan on stagnation | P5 |
| 5 | `SuperBrowser.act()` wiring to `AgentLoop` | P3, P4, P5 |
| 5 | `SuperBrowser.extract()` and `SuperBrowser.observe()` | -- |
| 5 | `SubagentDelegator` with parallel child execution | P6 |
| 5 | `SuperBrowser.delegate()` wiring to `SubagentDelegator` | P6 |
| 5 | `PluginSlot` abstract interface (implementation deferred) | P8 |
| 5 | Step event emission for GAP-11 tracing | P3 |
| 5 | End-to-end test: `browser.act("search for flights to Tokyo")` | All |
