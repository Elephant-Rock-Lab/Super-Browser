"""Markdown report formatter with badges and trend support."""

from __future__ import annotations

import json

from adversarial3.core import (
    AssessmentReport,
    BaseReporter,
    Severity,
    TierSummary,
    VectorResult,
    Verdict,
    severity_emoji,
    verdict_emoji,
)


class MarkdownReporter(BaseReporter):
    """Format assessment reports as Markdown with shields.io badges."""

    def __init__(self, *, include_trend: bool = False) -> None:
        self.include_trend = include_trend

    def render(self, report: AssessmentReport) -> str:
        lines: list[str] = []

        lines.append("# Adversarial Stealth Validation Report")
        lines.append("")
        lines.append(f"**Run ID:** `{report.run_id}`  ")
        lines.append(f"**Timestamp:** {report.timestamp}  ")
        lines.append(f"**Overall Score:** {self._score_badge(report.overall_score)}  ")
        lines.append(f"**Total Vectors:** {len(report.results)}  ")
        lines.append("")

        # Summary table
        lines.append("## Summary")
        lines.append("")
        lines.append("| Tier | Score | Passed | Failed | Skipped | Inconclusive |")
        lines.append("|------|-------|--------|--------|---------|-------------|")
        for ts in report.tier_summaries:
            lines.append(
                f"| {ts.tier.value} | {self._score_badge(ts.score)} | "
                f"{ts.passed} | {ts.failed} | {ts.skipped} | {ts.inconclusive} |"
            )
        lines.append("")

        # Critical failures
        criticals = [r for r in report.results if r.severity == Severity.CRITICAL and r.verdict == Verdict.FLAGGED]
        if criticals:
            lines.append("## Critical Failures")
            lines.append("")
            for r in criticals:
                lines.append(f"- `{r.vector_id}` -- {r.name}: {verdict_emoji(r.verdict)} {r.verdict}")
                if r.details:
                    lines.append("  ```json")
                    lines.append(f"  {json.dumps(r.details, indent=2, default=str)}")
                    lines.append("  ```")
            lines.append("")

        # Detailed results
        lines.append("## Detailed Results")
        lines.append("")
        for r in report.results:
            emoji = verdict_emoji(r.verdict)
            sev = severity_emoji(r.severity)
            lines.append(f"### {sev} {r.vector_id}: {r.name}")
            lines.append(f"**Verdict:** {emoji} {r.verdict} | **Score:** {r.score:.2f} | **Duration:** {r.duration_ms:.1f}ms")
            if r.details:
                lines.append("```json")
                lines.append(json.dumps(r.details, indent=2, default=str))
                lines.append("```")
            if r.error:
                lines.append(f"**Error:** `{r.error}`")
            lines.append("")

        # Metadata
        if report.metadata:
            lines.append("## Metadata")
            lines.append("```json")
            lines.append(json.dumps(report.metadata, indent=2, default=str))
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    def extension(self) -> str:
        return "md"

    def _score_badge(self, score: float) -> str:
        pct = int(score * 100)
        if pct >= 80:
            return f"![score](https://img.shields.io/badge/score-{pct}-brightgreen)"
        if pct >= 50:
            return f"![score](https://img.shields.io/badge/score-{pct}-yellow)"
        return f"![score](https://img.shields.io/badge/score-{pct}-red)"
