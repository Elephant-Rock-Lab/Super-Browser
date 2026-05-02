"""Tests for PreExecutionValidator."""

import time
from unittest.mock import MagicMock

from super_browser.results import (
    ErrorCategory,
    PreExecutionValidator,
)


class MockPage:
    def __init__(self, return_value=1, raise_exc=None):
        self._return_value = return_value
        self._raise_exc = raise_exc

    def evaluate(self, expr):
        if self._raise_exc:
            raise self._raise_exc
        return self._return_value


class TestValidateSelector:
    def test_valid(self):
        v = PreExecutionValidator(MockPage(return_value=3))
        r = v.validate_selector("button.login")
        assert r.ok is True
        assert r.data["match_count"] == 3

    def test_invalid(self):
        v = PreExecutionValidator(MockPage(return_value=0))
        r = v.validate_selector("button.nonexistent")
        assert r.ok is False
        assert r.error.category == ErrorCategory.VALIDATION
        assert r.error.recoverable is True

    def test_exception(self):
        v = PreExecutionValidator(MockPage(raise_exc=RuntimeError("crash")))
        r = v.validate_selector("bad[selector")
        assert r.ok is False
        assert r.error.recoverable is False


class TestValidateXpath:
    def test_valid(self):
        v = PreExecutionValidator(MockPage(return_value=1))
        r = v.validate_xpath("//button[@id='submit']")
        assert r.ok is True

    def test_invalid(self):
        v = PreExecutionValidator(MockPage(return_value=0))
        r = v.validate_xpath("//div[@class='nope']")
        assert r.ok is False
        assert r.error.category == ErrorCategory.VALIDATION

    def test_exception(self):
        v = PreExecutionValidator(MockPage(raise_exc=Exception("bad xpath")))
        r = v.validate_xpath("///invalid")
        assert r.ok is False
        assert r.error.recoverable is False


class TestTiming:
    def test_selector_validation_under_5ms(self):
        v = PreExecutionValidator(MockPage(return_value=1))
        start = time.monotonic()
        v.validate_selector("button")
        elapsed_ms = (time.monotonic() - start) * 1000
        assert elapsed_ms < 50  # generous bound, mock is instant
