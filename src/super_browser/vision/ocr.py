"""OCRGrounding — text-based element location via pytesseract."""

from __future__ import annotations

import logging
import re
from typing import Optional

from super_browser.vision.types import OCRWord, VisionLocation

logger = logging.getLogger(__name__)

_HAS_TESSERACT = False
try:
    from io import BytesIO

    import pytesseract
    from PIL import Image
    _HAS_TESSERACT = True
except ImportError:
    pass


class OCRGrounding:
    """OCR-based text grounding as a secondary element location path."""

    def __init__(self, tesseract_config: Optional[str] = None) -> None:
        self._config = tesseract_config or "--psm 11"

    async def locate_by_text(
        self,
        screenshot: bytes,
        description: str,
        viewport_size: tuple[int, int],
    ) -> Optional[VisionLocation]:
        if not _HAS_TESSERACT:
            return None
        words = self.extract_words(screenshot)
        if not words:
            return None
        quoted = self._extract_quoted_text(description)
        if quoted:
            return self.match_quoted_text(words, quoted)
        return self._match_description(words, description)

    def extract_words(self, screenshot: bytes) -> list[OCRWord]:
        if not _HAS_TESSERACT:
            return []
        try:
            img = Image.open(BytesIO(screenshot)).convert("RGB")
            data = pytesseract.image_to_data(img, config=self._config, output_type=pytesseract.Output.DICT)
            words: list[OCRWord] = []
            n = len(data.get("text", []))
            for i in range(n):
                text = data["text"][i].strip()
                conf = int(data["conf"][i])
                if not text or conf <= 30:
                    continue
                words.append(OCRWord(
                    text=text,
                    x=float(data["left"][i]),
                    y=float(data["top"][i]),
                    width=float(data["width"][i]),
                    height=float(data["height"][i]),
                    confidence=float(conf) / 100.0,
                ))
            return words
        except Exception as exc:
            logger.warning("OCR extraction failed: %s", exc)
            return []

    def match_quoted_text(
        self,
        words: list[OCRWord],
        quoted_text: str,
    ) -> Optional[VisionLocation]:
        if not words:
            return None
        target = quoted_text.lower()
        target_words = target.split()
        if len(target_words) == 1:
            for w in words:
                if w.text.lower() == target_words[0]:
                    return VisionLocation(
                        x=w.x + w.width / 2,
                        y=w.y + w.height / 2,
                        width=w.width,
                        height=w.height,
                        confidence=w.confidence,
                    )
            return None
        best: Optional[list[OCRWord]] = None
        for i in range(len(words) - len(target_words) + 1):
            seq = words[i:i + len(target_words)]
            combined = " ".join(w.text.lower() for w in seq)
            if combined == target:
                if best is None:
                    best = seq
        if best is not None:
            return self._combine_boxes(best)
        return None

    def _combine_boxes(self, words: list[OCRWord]) -> VisionLocation:
        if not words:
            raise ValueError("Cannot combine empty word list")
        min_x = min(w.x for w in words)
        min_y = min(w.y for w in words)
        max_x = max(w.x + w.width for w in words)
        max_y = max(w.y + w.height for w in words)
        avg_conf = sum(w.confidence for w in words) / len(words)
        return VisionLocation(
            x=(min_x + max_x) / 2,
            y=(min_y + max_y) / 2,
            width=max_x - min_x,
            height=max_y - min_y,
            confidence=avg_conf,
        )

    def _extract_quoted_text(self, description: str) -> Optional[str]:
        m = re.search(r'"([^"]+)"', description)
        if m:
            return m.group(1)
        m = re.search(r"'([^']+)'", description)
        if m:
            return m.group(1)
        return None

    def _match_description(
        self,
        words: list[OCRWord],
        description: str,
    ) -> Optional[VisionLocation]:
        desc_lower = description.lower()
        matches: list[OCRWord] = []
        for w in words:
            if w.text.lower() in desc_lower:
                matches.append(w)
        if matches:
            return self._combine_boxes(matches)
        return None
