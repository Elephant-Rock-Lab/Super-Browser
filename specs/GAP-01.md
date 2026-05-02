# GAP-01: Browser Session & CDP Integration

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap          | #1                                                           |
| Title        | Browser Session & CDP Integration                            |
| Phase        | 0 (Foundation)                                               |
| Status       | Spec Complete                                                 |
| Depends-On   | None (parallel with GAP-12)                                  |
| Enables      | GAP-02, GAP-08, GAP-11                                       |
| Build Order  | Week 1-3                                                     |

---

## 1. Problem

Super Browser requires a persistent, stealth-compatible CDP connection to a browser instance, but no single reference project provides both the anti-detection guarantees Patchright delivers and the raw CDP session management needed for compositor-level interaction. Without a unified session layer, every higher-level component (three-tier engine, visual verifier, domain skills) would need to independently manage browser connections, leading to inconsistent state and resource leaks.

The session layer must launch Patchright (not vanilla Playwright), open a raw CDP session alongside it via `context.new_cdp_session(page)`, support both Unix-socket daemon IPC and direct CDP WebSocket transports, and provide automatic recovery when sessions go stale or the browser process crashes.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                          |
|-------|----------------------------------------------------------------------------------------------------------------------|
| R1    | Launch a Patchright browser instance with stealth CLI switches (no `--enable-automation`, no `Runtime.enable`)       |
| R2    | Create a raw CDP session bridge via `context.new_cdp_session(page)` for compositor-level operations                 |
| R3    | Expose CDP protocol methods: `compositor_click()`, `compositor_type()`, `capture_screenshot()`, `evaluate()`        |
| R4    | Discover existing browser instances via DevToolsActivePort scanning (22+ profile paths across macOS/Linux/Windows)   |
| R5    | Support Unix domain socket IPC in daemon mode for one-shot JSON-line CDP passthrough                                |
| R6    | Multiplex concurrent CDP sessions with an inflight request map (correlate responses by message ID)                  |
| R7    | Handle OOPIF (Out-of-Process Iframe) session adoption via `Target.attachedToTarget` events                         |
| R8    | Auto-recover from stale sessions (detect "Session with given id not found", re-attach, retry)                       |
| R9    | Two-phase browser process cleanup: SIGTERM, wait up to 7s, then SIGKILL                                             |
| R10   | Buffer CDP events in a bounded deque (max 500) with tap-based interception for dialog detection                     |
| R11   | Validate end-to-end with: `python -c "from src.super_browser.browser.session import BrowserSession; ..."`           |

### Non-Functional

| ID    | Requirement                                                                                                         |
|-------|---------------------------------------------------------------------------------------------------------------------|
| NFR1  | Session establishment latency under 3 seconds for local browser, under 10 seconds for discovered browser            |
| NFR2  | Zero CDP leaks: no `Runtime.enable`, no automation flags in navigator properties                                   |
| NFR3  | Event buffer bounded at 500 entries to prevent unbounded memory growth in long sessions                            |
| NFR4  | Thread-safe session map for concurrent page operations via `asyncio.Lock`                                           |
| NFR5  | Graceful degradation: if CDP session drops mid-operation, operation returns structured error, does not hang         |

### Out of Scope

- Multi-backend browser provisioning (Browserbase, Camofox) -- deferred to GAP-08
- Network idle detection across sessions -- deferred to GAP-02 (interaction engine)
- Screenshot comparison / visual hashing -- deferred to GAP-03 (visual verification)
- LLM-based element location or action decisions -- deferred to GAP-02

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | CDP Daemon with Unix Socket IPC | browser-harness `daemon.py` (252 lines) | 4.50 | Low | Bootstrap transport |
| P2 | DevToolsActivePort Browser Discovery | browser-harness `daemon.py:61-85` | 3.15 | Low | Find running Chrome instances |
| P3 | CDP Session Multiplexing ("Understudy") | Stagehand `cdp.ts` (541 lines) | 4.80 | Medium | Production transport |
| P4 | OOPIF Session Adoption | Stagehand `page.ts`, `frameRegistry.ts` | 4.50 | High | Cross-origin iframe handling |
| P5 | Compositor-Level Click Primitives | browser-harness `helpers.py:70-72` | 3.95 | Low | Raw mouse dispatch |
| P6 | Key Dispatch with Virtual Key Codes | browser-harness `helpers.py:77-94` | 3.35 | Low | Keyboard event sequences |
| P7 | Event Buffering via Handler Tap | browser-harness `daemon.py:148-166` | 3.35 | Low | CDP event capture |
| P8 | Stale Session Auto-Recovery | browser-harness `daemon.py:183-191` | 3.45 | Low | Session resilience |
| P9 | Two-Phase Shutdown Supervisor | Stagehand `supervisor.ts` | 2.95 | Low | Process cleanup |
| P10 | Multi-Backend Browser Abstraction | Hermes `browser_tool.py`, `browser_providers/` | 4.20 | Medium | Provider interface |
| P11 | Patchright Stealth Launch | Patchright (adopted as dependency) | 4.55 | Low | Anti-detection browser |

### Per-Pattern Adoption Notes

**P1 -- CDP Daemon with Unix Socket IPC (browser-harness)**
Adopt the single-process asyncio daemon architecture. The daemon holds a persistent CDP WebSocket, listens on a Unix domain socket (or named pipe on Windows) for one-shot JSON-line requests, and routes them to the browser. Each request is either a CDP passthrough (`method` + `params`) or a meta command (`drain_events`, `pending_dialog`). Port the 252-line `daemon.py` structure directly. Replace the `cdp-use` dependency with Patchright's built-in CDP session capability.

**P2 -- DevToolsActivePort Browser Discovery (browser-harness)**
Adopt the profile path scanning logic. The original scans 22 paths across macOS, Linux, and Windows, reading `DevToolsActivePort` from each Chrome user profile directory. The discovery function returns a WebSocket URL (`ws://127.0.0.1:{port}{path}`). Add a 30-second polling loop with configurable interval for cases where Chrome is still starting. Fall back to `BU_CDP_WS` environment variable for explicit WebSocket URL override.

**P3 -- CDP Session Multiplexing (Stagehand "Understudy")**
Adopt the inflight request map pattern from Stagehand's `CdpConnection`. The map tracks every pending CDP call with its `asyncio.Future` resolve/reject, session ID, method, params, and timestamp. Route CDP responses by message `id`, unsolicited events by `sessionId`. This pattern is essential for concurrent operations on multiple pages and will be the production transport after the initial bootstrap with P1.

**P4 -- OOPIF Session Adoption (Stagehand)**
Adopt the OOPIF handling pattern: when `Target.attachedToTarget` fires for a cross-origin iframe, automatically create a child `CDPSession` object, register it in the session map, apply init scripts, and bridge events from child to parent. This is required for real-world sites that embed third-party content in iframes (payment forms, social widgets, ad frames).

**P5 -- Compositor-Level Click Primitives (browser-harness)**
Adopt the two-line compositor click: `Input.dispatchMouseEvent` with `mousePressed` followed by `mouseReleased` at exact viewport coordinates. These clicks operate at the compositor level, passing through shadow DOM, cross-origin iframes, and all DOM layers without traversal. The recommended workflow is screenshot, identify coordinates, click, screenshot to verify.

**P6 -- Key Dispatch with Virtual Key Codes (browser-harness)**
Adopt the proper keyDown/char/keyUp event sequence with virtual key code mapping for 15+ special keys. Include modifier bitmask support for Shift/Ctrl/Alt combinations. Missing the `char` event or using incorrect virtual key codes breaks text input on many sites.

**P7 -- Event Buffering via Handler Tap (browser-harness)**
Adopt the bounded deque (maxlen=500) with monkey-patched event handler for CDP event interception. Track special events: `Page.javascriptDialogOpening`/`Closed` for dialog state, `Page.loadEventFired`/`domContentEventFired` for page load tracking. Events drained on demand via `drain_events` meta command.

**P8 -- Stale Session Auto-Recovery (browser-harness)**
Adopt the detection-and-retry pattern: when a CDP call raises "Session with given id not found", automatically re-attach to the first available page target and retry the call. Add `ensure_real_tab()` to detect and switch away from `chrome://` internal pages.

**P9 -- Two-Phase Shutdown Supervisor (Stagehand)**
Adopt the out-of-process cleanup supervisor. Watch a lifeline (stdin pipe or event) from the parent process. On close or explicit signal, send SIGTERM to the browser process, wait up to 7 seconds, then escalate to SIGKILL. Poll the browser PID in a background loop to detect unexpected browser death.

**P10 -- Multi-Backend Browser Abstraction (Hermes)**
Adopt the provider interface pattern: an abstract `BrowserProvider` with concrete implementations for `LocalPatchrightProvider`, `BrowserbaseProvider`, and `CamofoxProvider`. The interface hides browser launch details behind a common `create_session()` method. This is the architectural hook for GAP-08 (Stealth & Anti-Bot Layer) to add cloud and alternative-browser providers.

**P11 -- Patchright Stealth Launch (Patchright)**
Adopt Patchright as a direct dependency (not reimplemented). The `patchright` Python package is a drop-in Playwright replacement that eliminates `Runtime.enable`, sanitizes CLI switches, and patches CDP leaks at the AST level. Launch with `patchright.async_api.async_playwright()` instead of `playwright.async_api.async_playwright()`. All 30 anti-detection patches come for free.

---

## 4. Interface Contract

### Dataclasses

```python
from __future__ import annotations

import asyncio
import enum
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SessionConfig:
    """Immutable configuration for a BrowserSession."""

    # Launch mode
    mode: SessionMode = SessionMode.PATCHRIGHT_LAUNCH  # launch fresh or attach
    headless: bool = False

    # Patchright launch options
    executable_path: Optional[str] = None        # explicit Chrome path
    chrome_args: tuple[str, ...] = ()             # extra CLI args
    user_data_dir: Optional[str] = None           # persistent profile
    proxy: Optional[str] = None                   # proxy URL

    # DevToolsActivePort discovery (mode = DISCOVER or DAEMON)
    discovery_timeout: float = 30.0               # seconds to poll
    discovery_interval: float = 0.5               # seconds between polls
    cdp_ws_url: Optional[str] = None              # explicit override (env var)

    # Daemon mode
    daemon_socket_path: Optional[str] = None      # Unix socket / named pipe
    daemon_request_timeout: float = 30.0          # per-request timeout

    # Session behaviour
    stale_recovery: bool = True                   # auto-recover stale sessions
    event_buffer_size: int = 500                  # max buffered CDP events
    shutdown_grace_period: float = 7.0            # SIGTERM grace before SIGKILL

    # Stealth
    disable_runtime_enable: bool = True           # Patchright handles this
    sanitize_switches: bool = True                # remove fingerprint-able switches


class SessionMode(enum.Enum):
    PATCHRIGHT_LAUNCH = "patchright_launch"       # launch new Patchright browser
    PATCHRIGHT_ATTACH = "patchright_attach"       # attach to running browser
    DISCOVER = "discover"                         # DevToolsActivePort scan
    DAEMON = "daemon"                             # daemon with Unix socket IPC


# ---------------------------------------------------------------------------
# Runtime state
# ---------------------------------------------------------------------------

@dataclass
class BrowserState:
    """Mutable snapshot of browser session state."""

    connected: bool = False
    browser_pid: Optional[int] = None
    browser_version: Optional[str] = None
    ws_url: Optional[str] = None                  # CDP WebSocket URL
    session_id: Optional[str] = None              # active CDP session ID
    page_url: Optional[str] = None                # current page URL
    page_title: Optional[str] = None              # current page title

    # Session timing
    connected_at: float = 0.0                     # monotonic timestamp
    last_activity_at: float = 0.0                 # monotonic timestamp

    # Recovery counters
    stale_recoveries: int = 0
    reattachment_count: int = 0

    # Dialog state (from event tap)
    pending_dialog: Optional[dict] = None         # Page.javascriptDialogOpening params

    def uptime(self) -> float:
        return time.monotonic() - self.connected_at if self.connected_at else 0.0


@dataclass
class CDPSession:
    """Represents a single CDP session (page or OOPIF target)."""

    session_id: str
    target_id: str
    target_type: str                              # "page", "iframe", "worker", etc.
    parent_session_id: Optional[str] = None       # None for root, set for OOPIF
    created_at: float = field(default_factory=time.monotonic)

    # Inflight request tracking
    _inflight: dict[int, CDPRequest] = field(default_factory=dict)
    _next_id: int = 0

    def allocate_id(self) -> int:
        self._next_id += 1
        return self._next_id

    @property
    def inflight_count(self) -> int:
        return len(self._inflight)


@dataclass
class CDPRequest:
    """Tracks a single in-flight CDP method call."""

    message_id: int
    method: str
    params: dict[str, Any]
    session_id: str
    future: asyncio.Future
    created_at: float = field(default_factory=time.monotonic)

    @property
    def age(self) -> float:
        return time.monotonic() - self.created_at


# ---------------------------------------------------------------------------
# Results
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CDPResult:
    """Structured result from any CDP operation."""

    ok: bool
    data: Optional[dict[str, Any]] = None
    error: Optional[str] = None
    method: Optional[str] = None                  # which CDP method was used
    duration_ms: float = 0.0
    screenshot_hash: Optional[str] = None         # SHA-256 of screenshot, if captured


@dataclass(frozen=True)
class ScreenshotResult:
    """Result from capture_screenshot()."""

    ok: bool
    data: bytes                                   # PNG image data
    width: int
    height: int
    mime_type: str = "image/png"
    duration_ms: float = 0.0
    sha256: str = ""


@dataclass(frozen=True)
class DiscoveryResult:
    """Result from DevToolsActivePort browser discovery."""

    found: bool
    ws_url: Optional[str] = None
    profile_path: Optional[str] = None
    browser_pid: Optional[int] = None
    attempted_paths: int = 0
    discovery_time_ms: float = 0.0
```

### Classes and Signatures

```python
class BrowserSession:
    """
    Top-level session manager. Launches Patchright, creates CDP bridge,
    manages lifecycle, and provides the entry point for all browser operations.

    Usage:
        session = BrowserSession(SessionConfig())
        await session.start()
        page = await session.new_page()
        await page.goto("https://example.com")
        # ... interact ...
        await session.stop()
    """

    def __init__(self, config: SessionConfig) -> None: ...

    # -- Lifecycle --------------------------------------------------------

    async def start(self) -> BrowserState:
        """Launch or attach to browser. Returns initial state snapshot."""
        ...

    async def stop(self) -> None:
        """Graceful shutdown: close pages, terminate browser, cleanup."""
        ...

    async def __aenter__(self) -> BrowserSession: ...
    async def __aexit__(self, *exc) -> None: ...

    # -- Page management --------------------------------------------------

    async def new_page(self) -> PageHandle:
        """Create a new browser page and return a handle."""
        ...

    async def get_pages(self) -> list[PageHandle]:
        """List all open pages."""
        ...

    # -- State inspection -------------------------------------------------

    def state(self) -> BrowserState:
        """Return current browser state snapshot."""
        ...

    def cdp(self) -> CDPBridge:
        """Return the CDP bridge for the active session."""
        ...


class PageHandle:
    """
    Wrapper around a Patchright Page with an associated CDPBridge.
    Provides Patchright-native methods + raw CDP access.
    """

    def __init__(self, page: Any, cdp_bridge: CDPBridge) -> None: ...

    # -- Patchright-native (Tier 1 operations) ----------------------------

    async def goto(self, url: str, *, wait_until: str = "domcontentloaded",
                   timeout: float = 30.0) -> CDPResult: ...

    async def title(self) -> str: ...

    async def url(self) -> str: ...

    async def close(self) -> None: ...

    # -- CDP bridge accessor ----------------------------------------------

    @property
    def cdp(self) -> CDPBridge:
        """Access the raw CDP bridge for this page."""
        ...


class CDPBridge:
    """
    Raw CDP protocol bridge. Created via context.new_cdp_session(page).
    Provides compositor-level operations that bypass the DOM entirely.
    """

    def __init__(self, cdp_session: Any, config: SessionConfig) -> None: ...

    # -- Compositor primitives --------------------------------------------

    async def compositor_click(self, x: float, y: float, *,
                               button: str = "left",
                               click_count: int = 1) -> CDPResult:
        """
        Dispatch mousePressed + mouseReleased at compositor level.
        Bypasses shadow DOM, iframes, and all DOM layers.
        """
        ...

    async def compositor_type(self, text: str, *,
                               delay_ms: int = 0) -> CDPResult:
        """
        Type text via CDP keyDown/char/keyUp event sequences.
        Maps special keys to virtual key codes.
        """
        ...

    async def compositor_key_press(self, key: str, *,
                                    modifiers: int = 0) -> CDPResult:
        """
        Press a single key (e.g., Enter, Tab, Escape) with optional
        modifiers (1=Alt, 2=Ctrl, 4=Shift, 8=Meta).
        """
        ...

    # -- Screenshot -------------------------------------------------------

    async def capture_screenshot(self, *,
                                  format: str = "png",
                                  quality: int = 80,
                                  clip: Optional[dict] = None,
                                  full_page: bool = False) -> ScreenshotResult:
        """
        Capture screenshot via CDP Page.captureScreenshot.
        Returns PNG bytes with dimensions and SHA-256 hash.
        """
        ...

    # -- JavaScript evaluation --------------------------------------------

    async def evaluate(self, expression: str, *,
                       return_by_value: bool = True) -> CDPResult:
        """
        Evaluate JavaScript in the page context via CDP Runtime.evaluate.
        Uses returnByValue for simple results, objectId for complex ones.
        """
        ...

    # -- Raw CDP passthrough ----------------------------------------------

    async def send(self, method: str, params: dict = None) -> CDPResult:
        """
        Send raw CDP command. Tracks in inflight map, resolves future.
        Auto-recovers from stale sessions if config.stale_recovery is True.
        """
        ...

    # -- Event management -------------------------------------------------

    async def drain_events(self) -> list[dict]:
        """Drain all buffered CDP events and return them."""
        ...

    def on_event(self, pattern: str, handler: callable) -> None:
        """Register handler for CDP events matching pattern (e.g. 'Page.*')."""
        ...

    # -- Session info -----------------------------------------------------

    @property
    def session_id(self) -> Optional[str]: ...

    @property
    def inflight_count(self) -> int: ...


class BrowserDiscovery:
    """
    Scans for running Chrome/Chromium instances via DevToolsActivePort.
    """

    # Platform-specific profile search paths
    PROFILE_PATHS: list[Path]  # 22+ paths across macOS/Linux/Windows

    @classmethod
    async def discover(cls, *,
                       timeout: float = 30.0,
                       interval: float = 0.5,
                       ws_url_override: Optional[str] = None) -> DiscoveryResult:
        """
        Scan DevToolsActivePort files in known profile directories.
        Returns the first valid WebSocket URL found, or the explicit
        override if provided.
        """
        ...


class ShutdownSupervisor:
    """
    Out-of-process browser cleanup. Two-phase kill:
    SIGTERM -> grace period -> SIGKILL.
    """

    def __init__(self, browser_pid: int, grace_period: float = 7.0) -> None: ...

    async def start(self, lifeline: asyncio.Event) -> None:
        """
        Start monitoring. When lifeline is cleared, initiate shutdown.
        Also polls PID to detect unexpected browser death.
        """
        ...

    async def force_shutdown(self) -> None:
        """Immediately send SIGKILL (or TerminateProcess on Windows)."""
        ...
```

---

## 5. Data Flow

```
                          +---------------------+
                          |   BrowserSession    |
                          | (lifecycle manager) |
                          +----------+----------+
                                     |
                          start() / stop()
                                     |
                    +----------------+----------------+
                    |                                 |
          +---------v----------+           +----------v---------+
          | Patchright Browser |           | BrowserDiscovery   |
          | (stealth launch)   |           | (DevToolsActivePort|
          |                    |           |  scanning)          |
          +--------+-----------+           +--------------------+
                   |
          context.new_cdp_session(page)
                   |
          +--------v-----------+
          |     CDPBridge      |
          | (raw CDP channel)  |
          +--------+-----------+
                   |
         +---------+---------+----------+
         |         |         |          |
         v         v         v          v
   compositor_  compositor_ capture_   send()
   click(x,y)  type(text)  screenshot (raw CDP)
         |         |         |          |
         v         v         v          v
   +-----------------------------------------------+
   |           CDP WebSocket (single)              |
   |   inflight: Map<id, Future>                   |
   |   events: deque<CDPEvent> (maxlen=500)        |
   +-----------------------------------------------+
         |                                 |
         v                                 v
   +------------+              +---------------------+
   | Browser    |              | OOPIF Sessions      |
   | Response   |              | (Target.attachedTo  |
   | Routing    |              |  Target children)   |
   +------------+              +---------------------+

   Daemon Mode Alternative:

   External  --->  Unix Socket   --->  Daemon  --->  CDP WebSocket  --->  Browser
   Client          (/tmp/sb.sock)       Process       (persistent)          |
                                                          <----------------+
                                                          auto-recovery on
                                                          stale session
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| `patchright` | >= 1.0 | Stealth browser (Playwright fork with 30 anti-detection patches) |
| Python | >= 3.11 | Required for `asyncio.TaskGroup`, `typing.Self`, native `dataclass` slots |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| `websockets` | Direct CDP WebSocket for daemon mode | Patchright's built-in CDP session |
| `psutil` | Cross-platform PID polling in shutdown supervisor | `os.kill` + signal handling |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-01 |
|-----|--------------------------|
| GAP-02 (Three-Tier Interaction Engine) | `CDPBridge.compositor_click()`, `CDPBridge.capture_screenshot()`, `CDPBridge.evaluate()` |
| GAP-08 (Stealth & Anti-Bot Layer) | Patchright launch with stealth config, `SessionConfig.proxy`, `BrowserProvider` abstraction |
| GAP-11 (Tracing & Observability) | `drain_events()`, inflight request tracking, event buffer tap |

---

## 7. Acceptance Criteria

### AC1: Patchright Launch with Stealth Configuration
The `BrowserSession` shall launch a Patchright browser instance with no `--enable-automation` flag, no `Runtime.enable` CDP call, and sanitized CLI switches. After launch, `navigator.webdriver` evaluated in the page context must return `undefined` or `false`.

### AC2: CDP Session Bridge Creation
After `session.start()`, calling `session.new_page()` must return a `PageHandle` whose `.cdp` property yields a `CDPBridge` with a valid `session_id`. The CDP session must be created via Patchright's `context.new_cdp_session(page)` -- no separate browser launch.

### AC3: Compositor Click at Specified Coordinates
`cdp.compositor_click(100, 200)` must dispatch `Input.dispatchMouseEvent` with type `mousePressed` at (100, 200) followed by type `mouseReleased` at (100, 200). The `CDPResult` must have `ok=True` and `method="compositor_click"`.

### AC4: Compositor Type with Key Sequence
`cdp.compositor_type("Hello")` must dispatch `keyDown`/`char`/`keyUp` event sequences for each character. `cdp.compositor_key_press("Enter")` must dispatch the correct virtual key code with `keyDown`/`keyUp`.

### AC5: Screenshot Capture with Hash
`cdp.capture_screenshot()` must return a `ScreenshotResult` with `ok=True`, non-empty PNG `data`, correct `width`/`height`, and a `sha256` hash matching the bytes. The operation must complete within 5 seconds on a local browser.

### AC6: DevToolsActivePort Browser Discovery
`BrowserDiscovery.discover()` must scan at least 22 profile paths across macOS, Linux, and Windows. When Chrome is running with a debug port, it must return a valid WebSocket URL within the configured timeout. When no browser is found, it must return `DiscoveryResult(found=False)` without raising.

### AC7: Stale Session Auto-Recovery
When a CDP session becomes stale (browser navigated away, tab replaced), calling `cdp.send()` must detect the "Session with given id not found" error, automatically re-attach to an available page target, retry the original command, and return the result. `BrowserState.stale_recoveries` must increment.

### AC8: Two-Phase Shutdown
`ShutdownSupervisor` must send SIGTERM (or `TerminateProcess` on Windows), wait up to `grace_period` seconds, then escalate to SIGKILL (or forced termination) if the process has not exited. After `session.stop()`, the browser PID must not exist.

### AC9: Event Buffering and Drain
CDP events must be buffered in a bounded deque. After navigating to a page that triggers `Page.javascriptDialogOpening`, `cdp.drain_events()` must return the dialog event. After 501+ events, the buffer must not exceed 500 entries (oldest discarded).

### AC10: Session Multiplexing with Inflight Map
When two concurrent `cdp.send()` calls are in flight, each must receive its own response (correlated by message ID). Neither call may resolve with the other's response. `CDPSession.inflight_count` must reflect the number of pending calls.

### Test Scenarios

| ID | Scenario | Steps | Expected Outcome |
|----|----------|-------|------------------|
| T1 | Fresh launch and navigate | `session.start()`, `page.goto("https://example.com")`, `page.title()` | Returns "Example Domain", state.connected is True |
| T2 | Compositor click on known element | Navigate to example.com, get bounding box of link, `cdp.compositor_click(x, y)` | Click registers, page navigates to `https://www.iana.org/...` |
| T3 | Screenshot round-trip | `cdp.capture_screenshot()`, verify PNG header bytes (`\x89PNG`) | ScreenshotResult.ok is True, data starts with PNG magic |
| T4 | Browser discovery with running Chrome | Start Chrome with `--remote-debugging-port`, call `BrowserDiscovery.discover()` | DiscoveryResult.found is True, ws_url is valid WebSocket URL |
| T5 | Stale session recovery | Open page, manually invalidate session ID, call `cdp.send("Page.reload")` | Auto-recovers, returns CDPResult.ok=True, state.stale_recoveries increments |
| T6 | Shutdown cleanup | `session.start()`, record PID, `session.stop()`, check PID | PID no longer exists, no orphan Chrome processes |
| T7 | Event buffer overflow | Generate 600+ CDP events, `cdp.drain_events()` | Returns at most 500 events, no memory error |
| T8 | Concurrent CDP calls | Dispatch 10 concurrent `cdp.send("Runtime.evaluate", {expression: "1+1"})` | All 10 return CDPResult.ok=True with data.result.value=2 |
| T9 | Daemon mode IPC | Start in daemon mode, send JSON-line request via Unix socket | Receive JSON-line response with CDP result |
| T10 | Validation command | Run: `python -c "from src.super_browser.browser.session import BrowserSession; ..."` | Imports succeed, session starts, page navigates, title prints, session stops |

---

## 8. Novel Work

None. All patterns are adopted from reference sources:

- Daemon architecture: browser-harness (252 lines)
- Session multiplexing: Stagehand "Understudy" (541 lines)
- OOPIF handling: Stagehand page.ts + frameRegistry.ts
- Compositor clicks: browser-harness helpers.py (2 lines)
- Key dispatch: browser-harness helpers.py
- Browser discovery: browser-harness daemon.py
- Stale recovery: browser-harness daemon.py
- Shutdown supervisor: Stagehand supervisor.ts
- Multi-backend abstraction: Hermes browser_tool.py
- Stealth launch: Patchright (adopted as dependency)

The integration work is combining these proven patterns into a single coherent Python module, adapting the TypeScript CDP transport from Stagehand to Python asyncio, and threading Patchright's stealth guarantees through every layer.

---

## 9. Adoption Timeline

| Week | Deliverable | Source |
|------|-------------|--------|
| 1 | `BrowserSession` + `CDPBridge` with Patchright launch and `context.new_cdp_session(page)` | P11, P3 |
| 1 | `compositor_click()`, `compositor_type()`, `capture_screenshot()`, `evaluate()` | P5, P6 |
| 2 | `BrowserDiscovery` with DevToolsActivePort scanning (22 paths) | P2 |
| 2 | Event buffering with bounded deque and handler tap | P7 |
| 2 | `ShutdownSupervisor` with two-phase process cleanup | P9 |
| 3 | Inflight request map and session multiplexing | P3 |
| 3 | Stale session auto-recovery | P8 |
| 3 | OOPIF session adoption via `Target.attachedToTarget` | P4 |
| 3 | Daemon mode with Unix socket IPC | P1 |
| 3 | Multi-backend `BrowserProvider` abstraction (interface only) | P10 |
