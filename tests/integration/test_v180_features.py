"""Integration tests for v1.8.0 — Live QA hardening."""

from __future__ import annotations

from packaging.version import Version as _V

from super_browser import __version__
from super_browser.interaction.recovery import StaleRefDetector


class TestV180Version:
    """Version is 1.8.0."""

    def test_version_string(self) -> None:
        assert _V(__version__) >= _V("1.8.0")


class TestV180StaleSignatures:
    """Live QA finding: 2 new stale-ref signatures added."""

    def test_not_found_is_stale(self) -> None:
        assert StaleRefDetector.is_stale(Exception("Element @e4 not found"))

    def test_detached_from_document_is_stale(self) -> None:
        assert StaleRefDetector.is_stale(Exception("element is detached from document"))

    def test_signature_count_is_10(self) -> None:
        assert len(StaleRefDetector.STALE_SIGNATURES) == 10

    def test_non_stale_still_false(self) -> None:
        assert not StaleRefDetector.is_stale(Exception("Network error"))
        assert not StaleRefDetector.is_stale(Exception("connection refused"))
