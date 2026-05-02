#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────────────────────
# run_stealth_gauntlet.sh — Execute the full stealth-detection test suite
#
# This script runs ALL stealth detection tests, including live-site checks
# that are excluded from CI.  Use it for local validation before merging.
#
# Usage:
#   ./scripts/run_stealth_gauntlet.sh          # run everything
#   ./scripts/run_stealth_gauntlet.sh --quick  # skip live-site tests
#
# ──────────────────────────────────────────────────────────────────────────────
#
# Patchright-verified detection services (14):
#
#   1.  bot.sannysoft.com          — WebDriver / headless / automation flags
#   2.  bot.incolumitas.com         — bot probability scoring
#   3.  abrahamjuliot.github.io/creepjs  — CreepJS fingerprint trust score
#   4.  browserscan.net             — bot detection & browser fingerprinting
#   5.  pixelscan.net               — canvas / WebGL fingerprint analysis
#   6.  browserleaks.com            — comprehensive browser leak detection
#   7.  whoer.net                   — anonymity & fingerprint checks
#   8.  ipleak.net                  — IP / DNS / WebRTC leak detection
#   9.  deviceinfo.me               — hardware & software fingerprinting
#  10.  amiunique.org               — cross-browser fingerprint uniqueness
#  11. covery.fail                  — anti-fingerprinting validation
#  12.  arh.antoinevastel.com       — bot detection (Vastel)
#  13.  daedaluszone.io/detect      — headless browser detection
#  14.  rekrab.eu                   — JavaScript-based bot detection
#
# ──────────────────────────────────────────────────────────────────────────────

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Colours (disabled when stdout is not a terminal)
if [ -t 1 ]; then
    RED='\033[0;31m'
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    CYAN='\033[0;36m'
    BOLD='\033[1m'
    NC='\033[0m'
else
    RED='' GREEN='' YELLOW='' CYAN='' BOLD='' NC=''
fi

echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}${BOLD}║        SUPER-BROWSER STEALTH GAUNTLET           ║${NC}"
echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
echo ""

cd "${PROJECT_ROOT}"

# ── Parse flags ──────────────────────────────────────────────────────────────
QUICK=0
if [ "${1:-}" = "--quick" ]; then
    QUICK=1
    echo -e "${YELLOW}⚡ Quick mode — skipping live-site tests${NC}"
fi

# ── Step 1: Programmatic stealth checks ──────────────────────────────────────
echo ""
echo -e "${BOLD}[1/2] Running programmatic stealth checks…${NC}"
echo -e "       (navigator.webdriver, Chrome runtime, headless indicators, TLS, CLI switches)"
echo ""

PROG_RC=0
pytest tests/stealth_detection/ -m "not live_stealth" -v --tb=short || PROG_RC=$?

# ── Step 2: Live detection-site tests ────────────────────────────────────────
LIVE_RC=0
if [ "${QUICK}" -eq 0 ]; then
    echo ""
    echo -e "${BOLD}[2/2] Running live detection-site tests…${NC}"
    echo -e "       (sannysoft · incolumitas · CreepJS · browserscan)"
    echo ""
    pytest tests/stealth_detection/ -m "live_stealth" -v --tb=short || LIVE_RC=$?
else
    echo ""
    echo -e "${BOLD}[2/2] Skipped (use without --quick to include live tests)${NC}"
fi

# ── Summary ──────────────────────────────────────────────────────────────────
echo ""
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
if [ "${QUICK}" -eq 0 ]; then
    if [ "${PROG_RC}" -eq 0 ] && [ "${LIVE_RC}" -eq 0 ]; then
        echo -e "${GREEN}${BOLD}  ✅  GAUNTLET PASSED — all stealth checks green${NC}"
    else
        echo -e "${RED}${BOLD}  ❌  GAUNTLET FAILED${NC}"
        [ "${PROG_RC}" -ne 0 ] && echo -e "${RED}       Programmatic checks: FAILED${NC}"
        [ "${LIVE_RC}" -ne 0 ]  && echo -e "${RED}       Live-site checks:    FAILED${NC}"
    fi
else
    if [ "${PROG_RC}" -eq 0 ]; then
        echo -e "${GREEN}${BOLD}  ✅  GAUNTLET PASSED (quick mode)${NC}"
    else
        echo -e "${RED}${BOLD}  ❌  GAUNTLET FAILED (programmatic checks)${NC}"
    fi
fi
echo -e "${CYAN}${BOLD}═══════════════════════════════════════════════════${NC}"
echo ""

# Exit with non-zero if any step failed
[ "${PROG_RC}" -eq 0 ] && ([ "${QUICK}" -eq 1 ] || [ "${LIVE_RC}" -eq 0 ])
