"""VisionController — orchestrator for vision-based element location."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from super_browser.interaction.types import VisionRequest, VisionResponse
from super_browser.interaction.vision import VisionProvider
from super_browser.vision.cache import VisionCache
from super_browser.vision.factory import VisionProviderFactory
from super_browser.vision.ocr import OCRGrounding
from super_browser.vision.types import (
    CaptchaSolution,
    CaptchaType,
    CascadeConfig,
    StateInference,
    VisionCostTracker,
    VisionTaskComplexity,
)

logger = logging.getLogger(__name__)

_COMPLEX_KEYWORDS = re.compile(
    r"captcha|recaptcha|hcaptcha|verify|prove\s+you|canvas|draw|toolbar|which|find\s+all|count",
    re.IGNORECASE,
)
_AMBIGUOUS_KEYWORDS = re.compile(
    r"\s+or\s+|either|whichever|one\s+of|any\s+of|best\s+match",
    re.IGNORECASE,
)


class VisionController(VisionProvider):
    """Vision-based element location controller with cascade, cache, and OCR fallback."""

    def __init__(
        self,
        factory: VisionProviderFactory,
        cache: Optional[VisionCache] = None,
        ocr: Optional[OCRGrounding] = None,
        cascade: Optional[CascadeConfig] = None,
        *,
        ax_snapshot_check: bool = True,
    ) -> None:
        self._factory = factory
        self._cache = cache
        self._ocr = ocr
        self._cascade = cascade or factory.cascade
        self._ax_snapshot_check = ax_snapshot_check
        self._cost_tracker = VisionCostTracker()

    # -- VisionProvider interface (drop-in for GAP-02 factory) --

    @property
    def name(self) -> str:
        return "vision_controller"

    @property
    def model_id(self) -> str:
        provider = self._factory.get_provider()
        return provider.model_id if provider else "none"

    async def locate(self, request: VisionRequest) -> VisionResponse:
        return await self.locate_element(
            request.screenshot,
            request.element_description,
            request.viewport_size,
        )

    # -- Core methods --

    async def locate_element(
        self,
        screenshot: bytes,
        description: str,
        viewport_size: tuple[int, int],
        *,
        complexity: Optional[VisionTaskComplexity] = None,
        ax_snapshot: Optional[Any] = None,
    ) -> VisionResponse:
        # 1. Cache check
        if self._cache:
            cached = self._cache.get(screenshot, description)
            if cached is not None:
                return cached

        # 2. AX snapshot pre-check
        if ax_snapshot is not None and self._ax_snapshot_check:
            ax_result = self._try_ax_resolve(ax_snapshot, description)
            if ax_result is not None:
                resp = VisionResponse(
                    found=True, x=ax_result[0], y=ax_result[1],
                    confidence=0.95, model="ax_snapshot",
                    raw_response="ax_pre_check",
                )
                if self._cache:
                    self._cache.put(screenshot, description, resp)
                return resp

        # 3. Classify complexity
        if complexity is None:
            complexity = self.classify_complexity(description)

        # 4-5. Select provider and call with failover + escalation
        response = await self._locate_with_cascade(
            screenshot, description, viewport_size, complexity,
        )

        # 7. OCR fallback
        if not response.found and self._ocr is not None:
            ocr_result = await self._ocr.locate_by_text(screenshot, description, viewport_size)
            if ocr_result is not None:
                response = VisionResponse(
                    found=True,
                    x=ocr_result.x,
                    y=ocr_result.y,
                    confidence=ocr_result.confidence,
                    model="ocr_fallback",
                    raw_response="ocr_fallback",
                )

        # 8. Cache result
        if self._cache and response.found:
            self._cache.put(screenshot, description, response)

        return response

    async def solve_captcha(
        self,
        screenshot: bytes,
        captcha_type: CaptchaType,
        *,
        prompt: Optional[str] = None,
        viewport_size: tuple[int, int] = (1280, 720),
    ) -> CaptchaSolution:
        complexity = VisionTaskComplexity.COMPLEX
        provider = self._factory.get_provider_for_complexity(complexity)
        if provider is None:
            return CaptchaSolution(solved=False)

        captcha_prompt = self._build_captcha_prompt(captcha_type, prompt)
        request = VisionRequest(
            screenshot=screenshot,
            element_description=captcha_prompt,
            page_url="",
            viewport_size=viewport_size,
        )
        start = time.monotonic()
        try:
            response = await self._call_with_failover(request, provider)
            dur = (time.monotonic() - start) * 1000
            self._cost_tracker.record(response.token_cost)

            answer = None
            grid_selections = None
            if response.found and response.raw_response:
                answer = response.raw_response
            elif response.found:
                answer = f"({response.x}, {response.y})"

            return CaptchaSolution(
                solved=response.found,
                answer=answer,
                grid_selections=grid_selections,
                provider=response.model,
                confidence=response.confidence,
                token_cost=response.token_cost,
                duration_ms=dur,
            )
        except Exception:
            dur = (time.monotonic() - start) * 1000
            return CaptchaSolution(solved=False, duration_ms=dur)

    async def infer_state(
        self,
        screenshot: bytes,
        question: str,
        *,
        viewport_size: tuple[int, int] = (1280, 720),
    ) -> StateInference:
        provider = self._factory.get_provider_for_complexity(VisionTaskComplexity.COMPLEX)
        if provider is None:
            return StateInference(answer="No provider available", confidence=0.0)

        request = VisionRequest(
            screenshot=screenshot,
            element_description=(
                f"Analyze this screenshot and answer: {question}. "
                'Return JSON: {"answer": str, "labels": {str: bool}, "confidence": float}'
            ),
            page_url="",
            viewport_size=viewport_size,
        )
        start = time.monotonic()
        try:
            response = await self._call_with_failover(request, provider)
            dur = (time.monotonic() - start) * 1000
            self._cost_tracker.record(response.token_cost)
            if response.raw_response:
                import json
                try:
                    data = json.loads(response.raw_response)
                    return StateInference(
                        answer=data.get("answer", ""),
                        labels=data.get("labels", {}),
                        confidence=data.get("confidence", response.confidence),
                        model=response.model,
                        token_cost=response.token_cost,
                        duration_ms=dur,
                    )
                except (json.JSONDecodeError, ValueError):
                    pass
            return StateInference(
                answer=response.raw_response or "Unable to determine state",
                confidence=response.confidence,
                model=response.model,
                token_cost=response.token_cost,
                duration_ms=dur,
            )
        except Exception as exc:
            dur = (time.monotonic() - start) * 1000
            return StateInference(answer=f"Error: {exc}", confidence=0.0, duration_ms=dur)

    # -- Complexity classification --

    def classify_complexity(self, description: str) -> VisionTaskComplexity:
        if _AMBIGUOUS_KEYWORDS.search(description) or len(description) > 100:
            return VisionTaskComplexity.AMBIGUOUS
        if _COMPLEX_KEYWORDS.search(description):
            return VisionTaskComplexity.COMPLEX
        return VisionTaskComplexity.SIMPLE

    # -- Provider failover --

    async def _call_with_failover(
        self,
        request: VisionRequest,
        preferred_provider: Any,
        exclude: Optional[set[str]] = None,
    ) -> VisionResponse:
        exclude = exclude or set()
        try:
            response = await preferred_provider.locate(request)
            if response.found:
                return response
            if response.model:
                exclude.add(str(response.model))
        except Exception:
            if hasattr(preferred_provider, "name"):
                exclude.add(str(preferred_provider.name))

        for name in self._factory.provider_priority:
            if name in exclude:
                continue
            provider = self._factory.get_provider(name)
            if provider is None or provider is preferred_provider:
                continue
            try:
                response = await provider.locate(request)
                if response.found:
                    return response
            except Exception:
                continue

        return VisionResponse(found=False)

    # -- Cascade with escalation --

    async def _locate_with_cascade(
        self,
        screenshot: bytes,
        description: str,
        viewport_size: tuple[int, int],
        complexity: VisionTaskComplexity,
    ) -> VisionResponse:
        complexities = [complexity]
        if complexity == VisionTaskComplexity.SIMPLE:
            complexities.append(VisionTaskComplexity.COMPLEX)
            complexities.append(VisionTaskComplexity.AMBIGUOUS)
        elif complexity == VisionTaskComplexity.COMPLEX:
            complexities.append(VisionTaskComplexity.AMBIGUOUS)

        escalations = 0
        for comp in complexities:
            if escalations >= self._cascade.max_escalations and comp != complexity:
                break
            provider = self._factory.get_provider_for_complexity(comp)
            if provider is None:
                continue

            request = VisionRequest(
                screenshot=screenshot,
                element_description=description,
                page_url="",
                viewport_size=viewport_size,
            )

            start = time.monotonic()
            response = await self._call_with_failover(request, provider)
            dur = (time.monotonic() - start) * 1000  # noqa: F841

            if response.found:
                self._cost_tracker.record(response.token_cost)
                if response.confidence >= self._cascade.confidence_threshold_for_escalation:
                    return response
                escalations += 1
                if comp == complexities[-1]:
                    return response
            else:
                escalations += 1

        return VisionResponse(found=False)

    # -- AX snapshot pre-check --

    def _try_ax_resolve(
        self,
        ax_snapshot: Any,
        description: str,
    ) -> Optional[tuple[float, float]]:
        try:
            nodes = ax_snapshot.find_by_text(description)
            if nodes:
                for node in nodes:
                    if node.center:
                        return node.center
            quoted = None
            if '"' in description:
                import re
                m = re.search(r'"([^"]+)"', description)
                if m:
                    quoted = m.group(1)
            if quoted:
                nodes = ax_snapshot.find_by_text(quoted)
                if nodes:
                    for node in nodes:
                        if node.center:
                            return node.center
        except Exception:
            pass
        return None

    # -- CAPTCHA prompt builder --

    def _build_captcha_prompt(self, captcha_type: CaptchaType, prompt: Optional[str]) -> str:
        prompts = {
            CaptchaType.TEXT_DISTORTED: "Read the text in this image",
            CaptchaType.IMAGE_GRID: f"Which grid cells contain {prompt or 'the target'}?",
            CaptchaType.RECAPTCHA_V2: "Click the checkbox or select matching images",
            CaptchaType.HCAPTCHA: f"Select all images matching {prompt or 'the target'}",
            CaptchaType.SLIDER: "What x-position should the slider be moved to?",
        }
        return prompts.get(captcha_type, "Analyze this CAPTCHA image")

    # -- Cost tracking --

    def total_cost(self) -> float:
        return self._cost_tracker.total_cost

    def call_count(self) -> int:
        return self._cost_tracker.call_count

    def cache_stats(self) -> dict[str, Any]:
        if self._cache is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "hit_rate": self._cache.hit_rate,
            "size": self._cache.size,
        }
