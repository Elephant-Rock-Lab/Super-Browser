#!/usr/bin/env python3
"""CLI entrypoint for Adversarial Capability Assessment Suite v3."""

from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from adversarial3.core import Severity, Tier, Verdict
from adversarial3.engines.scoring import ScoringConfig
from adversarial3.harness import AssessmentHarness


TIER_MAP = {
    "fingerprint": Tier.FINGERPRINT,
    "automation": Tier.AUTOMATION,
    "ejector": Tier.EJECTOR,
    "behavioral": Tier.BEHAVIORAL,
    "network": Tier.NETWORK,
    "external_scanner": Tier.EXTERNAL_SCANNER,
    "external_vendor": Tier.EXTERNAL_VENDOR,
    "controlled": Tier.CONTROLLED,
}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Adversarial Capability Assessment Suite v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "External scanners require SB_ADV=1.\n"
            "External vendors require SB_ADV=1 + SB_ADV_VENDORS=1 + SB_ADV_VENDORS_ACK=1.\n"
            "The corresponding --tier must also be selected.\n"
            "\n"
            "Note: --backend stub runs the full pipeline but produces INCONCLUSIVE\n"
            "results for vectors requiring real JS execution. Use a real browser\n"
            "(playwright, patchright, superbrowser) for meaningful assessments."
        ),
    )
    parser.add_argument(
        "--tier", action="append", choices=list(TIER_MAP.keys()),
        help="Tier(s) to run. Repeatable. Default: controlled only.",
    )
    parser.add_argument(
        "--vector", action="append",
        help="Specific vector ID(s) to run. Overrides --tier.",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Run all tiers (including behavioral vectors, which return SKIPPED).",
    )
    parser.add_argument(
        "--backend", choices=["auto", "playwright", "patchright", "superbrowser", "stub"],
        default="auto",
        help="Browser backend to use. Default: auto-detect.",
    )
    parser.add_argument(
        "--output-dir", type=Path, default=Path("adversarial-results"),
        help="Directory for reports. Default: adversarial-results/",
    )
    parser.add_argument(
        "--run-id", help="Custom run ID. Default: auto-generated UUID.",
    )
    parser.add_argument(
        "--no-skip-interaction", action="store_true",
        help="Include vectors requiring interaction (default: excluded unless --all).",
    )
    parser.add_argument(
        "--critical-cap", type=float, default=0.5,
        help="Overall score cap when CRITICAL+FLAGGED failures occur. Default: 0.5",
    )
    parser.add_argument(
        "--server-port", type=int, default=0,
        help="Port for controlled server. 0 = auto-assign.",
    )
    return parser


async def _main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    tiers: list[Tier] | None = None
    if args.all:
        tiers = list(TIER_MAP.values())
    elif args.tier:
        tiers = [TIER_MAP[t] for t in args.tier]
    elif not args.vector:
        tiers = [Tier.CONTROLLED]

    # --all includes all vectors, including behavioral (which return SKIPPED)
    skip_interaction = (not args.all) and (not args.no_skip_interaction)

    scoring_config = ScoringConfig(
        critical_failure_cap=args.critical_cap < 1.0,
        critical_cap_threshold=args.critical_cap,
    )

    harness = AssessmentHarness(
        backend_name=args.backend,
        server_port=args.server_port,
        output_dir=args.output_dir,
        scoring_config=scoring_config,
    )

    try:
        report = await harness.run(
            tiers=tiers,
            vectors=args.vector,
            skip_interaction=skip_interaction,
            run_id=args.run_id,
        )
    except KeyboardInterrupt:
        print("\nInterrupted by user.")
        return 130

    # Exit nonzero only for CRITICAL severity + FLAGGED verdict
    critical_flagged = any(
        r.severity == Severity.CRITICAL and r.verdict == Verdict.FLAGGED
        for r in report.results
    )
    return 1 if critical_flagged else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(_main()))
