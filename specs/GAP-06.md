# GAP-06: Vision-Based Element Location

| Field        | Value                                                        |
|--------------|--------------------------------------------------------------|
| Gap          | #6                                                           |
| Title        | Vision-Based Element Location                                |
| Phase        | Phase 5 (Vision & Advanced Control -- Weeks 9-10)            |
| Status       | Spec Complete                                                 |
| Depends-On   | GAP-02 (MultimodalController Tier 3 is this vision layer), GAP-09 (TokenBudgetGovernor for cost control on vision calls) |
| Enables      | GAP-03 (Visual Verification -- vision providers for state comparison), GAP-04 (Self-Healing -- vision as last-resort recovery), GAP-08 (Stealth -- CAPTCHA solving via vision) |
| Build Order  | Week 9-10                                                    |
| Effort       | High                                                         |

---

## 1. Problem

Super Browser's MultimodalController defines a three-tier interaction cascade where Tier 3 is vision: the most expensive, most general, and most capable tier. When DOM selectors fail and CDP coordinate resolution fails, the system must fall back to analyzing a screenshot through a vision model to locate the target element. Beyond simple element location, vision is also required for CAPTCHA solving (reading distorted text, selecting grid images), page state inference ("Is there an error banner?"), and canvas interaction (identifying toolbar icons that have zero DOM representation).

Five reference projects solve pieces of this problem but none unifies them. Stagehand provides a CUA client factory with four providers (Anthropic, OpenAI, Google, Microsoft) mapping model names to provider-specific protocol implementations. Agent-S provides UI-TARS visual grounding that converts a screenshot plus a natural language referring expression into pixel coordinates, plus an OCR text grounding path using pytesseract for word-level bounding boxes. Skyvern demonstrates a vision-first loop that combines screenshot and DOM context for action planning. agent-browser shows that AX-tree ref-based targeting handles deterministic cases without any vision at all. LaVague provides semantic HTML chunking for element discovery.

The challenge is composing these approaches behind a single `VisionController` that implements `MultimodalController`'s Tier 3 contract: given a screenshot and an element description, return pixel coordinates. The controller must support multiple providers (so no single vendor is a dependency), route tasks to the cheapest capable model (model cascade), cache results for static layouts, and offer OCR text grounding as a secondary path when vision models miss text-heavy elements.

---

## 2. Requirements

### Functional

| ID    | Requirement                                                                                                                    |
|-------|--------------------------------------------------------------------------------------------------------------------------------|
| R1    | Provide a `VisionController` class implementing the `VisionProvider` interface from GAP-02, with three methods: `locate_element()`, `solve_captcha()`, `infer_state()` |
| R2    | `locate_element(screenshot, description, viewport_size)` returns `VisionResponse` with `(x, y)` pixel coordinates in viewport space and a confidence score |
| R3    | `solve_captcha(screenshot, captcha_type)` returns `CaptchaSolution` with the solved text or selected grid coordinates and a `provider` field indicating which solver was used |
| R4    | `infer_state(screenshot, question)` returns `StateInference` with a natural language answer, structured labels (e.g., `has_error`, `is_logged_in`), and a confidence score |
| R5    | Provide an abstract `VisionProviderBase` class with method `locate(request: VisionRequest) -> VisionResponse` and properties `name`, `model_id`, `cost_per_1k_tokens` |
| R6    | Implement three concrete providers: `AnthropicCUAProvider`, `OpenAIResponseProvider`, `UITARSProvider` (local model) |
| R7    | `AnthropicCUAProvider` uses the Anthropic Computer Use API: sends screenshot as base64, receives tool_use blocks with `coordinate` actions, maps coordinates to viewport space |
| R8    | `OpenAIResponseProvider` uses the OpenAI Responses API: sends screenshot as image URL, receives structured output with coordinate fields |
| R9    | `UITARSProvider` runs the local UI-TARS 7B model: accepts screenshot + referring expression, returns pixel coordinates with coordinate resizing from model resolution (e.g., 1280x720) to actual viewport size |
| R10   | Implement `VisionProviderFactory` mapping provider names and model IDs to provider instances, with environment-variable-driven default configuration |
| R11   | Implement model cascade logic: task complexity `SIMPLE` (element location with clear description) routes to cheapest model, `COMPLEX` (CAPTCHA, canvas interaction) routes to mid-tier model, `AMBIGUOUS` (judgment calls, multiple candidates) routes to most capable model |
| R12   | The cascade is configurable via `CascadeConfig` with fields: `simple_model`, `complex_model`, `ambiguous_model`, `confidence_threshold_for_escalation` (default 0.6) |
| R13   | When a provider returns confidence below `confidence_threshold_for_escalation`, the controller must escalate to the next tier in the cascade and retry |
| R14   | Implement `VisionCache` with LRU eviction (max 500 entries), keyed by `SHA-256(screenshot_hash + description)`, persisting to `~/.super-browser/vision-cache/cache.json` |
| R15   | Cache entries store the `VisionResponse` and an `image_hash` (perceptual dHash, 64-bit) for invalidation: if the same description is requested but the screenshot's dHash differs by more than 4 bits, the cache entry is invalidated |
| R16   | Implement OCR text grounding as a secondary element location path: run pytesseract word-level OCR on the screenshot, match the description against OCR words via LLM, compute the bounding box center of matching words |
| R17   | The OCR path is invoked when the primary vision provider returns `found=False` or when `description` contains quoted text (e.g., `the button labeled "Submit Order"`) |
| R18   | All vision calls are cost-tracked: each `VisionResponse` includes `token_cost` (USD) and `model`. The `VisionController` exposes `total_cost()` and `call_count()` for budget monitoring by GAP-09 `TokenBudgetGovernor` |
| R19   | Each provider implements a `health_check()` method that sends a trivial request (e.g., "What color is the top-left pixel?") and returns `True`/`False` within 10 seconds, used for provider failover |
| R20   | When the primary provider fails (timeout, API error, rate limit), the controller tries the next provider in the factory's priority order before reporting failure |
| R21   | Coordinate resizing from model output to screen resolution uses the formula: `screen_x = model_x * (viewport_width / model_width)`, `screen_y = model_y * (viewport_height / model_height)`, with rounding to nearest integer pixel |
| R22   | All vision operations are logged via GAP-11 (Tracing) with fields: `provider`, `model`, `task_type`, `confidence`, `token_cost`, `duration_ms`, `cache_hit` |

### Non-Functional

| ID    | Requirement                                                                                                          |
|-------|----------------------------------------------------------------------------------------------------------------------|
| NFR1  | `locate_element()` must complete in under 15 seconds for cloud providers and under 5 seconds for the local UI-TARS provider |
| NFR2  | `solve_captcha()` must complete in under 30 seconds (some CAPTCHAs require multiple reasoning steps)                  |
| NFR3  | `infer_state()` must complete in under 10 seconds                                                                     |
| NFR4  | Vision cache lookup must complete in under 2 ms (in-memory SHA-256 key match); no screenshot re-processing on cache hit |
| NFR5  | Cache persistence must be asynchronous and non-blocking; cache writes never delay a vision response                   |
| NFR6  | Provider failover must add under 500 ms overhead (connection reuse, pre-initialized clients)                          |
| NFR7  | OCR grounding must complete in under 3 seconds (pytesseract is local, no network calls)                               |
| NFR8  | The `VisionController` must not hold screenshot data in memory longer than necessary: screenshots are released after provider call completes and cache entry is stored |
| NFR9  | Model cascade routing (complexity classification) must complete in under 1 ms (rule-based, no LLM call for routing)   |
| NFR10 | Each provider client must support connection pooling and reuse across calls (no per-request TCP handshake)             |

### Out of Scope

- Training or fine-tuning custom vision models -- using pre-trained models only
- Real-time video analysis -- single-frame screenshots only
- Image generation or editing -- read-only analysis
- Multi-image comparison (e.g., "which of these two screenshots shows a logged-in state?") -- deferred to future enhancement
- LaVague RAG-based semantic HTML chunking for element discovery -- high effort, low priority, may be revisited in a later phase
- Google CUA and Microsoft CUA provider implementations -- infrastructure exists but these are secondary priorities after Anthropic, OpenAI, and UI-TARS

---

## 3. Adopted Patterns

| # | Pattern | Source | Source Score | Effort | Role |
|---|---------|--------|-------------|--------|------|
| P1 | CUA Client Factory (4 Providers) | Stagehand `AgentProvider.ts`, `AnthropicCUAClient.ts`, `OpenAICUAClient.ts` | 4.00 | High | Multi-provider abstraction |
| P2 | Coordinate Mapping CUA Actions to Page Operations | Stagehand `AnthropicCUAClient.ts` | 4.00 | Low | Coordinate normalization |
| P3 | Visual Grounding via UI-TARS | Agent-S `grounding.py:229-245` (`generate_coords`) | 4.12 | Medium | Local model coordinate prediction |
| P4 | Coordinate Resizing (Model to Screen) | Agent-S `grounding.py:229-245` | 4.12 | Low | Resolution mismatch handling |
| P5 | OCR Text Grounding (pytesseract + LLM) | Agent-S `grounding.py:285-326` | 4.12 | Medium | Text-heavy element fallback |
| P6 | Vision-First Loop (Screenshot + DOM to LLM to Action) | Skyvern `forge/agent.py` | 3.80 | Medium | Vision call orchestration |
| P7 | Ref-Based AX Targeting (Deterministic Baseline) | agent-browser `snapshot.rs` | 3.95 | Low | Non-vision element location baseline |
| P8 | Model Cascade (Cheap for Simple, Expensive for Complex) | Skyvern `per-role LLM`, roadmap Phase 5 | 3.80 / Roadmap | Low | Cost-optimized model selection |
| P9 | Vision Result Caching for Static Layouts | Roadmap Phase 5 | Roadmap | Medium | Avoid re-analyzing unchanged pages |
| P10 | AgentProvider Model-to-Provider Mapping | Stagehand `AgentProvider.ts` | 4.00 | Low | Factory configuration |
| P11 | 6-Format Action Parser Chain (Chain-of-Responsibility) | UI-TARS-Desktop `FormatParsers.ts` (427), `ActionParserHelper.ts` (572) | 4.74 | Low | VLM output parsing |
| P12 | smart_resize Image Pipeline with Factor Divisibility | UI-TARS `action_parser.py:115-143` | 3.46 | Low | VLM image preprocessing |
| P13 | Dual Coordinate System (Absolute vs Relative) | UI-TARS `action_parser.py:164-266` | 3.46 | Low | Multi-model coordinate normalization |
| P14 | System Prompt Templates for Grounding/Desktop/Mobile | UI-TARS `prompt.py` (60 lines) | 3.13 | Low | Prompt engineering for VLM tasks |

### Per-Pattern Adoption Notes

**P1 -- CUA Client Factory (Stagehand)**
Adopt the provider factory pattern from Stagehand's `AgentProvider.ts`. The original maps 12+ model names (e.g., `claude-3-5-sonnet`, `gpt-4o`, `gemini-1.5-pro`) to provider-specific client classes. Each client implements a unified interface (`execute_step`, `capture_screenshot`, `set_viewport`). Super Browser adapts this as `VisionProviderFactory` which maps provider names (`anthropic`, `openai`, `uitars`) and model IDs to concrete `VisionProviderBase` subclasses. The factory reads defaults from environment variables (`SB_VISION_DEFAULT_PROVIDER`, `SB_VISION_DEFAULT_MODEL`, `SB_ANTHROPIC_API_KEY`, `SB_OPENAI_API_KEY`).

**P2 -- Coordinate Mapping CUA Actions to Page Operations (Stagehand)**
Adopt the coordinate mapping from CUA tool_use responses to page-level operations. Stagehand's `AnthropicCUAClient` receives `computer_use` tool results containing `coordinate` actions (e.g., `{type: "click", coordinate: [450, 320]}`). These coordinates are in the model's coordinate space and must be mapped to the actual viewport. Super Browser uses the same approach: extract coordinate tuples from provider-specific response formats, apply the resize formula from P4, and dispatch to `CDPBridge.compositor_click()`.

**P3 -- Visual Grounding via UI-TARS (Agent-S)**
Adopt the visual grounding approach from Agent-S's `grounding.py:229-245` (`generate_coords`). The original takes a full screenshot and a natural language referring expression, sends them to a UI-TARS 7B model, and receives predicted pixel coordinates. The UI-TARS model is specifically trained for GUI grounding -- given "the blue Submit button" it predicts the center pixel of that element. Super Browser wraps this as `UITARSProvider`, a local model provider that requires no API key and has zero per-call token cost (only compute cost). This is the cheapest provider for `SIMPLE` complexity tasks.

**P4 -- Coordinate Resizing (Agent-S)**
Adopt the coordinate resizing logic from Agent-S's `grounding.py:229-245`. Vision models operate on fixed resolutions (UI-TARS at 1280x720, Anthropic CUA at 1280x800, etc.) while the actual browser viewport may be any size. The formula `screen_x = model_x * (viewport_width / model_width)` is directly portable. Super Browser implements this as a shared utility function `resize_coordinates()` used by all providers. The viewport size is provided in `VisionRequest.viewport_size`.

**P5 -- OCR Text Grounding (Agent-S)**
Adopt the OCR text grounding path from Agent-S's `grounding.py:285-326`. The original runs pytesseract word-level OCR to get bounding boxes for each word, then uses an LLM to match a natural language phrase to the OCR words (handling multi-word phrases by combining adjacent word bounding boxes), and returns the center of the combined bounding box. This is effective for text-heavy elements (buttons with labels, form field placeholders) where vision models may hallucinate coordinates. Super Browser integrates this as a secondary path invoked when the primary vision provider fails or when the description contains quoted text patterns.

**P6 -- Vision-First Loop (Skyvern)**
Adopt the vision call orchestration pattern from Skyvern's `ForgeAgent.execute_step()`. The original captures a screenshot and scraped page DOM, sends both to the LLM with the task objective, and receives a structured action. Super Browser uses this pattern in `locate_element()`: capture screenshot via `CDPBridge.capture_screenshot()`, optionally include the AX snapshot (from GAP-02) as additional context for the vision provider, send to the selected provider, parse the coordinate response. The AX snapshot context helps the model disambiguate elements when multiple candidates exist.

**P7 -- Ref-Based AX Targeting (agent-browser)**
Adopt as the non-vision baseline. Before invoking any vision provider, the `VisionController` checks whether the AX snapshot (already captured by GAP-02's `MultimodalController`) can resolve the target via text/role matching. If the target can be found in the AX tree, no vision call is needed. This is not a vision technique itself but a pre-check that avoids unnecessary vision calls on pages where the AX tree is sufficient.

**P8 -- Model Cascade (Skyvern/Roadmap)**
Adopt the model cascade pattern for cost optimization. The roadmap specifies: "GPT-4o Mini for simple location, Claude Sonnet for complex reasoning, Claude Opus for ambiguous judgment calls." Skyvern uses per-role LLM selection for similar cost optimization. Super Browser implements this as `CascadeConfig` with three tiers. The routing is rule-based (no LLM call): `SIMPLE` tasks are single-element descriptions with no ambiguity markers, `COMPLEX` tasks involve CAPTCHA, canvas, or multi-step reasoning, `AMBIGUOUS` tasks contain words like "or", "either", "whichever" suggesting multiple candidates. The cascade also escalates automatically when a provider's confidence is below threshold.

**P9 -- Vision Result Caching for Static Layouts (Roadmap)**
Adopt the caching pattern from the roadmap: "Cache vision results to avoid re-analyzing static layouts." When the same element description is requested on a page that has not visually changed (same perceptual hash), the cached coordinates are returned without calling a vision model. The cache uses `SHA-256(screenshot_dhash + description)` as the key and stores the full `VisionResponse`. Perceptual dHash (64-bit) is used for invalidation: if the dHash changes by more than 4 bits (configurable), the page is considered to have changed and the cache entry is invalidated.

**P10 -- AgentProvider Model-to-Provider Mapping (Stagehand)**
Adopt the configuration pattern from Stagehand's `AgentProvider.ts`. The original defines a `modelToAgentProviderMap` that maps model IDs like `claude-3-5-sonnet-20241022` to provider type `AgentProvider.ANTHROPIC`. Super Browser's `VisionProviderFactory.from_env()` creates this mapping from environment variables, allowing users to configure which model is used for each complexity tier without code changes. Default configuration: `SIMPLE` -> UI-TARS (local, free), `COMPLEX` -> GPT-4o Mini (cheap cloud), `AMBIGUOUS` -> Claude Sonnet (capable cloud).

**P11 -- 6-Format Action Parser Chain (UI-TARS-Desktop)**
Adopt the chain-of-responsibility parser from UI-TARS-Desktop's action-parser module. The original tries 6 format parsers in sequence: XMLFormatParser (`<seed:tool_call>` tags), OmniFormatParser (`<computer_env>` tags), UnifiedBCFormatParser (`Thought:... Action:...`), BCComplexFormatParser (`Reflection:... Action_Summary:...`), O1FormatParser (`<Thought>...</Thought>`), FallbackFormatParser (any `function_call(...)`). This is the most robust VLM output parsing infrastructure found across all reference projects. It handles the reality that different VLM versions, providers, and prompt styles produce output in different formats. The `ActionParserHelper.parseCoordinates()` handles 4+ coordinate formats (`<point>x y</point>`, `<|box_start|>(x,y)<|box_end|>`, `[x1,y1,x2,y2]`, `<bbox>x1 y1 x2 y2</bbox>`), computing center point from bounding boxes. Super Browser should port this chain to Python and integrate it into `VisionController` as the VLM response parser. Each provider's `locate()` method delegates parsing to this chain, ensuring consistent coordinate extraction regardless of model output format.

**P12 -- smart_resize Image Pipeline with Factor Divisibility (UI-TARS)**
Adopt the `smart_resize()` function from UI-TARS's `action_parser.py:115-143`. Vision transformer models require image dimensions divisible by their patch factor (28 for Qwen2.5-VL). The algorithm: (1) round dimensions to nearest factor multiple, (2) if pixel count exceeds `max_pixels`, scale down by `beta = sqrt(pixels/max_pixels)` and floor to factor, (3) if below `min_pixels`, scale up. This ensures the image dimensions work with the model's vision encoder while staying within token bounds (78,400-12,845,056 pixels). Super Browser's `UITARSProvider` should use this directly before sending screenshots to the model. Cloud providers (Anthropic, OpenAI) handle resizing internally, so this is primarily for local model providers.

**P13 -- Dual Coordinate System (UI-TARS)**
Adopt the dual coordinate system handling from UI-TARS's `action_parser.py:164-266`. Different VLM architectures output coordinates in different formats: Qwen2.5-VL (UI-TARS-1.5) outputs absolute pixel coordinates in resized image space, while Qwen2-VL (UI-TARS-1.0) outputs relative coordinates normalized to [0, 1000]. The parser normalizes both to [0,1] by dividing by the appropriate dimension (resized width/height for absolute, factor=1000 for relative). This is critical for `UITARSProvider`: when the model outputs `<point>197 525</point>`, the parser must know whether those are absolute pixels or relative values, and normalize accordingly. Super Browser should implement this as `CoordinateNormalizer` with a `model_type` parameter.

**P14 -- System Prompt Templates for Grounding/Desktop/Mobile (UI-TARS)**
Adopt the three prompt templates from UI-TARS's `prompt.py`: (1) `COMPUTER_USE_DOUBAO` for desktop (9 actions: click, drag, hotkey, type, scroll, wait, finished), (2) `MOBILE_USE_DOUBAO` for mobile (touch adaptations: long_press, press_home, press_back), (3) `GROUNDING_DOUBAO` for single-step coordinate prediction without Thought/Action format. The grounding-only template is directly useful for Super Browser's `locate_element()`: it strips the multi-action planning format and focuses the model on predicting a single coordinate. This is more efficient than sending full agent-style prompts when only coordinate prediction is needed.

---

## 4. Interface Contract

### Dataclasses

```python
from __future__ import annotations

import abc
import enum
import hashlib
import io
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# Types from GAP-02 (consumed, not redefined)
# from src.super_browser.control.multimodal import VisionProvider, VisionRequest, VisionResponse
# from src.super_browser.browser.session import CDPBridge
# from src.super_browser.results import ActionResult, ActionMethod


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class VisionTaskComplexity(enum.Enum):
    """Complexity classification for model cascade routing."""
    SIMPLE = "simple"         # Single element, clear description, no ambiguity
    COMPLEX = "complex"       # CAPTCHA, canvas interaction, multi-step reasoning
    AMBIGUOUS = "ambiguous"   # Multiple candidates, judgment call required


class CaptchaType(enum.Enum):
    """Types of CAPTCHA the vision controller can solve."""
    TEXT_DISTORTED = "text_distorted"       # Distorted text image
    IMAGE_GRID = "image_grid"               # Select N images matching a prompt
    RECAPTCHA_V2 = "recaptcha_v2"           # Google reCAPTCHA checkbox + image
    HCAPTCHA = "hcaptcha"                   # hCaptcha image selection
    SLIDER = "slider"                       # Drag-to-position slider CAPTCHA


class VisionProviderName(enum.Enum):
    """Available vision providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    UITARS = "uitars"


# ---------------------------------------------------------------------------
# Vision Responses (extended from GAP-02 VisionResponse)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class VisionLocation:
    """Pixel coordinates returned by vision element location."""
    x: float
    y: float
    width: Optional[float] = None       # optional bounding box width
    height: Optional[float] = None      # optional bounding box height
    confidence: float = 0.0             # 0.0-1.0


@dataclass(frozen=True)
class CaptchaSolution:
    """Result of CAPTCHA solving."""
    solved: bool
    answer: Optional[str] = None            # text answer for text CAPTCHAs
    grid_selections: Optional[list[int]] = None  # selected grid indices
    slider_position: Optional[float] = None     # x-position for slider CAPTCHAs
    provider: Optional[str] = None          # which provider solved it
    confidence: float = 0.0
    token_cost: float = 0.0
    duration_ms: float = 0.0


@dataclass(frozen=True)
class StateInference:
    """Result of page state inference."""
    answer: str                             # natural language description
    labels: dict[str, bool] = field(default_factory=dict)  # structured labels
    # e.g., {"has_error": True, "is_logged_in": False, "is_loading": False}
    confidence: float = 0.0
    model: Optional[str] = None
    token_cost: float = 0.0
    duration_ms: float = 0.0


@dataclass(frozen=True)
class OCRWord:
    """Single word from OCR with bounding box."""
    text: str
    x: float
    y: float
    width: float
    height: float
    confidence: float


# ---------------------------------------------------------------------------
# Cascade Configuration
# ---------------------------------------------------------------------------

@dataclass
class CascadeConfig:
    """
    Model cascade configuration mapping task complexity to providers.

    Adopted from Skyvern per-role LLM + roadmap Phase 5 model cascade.
    """
    simple_provider: VisionProviderName = VisionProviderName.UITARS
    simple_model: Optional[str] = None                # None = provider default

    complex_provider: VisionProviderName = VisionProviderName.OPENAI
    complex_model: str = "gpt-4o-mini"

    ambiguous_provider: VisionProviderName = VisionProviderName.ANTHROPIC
    ambiguous_model: str = "claude-sonnet-4-20250514"

    confidence_threshold_for_escalation: float = 0.6  # escalate if below
    max_escalations: int = 2                           # max retry-escalations


# ---------------------------------------------------------------------------
# Cache Entry
# ---------------------------------------------------------------------------

@dataclass
class VisionCacheEntry:
    """A single entry in the vision result cache."""
    key: str                           # SHA-256(dhash_hex + description)
    description: str
    response: Any                      # VisionResponse or CaptchaSolution or StateInference
    image_dhash: int                   # 64-bit perceptual dHash
    created_at: float = field(default_factory=time.monotonic)
    last_hit: float = field(default_factory=time.monotonic)
    hit_count: int = 0


# ---------------------------------------------------------------------------
# Vision Provider Base (abstract)
# ---------------------------------------------------------------------------

class VisionProviderBase(abc.ABC):
    """
    Abstract base class for vision providers.

    Implements the VisionProvider interface from GAP-02.
    Each concrete provider handles model-specific request formatting
    and response parsing.
    """

    @abc.abstractmethod
    async def locate(self, request: VisionRequest) -> VisionResponse:
        """
        Locate an element in a screenshot by natural language description.

        Returns VisionResponse with pixel coordinates in viewport space.
        Coordinates must be resized from model resolution to viewport
        resolution before returning (P4 -- coordinate resizing).
        """
        ...

    @abc.abstractmethod
    async def health_check(self) -> bool:
        """
        Verify the provider is reachable and operational.

        Sends a trivial request and returns True if the provider
        responds within 10 seconds. Used for failover decisions.
        """
        ...

    @property
    @abc.abstractmethod
    def name(self) -> str:
        """Provider name (e.g., 'anthropic', 'openai', 'uitars')."""
        ...

    @property
    @abc.abstractmethod
    def model_id(self) -> str:
        """Model identifier (e.g., 'claude-sonnet-4-20250514', 'gpt-4o-mini')."""
        ...

    @property
    @abc.abstractmethod
    def cost_per_1k_tokens(self) -> float:
        """Approximate cost per 1000 tokens in USD."""
        ...

    @property
    @abc.abstractmethod
    def default_resolution(self) -> tuple[int, int]:
        """
        Default screenshot resolution this model expects.
        Used for coordinate resizing (P4).
        Returns (width, height), e.g., (1280, 800).
        """
        ...


# ---------------------------------------------------------------------------
# Concrete Providers
# ---------------------------------------------------------------------------

class AnthropicCUAProvider(VisionProviderBase):
    """
    Anthropic Computer Use API provider.

    Adopted from Stagehand AnthropicCUAClient.ts.
    Sends screenshot as base64, receives tool_use blocks with
    coordinate actions, maps coordinates to viewport space.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514",
        max_tokens: int = 4096,
    ) -> None: ...

    async def locate(self, request: VisionRequest) -> VisionResponse: ...

    async def health_check(self) -> bool: ...

    @property
    def name(self) -> str:
        return "anthropic"

    @property
    def model_id(self) -> str: ...

    @property
    def cost_per_1k_tokens(self) -> float: ...

    @property
    def default_resolution(self) -> tuple[int, int]:
        return (1280, 800)


class OpenAIResponseProvider(VisionProviderBase):
    """
    OpenAI Responses API provider.

    Adopted from Stagehand OpenAICUAClient.ts.
    Sends screenshot as image URL (data URI), receives structured
    output with coordinate fields.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4o-mini",
        max_tokens: int = 4096,
    ) -> None: ...

    async def locate(self, request: VisionRequest) -> VisionResponse: ...

    async def health_check(self) -> bool: ...

    @property
    def name(self) -> str:
        return "openai"

    @property
    def model_id(self) -> str: ...

    @property
    def cost_per_1k_tokens(self) -> float: ...

    @property
    def default_resolution(self) -> tuple[int, int]:
        return (1280, 720)


class UITARSProvider(VisionProviderBase):
    """
    Local UI-TARS 7B model provider for visual grounding.

    Adopted from Agent-S grounding.py:229-245 (generate_coords).
    Runs UI-TARS locally: accepts screenshot + referring expression,
    returns pixel coordinates. No API key required. Zero per-call
    token cost (only local compute).
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cuda",
        max_new_tokens: int = 512,
    ) -> None: ...

    async def locate(self, request: VisionRequest) -> VisionResponse: ...

    async def health_check(self) -> bool: ...

    @property
    def name(self) -> str:
        return "uitars"

    @property
    def model_id(self) -> str: ...

    @property
    def cost_per_1k_tokens(self) -> float:
        return 0.0  # local model, no token cost

    @property
    def default_resolution(self) -> tuple[int, int]:
        return (1280, 720)


# ---------------------------------------------------------------------------
# Vision Provider Factory
# ---------------------------------------------------------------------------

class VisionProviderFactory:
    """
    Factory for vision providers. Maps provider names and model IDs
    to provider instances.

    Adopted from Stagehand AgentProvider.ts model-to-provider mapping (P10).
    """

    def __init__(
        self,
        providers: Optional[dict[VisionProviderName, VisionProviderBase]] = None,
        cascade: Optional[CascadeConfig] = None,
    ) -> None:
        """
        Args:
            providers: Pre-initialized provider instances by name.
            cascade: Cascade configuration for model selection.
        """
        ...

    def get_provider(
        self,
        name: Optional[VisionProviderName] = None,
        model: Optional[str] = None,
    ) -> Optional[VisionProviderBase]:
        """
        Get a provider by name. If name is None, returns the default
        provider (first configured provider).
        """
        ...

    def get_provider_for_complexity(
        self,
        complexity: VisionTaskComplexity,
    ) -> VisionProviderBase:
        """
        Get the provider configured for the given task complexity.
        Uses CascadeConfig mapping.
        """
        ...

    @classmethod
    def from_env(cls) -> VisionProviderFactory:
        """
        Create factory from environment variables:
          SB_VISION_DEFAULT_PROVIDER: "anthropic" | "openai" | "uitars"
          SB_VISION_DEFAULT_MODEL: model ID string
          SB_VISION_CASCADE_SIMPLE_PROVIDER: provider for SIMPLE tasks
          SB_VISION_CASCADE_COMPLEX_PROVIDER: provider for COMPLEX tasks
          SB_VISION_CASCADE_AMBIGUOUS_PROVIDER: provider for AMBIGUOUS tasks
          SB_ANTHROPIC_API_KEY: Anthropic API key
          SB_OPENAI_API_KEY: OpenAI API key
          SB_UITARS_MODEL_PATH: local path to UI-TARS model weights
        """
        ...

    @property
    def provider_priority(self) -> list[VisionProviderName]:
        """Provider failover priority order (highest priority first)."""
        ...


# ---------------------------------------------------------------------------
# Vision Cache
# ---------------------------------------------------------------------------

class VisionCache:
    """
    LRU cache for vision results. Avoids re-analyzing static layouts.

    Adopted from roadmap Phase 5: "Cache vision results to avoid
    re-analyzing static layouts" (P9).

    Key: SHA-256(image_dhash_hex + description)
    Value: VisionCacheEntry with full response.

    Invalidation: If the same description is requested but the
    screenshot's dHash differs by more than dhash_threshold bits,
    the entry is considered stale.
    """

    MAX_ENTRIES = 500
    DHASH_THRESHOLD = 4  # bits of difference for invalidation

    def __init__(
        self,
        cache_dir: Path = Path.home() / ".super-browser" / "vision-cache",
        max_entries: int = 500,
        dhash_threshold: int = 4,
    ) -> None: ...

    def get(
        self,
        screenshot: bytes,
        description: str,
    ) -> Optional[Any]:
        """
        Look up a cached vision result.

        1. Compute dHash of screenshot.
        2. Compute SHA-256(dhash_hex + description) key.
        3. If entry exists and dhash difference <= threshold, return cached response.
        4. Otherwise, return None (cache miss or stale).
        """
        ...

    def put(
        self,
        screenshot: bytes,
        description: str,
        response: Any,
    ) -> None:
        """
        Store a vision result in the cache.

        Computes dHash and SHA-256 key. Evicts LRU entry if at capacity.
        """
        ...

    def invalidate(self, description: str) -> bool:
        """Remove all cache entries for a given description."""
        ...

    def clear(self) -> int:
        """Clear all cache entries. Returns count of entries cleared."""
        ...

    async def persist(self) -> None:
        """Write cache to disk. Non-blocking via asyncio.to_thread."""
        ...

    async def load(self) -> int:
        """Load cache from disk. Returns count of entries loaded."""
        ...

    @property
    def hit_rate(self) -> float:
        """Cache hit rate (hits / (hits + misses)). 0.0 if no lookups yet."""
        ...

    @property
    def size(self) -> int:
        """Current number of entries in cache."""
        ...

    @staticmethod
    def compute_dhash(image_bytes: bytes, hash_size: int = 8) -> int:
        """
        Compute perceptual difference hash (dHash) for an image.

        Returns a 64-bit integer. Two images with dHash difference
        <= DHASH_THRESHOLD are considered visually equivalent.
        """
        ...

    @staticmethod
    def dhash_distance(hash_a: int, hash_b: int) -> int:
        """Hamming distance between two dHash values."""
        ...


# ---------------------------------------------------------------------------
# OCR Grounding
# ---------------------------------------------------------------------------

class OCRGrounding:
    """
    OCR-based text grounding as a secondary element location path.

    Adopted from Agent-S grounding.py:285-326 (P5).
    Runs pytesseract word-level OCR on a screenshot, matches the
    description against OCR words via LLM phrase-to-word matching,
    computes the bounding box center of matching words.
    """

    def __init__(self, tesseract_config: Optional[str] = None) -> None:
        """
        Args:
            tesseract_config: Optional pytesseract config string.
                Default: "--psm 11" (sparse text mode).
        """
        ...

    async def locate_by_text(
        self,
        screenshot: bytes,
        description: str,
        viewport_size: tuple[int, int],
    ) -> Optional[VisionLocation]:
        """
        Locate an element by matching its text content via OCR.

        Steps:
        1. Run pytesseract image_to_data() with word-level bounding boxes.
        2. Filter words by confidence > 30.
        3. If description contains quoted text (e.g., "Submit Order"),
           directly match OCR words against the quoted text.
        4. Otherwise, send OCR words + description to a cheap LLM
           to identify which words correspond to the target element.
        5. Combine bounding boxes of matched words.
        6. Return center of combined bounding box as VisionLocation.

        Returns None if no words match or OCR confidence is too low.
        """
        ...

    def extract_words(self, screenshot: bytes) -> list[OCRWord]:
        """
        Run pytesseract word-level OCR and return structured OCRWords.
        """
        ...

    def match_quoted_text(
        self,
        words: list[OCRWord],
        quoted_text: str,
    ) -> Optional[VisionLocation]:
        """
        Directly match quoted text against OCR words.
        Handles multi-word matches by combining adjacent bounding boxes.
        Returns center of combined box.
        """
        ...


# ---------------------------------------------------------------------------
# Coordinate Utility
# ---------------------------------------------------------------------------

def resize_coordinates(
    x: float,
    y: float,
    model_resolution: tuple[int, int],
    viewport_resolution: tuple[int, int],
) -> tuple[int, int]:
    """
    Resize coordinates from model output space to screen viewport space.

    Adopted from Agent-S grounding.py:229-245 (P4).

    Formula:
        screen_x = model_x * (viewport_width / model_width)
        screen_y = model_y * (viewport_height / model_height)

    Returns rounded to nearest integer pixel.
    """
    model_w, model_h = model_resolution
    viewport_w, viewport_h = viewport_resolution

    screen_x = round(x * (viewport_w / model_w))
    screen_y = round(y * (viewport_h / model_h))

    return (screen_x, screen_y)


# ---------------------------------------------------------------------------
# Vision Controller
# ---------------------------------------------------------------------------

class VisionController:
    """
    Vision-based element location controller.

    Implements MultimodalController's Tier 3 contract from GAP-02.
    Manages multiple vision providers, model cascade, result caching,
    and OCR grounding fallback.

    Usage:
        factory = VisionProviderFactory.from_env()
        cache = VisionCache()
        ocr = OCRGrounding()

        controller = VisionController(
            factory=factory,
            cache=cache,
            ocr=ocr,
            cascade=CascadeConfig(),
        )

        # Locate an element
        response = await controller.locate_element(
            screenshot=png_bytes,
            description="the blue Submit button",
            viewport_size=(1920, 1080),
        )

        # Solve a CAPTCHA
        solution = await controller.solve_captcha(
            screenshot=png_bytes,
            captcha_type=CaptchaType.TEXT_DISTORTED,
        )

        # Infer page state
        state = await controller.infer_state(
            screenshot=png_bytes,
            question="Is there an error message visible?",
        )
    """

    def __init__(
        self,
        factory: VisionProviderFactory,
        cache: Optional[VisionCache] = None,
        ocr: Optional[OCRGrounding] = None,
        cascade: Optional[CascadeConfig] = None,
        *,
        ax_snapshot_check: bool = True,
    ) -> None:
        """
        Args:
            factory: Provider factory with configured providers.
            cache: Optional vision result cache. If None, caching is disabled.
            ocr: Optional OCR grounding module. If None, OCR fallback is disabled.
            cascade: Cascade configuration for model selection.
            ax_snapshot_check: If True, check AX snapshot before calling vision.
        """
        ...

    # -- Core Methods --------------------------------------------------------

    async def locate_element(
        self,
        screenshot: bytes,
        description: str,
        viewport_size: tuple[int, int],
        *,
        complexity: Optional[VisionTaskComplexity] = None,
        ax_snapshot: Optional[Any] = None,
    ) -> VisionResponse:
        """
        Locate an element in a screenshot by natural language description.

        This is the primary Tier 3 method called by MultimodalController
        when Tier 1 and Tier 2 fail.

        Flow:
        1. Check vision cache for (screenshot_dhash, description).
           Return cached result on hit.
        2. If ax_snapshot is provided and ax_snapshot_check is True,
           attempt to resolve via AX tree text/role matching.
           If found, return coordinates without calling vision model.
        3. Classify task complexity (SIMPLE/COMPLEX/AMBIGUOUS) if not provided.
        4. Select provider via cascade config for the classified complexity.
        5. Build VisionRequest(screenshot, description, url, viewport_size).
        6. Call provider.locate(request).
        7. If confidence < threshold, escalate to next complexity tier
           and retry with the next provider (max max_escalations retries).
        8. If all providers fail and OCR is available, try OCR text grounding.
        9. Cache the successful response.
        10. Return VisionResponse with coordinates, confidence, and cost.

        Args:
            screenshot: PNG image bytes of the current viewport.
            description: Natural language element description.
            viewport_size: (width, height) of the viewport.
            complexity: Optional pre-classified complexity. Auto-classified if None.
            ax_snapshot: Optional AXSnapshot from GAP-02 for pre-check.

        Returns:
            VisionResponse with found=True/False, coordinates, confidence, cost.
        """
        ...

    async def solve_captcha(
        self,
        screenshot: bytes,
        captcha_type: CaptchaType,
        *,
        prompt: Optional[str] = None,
        viewport_size: tuple[int, int] = (1280, 720),
    ) -> CaptchaSolution:
        """
        Solve a CAPTCHA from a screenshot.

        Always routes to COMPLEX or AMBIGUOUS tier (never SIMPLE).
        Uses the most capable provider for the given CAPTCHA type.

        Args:
            screenshot: PNG image bytes of the CAPTCHA.
            captcha_type: Type of CAPTCHA to solve.
            prompt: Optional additional context (e.g., "Select all images
                with traffic lights" for image grid CAPTCHAs).
            viewport_size: Viewport size for coordinate normalization.

        Returns:
            CaptchaSolution with the answer and metadata.
        """
        ...

    async def infer_state(
        self,
        screenshot: bytes,
        question: str,
        *,
        viewport_size: tuple[int, int] = (1280, 720),
    ) -> StateInference:
        """
        Infer page state from a screenshot.

        Sends the screenshot and a natural language question to a vision
        model and receives a structured answer.

        Routes to COMPLEX tier by default (state inference requires
        reasoning about page content, not just element location).

        Args:
            screenshot: PNG image bytes of the current viewport.
            question: Natural language question about page state.
            viewport_size: Viewport size for context.

        Returns:
            StateInference with answer, labels, and confidence.
        """
        ...

    # -- Complexity Classification -------------------------------------------

    def classify_complexity(self, description: str) -> VisionTaskComplexity:
        """
        Classify the complexity of a vision task based on the description.

        Rule-based classification (no LLM call, completes in <1ms):

        SIMPLE:
          - Single element description, no ambiguity markers
          - Examples: "the blue Submit button", "the search input field"

        COMPLEX:
          - Contains CAPTCHA-related keywords: "captcha", "recaptcha",
            "hcaptcha", "verify", "prove you are human"
          - Contains canvas-related keywords: "canvas", "draw", "toolbar"
          - Contains reasoning keywords: "which", "find all", "count"

        AMBIGUOUS:
          - Contains disjunction markers: " or ", "either", "whichever"
          - Contains "one of", "any of", "best match"
          - Description length > 100 characters (complex multi-step)

        Returns:
            VisionTaskComplexity enum value.
        """
        ...

    # -- Provider Failover ---------------------------------------------------

    async def _call_with_failover(
        self,
        request: VisionRequest,
        preferred_provider: VisionProviderBase,
        exclude: Optional[set[VisionProviderName]] = None,
    ) -> VisionResponse:
        """
        Call a vision provider with automatic failover.

        1. Try preferred_provider.
        2. On failure (timeout, API error, rate limit), try next provider
           in factory priority order (skipping excluded set).
        3. If all providers fail, return VisionResponse(found=False).

        Args:
            request: The vision request.
            preferred_provider: First provider to try.
            exclude: Provider names to skip during failover.

        Returns:
            VisionResponse from the first successful provider,
            or VisionResponse(found=False) if all fail.
        """
        ...

    # -- Cost Tracking -------------------------------------------------------

    def total_cost(self) -> float:
        """Total USD spent on vision calls in this session."""
        ...

    def call_count(self) -> int:
        """Total number of vision calls made (excluding cache hits)."""
        ...

    def cache_stats(self) -> dict[str, Any]:
        """Return cache statistics: hit_rate, size, evictions."""
        ...
```

### Storage Schema

```json
{
  "version": 1,
  "entries": {
    "a1b2c3d4e5f6...": {
      "key": "a1b2c3d4e5f6...",
      "description": "the blue Submit button",
      "response": {
        "found": true,
        "x": 450.0,
        "y": 320.0,
        "confidence": 0.95,
        "model": "uitars",
        "token_cost": 0.0,
        "duration_ms": 1200.5
      },
      "image_dhash": 18446744073709551615,
      "created_at": 1745326800.123,
      "last_hit": 1745327100.456,
      "hit_count": 3
    }
  },
  "metadata": {
    "max_entries": 500,
    "dhash_threshold": 4,
    "created_at": 1745326800.0,
    "last_persisted": 1745327100.456
  }
}
```

---

## 5. Data Flow

```
                        MultimodalController (GAP-02)
                                   |
                          Tier 1 failed, Tier 2 failed
                                   |
                          VisionController.locate_element()
                                   |
                         +---------+----------+
                         | 1. Check VisionCache |
                         |    SHA-256(dhash +  |
                         |    description)     |
                         +---------+----------+
                                   |
                           +-------+-------+
                           |               |
                      Cache HIT       Cache MISS
                           |               |
                           v               v
                  Return cached     +------+------+
                  VisionResponse    | 2. AX Check  |
                  (no LLM call)     | (if snapshot |
                                    |  provided)   |
                                    +------+------+
                                           |
                                    +------+------+
                                    |             |
                                AX Match      No Match
                                    |             |
                                    v             v
                           Return coords    3. Classify Complexity
                           (no LLM call)    (rule-based, <1ms)
                                                    |
                                          +---------+---------+
                                          |         |         |
                                       SIMPLE   COMPLEX   AMBIGUOUS
                                          |         |         |
                                          v         v         v
                                    +------+--------------------------------+
                                    |  4. Model Cascade Selection         |
                                    |                                     |
                                    |  SIMPLE  -> UITARS (local, free)    |
                                    |  COMPLEX -> GPT-4o Mini ($0.15/1k)  |
                                    |  AMBIGUOUS-> Claude Sonnet ($3/1k)  |
                                    +-------------------------------------+
                                                    |
                                                    v
                                    +---------------+---------------+
                                    | 5. Call Provider              |
                                    |                               |
                                    | provider.locate(VisionRequest)|
                                    |   screenshot=<PNG bytes>      |
                                    |   description=<text>          |
                                    |   viewport_size=(W, H)        |
                                    +---------------+---------------+
                                                    |
                                            +-------+-------+
                                            |               |
                                         Success         Failure
                                         (response)    (API error/
                                            |          timeout/rate limit)
                                            |               |
                                            v               v
                                    +-------+----+   +------+------+
                                    | Confidence  |   | Failover to |
                                    | >= 0.6?     |   | next provider|
                                    +------+------+   | in priority  |
                                           |          | order        |
                                    +------+------+   +------+------+
                                    |             |          |
                                   Yes          No         Retry
                                    |             |          |
                                    v             v          v
                              +-----+----+  Escalate   (repeat from
                              | Return   |  to next    step 5 with
                              | response |  complexity  next provider,
                              |          |  tier       max 2 escalations)
                              +-----+----+
                                    |
                              +-----+-----+
                              | 6. Cache  |
                              | the result|
                              | SHA-256   |
                              | (dhash +  |
                              | desc)     |
                              +-----+-----+
                                    |
                              +-----+-----+
                              | Return    |
                              | VisionResp|
                              | to GAP-02 |
                              | Multimodal|
                              +-----------+


    OCR Grounding Fallback (step 7, when vision providers fail):

    All vision providers failed
              or
    description contains quoted text
              |
              v
    +---------+-----------+
    | OCRGrounding         |
    |                      |
    | 1. pytesseract       |
    |    image_to_data()   |
    |    word-level OCR    |
    |                      |
    | 2. Filter by         |
    |    confidence > 30   |
    |                      |
    | 3. Match description |
    |    against OCR words |
    |    (quoted text:     |
    |     direct match;    |
    |     otherwise: LLM   |
    |     phrase-to-word)  |
    |                      |
    | 4. Combine bounding  |
    |    boxes of matched  |
    |    words             |
    |                      |
    | 5. Return center of  |
    |    combined bbox     |
    +---------+-----------+
              |
              v
    VisionLocation(x, y, confidence)
    or None (no words matched)


    CAPTCHA Solving Flow:

    VisionController.solve_captcha()
              |
              v
    Classify: always COMPLEX or AMBIGUOUS
              |
              v
    Select provider (most capable available)
              |
              v
    Build CAPTCHA-specific prompt:
      - TEXT_DISTORTED: "Read the text in this image"
      - IMAGE_GRID: "Which grid cells contain {prompt}?"
      - RECAPTCHA_V2: "Click the checkbox" / "Select images"
      - HCAPTCHA: "Select all images matching {prompt}"
      - SLIDER: "What x-position should the slider be moved to?"
              |
              v
    Call provider.locate() or provider.analyze()
              |
              v
    Parse response into CaptchaSolution
              |
              v
    Return CaptchaSolution(solved=True/False, answer, ...)


    State Inference Flow:

    VisionController.infer_state()
              |
              v
    Route to COMPLEX tier
              |
              v
    Build state inference prompt:
      "Analyze this screenshot and answer: {question}.
       Return JSON: {answer: str, labels: {key: bool}, confidence: float}"
              |
              v
    Call provider
              |
              v
    Parse response into StateInference
              |
              v
    Return StateInference(answer, labels, confidence)
```

---

## 6. Dependencies

### Hard Dependencies (must exist before implementation)

| Dependency | Version | Purpose |
|------------|---------|---------|
| GAP-02: `VisionProvider` interface | Spec complete | Abstract base class that `VisionController` implements; `VisionRequest`/`VisionResponse` dataclasses |
| GAP-02: `MultimodalController` | Spec complete | Tier 3 calls `VisionController.locate_element()` as the final cascade fallback |
| GAP-02: `CDPBridge` | Spec complete | `capture_screenshot()` provides PNG bytes for vision analysis |
| GAP-02: `AXSnapshot` | Spec complete | AX tree used for pre-check before vision calls (skip vision when AX tree resolves target) |
| GAP-09: `TokenBudgetGovernor` | Spec complete | Cost tracking integration: vision calls check budget before execution and report costs after |
| Python | >= 3.11 | `abc.ABC`, `enum.Enum`, `dataclasses`, `asyncio` |
| `anthropic` SDK | >= 0.30 | `AnthropicCUAProvider` for Anthropic Computer Use API |
| `openai` SDK | >= 1.0 | `OpenAIResponseProvider` for OpenAI Responses API |

### Soft Dependencies (recommended, not blocking)

| Dependency | Purpose | Fallback if Absent |
|------------|---------|-------------------|
| `transformers` + `torch` | `UITARSProvider` requires UI-TARS model weights and transformers inference | UITARS provider disabled, cascade skips to cloud providers for SIMPLE tasks |
| `pytesseract` + Tesseract binary | `OCRGrounding` for text-based element location fallback | OCR grounding disabled, no secondary path when vision providers fail |
| `Pillow` (PIL) | Image processing for dHash computation and OCR preprocessing | Cache invalidation uses full screenshot hash (slower), OCR preprocessing skipped |
| GAP-11: Tracing subsystem | Log vision operations (provider, model, cost, duration, cache_hit) for observability | Vision operations proceed without tracing |
| GAP-01: `BrowserSession` | Screenshot capture via `CDPBridge.capture_screenshot()` | Caller must provide pre-captured screenshot bytes |

### Enables (gaps that depend on this one)

| Gap | What It Needs from GAP-06 |
|-----|--------------------------|
| GAP-03 (Visual Verification) | Vision providers for screenshot comparison, `infer_state()` for "did the action succeed" verification |
| GAP-04 (Self-Healing & Session Recovery) | Vision as last-resort recovery when selectors and coordinates both fail, `locate_element()` with AX fallback |
| GAP-08 (Stealth & Anti-Bot Layer) | `solve_captcha()` for CAPTCHA lifecycle handling, CAPTCHA type detection integrated with watchdog |
| GAP-07 (Agent Orchestration & Facade) | `VisionController` as the Tier 3 implementation behind `SuperBrowser.act()`, cost tracking exposed via `total_cost()` |

---

## 7. Acceptance Criteria

### AC1: VisionController Implements VisionProvider Interface
The `VisionController` class must implement the `VisionProvider` interface from GAP-02, specifically the `locate()` method accepting `VisionRequest` and returning `VisionResponse`. Calling `VisionController.locate(request)` must produce the same result signature as calling `controller.locate_element(screenshot, description, viewport_size)`.

### AC2: AnthropicCUAProvider Locates Elements
Given a screenshot of a page with a clearly visible blue "Submit" button, calling `AnthropicCUAProvider.locate(VisionRequest)` must return `VisionResponse(found=True, x=<coordinate>, y=<coordinate>, confidence>=0.7)`. The returned coordinates must be within 20 pixels of the actual button center when resized to viewport space.

### AC3: OpenAIResponseProvider Locates Elements
Given the same screenshot, calling `OpenAIResponseProvider.locate(VisionRequest)` must return `VisionResponse(found=True)` with coordinates within 20 pixels of the actual element center. The response must include `model="gpt-4o-mini"` and `token_cost > 0`.

### AC4: UITARSProvider Locates Elements Locally
Given a screenshot and description "the search bar", calling `UITARSProvider.locate(VisionRequest)` must return `VisionResponse(found=True)` with `token_cost=0.0` (local model, no API cost). The response must complete in under 5 seconds.

### AC5: Model Cascade Routes SIMPLE to Cheapest Provider
Calling `controller.locate_element(screenshot, "the search input field", viewport_size)` with `complexity=SIMPLE` must route to the UITARS provider (or whatever is configured as `cascade.simple_provider`). The response must have `model` matching the SIMPLE tier model. No COMPLEX or AMBIGUOUS tier provider should be called.

### AC6: Model Cascade Routes COMPLEX to Mid-Tier Provider
Calling `controller.solve_captcha(screenshot, CaptchaType.TEXT_DISTORTED)` must route to the COMPLEX tier provider (default: GPT-4o Mini). The response must have `provider` matching the COMPLEX tier provider.

### AC7: Model Cascade Escalates on Low Confidence
When a provider returns `VisionResponse(confidence=0.4)` (below the default threshold of 0.6), the controller must escalate to the next complexity tier's provider and retry. The final response must reflect the escalated provider's result, not the low-confidence result. A maximum of 2 escalations must be enforced.

### AC8: VisionCache Returns Cached Results for Static Layouts
After calling `controller.locate_element(screenshot, "Submit button", viewport)` which returns `VisionResponse(found=True, x=450, y=320)`, calling the same method with the same description and a visually identical screenshot (dHash difference <= 4 bits) must return the cached result without calling any vision provider. The `duration_ms` of the cached response must be under 5 ms.

### AC9: VisionCache Invalidates on Visual Change
After caching a result for description "Submit button", navigating to a different page (screenshot dHash difference > 4 bits) and calling `controller.locate_element(screenshot, "Submit button", viewport)` must NOT return the stale cached result. It must call the vision provider and return fresh coordinates.

### AC10: OCR Grounding Locates Text Elements
Given a screenshot containing a button with the text "Submit Order" rendered as an image (no DOM representation), calling `OCRGrounding.locate_by_text(screenshot, 'the button labeled "Submit Order"', viewport)` must return `VisionLocation` with coordinates within 30 pixels of the button center. The OCR path must complete in under 3 seconds.

### AC11: OCR Grounding as Fallback When Vision Fails
When all configured vision providers fail (API errors, timeouts) and OCR is enabled, calling `controller.locate_element(screenshot, 'the "Submit Order" button', viewport)` must fall back to OCR text grounding and return a result. The `raw_response` field must indicate "ocr_fallback".

### AC12: Provider Failover on API Error
When the primary provider (e.g., Anthropic) returns an API error (503, rate limit), the controller must automatically try the next provider in the factory's priority order (e.g., OpenAI) without raising an exception to the caller. The final response must reflect the failover provider's result.

### AC13: Health Check for Provider Availability
Calling `AnthropicCUAProvider.health_check()` with a valid API key must return `True` within 10 seconds. Calling it with an invalid API key must return `False`. Calling `UITARSProvider.health_check()` when model weights are not loaded must return `False`.

### AC14: Cost Tracking Integration
After making 5 vision calls with varying costs, calling `controller.total_cost()` must return the sum of all `token_cost` values from the 5 responses. Calling `controller.call_count()` must return 5 (excluding cache hits). The costs must be accurate to within 0.001 USD.

### AC15: CAPTCHA Solving
Given a screenshot of a text-distortion CAPTCHA, calling `controller.solve_captcha(screenshot, CaptchaType.TEXT_DISTORTED)` must return `CaptchaSolution(solved=True, answer=<text>, confidence>=0.5)`. The solution must route to a COMPLEX or AMBIGUOUS tier provider, never SIMPLE.

### AC16: State Inference
Given a screenshot of a page displaying an error banner, calling `controller.infer_state(screenshot, "Is there an error message visible?")` must return `StateInference(answer=<describes error>, labels={"has_error": True}, confidence>=0.7)`.

### AC17: Coordinate Resizing Accuracy
Given model output coordinates `(640, 360)` from a model with default resolution `(1280, 720)`, and viewport size `(1920, 1080)`, calling `resize_coordinates(640, 360, (1280, 720), (1920, 1080))` must return `(960, 540)` (exactly half of viewport dimensions). Given `(100, 50)` with the same resolutions, must return `(150, 75)`.

### AC18: VisionProviderFactory from Environment
Setting environment variables `SB_VISION_DEFAULT_PROVIDER=openai`, `SB_VISION_DEFAULT_MODEL=gpt-4o-mini`, `SB_OPENAI_API_KEY=sk-test` and calling `VisionProviderFactory.from_env()` must return a factory with the OpenAI provider as default and the specified model ID.

### Test Scenarios

| ID  | Scenario | Steps | Expected Outcome | AC |
|-----|----------|-------|------------------|----|
| T1  | Anthropic provider locates button | Capture screenshot of page with visible button, call `AnthropicCUAProvider.locate()` | `found=True`, coordinates within 20px of center | AC2 |
| T2  | OpenAI provider locates input field | Same screenshot, call `OpenAIResponseProvider.locate()` | `found=True`, `model="gpt-4o-mini"`, `token_cost > 0` | AC3 |
| T3  | UITARS provider locates element locally | Call `UITARSProvider.locate()` with UI-TARS model loaded | `found=True`, `token_cost=0.0`, completes in <5s | AC4 |
| T4  | SIMPLE task routes to UITARS | Call `locate_element()` with simple description, no ambiguity | UITARS provider called, not OpenAI or Anthropic | AC5 |
| T5  | COMPLEX task routes to OpenAI | Call `solve_captcha()` | OpenAI (or COMPLEX tier) provider called | AC6 |
| T6  | Low-confidence escalation | Mock provider returning confidence=0.4, call `locate_element()` | Controller escalates to next tier, response reflects escalated provider | AC7 |
| T7  | Cache hit on identical screenshot | Locate element, then locate again with same screenshot and description | Second call returns cached result, <5ms, no provider called | AC8 |
| T8  | Cache miss on visual change | Cache result, navigate to different page, locate same description | Cache invalidated, fresh provider call made | AC9 |
| T9  | OCR locates text button | Screenshot of image-rendered "Submit Order" button, call `locate_by_text()` | Coordinates within 30px of button center, <3s | AC10 |
| T10 | OCR fallback when vision fails | Disable all providers, call `locate_element()` with quoted text | OCR fallback activates, returns result with "ocr_fallback" marker | AC11 |
| T11 | Provider failover on API error | Mock Anthropic returning 503, call `locate_element()` | OpenAI (next in priority) called, response returned | AC12 |
| T12 | Health check passes with valid key | Call `AnthropicCUAProvider.health_check()` with valid key | Returns `True` in <10s | AC13 |
| T13 | Health check fails with invalid key | Call `AnthropicCUAProvider.health_check()` with invalid key | Returns `False` | AC13 |
| T14 | Cost tracking accuracy | Make 5 calls with known costs, check `total_cost()` and `call_count()` | `total_cost()` matches sum, `call_count()` == 5 | AC14 |
| T15 | Text CAPTCHA solving | Screenshot of text CAPTCHA, call `solve_captcha(TEXT_DISTORTED)` | `solved=True`, `answer` matches CAPTCHA text, uses COMPLEX/AMBIGUOUS tier | AC15 |
| T16 | State inference detects error | Screenshot with error banner, call `infer_state("Is there an error?")` | `labels={"has_error": True}`, `confidence >= 0.7` | AC16 |
| T17 | Coordinate resizing correctness | Call `resize_coordinates(640, 360, (1280, 720), (1920, 1080))` | Returns `(960, 540)` exactly | AC17 |
| T18 | Factory from environment variables | Set env vars, call `VisionProviderFactory.from_env()` | Factory has correct default provider and model | AC18 |
| T19 | Cache LRU eviction at capacity | Insert 501 entries into cache (max 500) | Oldest entry evicted, cache size remains 500 | AC8 |
| T20 | AX snapshot pre-check skips vision | Provide AX snapshot containing matching element, call `locate_element()` | No vision provider called, coordinates from AX tree returned | AC1 |

---

## 8. Novel Work

No novel work. All patterns are adopted from the seven reference projects:

- **Multi-provider abstraction**: Adopted from Stagehand CUA client factory (P1, P10)
- **Coordinate mapping and resizing**: Adopted from Stagehand coordinate mapping (P2) and Agent-S coordinate resizing (P4)
- **Visual grounding via local model**: Adopted from Agent-S UI-TARS integration (P3)
- **OCR text grounding**: Adopted from Agent-S pytesseract grounding (P5)
- **Vision-first loop**: Adopted from Skyvern screenshot+DOM analysis (P6)
- **AX tree baseline**: Adopted from agent-browser ref-based targeting (P7)
- **Model cascade**: Adopted from Skyvern per-role LLM and roadmap Phase 5 specification (P8)
- **Result caching**: Adopted from roadmap Phase 5 caching specification (P9)
- **VLM output parsing**: Adopted from UI-TARS-Desktop 6-format chain-of-responsibility parser (P11)
- **Image preprocessing**: Adopted from UI-TARS smart_resize with factor divisibility (P12)
- **Coordinate normalization**: Adopted from UI-TARS dual coordinate system (P13)
- **Prompt engineering**: Adopted from UI-TARS system prompt templates for grounding (P14)

The value of this gap is in composition: unifying seven independently developed vision approaches behind a single `VisionController` interface with multi-format VLM parsing, model cascade routing, provider failover, result caching, and OCR fallback. Each individual pattern is proven in its source project; the integration is the engineering effort.

---

## 9. Adoption Timeline

| Week | Deliverable | Source Pattern |
|------|-------------|----------------|
| 9 | `VisionProviderBase` abstract class with `locate()`, `health_check()`, and coordinate resizing | P2, P4 |
| 9 | `AnthropicCUAProvider` implementation with Computer Use API | P1, P2 |
| 9 | `OpenAIResponseProvider` implementation with Responses API | P1 |
| 9 | `UITARSProvider` implementation with local UI-TARS model | P3, P4 |
| 9 | 6-format action parser chain ported from TypeScript to Python | P11 |
| 9 | `smart_resize()` image pipeline for local model input | P12 |
| 9 | Dual coordinate normalizer (absolute vs relative) | P13 |
| 9 | Grounding-only system prompt template for single-step prediction | P14 |
| 9 | `VisionProviderFactory` with `from_env()` and provider priority | P10 |
| 9 | `CascadeConfig` and complexity classification (SIMPLE/COMPLEX/AMBIGUOUS) | P8 |
| 9 | `VisionController` with `locate_element()`, `solve_captcha()`, `infer_state()` | P6, P8 |
| 9 | Provider failover logic with health checks | P1 |
| 10 | `VisionCache` with LRU eviction, dHash invalidation, and persistence | P9 |
| 10 | `OCRGrounding` with pytesseract word-level OCR and phrase matching | P5 |
| 10 | AX snapshot pre-check integration (skip vision when AX resolves target) | P7 |
| 10 | Cost tracking integration with GAP-09 `TokenBudgetGovernor` | P8 |
| 10 | End-to-end tests: canvas pages, CAPTCHA demo, SVG icons, static layout caching | All |
