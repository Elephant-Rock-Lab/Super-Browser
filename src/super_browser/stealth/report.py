"""StealthReport — HTML and Markdown report generation for stealth checks.

Uses :class:`FingerprintScore` to produce formatted reports.
"""

from __future__ import annotations

import html
import time

from super_browser.stealth.scoring import FingerprintScore


class StealthReport:
    """Generate HTML and Markdown reports from a FingerprintScore."""

    @staticmethod
    def generate_markdown(score: FingerprintScore) -> str:
        """Produce a Markdown report from *score*.

        Returns a string containing a full Markdown document with header,
        score summary, and per-check details table.
        """
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(score.timestamp))
        lines = [
            "# Stealth Report",
            "",
            f"**Backend:** {score.backend}  ",
            f"**Overall Score:** {score.overall}/100  ",
            f"**Timestamp:** {ts}  ",
            "",
            "## Checks",
            "",
        ]

        for check in score.checks:
            status = "✅ PASS" if check.passed else "❌ FAIL"
            lines.append(f"### {check.name}")
            lines.append("")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **Score:** {check.score}/100")
            lines.append(f"- **Detail:** {check.detail}")
            lines.append("")

        # Summary
        passed_count = sum(1 for c in score.checks if c.passed)
        total = len(score.checks)
        lines.append("---")
        lines.append("")
        lines.append(f"**Summary:** {passed_count}/{total} checks passed")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def generate_html(score: FingerprintScore) -> str:
        """Produce an HTML report from *score*.

        Returns a complete HTML document with inline CSS styling.
        """
        ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(score.timestamp))
        passed_count = sum(1 for c in score.checks if c.passed)
        total = len(score.checks)

        # Build check rows
        rows = []
        for check in score.checks:
            status_cls = "pass" if check.passed else "fail"
            status_text = "PASS" if check.passed else "FAIL"
            rows.append(
                f"<tr>"
                f"<td>{html.escape(check.name)}</td>"
                f'<td class="{status_cls}">{status_text}</td>'
                f"<td>{check.score}</td>"
                f"<td>{html.escape(check.detail)}</td>"
                f"</tr>"
            )

        rows_html = "\n".join(rows)

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Stealth Report</title>
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; margin: 2rem; color: #1a1a1a; }}
  h2 {{ color: #2c3e50; }}
  .score {{ font-size: 2.5rem; font-weight: bold; color: {'#27ae60' if score.overall >= 70 else '#e74c3c'}; }}
  table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
  th, td {{ border: 1px solid #ddd; padding: 0.75rem; text-align: left; }}
  th {{ background-color: #f5f5f5; }}
  .pass {{ color: #27ae60; font-weight: bold; }}
  .fail {{ color: #e74c3c; font-weight: bold; }}
  .meta {{ color: #666; font-size: 0.9rem; margin-top: 0.5rem; }}
</style>
</head>
<body>
<h2>Stealth Report</h2>
<div class="score">{score.overall}/100</div>
<div class="meta">Backend: {html.escape(score.backend)} | {ts} | {passed_count}/{total} checks passed</div>
<table>
<thead>
<tr><th>Check</th><th>Status</th><th>Score</th><th>Detail</th></tr>
</thead>
<tbody>
{rows_html}
</tbody>
</table>
</body>
</html>"""
