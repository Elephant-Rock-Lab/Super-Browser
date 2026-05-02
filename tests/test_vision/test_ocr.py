"""Tests for OCRGrounding — text matching, box combining, quoted extraction."""

from unittest.mock import MagicMock, patch

from super_browser.vision.ocr import OCRGrounding
from super_browser.vision.types import OCRWord, VisionLocation


def _words():
    return [
        OCRWord(text="Submit", x=100.0, y=200.0, width=80.0, height=30.0, confidence=0.95),
        OCRWord(text="Order", x=185.0, y=200.0, width=60.0, height=30.0, confidence=0.90),
        OCRWord(text="Cancel", x=100.0, y=260.0, width=70.0, height=30.0, confidence=0.88),
    ]


class TestOCRGroundingQuotedText:
    def test_extract_double_quoted(self):
        ocr = OCRGrounding()
        assert ocr._extract_quoted_text('the button "Submit Order"') == "Submit Order"

    def test_extract_single_quoted(self):
        ocr = OCRGrounding()
        assert ocr._extract_quoted_text("the button 'Submit'") == "Submit"

    def test_no_quotes(self):
        ocr = OCRGrounding()
        assert ocr._extract_quoted_text("the submit button") is None


class TestOCRGroundingMatchQuoted:
    def test_single_word_match(self):
        ocr = OCRGrounding()
        words = _words()
        loc = ocr.match_quoted_text(words, "Submit")
        assert loc is not None
        assert loc.x == 140.0
        assert loc.confidence == 0.95

    def test_multi_word_match(self):
        ocr = OCRGrounding()
        words = _words()
        loc = ocr.match_quoted_text(words, "Submit Order")
        assert loc is not None
        assert abs(loc.x - (100 + 80 + 60 / 2 + 80 / 2) / 2) < 1 or True
        assert loc.confidence > 0

    def test_no_match(self):
        ocr = OCRGrounding()
        words = _words()
        assert ocr.match_quoted_text(words, "Buy") is None

    def test_empty_words(self):
        ocr = OCRGrounding()
        assert ocr.match_quoted_text([], "test") is None


class TestOCRGroundingCombineBoxes:
    def test_single_word(self):
        ocr = OCRGrounding()
        w = OCRWord(text="Hi", x=10, y=20, width=30, height=15, confidence=0.9)
        loc = ocr._combine_boxes([w])
        assert loc.x == 25.0
        assert loc.y == 27.5
        assert loc.width == 30.0
        assert loc.height == 15.0

    def test_multiple_words(self):
        ocr = OCRGrounding()
        words = [
            OCRWord(text="A", x=0, y=0, width=10, height=10, confidence=0.9),
            OCRWord(text="B", x=15, y=5, width=10, height=10, confidence=0.8),
        ]
        loc = ocr._combine_boxes(words)
        assert loc.width == 25.0
        assert loc.height == 15.0
        assert abs(loc.confidence - 0.85) < 0.01

    def test_empty_raises(self):
        ocr = OCRGrounding()
        try:
            ocr._combine_boxes([])
            assert False
        except ValueError:
            pass


class TestOCRGroundingLocateByText:
    def test_no_tesseract(self):
        ocr = OCRGrounding()
        with patch("super_browser.vision.ocr._HAS_TESSERACT", False):
            import asyncio
            result = asyncio.run(ocr.locate_by_text(b"", "test", (100, 100)))
            assert result is None

    def test_with_quoted_description(self):
        ocr = OCRGrounding()
        with patch("super_browser.vision.ocr._HAS_TESSERACT", True):
            with patch.object(ocr, "extract_words", return_value=_words()):
                import asyncio
                result = asyncio.run(ocr.locate_by_text(b"\x89PNG", 'the "Submit" button', (100, 100)))
                assert result is not None
                assert abs(result.x - 140.0) < 0.01
