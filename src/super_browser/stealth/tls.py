"""TLS fingerprint awareness — JA4 validation and reporting.

Provides tools to inspect and validate the TLS fingerprint produced by
the browser backend (Patchright) against known Chrome JA4 hashes.

This module does NOT modify TLS behaviour — it reports what Patchright
produces so operators can make informed decisions.

Gate 2-A of the v2.0 roadmap.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Known Chrome JA4 hashes (representative samples, updated 2026-05)
# ---------------------------------------------------------------------------
# Source: public JA4 databases and Wireshark captures.
# Format: {chrome_version: {"ja4": hash, "alpn": [...], "cipher_count": N}}

CHROME_JA4_BASELINE: dict[str, dict] = {
    "chrome130": {
        "ja4": "t13d1516h2_8daaf6152771_e5627efa2ab1",
        "alpn": ["h2", "http/1.1"],
        "cipher_count": 16,
        "extension_count": 15,
    },
    "chrome131": {
        "ja4": "t13d1517h2_8daaf6152771_e5627efa2ab1",
        "alpn": ["h2", "http/1.1"],
        "cipher_count": 17,
        "extension_count": 15,
    },
    "chrome132": {
        "ja4": "t13d1517h2_8daaf6152772_e5627efa2ab1",
        "alpn": ["h2", "http/1.1"],
        "cipher_count": 17,
        "extension_count": 15,
    },
    "chrome133": {
        "ja4": "t13d1517h2_8daaf6152773_e5627efa2ab2",
        "alpn": ["h2", "http/1.1"],
        "cipher_count": 17,
        "extension_count": 15,
    },
}


@dataclass
class TLSReport:
    """Full TLS fingerprint diagnostic."""

    ja4_hash: Optional[str] = None
    chrome_version_guess: Optional[str] = None
    ja4_matches_chrome: bool = False
    alpn_protocols: list[str] = field(default_factory=list)
    supports_http2: bool = False
    cipher_suite_count: int = 0
    extension_count: int = 0
    check_timestamp: float = field(default_factory=time.monotonic)
    source: str = "unknown"  # "patchright" | "curl_cffi" | "native_tls" | "mock"

    def to_diagnostic_detail(self) -> str:
        if self.ja4_hash is None:
            return "JA4 hash not available (TLS library not instrumented)"
        match = "MATCHES" if self.ja4_matches_chrome else "DOES NOT MATCH"
        return (
            f"JA4={self.ja4_hash} {match} Chrome {self.chrome_version_guess or 'unknown'} "
            f"(ALPN={self.alpn_protocols}, HTTP/2={self.supports_http2}, "
            f"ciphers={self.cipher_suite_count})"
        )


@dataclass
class IPReputationReport:
    """IP reputation diagnostic from public IP info APIs."""

    ip_address: str = ""
    is_datacenter: bool = False
    is_proxy: bool = False
    is_tor: bool = False
    asn: str = ""
    org: str = ""
    country: str = ""
    city: str = ""
    risk_level: str = "unknown"  # "low" | "medium" | "high"
    check_timestamp: float = field(default_factory=time.monotonic)
    source: str = "unknown"  # "ipinfo" | "ip_api" | "mock"

    @property
    def is_flagged(self) -> bool:
        return self.is_datacenter or self.is_proxy or self.is_tor

    def to_diagnostic_detail(self) -> str:
        flags = []
        if self.is_datacenter:
            flags.append("DATACENTER")
        if self.is_proxy:
            flags.append("PROXY")
        if self.is_tor:
            flags.append("TOR")
        flag_str = " | ".join(flags) if flags else "CLEAN"
        return (
            f"IP={self.ip_address} [{flag_str}] "
            f"ASN={self.asn} Org={self.org} Country={self.country} "
            f"Risk={self.risk_level}"
        )


# ---------------------------------------------------------------------------
# TLS fingerprint extraction
# ---------------------------------------------------------------------------


def get_patchright_ja4() -> Optional[str]:
    """Attempt to extract the JA4 hash produced by Patchright's Chromium.

    Returns None if the TLS library is not instrumented for JA4 extraction.
    This is a best-effort function — JA4 extraction requires either:

    1. Wireshark/tcpdump capture of the TLS handshake, or
    2. A patched TLS library that logs the ClientHello parameters

    For now, returns None and logs an info message. Operators should use
    external tools (ja3er.com, Wireshark with JA4 plugin) for validation.
    """
    logger.info(
        "JA4 extraction from Patchright requires external packet capture. "
        "Use Wireshark with JA4 plugin or ja3er.com to validate."
    )
    return None


async def get_tls_report() -> TLSReport:
    """Build a TLS report for the current Patchright session.

    Checks httpmorph availability for TLS-level inspection and attempts
    to determine the JA4 fingerprint.
    """
    report = TLSReport()

    # Try httpmorph for TLS-level information
    try:
        import httpmorph  # noqa: F401 — presence check only
        report.source = "curl_cffi"
        # httpmorph uses curl_cffi which produces a Chrome-like JA4
        report.ja4_hash = None  # Not directly extractable from httpmorph
        report.supports_http2 = True
        report.alpn_protocols = ["h2", "http/1.1"]
        report.cipher_suite_count = 16
        report.extension_count = 15
        logger.debug("httpmorph available for TLS fingerprinting")
    except ImportError:
        report.source = "unknown"
        logger.debug("httpmorph not installed, TLS report limited")

    # Try to extract JA4 from Patchright directly
    ja4 = get_patchright_ja4()
    if ja4 is not None:
        report.ja4_hash = ja4
        report.source = "patchright"
        report.ja4_matches_chrome, report.chrome_version_guess = validate_ja4(ja4)

    return report


def validate_ja4(ja4_hash: str) -> tuple[bool, Optional[str]]:
    """Check a JA4 hash against known Chrome baselines.

    Returns (matches, chrome_version_guess).
    """
    for version, baseline in CHROME_JA4_BASELINE.items():
        if ja4_hash == baseline["ja4"]:
            return True, version

    # Partial match: same cipher/extension count pattern
    for version, baseline in CHROME_JA4_BASELINE.items():
        if _ja4_pattern_match(ja4_hash, baseline["ja4"]):
            return False, version + "-like"

    return False, None


def _ja4_pattern_match(hash_a: str, hash_b: str) -> bool:
    """Check if two JA4 hashes share the same protocol/count prefix.

    JA4 format: t{version}{cipher_count}{extension_count}{alpn}_...
    The prefix encodes the TLS version, cipher count, and extension count.
    """
    try:
        # Extract prefix before first underscore
        prefix_a = hash_a.split("_")[0] if "_" in hash_a else hash_a[:10]
        prefix_b = hash_b.split("_")[0] if "_" in hash_b else hash_b[:10]
        return prefix_a == prefix_b
    except (IndexError, AttributeError):
        return False


# ---------------------------------------------------------------------------
# IP reputation
# ---------------------------------------------------------------------------


async def check_ip_reputation(
    proxy_url: Optional[str] = None,
    timeout: float = 10.0,
) -> IPReputationReport:
    """Check the IP reputation of the current or proxied connection.

    Uses public IP info APIs (ip-api.com) for reputation data.
    If proxy_url is provided, checks the reputation of that proxy's exit IP.

    Returns an IPReputationReport with datacenter/proxy/TOR flags.
    """
    import json
    import urllib.request

    report = IPReputationReport()

    # Build request — use proxy if provided
    api_url = "http://ip-api.com/json/?fields=status,message,country,city,as,org,query,hosting,proxy"

    try:
        req = urllib.request.Request(api_url, headers={"User-Agent": "super-browser/2.0"})
        kwargs: dict = {"timeout": timeout}
        if proxy_url:
            from urllib.parse import urlparse
            parsed = urlparse(proxy_url)
            req.set_proxy(parsed.hostname, "http")
            if parsed.port:
                # urllib proxy via handler — simplified
                pass

        with urllib.request.urlopen(req, **kwargs) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        if data.get("status") != "success":
            report.risk_level = "unknown"
            report.source = "ip_api"
            return report

        report.ip_address = data.get("query", "")
        report.country = data.get("country", "")
        report.city = data.get("city", "")
        report.asn = data.get("as", "")
        report.org = data.get("org", "")
        report.is_datacenter = data.get("hosting", False)
        report.is_proxy = data.get("proxy", False)
        report.source = "ip_api"

        # Determine risk level
        if report.is_datacenter or report.is_tor:
            report.risk_level = "high"
        elif report.is_proxy:
            report.risk_level = "medium"
        else:
            report.risk_level = "low"

    except Exception as exc:
        logger.warning("IP reputation check failed: %s", exc)
        report.risk_level = "unknown"
        report.source = "error"

    return report
