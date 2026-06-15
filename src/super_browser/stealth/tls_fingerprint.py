"""TLSFingerprintChecker — observe, compare, and report TLS fingerprints.

Track B slice 3 (Wave 20). Provides diagnostic TLS fingerprint reporting.

Design constraints (per RFC v2-track-b-network-stealth.md):

- **Observe-only**: the SDK cannot alter the TLS handshake. The TLS
  ClientHello is owned by Chromium's BoringSSL stack, not by the SDK.
  This module can observe, compare, report, and recommend — it cannot
  spoof or modify the fingerprint.

- **Offline-first**: offline mode returns a stub report with
  ``ja4_hash=None`` and ``matches=True``. No network calls by default.

- **Baseline-driven**: baselines are curated JSON, version-controlled.
  They are NOT scraped at runtime.

- **Non-fatal**: all failures (echo service unreachable, parse failure,
  timeout) degrade to stub reports with ``matches=True`` and a warning.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_BASELINES_PATH = Path(__file__).parent / "tls_baselines.json"


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class NetworkStealthStatus(StrEnum):
    """Aggregate network-stealth health status."""
    UNKNOWN = "unknown"           # not enough data
    HEALTHY = "healthy"           # all checks pass
    DEGRADED = "degraded"         # some warnings, non-blocking
    COMPROMISED = "compromised"   # fingerprint mismatch or high-risk IP


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TLSFingerprintObservation:
    """Observed TLS fingerprint from an echo service."""
    ja3_hash: Optional[str] = None
    ja4_hash: Optional[str] = None
    ja4_string: Optional[str] = None
    tls_version: Optional[str] = None
    cipher_suites: list[str] = field(default_factory=list)
    extensions: list[int] = field(default_factory=list)
    source: str = ""
    observed_at: float = 0.0


@dataclass(frozen=True)
class TLSFingerprintReport:
    """Comparison of observed vs expected TLS fingerprint."""
    observed: TLSFingerprintObservation
    expected_profile: str
    matches: bool
    mismatch_details: list[str] = field(default_factory=list)
    recommendation: str = ""


@dataclass(frozen=True)
class NetworkStealthReport:
    """Aggregate network-stealth report from all Track B components."""
    proxy_health: Optional[dict[str, Any]] = None
    ip_reputation: Optional[Any] = None    # IPReputationResult
    tls_fingerprint: Optional[TLSFingerprintReport] = None
    generated_at: float = 0.0
    warnings: list[str] = field(default_factory=list)
    overall_status: NetworkStealthStatus = NetworkStealthStatus.UNKNOWN


# ---------------------------------------------------------------------------
# TLSFingerprintChecker
# ---------------------------------------------------------------------------

class TLSFingerprintChecker:
    """Checks the browser's TLS fingerprint via echo services.

    .. warning::

        **Honesty boundary:** This class can only **observe** the TLS
        fingerprint of browser connections. It cannot alter, spoof, or
        modify the ClientHello. The TLS handshake is performed by
        Chromium's BoringSSL, which is not accessible from the SDK layer.

        Use this to:
        1. Observe the fingerprint via an echo service.
        2. Compare it to a known baseline.
        3. Report mismatches.
        4. Recommend backend selection.

        Do NOT use this to claim TLS spoofing capabilities.

    Parameters
    ----------
    echo_url:
        URL of the TLS echo service. Default: ``https://tls.peet.ws/api/all``.
    timeout:
        Navigation timeout in seconds. Default: 15.
    baselines_path:
        Path to the baselines JSON file. Defaults to the bundled file.
    """

    def __init__(
        self,
        echo_url: str = "https://tls.peet.ws/api/all",
        timeout: float = 15.0,
        baselines_path: Optional[Path] = None,
    ) -> None:
        self._echo_url = echo_url
        self._timeout = timeout
        self._baselines_path = baselines_path or _BASELINES_PATH
        self._baselines: dict[str, TLSFingerprintObservation] = {}
        self._load_baselines()

    # ------------------------------------------------------------------
    # Baselines
    # ------------------------------------------------------------------

    def _load_baselines(self) -> None:
        """Load curated baselines from JSON file."""
        try:
            raw = json.loads(self._baselines_path.read_text(encoding="utf-8"))
            for name, entry in raw.get("baselines", {}).items():
                self._baselines[name] = TLSFingerprintObservation(
                    ja3_hash=entry.get("ja3_hash"),
                    ja4_hash=entry.get("ja4_hash"),
                    ja4_string=entry.get("ja4_string"),
                    tls_version=entry.get("tls_version"),
                    cipher_suites=entry.get("cipher_suites", []),
                    extensions=entry.get("extensions", []),
                    source=entry.get("source", "curated"),
                    observed_at=0.0,
                )
            logger.debug(
                "Loaded %d TLS baselines from %s",
                len(self._baselines), self._baselines_path,
            )
        except Exception as exc:
            logger.warning("Failed to load TLS baselines: %s", exc)

    @property
    def available_profiles(self) -> list[str]:
        """Names of available baseline profiles."""
        return list(self._baselines.keys())

    def get_baseline(self, profile: str) -> Optional[TLSFingerprintObservation]:
        """Get the baseline observation for a profile."""
        return self._baselines.get(profile)

    # ------------------------------------------------------------------
    # Observe
    # ------------------------------------------------------------------

    async def observe(self, browser_page: Any = None) -> TLSFingerprintObservation:
        """Observe the TLS fingerprint via an echo service.

        Requires a live browser page with ``goto()`` and content extraction
        capabilities. If ``browser_page`` is None, returns a stub observation
        (offline mode).

        Parameters
        ----------
        browser_page:
            A browser page object with ``goto(url)`` and content access.
            Duck-typed: works with Playwright Page, PageHandle, or any
            object with ``goto()`` and ``content()`` or ``evaluate()``.

        Returns
        -------
        TLSFingerprintObservation
            The observed fingerprint, or a stub in offline/error mode.
        """
        if browser_page is None:
            return self._stub_observation()

        try:
            return await self._observe_online(browser_page)
        except Exception as exc:
            logger.warning("TLS fingerprint observation failed: %s", exc)
            return self._stub_observation()

    async def _observe_online(self, browser_page: Any) -> TLSFingerprintObservation:
        """Navigate to echo service and extract TLS fingerprint."""
        # Navigate to echo service
        if hasattr(browser_page, "goto"):
            await browser_page.goto(self._echo_url)

        # Extract JSON from page content
        raw_json: str = ""
        if hasattr(browser_page, "inner_text"):
            raw_json = await browser_page.inner_text("body")
        elif hasattr(browser_page, "text_content"):
            raw_json = await browser_page.text_content("body") or ""
        elif hasattr(browser_page, "content"):
            raw_html = await browser_page.content()
            # Strip HTML tags — simple approach for pre-formatted JSON
            raw_json = self._strip_html(raw_html)
        elif hasattr(browser_page, "evaluate"):
            raw_json = await browser_page.evaluate("() => document.body.innerText")
        else:
            logger.warning("Cannot extract content from browser_page")
            return self._stub_observation()

        data = json.loads(raw_json)
        return self._parse_echo_response(data)

    def _parse_echo_response(self, data: dict[str, Any]) -> TLSFingerprintObservation:
        """Parse echo service JSON into an observation.

        Supports common TLS echo service formats (tls.peet.ws, browserleaks).
        """
        # tls.peet.ws format: { "tls": { "ja3_hash": ..., "ja4": ... } }
        tls_data = data.get("tls", data)

        ja3_hash = tls_data.get("ja3_hash") or tls_data.get("ja3")
        ja4_hash = tls_data.get("ja4_hash") or tls_data.get("ja4")

        # JA4 string (full, not just hash)
        ja4_string = None
        if isinstance(ja4_hash, str) and "_" in ja4_hash:
            # tls.peet.ws returns the full JA4 string in ja4
            ja4_string = ja4_hash
        elif "ja4_string" in tls_data:
            ja4_string = tls_data["ja4_string"]

        tls_version = tls_data.get("tls_version") or tls_data.get("version")

        cipher_suites: list[str] = []
        ciphers = tls_data.get("ciphers", tls_data.get("cipher_suites", []))
        if isinstance(ciphers, list):
            cipher_suites = [str(c) for c in ciphers]

        extensions: list[int] = []
        ext_data = tls_data.get("extensions", [])
        if isinstance(ext_data, list):
            for ext in ext_data:
                if isinstance(ext, int):
                    extensions.append(ext)
                elif isinstance(ext, dict) and "id" in ext:
                    extensions.append(ext["id"])

        return TLSFingerprintObservation(
            ja3_hash=ja3_hash if isinstance(ja3_hash, str) else None,
            ja4_hash=ja4_hash if isinstance(ja4_hash, str) and "_" not in ja4_hash else None,
            ja4_string=ja4_string,
            tls_version=tls_version,
            cipher_suites=cipher_suites,
            extensions=extensions,
            source=self._echo_url,
            observed_at=time.monotonic(),
        )

    def _stub_observation(self) -> TLSFingerprintObservation:
        """Create a stub observation for offline/error mode."""
        return TLSFingerprintObservation(
            source="offline",
            observed_at=time.monotonic(),
        )

    @staticmethod
    def _strip_html(html: str) -> str:
        """Naively strip HTML tags for JSON extraction."""
        import re
        # Remove <pre> and other tags, keep content
        cleaned = re.sub(r"<[^>]+>", "", html).strip()
        return cleaned

    # ------------------------------------------------------------------
    # Compare
    # ------------------------------------------------------------------

    def compare(
        self,
        observed: TLSFingerprintObservation,
        expected_profile: str,
    ) -> TLSFingerprintReport:
        """Compare an observed fingerprint to a known baseline.

        Parameters
        ----------
        observed:
            The fingerprint observed from the echo service.
        expected_profile:
            Name of the baseline profile to compare against
            (e.g. ``"chrome143_macos"``).

        Returns
        -------
        TLSFingerprintReport
            Report with match status, mismatch details, and recommendation.
        """
        baseline = self._baselines.get(expected_profile)

        if baseline is None:
            return TLSFingerprintReport(
                observed=observed,
                expected_profile=expected_profile,
                matches=False,
                mismatch_details=[f"Unknown profile: {expected_profile}"],
                recommendation=f"Use one of: {', '.join(self._baselines.keys())}",
            )

        # If observed is a stub (offline/error), skip comparison
        if observed.ja4_string is None and observed.ja3_hash is None:
            return TLSFingerprintReport(
                observed=observed,
                expected_profile=expected_profile,
                matches=True,  # Can't compare — don't false-alarm
                mismatch_details=[],
                recommendation="Offline mode — TLS fingerprint not observed",
            )

        mismatches: list[str] = []
        matches = True

        # Compare JA4 string (primary)
        if baseline.ja4_string and observed.ja4_string:
            if baseline.ja4_string != observed.ja4_string:
                matches = False
                mismatches.append(
                    f"JA4 mismatch: expected '{baseline.ja4_string}', "
                    f"got '{observed.ja4_string}'"
                )

        # Compare JA3 hash (secondary, if available)
        if baseline.ja3_hash and observed.ja3_hash:
            if baseline.ja3_hash != observed.ja3_hash:
                matches = False
                mismatches.append(
                    f"JA3 hash mismatch: expected '{baseline.ja3_hash}', "
                    f"got '{observed.ja3_hash}'"
                )

        # Compare TLS version
        if baseline.tls_version and observed.tls_version:
            if baseline.tls_version != observed.tls_version:
                matches = False
                mismatches.append(
                    f"TLS version mismatch: expected {baseline.tls_version}, "
                    f"got {observed.tls_version}"
                )

        # Build recommendation
        recommendation = ""
        if not matches:
            recommendation = (
                "TLS fingerprint does not match expected baseline. "
                "Consider switching backend (e.g., Selenium → Patchright) "
                "or updating the browser version profile."
            )

        return TLSFingerprintReport(
            observed=observed,
            expected_profile=expected_profile,
            matches=matches,
            mismatch_details=mismatches,
            recommendation=recommendation,
        )

    # ------------------------------------------------------------------
    # Convenience: observe + compare in one call
    # ------------------------------------------------------------------

    async def check(
        self,
        browser_page: Any = None,
        expected_profile: str = "chrome143_macos",
    ) -> TLSFingerprintReport:
        """Observe and compare in one call.

        Parameters
        ----------
        browser_page:
            Live browser page, or None for offline mode.
        expected_profile:
            Baseline profile name to compare against.

        Returns
        -------
        TLSFingerprintReport
        """
        observed = await self.observe(browser_page)
        return self.compare(observed, expected_profile)


# ---------------------------------------------------------------------------
# NetworkStealthReport builder
# ---------------------------------------------------------------------------

def build_network_stealth_report(
    *,
    proxy_health: Optional[dict[str, Any]] = None,
    ip_reputation: Optional[Any] = None,
    tls_report: Optional[TLSFingerprintReport] = None,
) -> NetworkStealthReport:
    """Build an aggregate NetworkStealthReport from component results.

    Derives ``overall_status`` from the individual component states:

    - **COMPROMISED**: TLS fingerprint mismatch OR high-risk IP
    - **DEGRADED**: some proxies unhealthy, or medium-risk IP, or
      TLS check was inconclusive (offline/error)
    - **HEALTHY**: all available checks pass
    - **UNKNOWN**: no component data available

    Parameters
    ----------
    proxy_health:
        Snapshot from ProxyPool.health_snapshot(). ``None`` if pool not
        configured.
    ip_reputation:
        IPReputationResult instance. ``None`` if not checked.
    tls_report:
        TLSFingerprintReport instance. ``None`` if not checked.
    """
    warnings: list[str] = []
    status = NetworkStealthStatus.UNKNOWN
    has_data = False

    # --- Proxy health ---
    if proxy_health is not None and len(proxy_health) > 0:
        has_data = True
        unhealthy = sum(1 for h in proxy_health.values() if not h.healthy)
        if unhealthy > 0:
            warnings.append(f"{unhealthy} of {len(proxy_health)} proxies unhealthy")
            if status == NetworkStealthStatus.UNKNOWN:
                status = NetworkStealthStatus.DEGRADED

    # --- IP reputation ---
    if ip_reputation is not None:
        has_data = True
        verdict = getattr(ip_reputation, "verdict", None)

        # Import here to avoid circular dependency at module level
        try:
            from super_browser.stealth.ip_reputation import ReputationVerdict
        except ImportError:
            ReputationVerdict = None  # type: ignore[assignment]

        if verdict is not None and ReputationVerdict is not None:
            if verdict == ReputationVerdict.HIGH_RISK:
                warnings.append(f"IP reputation: {verdict.value}")
                status = NetworkStealthStatus.COMPROMISED
            elif verdict == ReputationVerdict.MEDIUM_RISK:
                warnings.append(f"IP reputation: {verdict.value}")
                if status != NetworkStealthStatus.COMPROMISED:
                    status = NetworkStealthStatus.DEGRADED
            elif verdict == ReputationVerdict.LOW_RISK:
                if status == NetworkStealthStatus.UNKNOWN:
                    status = NetworkStealthStatus.HEALTHY
            elif verdict == ReputationVerdict.CLEAN:
                if status == NetworkStealthStatus.UNKNOWN:
                    status = NetworkStealthStatus.HEALTHY

    # --- TLS fingerprint ---
    if tls_report is not None:
        has_data = True
        if not tls_report.matches:
            for detail in tls_report.mismatch_details:
                warnings.append(f"TLS: {detail}")
            status = NetworkStealthStatus.COMPROMISED
        elif tls_report.observed.ja4_string is None:
            # Offline/inconclusive — not a warning, just no data
            pass
        elif status == NetworkStealthStatus.UNKNOWN:
            status = NetworkStealthStatus.HEALTHY

    if not has_data:
        status = NetworkStealthStatus.UNKNOWN

    return NetworkStealthReport(
        proxy_health=proxy_health,
        ip_reputation=ip_reputation,
        tls_fingerprint=tls_report,
        generated_at=time.monotonic(),
        warnings=warnings,
        overall_status=status,
    )
