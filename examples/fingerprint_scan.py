#!/usr/bin/env python3
"""Fingerprint scanning demo - offline stealth assessment.

This example demonstrates the FingerprintScanner and FingerprintScorer
for assessing browser stealth. Uses offline mode - no real browser needed.

Usage:
    python examples/fingerprint_scan.py
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure the local src/ is importable when running from the repo root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from super_browser.stealth.fingerprint_scanner import FingerprintScanner
from super_browser.stealth.fingerprint_score import FingerprintScorer, FingerprintGrade
from super_browser.stealth.scoring import FingerprintCheck


async def demo_offline_scan() -> None:
    """Run an offline fingerprint scan with default checks."""
    print("=" * 60)
    print("Offline Fingerprint Scan (Default Checks)")
    print("=" * 60)

    scanner = FingerprintScanner(scanner_config={"offline": True, "backend": "patchright"})
    score = await scanner.scan()

    print(f"\n  Backend:  {score.backend}")
    print(f"  Overall:  {score.overall}/100")
    print(f"  Checks:   {len(score.checks)}")
    print()

    for check in score.checks:
        status = "[PASS]" if check.passed else "[FAIL]"
        print(f"  {status} {check.name}: {check.score}/100 - {check.detail}")

    # Generate Markdown report (write to file to avoid console encoding issues)
    report = FingerprintScanner.format_report(score)
    report_path = Path(__file__).resolve().parent.parent / "docs" / "stealth-report-example.md"
    try:
        report_path.write_text(report, encoding="utf-8")
        print(f"\n  Report saved to {report_path}")
    except Exception:
        print(f"\n  Report generated ({len(report)} chars)")


async def demo_custom_checks() -> None:
    """Run a scan with custom checks to simulate mixed results."""
    print("\n" + "=" * 60)
    print("Custom Checks (Mixed Results)")
    print("=" * 60)

    custom_checks = [
        FingerprintCheck(name="webdriver", passed=True, score=100,
                         detail="navigator.webdriver is undefined"),
        FingerprintCheck(name="canvas_fingerprint", passed=True, score=90,
                         detail="Canvas fingerprint varies per session"),
        FingerprintCheck(name="webgl_renderer", passed=False, score=45,
                         detail="WebGL renderer reveals headless Chromium"),
        FingerprintCheck(name="audio_fingerprint", passed=False, score=30,
                         detail="AudioContext fingerprint inconsistent"),
        FingerprintCheck(name="font_enumeration", passed=True, score=85,
                         detail="Font list appears normal"),
    ]

    scanner = FingerprintScanner(
        scanner_config={"offline": True, "custom_checks": custom_checks, "backend": "patchright"}
    )
    score = await scanner.scan()

    print(f"\n  Overall: {score.overall}/100")
    print()

    for check in score.checks:
        status = "[PASS]" if check.passed else "[FAIL]"
        print(f"  {status} {check.name}: {check.score}/100 - {check.detail}")

    # Assessment
    if score.overall >= 90:
        print("\n  [A] Grade A - Excellent stealth")
    elif score.overall >= 75:
        print("\n  [B] Grade B - Good stealth")
    elif score.overall >= 60:
        print("\n  [C] Grade C - Fair stealth, some signals detected")
    else:
        print("\n  [D] Grade D - Poor stealth, easily detectable")


async def demo_scorer() -> None:
    """Demonstrate FingerprintScorer for weighted composite scoring."""
    print("\n" + "=" * 60)
    print("FingerprintScorer (Weighted Composite)")
    print("=" * 60)

    scorer = FingerprintScorer()
    print(f"\n  Weights:")
    for cat, weight in scorer.WEIGHTS.items():
        print(f"    {cat}: {weight * 100:.0f}%")

    # All pass
    result_all = scorer.score_from_checks({
        "webdriver": {"passed": True, "detail": "OK"},
        "plugins_mimetypes": {"passed": True, "detail": "OK"},
        "user_agent": {"passed": True, "detail": "OK"},
        "headers": {"passed": True, "detail": "OK"},
        "tls": {"passed": True, "detail": "OK"},
        "misc": {"passed": True, "detail": "OK"},
    })
    print(f"\n  All Pass -> Score: {result_all.score}/100, Grade: {result_all.grade}")

    # TLS fails
    result_tls = scorer.score_from_checks({
        "webdriver": {"passed": True, "detail": "OK"},
        "plugins_mimetypes": {"passed": True, "detail": "OK"},
        "user_agent": {"passed": True, "detail": "OK"},
        "headers": {"passed": True, "detail": "OK"},
        "tls": {"passed": False, "detail": "JA3 fingerprint reveals automation"},
        "misc": {"passed": True, "detail": "OK"},
    })
    print(f"  TLS Fail -> Score: {result_tls.score}/100, Grade: {result_tls.grade}")
    print(f"  Deductions: {result_tls.deductions}")

    # Multiple failures
    result_multi = scorer.score_from_checks({
        "webdriver": {"passed": False, "detail": "navigator.webdriver = true"},
        "plugins_mimetypes": {"passed": True, "detail": "OK"},
        "user_agent": {"passed": False, "detail": "Headless Chrome detected"},
        "headers": {"passed": True, "detail": "OK"},
        "tls": {"passed": False, "detail": "TLS fingerprint mismatch"},
        "misc": {"passed": True, "detail": "OK"},
    })
    print(f"  Multi Fail -> Score: {result_multi.score}/100, Grade: {result_multi.grade}")
    print(f"  Deductions: {result_multi.deductions}")


async def demo_cloak_backend() -> None:
    """Run a scan with CloakBrowser backend label."""
    print("\n" + "=" * 60)
    print("CloakBrowser Backend Scan")
    print("=" * 60)

    scanner = FingerprintScanner(
        scanner_config={"offline": True, "backend": "cloak"}
    )
    score = await scanner.scan()

    print(f"\n  Backend:  {score.backend}")
    print(f"  Overall:  {score.overall}/100")
    print(f"  Checks:   {len(score.checks)}")


async def main() -> None:
    print("Super Browser - Fingerprint Scanning Demo\n")

    await demo_offline_scan()
    await demo_custom_checks()
    await demo_scorer()
    await demo_cloak_backend()

    print("\n[PASS] All demos completed successfully")


if __name__ == "__main__":
    asyncio.run(main())
