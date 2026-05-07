"""Typed result payloads for each action kind."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from super_browser.results.types import ActionMethod, CompletionReason


@dataclass
class ClickResult:
    target: str
    method: ActionMethod
    coordinates: Optional[tuple[float, float]] = None
    element_tag: Optional[str] = None
    page_changed: Optional[bool] = None


@dataclass
class NavigateResult:
    url: str
    final_url: str
    status_code: Optional[int] = None
    title: Optional[str] = None
    redirect_chain: list[str] = field(default_factory=list)
    load_time_ms: Optional[float] = None


@dataclass
class ExtractResult:
    selector: str
    extracted: Any
    schema_used: Optional[dict] = None
    element_count: int = 0
    truncated: bool = False


@dataclass
class ScreenshotResult:
    image_hash: str
    width: int
    height: int
    format: str = "png"
    file_path: Optional[str] = None
    base64_preview: Optional[str] = None


@dataclass
class FillResult:
    selector: str
    value_entered: str
    method: ActionMethod
    character_count: int = 0
    clear_first: bool = True


@dataclass
class SelectResult:
    selector: str
    option: str
    method: ActionMethod
    by: str = "text"


@dataclass
class HoverResult:
    target: str
    method: ActionMethod
    coordinates: Optional[tuple[float, float]] = None


@dataclass
class DragResult:
    source: str
    destination: str
    method: ActionMethod
    source_coords: Optional[tuple[float, float]] = None
    dest_coords: Optional[tuple[float, float]] = None


@dataclass
class ScrollResult:
    direction: str
    amount: int
    method: ActionMethod


@dataclass
class KeypressResult:
    key: str
    modifiers: int = 0


@dataclass
class JSEvalResult:
    expression: str
    result_type: str
    result: Any
    console_errors: list[str] = field(default_factory=list)


@dataclass
class DelegatedResult:
    instruction: str
    completion_reason: CompletionReason
    summary: str
    steps_executed: int
    budget_remaining: float
    execution_history: list[dict] = field(default_factory=list)


@dataclass
class SpilledResult:
    preview: str
    file_path: str
    original_type: str
    original_size_chars: int


@dataclass
class DownloadResult:
    """Result from a file download."""
    url: str
    file_path: str
    file_size_bytes: int = 0
    mime_type: Optional[str] = None
    suggested_filename: Optional[str] = None


@dataclass
class UploadResult:
    """Result from a file upload."""
    selector: str
    file_path: str
    file_name: str
    success: bool = True


@dataclass
class ShadowQueryResult:
    """Result from querying inside a Shadow DOM."""
    host_selector: str
    inner_selector: str
    text: Optional[str] = None
    bounds: Optional[dict] = None
    found: bool = False


@dataclass
class NetworkInterceptResult:
    """Result from a network interception action."""
    pattern: str
    action: str  # "block", "mock", "modify"
    request_count: int = 0
    active: bool = True


# Tuple of all typed result classes for isinstance checks
TYPED_RESULT_TYPES = (
    ClickResult, NavigateResult, ExtractResult, ScreenshotResult,
    FillResult, SelectResult, HoverResult, DragResult, ScrollResult,
    KeypressResult, JSEvalResult, DelegatedResult, SpilledResult,
    DownloadResult, UploadResult, ShadowQueryResult, NetworkInterceptResult,
)
