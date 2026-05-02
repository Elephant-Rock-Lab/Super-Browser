# GAP-02: Three-Tier Interaction Engine

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap          | #2                                                           |
| Title        | Three-Tier Interaction Engine                                |
| Phase        | Phase 1 (Core Control)                                       |
| Status       | Spec Complete                                                 |
| Depends-On   | GAP-01 (Browser Session & CDP), GAP-12 (Structured Action Results) |
| Enables      | GAP-03, GAP-04, GAP-05, GAP-06, GAP-07                      |
| Build Order  | Week 2-5                                                     |

---

## 1. Problem

Super Browser must interact with any element on any page, but the web is fractally hostile to automation: shadow DOM encapsulates click targets, cross-origin iframes block DOM traversal, dynamic frameworks generate unstable selectors, and canvas/SVG elements have no DOM representation at all. No single interaction method works universally. A three-tier cascade -- selector (DOM-level), coordinate (CDP compositor-level), and vision (LLM pixel-level) -- is required, where each tier catches what the previous tier cannot reach and every result records which method succeeded so the system can learn the optimal tier per domain over time.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                                    |
|-------|--------------------------------------------------------------------------------------------------------------------------------|
| R1    | Provide a `MultimodalController` with five action methods: `click()`, `fill()`, `select()`, `hover()`, `drag()`                |
| R2    | Each action method implements a three-tier fallback cascade: Tier 1 (DOM selector) -> Tier 2 (CDP coordinate) -> Tier 3 (vision) |
| R3    | Tier 1 (selector): Use Patchright's native `page.click(selector)` / `page.fill(selector, value)` / etc. via the `PageHandle` from GAP-01 |
| R4    | Tier 2 (coordinate): Resolve target to bounding box via CDP `DOM.getBoxModel` or `Runtime.evaluate`, then dispatch `Input.dispatchMouseEvent` via `CDPBridge.compositor_click()` |
| R5    | Tier 3 (vision): Capture screenshot via `CDPBridge.capture_screenshot()`, send to vision LLM with element description, receive pixel coordinates, dispatch compositor click |
| R6    | Every `ActionResult` records `meta.method` as `ActionMethod.SELECTOR`, `.COORDINATE`, or `.VISION` indicating which tier succeeded |
| R7    | Implement a `TierPreferenceCache` that stores which tier succeeded per (domain, selector_pattern) pair and persists to `~/.super-browser/tier-cache/{domain}.json` with LRU eviction at 1000 entries per domain |
| R8    | When a cached preference exists for the current domain/target pattern, attempt the preferred tier first (skip lower tiers) to optimize latency and cost |
| R9    | Expose an `@agent_action` decorator that marks methods as browser actions, auto-discovers them via `inspect.signature()`, and generates dynamic action API descriptions for the agent's system prompt |
| R10   | Support a two-phase act pattern: Phase 1 captures snapshot and proposes action, Phase 2 re-captures snapshot to compute diff and verify action success |
| R11   | Provide an AX snapshot via CDP `Accessibility.getFullAXTree` that assigns stable ref IDs (`@e0`, `@e1`, ...) to interactive elements for ref-based targeting in Tier 1 |
| R12   | Implement key dispatch via `CDPBridge.compositor_type()` and `CDPBridge.compositor_key_press()` for Tier 2 text input and special key presses |
| R13   | The `fill()` method supports a `clear_first` option that selects all existing text (Ctrl+A) before typing new content                          |
| R14   | The `select()` method handles dropdown elements by clicking to open, then clicking the target option by visible text or value                   |
| R15   | The `drag()` method dispatches mousePressed at source, intermediate mouseMoved events, and mouseReleased at destination via compositor           |
| R16   | All tier attempts are bounded by configurable timeouts: Tier 1 (5s), Tier 2 (3s), Tier 3 (15s)                                                  |
| R17   | Validate end-to-end with live tests against `https://example.com` (Tier 1), `https://threads.net` (shadow DOM, Tier 2), and canvas pages (Tier 3) |

### Non-Functional

| ID    | Requirement                                                                                                          |
|-------|----------------------------------------------------------------------------------------------------------------------|
| NFR1  | Tier 1 actions must complete in under 100 ms (no network calls, DOM-only)                                            |
| NFR2  | Tier 2 actions must complete in under 500 ms (one CDP round-trip for bounding box + one for click)                   |
| NFR3  | Tier 3 actions must complete in under 15 seconds (screenshot capture + LLM inference + compositor dispatch)          |
| NFR4  | The tier preference cache lookup must add under 1 ms per action (in-memory dict, no disk I/O on the hot path)        |
| NFR5  | Cache persistence (disk writes) must be asynchronous and non-blocking; cache misses never block action execution      |
| NFR6  | The `@agent_action` introspection must run once at registration time, not per-action, to avoid runtime overhead       |
| NFR7  | No tier may leak browser automation fingerprints: Tier 1 uses Patchright (stealth), Tier 2 uses raw CDP (invisible), Tier 3 produces user-like input |

### Out of Scope

- Full CUA (Computer Use Agent) provider integration -- deferred to GAP-06 (Vision-Based Element Location)
- Visual verification of action results (before/after comparison) -- deferred to GAP-03 (Visual Verification)
- Self-healing selector retry with alternative selectors -- deferred to GAP-04 (Self-Healing & Session Recovery)
- Domain skill auto-generation from successful interactions -- deferred to GAP-05 (Domain Skill Registry)
- Multi-step agent loop (plan, act, observe, replan) -- deferred to GAP-07 (Agent Orchestration & Facade)

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | AX Snapshot with Ref-Based Targeting | agent-browser `snapshot.rs` | 3.95 | Medium | Tier 1 element discovery |
| P2 | Hybrid DOM+AX 5-Phase Snapshot | Stagehand `capture.ts` (475 lines) | 4.25 | Medium | Tier 1 rich page representation |
| P3 | Two-Phase Act with Self-Healing Retry | Stagehand `actHandler.ts` (535 lines) | 3.95 | Medium | Action execution pipeline |
| P4 | Compositor-Level Click Primitives | browser-harness `helpers.py:70-72` | 3.95 | Low | Tier 2 raw mouse dispatch |
| P5 | Key Dispatch with Virtual Key Codes | browser-harness `helpers.py:77-94` | 3.35 | Low | Tier 2 keyboard input |
| P6 | @agent_action Decorator + Dynamic Prompts | Agent-S `grounding.py:25-28`, `procedural_memory.py:78-89` | 4.12 | Low | Action registration |
| P7 | Visual Grounding via UI-TARS | Agent-S `grounding.py:229-245` | 4.12 | Medium | Tier 3 coordinate resolution |
| P8 | CUA Client Factory (4 Providers) | Stagehand `AgentProvider.ts`, `AnthropicCUAClient.ts` | 4.00 | High | Tier 3 LLM provider abstraction |
| P9 | Vision-First Loop (Screenshot+DOM -> LLM -> Action) | Skyvern `forge/agent.py` | 3.80 | Medium | Tier 3 action loop pattern |
| P10 | ActCache with SHA-256 Keyed Self-Healing | Stagehand `ActCache.ts` (387 lines) | 3.45 | Low | Cache key design for tier preferences |
| P11 | 3-Strategy Browser Control (DOM/Visual-Grounding/Hybrid) | UI-TARS-Desktop `browser-control-strategies/` | 4.49 | Medium | Architecture for strategy selection |
| P12 | Operator Type System with Normalized Coordinates | UI-TARS-Desktop `operator.ts` (221), `actions.ts` (383) | 4.74 | Medium | Action vocabulary and coordinate system |

### Per-Pattern Adoption Notes

**P1 -- AX Snapshot with Ref-Based Targeting (agent-browser)**
Adopt the accessibility tree capture via CDP `Accessibility.getFullAXTree`. The original captures the tree in Rust, classifies nodes as interactive/content/structural, assigns short `@eN` ref IDs, and builds a RefMap for coordinate resolution. Port this to Python: call CDP `Accessibility.getFullAXTree` via `CDPBridge.send()`, filter for interactive nodes (role `button`, `link`, `textbox`, `combobox`, `checkbox`, `radio`, `menuitem`, `tab`, `slider`), assign sequential `@eN` refs, and store bounding boxes. This is the most token-efficient page representation for Tier 1 -- a 50-element page produces ~500 tokens of AX snapshot vs ~5000 tokens of full HTML.

**P2 -- Hybrid DOM+AX 5-Phase Snapshot (Stagehand)**
Adopt the sequential 5-phase capture pipeline for richer Tier 1 data. Phase 1: scoped snapshot via focus selector. Phase 2: `DOM.getDocument` per CDP session. Phase 3: per-frame DOM tag/xpath/scroll maps + AX trees. Phase 4: BFS walk computing absolute XPath prefixes. Phase 5: merge into combined snapshot with nested iframe outlines. This provides the most complete page representation, essential for complex sites with OOPIFs. Use as the Tier 1 page model when the simpler AX snapshot (P1) is insufficient.

**P3 -- Two-Phase Act with Self-Healing Retry (Stagehand)**
Adopt the two-phase act pipeline. Phase 1: capture snapshot, build action prompt, get proposed action from system/LLM, execute deterministic action. Phase 2 (optional): re-capture snapshot, compute diff, verify action succeeded. Self-healing path: on action failure, re-capture snapshot and retry with fresh selectors. This pattern wraps the entire three-tier cascade -- the "execute action" step in Phase 1 IS the three-tier fallback. Phase 2 is the verification hook that GAP-03 (Visual Verification) will consume.

**P4 -- Compositor-Level Click Primitives (browser-harness)**
Adopt the two-line compositor click: `Input.dispatchMouseEvent` with `mousePressed` followed by `mouseReleased` at exact viewport coordinates. Already provided by `CDPBridge.compositor_click()` from GAP-01. These clicks bypass shadow DOM, cross-origin iframes, and all DOM layers. This IS Tier 2 -- no additional implementation needed beyond calling `CDPBridge.compositor_click()` with coordinates resolved from the target element.

**P5 -- Key Dispatch with Virtual Key Codes (browser-harness)**
Adopt the proper keyDown/char/keyUp event sequence with virtual key code mapping for 15+ special keys. Already provided by `CDPBridge.compositor_type()` and `CDPBridge.compositor_key_press()` from GAP-01. Used by Tier 2 `fill()` actions: after clicking the target input (via compositor click), type the text character-by-character via compositor_type. Supports modifier bitmask for Shift/Ctrl/Alt combinations in special key dispatch.

**P6 -- @agent_action Decorator + Dynamic Prompts (Agent-S)**
Adopt the minimal decorator pattern: `func.is_agent_action = True` marks action methods. At registration time, iterate all class methods via `dir()`/`getattr()`, extract `inspect.signature()` for parameter names/types and `__doc__` for descriptions. Assemble into a formatted API description for the agent's system prompt. This eliminates prompt documentation drift -- the LLM always sees an API that exactly matches the available actions. Every method on `MultimodalController` (`click`, `fill`, `select`, `hover`, `drag`, `scroll`, `keypress`) is decorated with `@agent_action`.

**P7 -- Visual Grounding via UI-TARS (Agent-S)**
Adopt the visual grounding pattern for Tier 3: send full screenshot + natural language element description to a vision model, receive pixel coordinates, resize from model resolution to screen resolution. The original uses a dedicated UI-TARS 7B model; Super Browser generalizes to any vision-capable LLM via the CUA provider factory (P8). The coordinate resizing logic (`resize_coordinates()`) from Agent-S `grounding.py:229-245` is directly portable.

**P8 -- CUA Client Factory (Stagehand)**
Adopt the provider factory pattern mapping model names to provider-specific clients (Anthropic, OpenAI, Google, Microsoft). Each client implements an abstract interface: `execute_step()` (screenshot -> model -> action), `capture_screenshot()`, `set_viewport()`. The factory `modelToAgentProviderMap` maps 12+ model names to provider types. This provides Tier 3's LLM abstraction -- the `MultimodalController` does not know which vision provider is in use.

**P9 -- Vision-First Loop (Skyvern)**
Adopt the screenshot+DOM -> LLM -> action pattern as Tier 3's execution loop. Skyvern's `ForgeAgent.execute_step()` captures scraped page + screenshot, sends both to LLM with task objective, receives structured action output. For Super Browser's Tier 3, this becomes: capture screenshot via `CDPBridge.capture_screenshot()`, optionally include AX snapshot for context, send to vision LLM with "Find '{element_description}' and return x,y coordinates", parse coordinates from response, dispatch compositor click.

**P10 -- ActCache with SHA-256 Keyed Self-Healing (Stagehand)**
Adopt the SHA-256 cache key pattern for the tier preference cache. Stagehand keys its action cache by `SHA-256(instruction + url + variableKeys)`. Super Browser keys tier preferences by `SHA-256(domain + selector_pattern)`. The self-healing concept -- detecting when cached selectors change and updating the cache -- inspires the tier preference cache's invalidation: when a preferred tier fails, the cache entry is demoted or removed, forcing re-exploration.

**P11 -- 3-Strategy Browser Control (UI-TARS-Desktop)**
Adopt the DOM / visual-grounding / hybrid strategy pattern from UI-TARS-Desktop's Agent TARS. The original defines three browser control strategies selectable at runtime: (1) DOM strategy using Puppeteer selectors, (2) Visual Grounding strategy using VLM screenshot analysis, (3) Hybrid strategy registering both DOM tools and a `browser_vision_control` tool, letting the LLM choose which to call per action. This directly maps to Super Browser's three-tier cascade: the forced-fallback approach (try Tier 1, catch, try Tier 2, catch, try Tier 3) handles automatic degradation, while the hybrid strategy's LLM-choice pattern provides an alternative where the agent can deliberately select a higher tier when it knows DOM interaction will fail (e.g., canvas elements). The hybrid pattern should be available as an optional mode alongside the default cascade.

**P12 -- Operator Type System with Normalized Coordinates (UI-TARS-Desktop)**
Adopt the `Coordinates` type carrying both `raw: {x, y}` (click point) and `referenceBox: {x1, y1, x2, y2}` (bounding box) from UI-TARS-Desktop's operator abstraction. The original defines 30+ action types with full parameter schemas and uses a normalized [0,1] coordinate system where VLM output is scaled to physical pixels per operator. Super Browser should adopt the `referenceBox` concept for Tier 2/3 results: when a coordinate click lands, the bounding box of the intended target is recorded alongside the click point. This provides visual feedback (highlight the clicked area) and debugging context (was the click on the right element?). The normalized [0,1] coordinate system is the canonical internal representation, converted to viewport pixels only at dispatch time.

---

## 4. Interface Contract

### Dataclasses

```python
from __future__ import annotations

import hashlib
import inspect
import json
import time
import uuid
from collections import OrderedDict
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import Any, Callable, Optional

# Types from GAP-01 (consumed, not redefined)
# from src.super_browser.browser.session import CDPBridge, PageHandle, BrowserSession
# from src.super_browser.results import ActionResult, ResultMeta, ActionError, ActionMethod
# from src.super_browser.results import ClickResult, FillResult, timed_action_result


# ---------------------------------------------------------------------------
# Tier Definitions
# ---------------------------------------------------------------------------

class Tier(IntEnum):
    """Interaction tiers in priority order. Lower value = cheaper and faster."""
    SELECTOR = 1    # Tier 1: DOM selector via Patchright page methods
    COORDINATE = 2  # Tier 2: CDP compositor-level coordinate dispatch
    VISION = 3      # Tier 3: LLM vision screenshot analysis + coordinate dispatch


class TierOutcome(StrEnum):
    """Result of a single tier attempt within the cascade."""
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"        # skipped due to preference cache hit
    UNAVAILABLE = "unavailable"  # e.g., no vision provider configured


@dataclass(frozen=True)
class TierAttempt:
    """Record of a single tier attempt within a cascade."""
    tier: Tier
    outcome: TierOutcome
    duration_ms: float
    error: Optional[str] = None
    coordinates: Optional[tuple[float, float]] = None  # set for Tier 2/3


@dataclass(frozen=True)
class CascadeResult:
    """Complete record of a three-tier cascade execution."""
    action: str                            # "click", "fill", "select", etc.
    target: str                            # original target description
    attempts: tuple[TierAttempt, ...]      # ordered attempts (Tier 1, 2, 3)
    succeeded_tier: Optional[Tier] = None  # which tier succeeded (None = all failed)
    total_duration_ms: float = 0.0


# ---------------------------------------------------------------------------
# AX Snapshot (P1 -- agent-browser adoption)
# ---------------------------------------------------------------------------

@dataclass
class AXNode:
    """Single node from the accessibility tree."""
    ref: str                              # @e0, @e1, etc.
    role: str                             # "button", "link", "textbox", etc.
    name: str                             # accessible name / label
    url: Optional[str] = None             # for links
    value: Optional[str] = None           # for inputs
    description: Optional[str] = None     # aria-description
    bounds: Optional[tuple[float, float, float, float]] = None  # (x, y, w, h)
    focused: bool = False
    disabled: bool = False

    @property
    def center(self) -> Optional[tuple[float, float]]:
        """Center coordinates of the element bounding box."""
        if self.bounds:
            return (self.bounds[0] + self.bounds[2] / 2,
                    self.bounds[1] + self.bounds[3] / 2)
        return None

    @property
    def is_interactive(self) -> bool:
        """Whether this node is an interactive element."""
        return self.role in {
            "button", "link", "textbox", "combobox", "checkbox",
            "radio", "menuitem", "tab", "slider", "searchbox",
            "spinbutton", "switch", "option", "treeitem",
        }


@dataclass
class AXSnapshot:
    """Complete accessibility tree snapshot with ref-based element map."""
    url: str
    title: str
    nodes: dict[str, AXNode] = field(default_factory=dict)  # ref -> AXNode
    captured_at: float = field(default_factory=time.monotonic)
    token_count: int = 0                 # estimated tokens for the snapshot

    def resolve(self, ref: str) -> Optional[AXNode]:
        """Resolve a ref ID (e.g., '@e2') to its AXNode."""
        return self.nodes.get(ref.lstrip("@"))

    def find_by_text(self, text: str) -> list[AXNode]:
        """Find all interactive nodes whose name contains the given text."""
        text_lower = text.lower()
        return [n for n in self.nodes.values()
                if n.is_interactive and text_lower in n.name.lower()]

    def find_by_role(self, role: str) -> list[AXNode]:
        """Find all nodes with the given role."""
        return [n for n in self.nodes.values() if n.role == role]

    def to_compact_str(self) -> str:
        """
        Serialize to compact string for LLM context.
        Format: [@e0] button "Login" [url=...] [value=...]
        """
        lines = []
        for ref, node in sorted(self.nodes.items(), key=lambda x: int(x[0][1:])):
            parts = [f"[{node.ref}]", node.role, f'"{node.name}"']
            if node.url:
                parts.append(f"url={node.url}")
            if node.value:
                parts.append(f"value={node.value}")
            if node.disabled:
                parts.append("[disabled]")
            lines.append(" ".join(parts))
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tier Preference Cache (Novel Work)
# ---------------------------------------------------------------------------

@dataclass
class CacheEntry:
    """Single entry in the tier preference cache."""
    selector_pattern: str       # e.g., "button.login", "input[type='email']"
    preferred_tier: Tier
    hit_count: int = 0          # number of times this preference was used
    miss_count: int = 0         # number of times the preferred tier failed
    last_used: float = 0.0      # monotonic timestamp
    last_updated: float = 0.0   # when the preference was last changed
    confidence: float = 1.0     # 0.0-1.0, increases with hits, decreases with misses


class TierPreferenceCache:
    """
    Per-domain tier preference cache with LRU eviction and persistence.

    Persists to ~/.super-browser/tier-cache/{domain}.json
    LRU eviction at 1000 entries per domain.
    """

    MAX_ENTRIES_PER_DOMAIN = 1000

    def __init__(self, cache_dir: Path = Path.home() / ".super-browser" / "tier-cache") -> None:
        self._cache_dir = cache_dir
        self._domains: dict[str, OrderedDict[str, CacheEntry]] = {}

    # -- Lookup --

    def get(self, domain: str, selector_pattern: str) -> Optional[Tier]:
        """
        Look up the preferred tier for a domain+selector_pattern.
        Returns None if no preference exists (cache miss).
        Moves the entry to the end of the LRU (most recently used).
        """
        ...

    # -- Update --

    def record_success(self, domain: str, selector_pattern: str, tier: Tier) -> None:
        """
        Record that a tier succeeded. If no entry exists, create one.
        If an entry exists with a different tier, update the preference.
        Increment hit_count and adjust confidence.
        """
        ...

    def record_failure(self, domain: str, selector_pattern: str, tier: Tier) -> None:
        """
        Record that a tier failed. Decrement confidence for this tier.
        If confidence drops below 0.3, demote: remove the entry so the
        next action re-explores all tiers.
        """
        ...

    # -- Persistence --

    async def persist(self, domain: str) -> None:
        """
        Write the domain's cache to disk as JSON.
        File: ~/.super-browser/tier-cache/{domain}.json
        Non-blocking: runs in a background thread via asyncio.to_thread.
        """
        ...

    async def load(self, domain: str) -> None:
        """
        Load the domain's cache from disk.
        No error if file does not exist -- starts with empty cache.
        """
        ...

    # -- Eviction --

    def _evict_if_needed(self, domain: str) -> None:
        """
        If the domain cache exceeds MAX_ENTRIES_PER_DOMAIN, evict the
        least recently used entries (front of OrderedDict).
        """
        ...

    # -- Stats --

    def stats(self, domain: str) -> dict[str, Any]:
        """Return cache statistics for a domain."""
        ...


# ---------------------------------------------------------------------------
# @agent_action Decorator (P6 -- Agent-S adoption)
# ---------------------------------------------------------------------------

def agent_action(func: Callable) -> Callable:
    """
    Mark a method as a browser action. The MultimodalController
    introspects decorated methods at registration time to build
    the dynamic action API description for the agent's system prompt.

    Adopted from Agent-S grounding.py:25-28.

    Usage:
        @agent_action
        async def click(self, target: str, *, button: str = "left") -> ActionResult:
            '''Click on an element identified by selector, coordinates, or description.'''
            ...
    """
    func.is_agent_action = True
    return func


def build_action_api_description(controller: MultimodalController) -> str:
    """
    Introspect all @agent_action methods on the controller and build
    a formatted API description for the agent's system prompt.

    Adopted from Agent-S procedural_memory.py:78-89.

    Returns a string like:
        Available browser actions:

        def click(target: str, *, button: str = "left") -> ActionResult:
        '''Click on an element identified by selector, coordinates, or description.'''

        def fill(target: str, value: str, *, clear_first: bool = True) -> ActionResult:
        '''Fill a text input with the given value.'''
        ...
    """
    ...


# ---------------------------------------------------------------------------
# Vision Provider Interface (P8 -- Stagehand CUA adoption)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VisionRequest:
    """Request to a vision provider for element location."""
    screenshot: bytes                     # PNG image data
    element_description: str              # natural language description
    page_url: str                         # current page URL for context
    viewport_size: tuple[int, int]        # (width, height) for coordinate normalization


@dataclass(frozen=True)
class VisionResponse:
    """Response from a vision provider with resolved coordinates."""
    found: bool
    x: Optional[float] = None
    y: Optional[float] = None
    confidence: float = 0.0              # 0.0-1.0
    raw_response: Optional[str] = None    # original LLM response for debugging
    model: Optional[str] = None          # which model was used
    token_cost: float = 0.0              # cost in USD
    duration_ms: float = 0.0


class VisionProvider:
    """Abstract base for vision-based element location providers."""

    async def locate(self, request: VisionRequest) -> VisionResponse:
        """
        Locate an element in a screenshot by natural language description.

        Returns VisionResponse with pixel coordinates if found.
        Coordinates are in viewport space (0,0 = top-left).
        """
        ...

    @property
    def name(self) -> str: ...

    @property
    def model_id(self) -> str: ...
```

### Classes and Signatures

```python
class MultimodalController:
    """
    Three-tier interaction engine. Every action method attempts
    Tier 1 (selector) -> Tier 2 (coordinate) -> Tier 3 (vision)
    and returns an ActionResult recording which tier succeeded.

    Consumes:
      - PageHandle from GAP-01 for Tier 1 operations
      - CDPBridge from GAP-01 for Tier 2/3 operations
      - ActionResult / ResultMeta from GAP-12 for structured results

    Usage:
        session = BrowserSession(SessionConfig())
        await session.start()
        page = await session.new_page()

        controller = MultimodalController(
            page=page,
            cdp=page.cdp,
            tier_cache=TierPreferenceCache(),
        )

        result = await controller.click("button.login")
        assert result.ok
        assert result.meta.method == ActionMethod.SELECTOR  # Tier 1 worked
    """

    def __init__(
        self,
        page: PageHandle,
        cdp: CDPBridge,
        tier_cache: Optional[TierPreferenceCache] = None,
        vision_provider: Optional[VisionProvider] = None,
        *,
        tier_timeouts: Optional[dict[Tier, float]] = None,
        two_phase: bool = False,
    ) -> None:
        """
        Args:
            page: Patchright PageHandle for Tier 1 operations.
            cdp: CDPBridge for Tier 2/3 compositor operations.
            tier_cache: Optional tier preference cache. If None, no caching.
            vision_provider: Optional vision provider for Tier 3. If None,
                Tier 3 is unavailable (cascade stops at Tier 2).
            tier_timeouts: Per-tier timeout overrides. Defaults:
                Tier.SELECTOR: 5.0, Tier.COORDINATE: 3.0, Tier.VISION: 15.0
            two_phase: If True, enable two-phase act with diff verification
                (requires GAP-03 VisualVerifier -- initially False).
        """
        ...

    # -- Action Methods (all decorated with @agent_action) ----------------

    @agent_action
    async def click(
        self,
        target: str,
        *,
        button: str = "left",
        click_count: int = 1,
        description: Optional[str] = None,
    ) -> ActionResult:
        """
        Click on an element.

        Args:
            target: CSS selector, XPath, AX ref (@eN), or element description.
            button: Mouse button ("left", "right", "middle").
            click_count: Number of clicks (1=single, 2=double).
            description: Natural language description for Tier 3 vision.
        """
        ...

    @agent_action
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

        Args:
            target: CSS selector, XPath, AX ref, or element description.
            value: Text to type into the element.
            clear_first: Select all existing text (Ctrl+A) before typing.
            description: Natural language description for Tier 3 vision.
        """
        ...

    @agent_action
    async def select(
        self,
        target: str,
        option: str,
        *,
        by: str = "text",
        description: Optional[str] = None,
    ) -> ActionResult:
        """
        Select an option in a dropdown/select element.

        Args:
            target: CSS selector, XPath, AX ref, or element description.
            option: Option text or value to select.
            by: How to match the option: "text" or "value".
            description: Natural language description for Tier 3 vision.
        """
        ...

    @agent_action
    async def hover(
        self,
        target: str,
        *,
        description: Optional[str] = None,
    ) -> ActionResult:
        """
        Hover over an element.

        Args:
            target: CSS selector, XPath, AX ref, or element description.
            description: Natural language description for Tier 3 vision.
        """
        ...

    @agent_action
    async def drag(
        self,
        source: str,
        destination: str,
        *,
        steps: int = 5,
        source_description: Optional[str] = None,
        destination_description: Optional[str] = None,
    ) -> ActionResult:
        """
        Drag from source element to destination element.

        Args:
            source: CSS selector or description for the drag source.
            destination: CSS selector or description for the drop target.
            steps: Number of intermediate mouseMoved events.
            source_description: Natural language for source (Tier 3).
            destination_description: Natural language for destination (Tier 3).
        """
        ...

    @agent_action
    async def scroll(
        self,
        *,
        direction: str = "down",
        amount: int = 3,
        target: Optional[str] = None,
    ) -> ActionResult:
        """
        Scroll the page or a specific element.

        Args:
            direction: "up", "down", "left", or "right".
            amount: Number of scroll steps (each ~100px).
            target: Optional element to scroll within. If None, scrolls page.
        """
        ...

    @agent_action
    async def keypress(
        self,
        key: str,
        *,
        modifiers: int = 0,
    ) -> ActionResult:
        """
        Press a key with optional modifiers.

        Args:
            key: Key name (e.g., "Enter", "Tab", "Escape", "a").
            modifiers: Bitmask (1=Alt, 2=Ctrl, 4=Shift, 8=Meta).

        Always uses Tier 2 (CDP key dispatch). No cascade.
        """
        ...

    # -- AX Snapshot (P1) -------------------------------------------------

    async def capture_ax_snapshot(self) -> AXSnapshot:
        """
        Capture accessibility tree via CDP Accessibility.getFullAXTree.
        Assign stable @eN ref IDs to interactive elements.
        Returns AXSnapshot with ref-based element map.
        """
        ...

    # -- Cascade Engine ----------------------------------------------------

    async def _cascade(
        self,
        action: str,
        target: str,
        description: Optional[str],
        tier1_fn: Callable,
        tier2_fn: Callable,
        tier3_fn: Optional[Callable] = None,
    ) -> tuple[ActionResult, CascadeResult]:
        """
        Execute the three-tier cascade for an action.

        1. Check tier preference cache for target domain+pattern.
        2. If cached preference exists, try that tier first.
        3. If preference fails or no cache, try tiers in order: 1 -> 2 -> 3.
        4. Record success/failure in tier preference cache.
        5. Return ActionResult with method set to the tier that succeeded.

        Args:
            action: Action name (e.g., "click", "fill").
            target: Original target string.
            description: Optional natural language description.
            tier1_fn: Async callable for Tier 1 execution.
            tier2_fn: Async callable for Tier 2 execution (receives coords).
            tier3_fn: Optional async callable for Tier 3 execution.

        Returns:
            Tuple of (ActionResult, CascadeResult).
        """
        ...

    # -- Tier Executors ----------------------------------------------------

    async def _tier1_click(self, target: str, **kwargs) -> ActionResult:
        """Tier 1: page.click(selector) via Patchright."""
        ...

    async def _tier2_click(self, target: str, **kwargs) -> ActionResult:
        """Tier 2: resolve bounding box -> CDPBridge.compositor_click()."""
        ...

    async def _tier3_click(self, target: str, description: str, **kwargs) -> ActionResult:
        """Tier 3: screenshot -> vision LLM -> compositor click."""
        ...

    async def _resolve_to_coordinates(self, target: str) -> Optional[tuple[float, float]]:
        """
        Resolve a target (selector, XPath, or AX ref) to viewport coordinates.

        Resolution order:
          1. AX ref (@eN) -> AXSnapshot bounds center
          2. CSS selector -> CDP DOM.getBoxModel -> center
          3. XPath -> CDP Runtime.evaluate -> bounding rect -> center
        """
        ...

    # -- Utility -----------------------------------------------------------

    def _extract_domain(self) -> str:
        """Extract the current page domain for cache keying."""
        ...

    def _classify_selector_pattern(self, target: str) -> str:
        """
        Classify a target string into a generalizable selector pattern.
        E.g., "button.login-btn" -> "button.*"
             "#submit-abc123" -> "#submit-*"  (strip dynamic suffixes)
             "@e5" -> "@ref"
        """
        ...


class SnapshotProvider:
    """
    Builds page snapshots for the interaction engine.
    Supports AX-only (P1) and hybrid DOM+AX (P2) modes.
    """

    def __init__(self, cdp: CDPBridge) -> None: ...

    async def capture_ax_only(self, url: str, title: str) -> AXSnapshot:
        """
        Capture AX tree only. Most token-efficient.
        Calls CDP Accessibility.getFullAXTree, filters interactive nodes,
        assigns @eN refs, builds AXSnapshot.
        """
        ...

    async def capture_hybrid(self, url: str, title: str) -> AXSnapshot:
        """
        Capture hybrid DOM+AX snapshot (P2 -- Stagehand 5-phase).
        More complete but slower and larger.
        """
        ...


class VisionProviderFactory:
    """
    Factory for vision providers. Maps model names to provider instances.
    Adopted from Stagehand AgentProvider.ts model-to-provider mapping.
    """

    def __init__(self, providers: Optional[dict[str, VisionProvider]] = None) -> None: ...

    def get_provider(self, model: Optional[str] = None) -> Optional[VisionProvider]:
        """
        Get a vision provider by model name.
        If model is None, returns the default provider.
        Returns None if no providers are configured.
        """
        ...

    @classmethod
    def from_env(cls) -> VisionProviderFactory:
        """
        Create factory from environment variables:
          - SB_VISION_DEFAULT_PROVIDER: "anthropic" | "openai" | "google"
          - SB_VISION_DEFAULT_MODEL: model ID string
          - SB_ANTHROPIC_API_KEY, SB_OPENAI_API_KEY, etc.
        """
        ...
```

---

## 5. Data Flow

```
                         Agent / SuperBrowser Facade
                                    |
                                    v
                      +-------------+---------------+
                      |    MultimodalController      |
                      |  (action: click/fill/...)    |
                      +-------------+---------------+
                                    |
                          1. Check TierPreferenceCache
                          (domain + selector_pattern)
                                    |
                      +-------------+-------------+
                      |                           |
                 Cache HIT                   Cache MISS
                 (preferred tier)           (try Tier 1 first)
                      |                           |
                      v                           v
           +----------+-----------+    +----------+-----------+
           | Attempt preferred     |    | Tier 1: page.click() |
           | tier directly         |    | (Patchright native)  |
           +----------+-----------+    +----------+-----------+
                      |                           |
               +------+------+            +-------+-------+
               |             |         Success   Failure
          Success       Failure        (ok=True)  (exception)
               |             |            |           |
               v             |            v           v
    +----------+---+         |   ActionResult     +--+------------+
    | ActionResult |         |   method=SELECTOR  | Tier 2:       |
    | method=<pref>|         |                    | resolve coords |
    +----------+---+         |                    | via AX ref /   |
               |             |                    | DOM.getBoxModel|
    Record success           |                    +--+------------+
    in TierCache             |                       |         |
               |             |                  Success    Failure
               |             |                  (ok=True)  (no bbox)
               |             |                     |           |
               |             |                     v           v
               |             |           ActionResult     +---+---------+
               |             |           method=          | Tier 3:     |
               |             |           COORDINATE       | screenshot  |
               |             |                           | -> vision   |
               |             |                           | LLM ->      |
               |             |                           | coords ->   |
               |             |                           | compositor  |
               |             |                           | click       |
               |             |                           +--+----------+
               |             |                              |        |
               |             |                         Success   Failure
               |             |                         (ok=True)  (not found)
               |             |                            |           |
               |             |                            v           v
               |             |                  ActionResult   ActionResult
               |             |                  method=        (ok=False,
               |             |                  VISION         all tiers
               |             |                                 failed)
               |             |                     |
               +----+--------+---------------------+---+
                    |
          Record success/failure
          in TierPreferenceCache
                    |
          Async persist to
          ~/.super-browser/tier-cache/{domain}.json
                    |
                    v
          +---------+----------+
          |   ActionResult     |
          |   ok=True/False    |
          |   meta.method =    |
          |     SELECTOR /     |
          |     COORDINATE /   |
          |     VISION         |
          |   data =           |
          |     ClickResult /  |
          |     FillResult /   |
          |     CascadeResult  |
          +--------------------+


    Tier 2 Coordinate Resolution Detail:

    Target String
         |
         v
    +----+----+----+----+
    | starts   | starts  | CSS     |
    | with @   | with // | selector|
    | (AX ref) | (XPath) |         |
    +----+----+----+----+---------+
         |         |              |
         v         v              v
    AXSnapshot  CDP Runtime.   CDP DOM.
    .resolve()  evaluate()     getBoxModel
         |         |              |
         v         v              v
    bounds.center  bounding      bounding
                   rect center   box center
         |         |              |
         +----+----+--------------+
              |
              v
    CDPBridge.compositor_click(x, y)
              |
              v
    Input.dispatchMouseEvent
      type=mousePressed
    Input.dispatchMouseEvent
      type=mouseReleased


    Tier 3 Vision Detail:

    CDPBridge.capture_screenshot()
              |
              v
    VisionProvider.locate(
      VisionRequest(
        screenshot=<PNG>,
        element_description=<text>,
        viewport_size=(W, H)))
              |
              v
    LLM (Anthropic/OpenAI/Google)
    "Find '{description}' and return
     pixel coordinates as {x, y}"
              |
              v
    VisionResponse(
      found=True,
      x=450, y=320,
      confidence=0.95)
              |
              v
    CDPBridge.compositor_click(450, 320)
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| GAP-01: `CDPBridge` | Spec complete | `compositor_click()`, `compositor_type()`, `compositor_key_press()`, `capture_screenshot()`, `send()`, `evaluate()` for Tier 2/3 operations |
| GAP-01: `PageHandle` | Spec complete | Patchright-native `page.click()`, `page.fill()`, `page.hover()` for Tier 1 operations |
| GAP-12: `ActionResult` | Spec complete | `ActionResult`, `ResultMeta`, `ActionError`, `ActionMethod`, `ClickResult`, `FillResult`, `timed_action_result()` as the return envelope |
| `patchright` | >= 1.0 | Stealth browser with native page interaction methods |
| Python | >= 3.11 | `asyncio.TaskGroup`, `typing.Self`, `enum.StrEnum` |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| Vision LLM API (Anthropic/OpenAI) | Tier 3 vision-based element location | Tier 3 unavailable, cascade stops at Tier 2 |
| `anthropic` SDK | Default Tier 3 vision provider | Use OpenAI provider or disable Tier 3 |
| `openai` SDK | Alternative Tier 3 vision provider | Use Anthropic provider or disable Tier 3 |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-02 |
|-----|--------------------------|
| GAP-03 (Visual Verification) | `CascadeResult` with before/after state, `capture_ax_snapshot()` for structural diff, two-phase act hook for verification injection |
| GAP-04 (Self-Healing & Session Recovery) | `TierAttempt` records for failure analysis, tier preference cache as a recovery hint source, cascade retry logic as the self-healing mechanism |
| GAP-05 (Domain Skill Registry) | Tier preference cache entries as domain knowledge, `@agent_action` methods as the skill execution targets, AX snapshot ref IDs as stable selectors |
| GAP-06 (Vision-Based Element Location) | `VisionProvider` interface, `VisionProviderFactory`, `VisionRequest`/`VisionResponse` dataclasses as the vision abstraction layer |
| GAP-07 (Agent Orchestration & Facade) | `@agent_action` decorated methods as the tool API, `build_action_api_description()` for dynamic tool registration, `MultimodalController` as the core tool implementation |

---

## 7. Acceptance Criteria

### AC1: Tier 1 Selector Click
Given a page with a `<button id="submit">Submit</button>`, calling `controller.click("#submit")` must succeed via Tier 1 (Patchright native), returning `ActionResult(ok=True, meta.method=SELECTOR)` with `ClickResult(target="#submit", method=ActionMethod.SELECTOR)`. The action must complete in under 100 ms.

### AC2: Tier 1 to Tier 2 Fallback on Shadow DOM
Given a page with a shadow DOM element that cannot be reached by CSS selector, calling `controller.click("button.inside-shadow")` must fail at Tier 1 (selector not found), automatically fall back to Tier 2 (resolve via CDP `DOM.getBoxModel` if accessible, or via AX snapshot ref resolution), and succeed via coordinate click. The result must have `meta.method=COORDINATE`.

### AC3: Tier 2 to Tier 3 Fallback on Canvas Element
Given a page with a canvas element that has no DOM representation, calling `controller.click("blue pen tool", description="the pen icon in the drawing toolbar")` must fail at Tier 1 (no selector match), fail at Tier 2 (no bounding box), succeed at Tier 3 (vision LLM identifies the canvas element and returns coordinates). The result must have `meta.method=VISION` and `meta.token_cost > 0`.

### AC4: Tier 2 Coordinate Click Bypasses Iframes
Given a page with a cross-origin iframe containing a button, calling `controller.click("button inside iframe")` must resolve coordinates via AX snapshot (which captures iframe contents) and dispatch a compositor click that bypasses the iframe boundary. The compositor click must reach the element without DOM traversal errors.

### AC5: Fill Action with Clear-First Behavior
Calling `controller.fill("#email", "user@example.com", clear_first=True)` on an input that already contains text must: (1) click the input to focus it, (2) dispatch Ctrl+A to select existing text, (3) type the new value character-by-character via compositor_type. The resulting `FillResult` must have `value_entered="user@example.com"` and `method=ActionMethod.SELECTOR` (if Tier 1 succeeded) or `ActionMethod.COORDINATE` (if Tier 2 was needed).

### AC6: Select Action on Dropdown
Calling `controller.select("#country", "United States", by="text")` on a `<select>` element must: (1) click the select to open it (Tier 1 or 2), (2) locate the option with text "United States" via AX snapshot or DOM query, (3) click the option. If the select is a custom dropdown (not a native `<select>`), the system must fall back to coordinate clicking the option.

### AC7: Drag Action with Intermediate Mouse Moves
Calling `controller.drag("#draggable", "#dropzone")` must: (1) resolve source coordinates, (2) resolve destination coordinates, (3) dispatch `mousePressed` at source, (4) dispatch `N` intermediate `mouseMoved` events between source and destination, (5) dispatch `mouseReleased` at destination. The `steps` parameter controls the number of intermediate events (default 5).

### AC8: Hover Action via Compositor
Calling `controller.hover("#menu-item")` must dispatch a `mouseMoved` event at the element's center coordinates. For Tier 2, this uses `CDPBridge.send("Input.dispatchMouseEvent", type="mouseMoved", x=..., y=...)`. The result records which tier resolved the coordinates.

### AC9: AX Snapshot with Ref-Based Targeting
Calling `controller.capture_ax_snapshot()` must return an `AXSnapshot` containing all interactive elements from the page, each with a stable `@eN` ref ID and bounding box. Calling `controller.click("@e3")` must resolve `@e3` to its coordinates from the snapshot and click at that location. The snapshot must be capturable in under 500 ms.

### AC10: Tier Preference Cache -- Success Recording
After `controller.click("button.login")` succeeds via Tier 2 on `github.com`, the `TierPreferenceCache` must contain an entry for domain `github.com` with selector pattern matching `button.*` and `preferred_tier=Tier.COORDINATE`. On the next call to `controller.click("button.signup")` on `github.com`, the system must attempt Tier 2 first (skipping Tier 1), and the cache lookup must complete in under 1 ms.

### AC11: Tier Preference Cache -- Failure Demotion
When a cached preference for Tier 2 on `github.com` with pattern `button.*` fails (element moved, page changed), the system must: (1) record the failure, (2) decrement the confidence score, (3) fall back to the next tier, (4) if confidence drops below 0.3 after repeated failures, remove the entry so the next action re-explores all tiers.

### AC12: Tier Preference Cache -- Persistence
After recording 10+ preferences for `github.com`, the cache must be persisted to `~/.super-browser/tier-cache/github.com.json` as valid JSON. After restarting the controller and calling `cache.load("github.com")`, the previously recorded preferences must be available. The file write must not block any action execution.

### AC13: Tier Preference Cache -- LRU Eviction
When a domain accumulates more than 1000 cache entries, the least recently used entries must be evicted to maintain the limit. After eviction, `len(cache._domains[domain])` must equal exactly 1000, and the evicted entries must be the ones with the oldest `last_used` timestamps.

### AC14: @agent_action Decorator and Dynamic API Description
All seven action methods (`click`, `fill`, `select`, `hover`, `drag`, `scroll`, `keypress`) on `MultimodalController` must be decorated with `@agent_action`. Calling `build_action_api_description(controller)` must return a string containing the exact function signatures and docstrings of all seven methods. The introspection must run once at construction time, not per action call.

### AC15: Cascade Timeout Enforcement
Tier 1 actions must time out after 5 seconds, Tier 2 after 3 seconds, Tier 3 after 15 seconds (configurable). When a tier times out, the cascade must proceed to the next tier without raising an exception. The `TierAttempt` for the timed-out tier must have `outcome=FAILED` and `error` containing "timeout".

### AC16: Complete Cascade Failure
When all three tiers fail for an action, the `ActionResult` must have `ok=False` with `error.category=SELECTOR_NOT_FOUND` (or the relevant error category), and `CascadeResult.succeeded_tier` must be `None`. The error must include a summary of all three tier attempts and their failure reasons. No exception must propagate to the caller.

### AC17: Keypress Action (Tier 2 Only)
Calling `controller.keypress("Enter")` must dispatch a key event via `CDPBridge.compositor_key_press("Enter")` directly, without any cascade. Calling `controller.keypress("c", modifiers=2)` must dispatch Ctrl+C. The result must have `meta.method=COORDINATE`.

### Test Scenarios

| ID  | Scenario | Steps | Expected Outcome | AC |
|-----|----------|-------|------------------|----|
| T1  | Tier 1 click on simple button | Navigate to example.com, `controller.click("a")` | `ActionResult(ok=True, meta.method=SELECTOR)`, page navigates | AC1 |
| T2  | Shadow DOM fallback to Tier 2 | Navigate to a shadow DOM test page, click button inside shadow root | Tier 1 fails, Tier 2 succeeds, `meta.method=COORDINATE` | AC2 |
| T3  | Canvas element via Tier 3 | Navigate to canvas page, `controller.click("pen tool", description="drawing pen icon")` | Tier 1/2 fail, Tier 3 vision succeeds, `meta.method=VISION`, `token_cost > 0` | AC3 |
| T4  | Cross-origin iframe click | Navigate to page with cross-origin iframe, click button inside iframe | Compositor click reaches element, no DOM traversal error | AC4 |
| T5  | Fill with clear-first | Fill input with "old", then `controller.fill(selector, "new", clear_first=True)` | Input contains "new", `method=SELECTOR`, `clear_first=True` in result | AC5 |
| T6  | Select dropdown option | Navigate to page with `<select>`, `controller.select("#sel", "Option B")` | Option B selected, Tier 1 or 2 succeeds | AC6 |
| T7  | Drag and drop | Navigate to page with drag-and-drop, `controller.drag("#src", "#dst")` | Element moved from source to destination | AC7 |
| T8  | Hover triggers tooltip | `controller.hover("#tooltip-trigger")` | Tooltip appears, `mouseMoved` dispatched at correct coords | AC8 |
| T9  | AX snapshot capture and ref resolution | `snapshot = controller.capture_ax_snapshot()`, then `controller.click("@e0")` | Snapshot has refs, click at ref center succeeds | AC9 |
| T10 | Cache records Tier 2 preference | Click "button.login" on github.com (Tier 2), check cache | Cache has entry for github.com, `preferred_tier=COORDINATE` | AC10 |
| T11 | Cache preference accelerates next action | After T10, click "button.signup" on github.com | Tier 2 attempted first (skips Tier 1), cache lookup < 1ms | AC10 |
| T12 | Cache failure demotion | Force Tier 2 failure 5 times on cached entry | Confidence drops below 0.3, entry removed, next action re-explores | AC11 |
| T13 | Cache persistence and reload | Record preferences, persist, restart controller, load | Preferences available after restart, file is valid JSON | AC12 |
| T14 | Cache LRU eviction at 1001 entries | Insert 1001 entries for a single domain | Eviction to 1000, oldest entries removed | AC13 |
| T15 | @agent_action API description | `build_action_api_description(controller)` | String contains all 7 method signatures and docstrings | AC14 |
| T16 | Tier 1 timeout triggers fallback | Set Tier 1 timeout to 0.001s, click a slow element | Tier 1 times out, Tier 2 succeeds | AC15 |
| T17 | All tiers fail | Navigate to blank page, click non-existent element | `ok=False`, `succeeded_tier=None`, error summarizes all attempts | AC16 |
| T18 | Keypress dispatches without cascade | `controller.keypress("Enter")` | Direct CDP dispatch, `meta.method=COORDINATE`, no cascade | AC17 |
| T19 | Live test: example.com click | Navigate to example.com, click "More information..." link | Page navigates to iana.org, `ok=True` | AC1 |
| T20 | Live test: threads.net shadow DOM | Navigate to threads.net, interact with shadow DOM element | Tier 2 compositor click succeeds | AC2 |

---

## 8. Novel Work

**Tier Preference Cache with Automatic Tier Selection and Domain-Level Persistence**

No reference project implements the full three-tier cascade with automatic tier selection and domain-level preference caching. The individual tiers exist: agent-browser has AX snapshots (Tier 1), browser-harness has compositor clicks (Tier 2), Stagehand/Agent-S/Skyvern have vision approaches (Tier 3). Stagehand has an ActCache for caching actions, but it caches selectors and actions, not tier preferences. No project learns over time which tier works best for a given domain/element-type combination.

The novel design:

1. **Cache Key**: `SHA-256(domain + selector_pattern)` where `selector_pattern` generalizes specific selectors into patterns (e.g., `button.login-btn` becomes `button.*`, `#submit-abc123` becomes `#submit-*`, `@e5` becomes `@ref`). This generalization enables cross-element learning -- if coordinate clicks work for one button on github.com, they likely work for all buttons on github.com.

2. **Confidence Scoring**: Each cache entry has a `confidence` float (0.0-1.0) that increases with successes (+0.1) and decreases with failures (-0.3). The asymmetric penalties reflect that failures are more informative than successes. When confidence drops below 0.3, the entry is removed entirely, forcing re-exploration.

3. **Domain Isolation**: Each domain maintains its own cache file at `~/.super-browser/tier-cache/{domain}.json`. This prevents cross-domain pollution -- aggressive learning on a shadow-DOM-heavy site does not affect a simpler site that works perfectly with Tier 1.

4. **LRU Eviction**: Each domain is capped at 1000 entries. When the cap is exceeded, the least recently used entries (oldest `last_used` timestamp) are evicted. This bounds disk usage and keeps the cache focused on actively used patterns.

5. **Async Persistence**: Cache writes are non-blocking. The `persist()` method runs via `asyncio.to_thread()` so disk I/O never blocks an action. Cache reads are in-memory after the initial load, adding under 1 ms per action.

6. **Preference Skipping**: When a cache hit occurs, the preferred tier is attempted first, potentially skipping cheaper tiers. This is a deliberate trade-off: if Tier 2 always works on `github.com`, attempting Tier 1 first wastes time on an inevitable failure. The confidence score prevents premature optimization -- a preference must earn at least 2 consecutive successes before it causes tier skipping.

---

## 9. Adoption Timeline

| Week | Deliverable | Source Pattern |
|------|-------------|----------------|
| 2 | `MultimodalController` with `click()`, `fill()`, `keypress()` Tier 1 (Patchright native) | P6 |
| 2 | AX snapshot capture via `Accessibility.getFullAXTree` with ref-based targeting | P1 |
| 3 | `@agent_action` decorator and `build_action_api_description()` | P6 |
| 3 | Tier 2 fallback: coordinate resolution + `CDPBridge.compositor_click()` | P4, P5 |
| 3 | `select()`, `hover()`, `drag()`, `scroll()` action methods | P4 |
| 4 | Tier 3 fallback: screenshot -> vision LLM -> compositor click | P7, P8, P9 |
| 4 | Two-phase act pattern (snapshot -> act -> diff snapshot) | P3 |
| 4 | 3-strategy browser control: hybrid mode alongside cascade | P11 |
| 4 | `VisionProvider` interface and `VisionProviderFactory` | P8 |
| 4 | Hybrid DOM+AX snapshot (Stagehand 5-phase) for complex pages | P2 |
| 5 | `TierPreferenceCache` with LRU eviction and domain persistence | P10 + Novel |
| 5 | Cache-driven tier skipping with confidence scoring | Novel |
| 5 | Operator type system: normalized coordinates + referenceBox on results | P12 |
| 5 | End-to-end live tests against example.com, threads.net, canvas pages | All |
