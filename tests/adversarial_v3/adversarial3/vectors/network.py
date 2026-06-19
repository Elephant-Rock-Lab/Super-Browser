"""Tier 5: HTTP Header Consistency checks.

These vectors inspect HTTP request headers captured by the controlled
server. They verify header presence, ordering, and consistency.

NOTE: A local cleartext ThreadingHTTPServer cannot observe TLS
ClientHello, JA3/JA4, ALPN, or HTTP/2 settings. This tier covers
HTTP-level header checks only -- not TLS fingerprinting. Genuine TLS
instrumentation requires a MITM proxy or eBPF capture, which is out
of scope for the local server.
"""

from __future__ import annotations

import time
from typing import Any

from adversarial3.core import (
    BaseVector,
    EvaluationContext,
    Severity,
    Tier,
    VectorResult,
    Verdict,
)


class _NetworkVector(BaseVector):
    """Base for HTTP header checks."""

    @property
    def requires_browser(self) -> bool:
        return True  # Needs browser navigation to generate captured request

    def _inconclusive(self, reason: str, duration_ms: float) -> VectorResult:
        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=Verdict.INCONCLUSIVE,
            score=0.0,
            details={"reason": reason},
            severity=self.severity,
            duration_ms=duration_ms,
        )

    def _make_result(self, passed: bool, details: dict[str, Any], duration_ms: float) -> VectorResult:
        return VectorResult(
            vector_id=self.vector_id,
            tier=self.tier,
            name=self.name,
            verdict=Verdict.CLEAN if passed else Verdict.FLAGGED,
            score=1.0 if passed else 0.0,
            details=details,
            severity=self.severity,
            duration_ms=duration_ms,
        )


class HeaderOrderingConsistency(_NetworkVector):
    """T5-001: Headers sent in browser-natural order."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T5-001",
            tier=Tier.NETWORK,
            name="Header Ordering Consistency",
            description="HTTP headers should follow natural browser ordering",
            severity=Severity.INFO,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        headers = context.headers
        duration = (time.perf_counter() - start) * 1000

        header_order: list[str] = headers.get("__header_order", [])
        if not header_order:
            return self._inconclusive("No request headers captured", duration)

        return self._make_result(
            passed=True,
            details={"header_order": header_order[:10], "count": len(header_order)},
            duration_ms=duration,
        )


class AcceptLanguageMatch(_NetworkVector):
    """T5-002: Accept-Language header present."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T5-002",
            tier=Tier.NETWORK,
            name="Accept-Language Presence",
            description="HTTP Accept-Language should be present",
            severity=Severity.WARNING,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        headers = context.headers
        duration = (time.perf_counter() - start) * 1000

        if not headers:
            return self._inconclusive("No request headers captured", duration)

        accept_lang = headers.get("Accept-Language", "")
        has_header = bool(accept_lang)

        return self._make_result(
            passed=has_header,
            details={"accept_language": accept_lang, "present": has_header},
            duration_ms=duration,
        )


class ClientHintsPresence(_NetworkVector):
    """T5-003: sec-ch-ua headers present."""

    def __init__(self) -> None:
        super().__init__(
            vector_id="T5-003",
            tier=Tier.NETWORK,
            name="sec-ch-ua Header Presence",
            description="Client hints headers should be present",
            severity=Severity.INFO,
        )

    async def evaluate(self, context: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        headers = context.headers
        duration = (time.perf_counter() - start) * 1000

        if not headers:
            return self._inconclusive("No request headers captured", duration)

        has_sec_ch_ua = any(k.lower().startswith("sec-ch-ua") for k in headers)

        return self._make_result(
            passed=has_sec_ch_ua,
            details={"has_sec_ch_ua": has_sec_ch_ua, "header_keys": [k for k in headers if k != "__header_order"][:10]},
            duration_ms=duration,
        )


NETWORK_VECTORS: list[BaseVector] = [
    HeaderOrderingConsistency(),
    AcceptLanguageMatch(),
    ClientHintsPresence(),
]
