# RFC: v2.0 Track C — Behavioral Realism

## Status

Implemented. See v2.0.0 release.

## Goal

Define the behavioral-realism layer for `v2.0-alpha.3`. This document
freezes the component contracts, config model, determinism guarantees,
and test strategy before any code is changed.

Track C builds on the **existing** behavioral synthesis engine
(`behavioral/mouse.py`, `behavioral/keyboard.py`, `behavioral/scroll.py`)
and the `HumanBehaviorAdapter` (`stealth/human.py`). These are already
functional — Track C adds the missing orchestration layer: dwell timing,
navigation variation, and unified session-level determinism.

---

## Non-goals

- No network stealth improvements (Track B — done).
- No challenge detection or solving (Track D).
- No E2E harness implementation (Track E).
- No default-CI real-browser calls.
- No claim of being "undetectable" — behavioral realism raises the
  cost of detection, it does not eliminate it.
- No replacement of the existing behavioral synthesis pipeline. The
  pure-data functions (`synthesize_mouse_trajectory`,
  `synthesize_keystrokes`, `synthesize_scroll`) are already sound.
  Track C wraps them with timing orchestration.

---

## Current state assessment

### What exists today

| Component | File | What it does | Limitations |
|:----------|:-----|:-------------|:------------|
| `synthesize_mouse_trajectory()` | `behavioral/mouse.py` | Cubic-Bézier mouse paths with overshoot, Fitts' Law timing, tremor jitter. | Pure data — no I/O. Returns `list[TrajectoryEvent]`. Already deterministic via `seed` param. |
| `synthesize_keystrokes()` | `behavioral/keyboard.py` | Realistic typing with digraph delays, mistake injection, WPM scaling. | Pure data. Returns `list[KeystrokeEvent]`. Already deterministic. |
| `synthesize_scroll()` | `behavioral/scroll.py` | Inertial scroll with exponential decay, frame-rate sampling. | Pure data. Returns `list[ScrollEvent]`. Already deterministic. |
| `HumanBehaviorAdapter` | `stealth/human.py` | Dispatches synthesized events to Patchright/CloakBrowser pages. Wraps the pure-data functions with CDP/page calls. | No dwell timing before/after actions. No navigation variation. No session-level seed propagation. |
| `HumanConfig` | `stealth/human_config.py` | Preset-based config with behavioral fields (hand, tremor, wpm, scroll_style). | Missing dwell-time, navigation-variation, and session-seed fields. |
| `BehaviorProfile` | `behavioral/types.py` | Frozen dataclass with 4 fields (hand, tremor, wpm, scroll_style). | Minimal — no dwell or navigation config. |
| `Fitts' Law` | `behavioral/fitts.py` | `fitts_mt(distance, width)` → movement time in ms. | Correct and tested. No changes needed. |
| `prng_for()` | `behavioral/prng.py` | Creates deterministic `random.Random` from string seed. | Correct. Session-level seed not yet wired. |

### What's already deterministic

The behavioral synthesis functions are **already fully deterministic**:
same `(options, seed)` → byte-identical event array. This is a core
design principle of the behavioral layer and is tested.

### What's missing (Track C scope)

1. **Dwell timing** — no pre-action or post-action delays between
   synthesized events. Actions fire immediately after each other.
2. **Navigation variation** — all navigations use direct `page.goto()`.
   No typing URLs into the address bar, no referral headers, no random
   navigation paths.
3. **Session-level seed propagation** — each action uses
   `_action_seed()` which includes `time.monotonic_ns()`, making
   sessions non-reproducible. A session seed should override this.
4. **Behavioral coordination** — no orchestrator that sequences
   actions with realistic gaps, reads content before acting, or varies
   interaction patterns across a session.

---

## Components

### 1. DwellTimer

**Purpose:** Add realistic pre-action and post-action delays between
browser interactions. Models human reading/thinking time.

**Design:**

```python
@dataclass(frozen=True)
class DwellConfig:
    """Configuration for action dwell timing."""
    # Pre-action: time spent "looking" before clicking/typing
    pre_action_min_ms: float = 200.0
    pre_action_max_ms: float = 1500.0

    # Post-action: time spent "reading" after an action completes
    post_action_min_ms: float = 300.0
    post_action_max_ms: float = 3000.0

    # Page-load dwell: time after navigation before interacting
    page_settle_ms: float = 800.0

    # Variability: 0.0 = uniform, 1.0 = high variance
    variability: float = 0.7

class DwellTimer:
    """Generates realistic dwell durations between actions."""

    def __init__(
        self,
        config: DwellConfig | None = None,
        rng: random.Random | None = None,
    ) -> None: ...

    def pre_action_delay(self, action_type: str) -> float:
        """Return pre-action delay in seconds. Action-aware."""

    def post_action_delay(self, action_type: str) -> float:
        """Return post-action delay in seconds."""

    def page_settle_delay(self) -> float:
        """Return delay after page load before interaction."""
```

**Action-aware timing:**

Different actions get different dwell distributions:

| Action | Pre-delay range | Post-delay range |
|:-------|:----------------|:-----------------|
| click | 200–1500 ms | 300–2000 ms |
| type | 300–1000 ms | 200–800 ms |
| scroll | 100–500 ms | 200–1500 ms |
| navigate | 0 ms | 800–3000 ms |

**Determinism:** `DwellTimer` accepts a `random.Random` instance.
Same seed → same dwell sequence. Without a seed, uses system entropy
(production default).

### 2. NavigationVariation

**Purpose:** Vary how the browser navigates between pages — not every
navigation should be a direct `goto()`. Humans sometimes click links,
sometimes type URLs, sometimes use back/forward.

**Design:**

```python
class NavigationStyle(StrEnum):
    DIRECT = "direct"              # page.goto(url)
    TYPE_AND_ENTER = "type_enter"  # type URL into address bar (simulated)
    CLICK_LINK = "click_link"      # find and click an <a> matching URL
    REFERRER = "referrer"          # navigate with Referer header set

@dataclass(frozen=True)
class NavigationConfig:
    """Configuration for navigation variation."""
    style_weights: dict[str, float] = field(default_factory=lambda: {
        "direct": 0.5,
        "type_enter": 0.15,
        "click_link": 0.20,
        "referrer": 0.15,
    })
    referrer_pool: tuple[str, ...] = (
        "https://www.google.com/",
        "https://duckduckgo.com/",
        "https://www.bing.com/",
    )
    type_url_delay_ms: tuple[float, float] = (50.0, 150.0)

class NavigationVariator:
    """Selects navigation style and generates variation parameters."""

    def __init__(
        self,
        config: NavigationConfig | None = None,
        rng: random.Random | None = None,
    ) -> None: ...

    def select_style(self) -> NavigationStyle:
        """Select a navigation style based on configured weights."""

    def pick_referrer(self) -> str:
        """Return a random referrer from the pool."""

    def type_delay(self) -> float:
        """Return inter-keystroke delay for URL typing simulation."""
```

**Honesty note:** `TYPE_AND_ENTER` and `CLICK_LINK` are **simulated** —
the SDK still uses `page.goto()` under the hood (it cannot control the
browser's address bar). The variation is in timing and headers, not
in the actual navigation mechanism. This is documented in the class
docstring.

### 3. SessionSeed

**Purpose:** Unify determinism across all behavioral components within
a single session. A session seed flows into the behavioral synthesis
functions, dwell timer, and navigation variator.

**Design:**

```python
class SessionSeed:
    """Manages per-session deterministic seeds for behavioral synthesis.

    Given a base session seed string, derives per-action seeds that are
    deterministic but unique per action.

    Usage::

        session = SessionSeed("my-session-123")
        mouse_seed = session.derive("click", "#submit-btn")
        # → "my-session-123:click:#submit-btn"
    """

    def __init__(self, base_seed: str = "") -> None:
        self._base = base_seed

    @property
    def is_deterministic(self) -> bool:
        """True if a base seed was set."""
        return bool(self._base)

    def derive(self, action_type: str, target: str = "") -> str:
        """Derive a deterministic seed for a specific action."""
        if not self._base:
            return ""  # Non-deterministic
        return f"{self._base}:{action_type}:{target}"

    def rng(self, action_type: str, target: str = "") -> random.Random:
        """Get a deterministic Random for an action."""
        return random.Random(self.derive(action_type, target))
```

**Integration with existing code:**

The current `HumanBehaviorAdapter._action_seed()` includes
`time.monotonic_ns()`. When a `SessionSeed` is set, it replaces the
timestamp-based seed with the deterministic derived seed. When no
session seed is set (production default), the existing timestamp-based
behavior is preserved.

### 4. BehaviorOrchestrator

**Purpose:** Coordinate dwell timing, navigation variation, and the
existing behavioral synthesis into a single session-level flow.

**Design:**

```python
class BehaviorOrchestrator:
    """Coordinates behavioral realism across a browsing session.

    Wraps HumanBehaviorAdapter with:
    - Pre/post-action dwell timing
    - Navigation variation
    - Session-level seed propagation

    Usage::

        orch = BehaviorOrchestrator(
            adapter=human_adapter,
            dwell=DwellTimer(config=dwell_cfg, rng=rng),
            navigator=NavigationVariator(config=nav_cfg, rng=rng),
            session_seed=SessionSeed("repro-001"),
        )
        await orch.navigate(page, "https://example.com")
        await orch.click(page, "#login")
        await orch.type(page, "#email", "user@example.com")
    """

    def __init__(
        self,
        adapter: HumanBehaviorAdapter,
        dwell: DwellTimer | None = None,
        navigator: NavigationVariator | None = None,
        session_seed: SessionSeed | None = None,
    ) -> None: ...

    async def navigate(self, page: Any, url: str) -> None: ...
    async def click(self, page: Any, selector: str) -> None: ...
    async def type(self, page: Any, selector: str, text: str) -> None: ...
    async def scroll(self, page: Any, direction: str = "down", amount: float = 500) -> None: ...
```

Each method:
1. Calls `dwell.pre_action_delay()` → `asyncio.sleep()`
2. Delegates to `adapter.humanize_*()` with session-seed-derived seed
3. Calls `dwell.post_action_delay()` → `asyncio.sleep()`

**Not a replacement for `HumanBehaviorAdapter`:** The orchestrator is
a thin coordination layer. The adapter still does the actual event
dispatch. The orchestrator adds timing and seed management around it.

### 5. Config Model

**Additive only.** Extends `HumanConfig` with new fields.

```python
# New fields added to HumanConfig (backward-compatible defaults):

# Dwell timing
dwell_pre_action_ms: tuple[float, float] = (200.0, 1500.0)
dwell_post_action_ms: tuple[float, float] = (300.0, 3000.0)
dwell_page_settle_ms: float = 800.0
dwell_variability: float = 0.7

# Navigation variation
nav_style_weights: dict[str, float] = field(default_factory=lambda: {
    "direct": 0.5, "type_enter": 0.15, "click_link": 0.20, "referrer": 0.15,
})
nav_referrer_pool: tuple[str, ...] = (
    "https://www.google.com/",
    "https://duckduckgo.com/",
    "https://www.bing.com/",
)

# Session determinism (already exists as session_seed)
# session_seed: str = ""  ← already in HumanConfig
```

No new sub-config on `Config`. All fields go on the existing
`HumanConfig` / `StealthConfig.human_*` path. This preserves
backward compatibility with existing presets.

---

## Determinism guarantees

Track C enforces strict reproducibility when a session seed is set:

| Component | Deterministic? | Mechanism |
|:----------|:---------------|:----------|
| Mouse trajectory | ✅ | `seed` param → `prng_for()` |
| Keystroke synthesis | ✅ | `seed` param → `prng_for()` |
| Scroll synthesis | ✅ | `seed` param → `prng_for()` |
| Dwell timing | ✅ (with seed) | `random.Random(seed)` |
| Navigation style | ✅ (with seed) | `random.Random(seed)` |
| Session flow | ✅ (with seed) | `SessionSeed.derive()` |

**When no session seed is set** (production default), all components
use entropy-based randomness. Sessions are non-reproducible. This is
the correct production behavior.

**When a session seed is set** (testing/replay), every action in the
session is byte-for-byte reproducible. Same seed → same mouse paths,
same keystrokes, same dwell times, same navigation styles.

---

## Test strategy

### Pure-data tests (default CI, no browser)

| Component | Fixture approach |
|:----------|:-----------------|
| `DwellTimer` | Seeded `random.Random`. Assert delay ranges, action-awareness, and determinism (same seed → same sequence). |
| `NavigationVariator` | Seeded RNG. Assert style distribution, referrer pool, type delays. |
| `SessionSeed` | Assert `derive()` produces expected strings. Assert `rng()` returns independent streams. |
| `BehaviorOrchestrator` | Mock `HumanBehaviorAdapter`. Assert call order, dwell timing injection, and seed propagation. No real browser. |

### Reproducibility tests (default CI, no browser)

```python
def test_session_reproducible():
    """Same session seed → same behavioral output."""
    seed = "repro-test-001"

    session1 = SessionSeed(seed)
    session2 = SessionSeed(seed)

    seed_a = session1.derive("click", "#btn")
    seed_b = session2.derive("click", "#btn")
    assert seed_a == seed_b

    traj1 = synthesize_mouse_trajectory(
        (0, 0), (100, 100), seed=seed_a,
    )
    traj2 = synthesize_mouse_trajectory(
        (0, 0), (100, 100), seed=seed_b,
    )
    assert traj1 == traj2  # Byte-identical
```

### Live tests (opt-in only)

Gated by `SB_LIVE_BEHAVIOR=1`:

```python
@pytest.mark.live
@pytest.mark.skipif(not os.getenv("SB_LIVE_BEHAVIOR"), reason="requires live browser")
class TestLiveBehavior:
    async def test_real_click_timing(self): ...
    async def test_real_scroll_inertial(self): ...
```

### No hidden delays in unit tests

All unit tests that use `DwellTimer` must either:
1. Inject a `random.Random(0)` that produces zero delays, OR
2. Mock `asyncio.sleep` to capture delays without actually waiting.

Default CI must never call real `asyncio.sleep()` for behavioral timing.

---

## Rollback plan

Track C is purely additive. Reverting the PR:

1. Removes `DwellTimer`, `NavigationVariator`, `SessionSeed`,
   `BehaviorOrchestrator`, and new `HumanConfig` fields.
2. Existing behavioral synthesis pipeline and `HumanBehaviorAdapter`
   are completely unaffected.
3. No migration needed. No data to preserve.

---

## Acceptance criteria for implementation PR

The Track C implementation PR (Wave 22+) must satisfy:

1. **`DwellTimer`** — functional with action-aware timing, seeded
   determinism, configurable ranges.
2. **`NavigationVariator`** — style selection by weights, referrer
   pool, type delay generation. Honesty note in docstring about
   simulated address bar.
3. **`SessionSeed`** — `derive()` produces deterministic seeds.
   `rng()` returns independent streams. Non-deterministic when base
   seed is empty.
4. **`BehaviorOrchestrator`** — coordinates dwell + navigate + adapter.
   Injects session seeds. All `asyncio.sleep` calls are mockable.
5. **`HumanConfig`** — new fields added with backward-compatible
   defaults. Existing presets (`default`, `careful`, `fast`) updated
   with dwell/nav values.
6. **Determinism test** — same session seed → byte-identical behavioral
   output across mouse, keyboard, scroll, dwell, and navigation.
7. **No hidden delays in unit tests** — all behavioral tests use mocked
   time or seeded zero-delay RNG.
8. **No default-CI browser calls** — all live tests gated by
   `SB_LIVE_BEHAVIOR=1`.
9. **Lint clean.** `ruff check src/ tests/` passes.
10. **Full suite green.** All existing tests pass unmodified.
11. **No "undetectable" claims** in docstrings, comments, or docs.

---

## Implementation sequencing

Track C is decomposed into implementation slices:

| Slice | Wave | Scope |
|:------|:-----|:------|
| 1 | Wave 22 | `DwellTimer` + `SessionSeed` + `HumanConfig` fields |
| 2 | Wave 23 | `NavigationVariator` + `BehaviorOrchestrator` |

Each slice is a separate PR with its own acceptance criteria subset.
