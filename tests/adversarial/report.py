"""JSON + Markdown report builder for adversarial test results.

Consumes per-tier TargetResult collections and produces:
- A machine-readable JSON report (for CI artifacts, dashboards)
- A human-readable Markdown report (for PR comments, docs)
- Appends to adversarial-history.json for trend tracking
"""

from __future__ import annotations

import json
from pathlib import Path

from .scoring import AdversarialReport, append_to_history, build_report
from .targets import TargetResult, Tier


def _verdict_emoji(verdict: str) -> str:
    return {
        "clean": "✅",
        "flagged": "🚫",
        "challenged": "⚠️",
        "inconclusive": "❓",
    }.get(verdict, "❓")


def _score_badge(score: int) -> str:
    if score >= 80:
        return f"![score](https://img.shields.io/badge/score-{score}-brightgreen)"
    if score >= 50:
        return f"![score](https://img.shields.io/badge/score-{score}-yellow)"
    return f"![score](https://img.shields.io/badge/score-{score}-red)"


def render_markdown(report: AdversarialReport) -> str:
    """Render an AdversarialReport as Markdown."""
    lines: list[str] = []

    lines.append("# Adversarial Stealth Validation Report\n")
    lines.append(f"**Run ID:** `{report.run_id}`  ")
    lines.append(f"**Timestamp:** {report.timestamp}  ")
    lines.append(f"**Overall Score:** {report.overall_score}/100  ")
    lines.append(f"**Inconclusive Rate:** {report.inconclusive_rate:.1%}\n")

    lines.append("---\n")

    for ts in report.tier_scores:
        tier_name = ts.tier.value.replace("_", " ").title()
        lines.append(f"## {tier_name}\n")
        lines.append(f"{_score_badge(ts.composite_score)}  ")
        lines.append(
            f"**Targets:** {ts.target_count} | "
            f"**Conclusive:** {ts.conclusive_count} | "
            f"**Clean:** {ts.clean_count} | "
            f"**Challenged:** {ts.challenged_count} | "
            f"**Flagged:** {ts.flagged_count} | "
            f"**Inconclusive:** {ts.inconclusive_count}\n"
        )
        lines.append("\n| Target | Verdict | Score | Detail |")
        lines.append("|---|---|---|---|")
        for d in ts.details:
            emoji = _verdict_emoji(d.verdict.value)
            lines.append(
                f"| `{d.target_id}` | {emoji} {d.verdict.value} | {d.score} | {d.detail} |"
            )
        lines.append("")

    lines.append("---\n")
    lines.append("## Summary\n")
    lines.append(report.summary)
    lines.append("")

    return "\n".join(lines)


def write_json_report(report: AdversarialReport, path: Path) -> None:
    """Write the full report as JSON."""
    with path.open("w", encoding="utf-8") as f:
        json.dump(report.to_dict(), f, indent=2)


def write_markdown_report(report: AdversarialReport, path: Path) -> None:
    """Write the full report as Markdown."""
    with path.open("w", encoding="utf-8") as f:
        f.write(render_markdown(report))


def build_and_write(
    run_id: str,
    results_by_tier: dict[Tier, list[TargetResult]],
    output_dir: Path,
    write_history: bool = True,
) -> AdversarialReport:
    """Build report, write JSON + Markdown, optionally append to history."""
    report = build_report(run_id, results_by_tier)

    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / f"{run_id}.json"
    md_path = output_dir / f"{run_id}.md"

    write_json_report(report, json_path)
    write_markdown_report(report, md_path)

    if write_history:
        history_path = output_dir / "adversarial-history.json"
        append_to_history(report, history_path)

    return report
