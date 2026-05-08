"""HTML audit report generator for RecordingSession.

Produces a self-contained HTML file with a summary table and action details.
"""

from __future__ import annotations

import html as html_lib
import logging
from pathlib import Path
from typing import Union

from super_browser.recording.types import RecordingSession

logger = logging.getLogger(__name__)


def export_html(recording: RecordingSession) -> str:
    """Generate an HTML audit report string for *recording*.

    Returns a complete HTML document with:
      - Session metadata (ID, duration, action/error counts)
      - Action table with timestamps, params, URLs, errors
    """
    meta = recording.metadata
    rows = _build_rows(recording)
    return _TEMPLATE.format(
        session_id=html_lib.escape(recording.session_id),
        schema_version=html_lib.escape(recording.schema_version),
        action_count=meta["action_count"],
        error_count=meta["error_count"],
        duration_ms=f"{meta['duration_ms']:.1f}",
        rows=rows,
    )


def save_html(recording: RecordingSession, path: Union[str, Path]) -> None:
    """Write an HTML audit report to *path*."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    report = export_html(recording)
    path.write_text(report, encoding="utf-8")
    logger.info("HTML report saved to %s", path)


def _build_rows(recording: RecordingSession) -> str:
    """Build HTML table rows for each action."""
    parts: list[str] = []
    for action in recording.actions:
        status_class = "status-ok" if action.ok else "status-err"
        status_text = "OK" if action.ok else "FAIL"
        err_cell = (
            f'<td class="error">{html_lib.escape(action.error or "")}</td>'
            if action.error
            else "<td>—</td>"
        )
        parts.append(
            f"<tr class='{status_class}'>"
            f"<td>{action.index}</td>"
            f"<td>{action.timestamp:.3f}</td>"
            f"<td>{html_lib.escape(action.action)}</td>"
            f"<td>{html_lib.escape(action.url)}</td>"
            f"<td>{html_lib.escape(action.title)}</td>"
            f"<td>{html_lib.escape(str(action.params))}</td>"
            f"<td>{status_text}</td>"
            f"{err_cell}"
            f"<td>{action.duration_ms:.1f}</td>"
            f"</tr>"
        )
    return "\n".join(parts)


_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Recording Report — {session_id}</title>
<style>
  body {{ font-family: system-ui, sans-serif; margin: 2rem; background: #f8f9fa; }}
  h1 {{ color: #1a1a2e; }}
  .meta {{ background: #fff; border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 1.5rem;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
  .meta span {{ margin-right: 2rem; font-weight: 500; }}
  table {{ width: 100%; border-collapse: collapse; background: #fff;
           box-shadow: 0 1px 3px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
  th {{ background: #1a1a2e; color: #fff; padding: 0.75rem 1rem; text-align: left; }}
  td {{ padding: 0.5rem 1rem; border-bottom: 1px solid #eee; }}
  .status-ok td:first-child {{ color: #2d6a4f; }}
  .status-err {{ background: #fff0f0; }}
  .status-err td:first-child {{ color: #d62828; }}
  .error {{ color: #d62828; font-weight: 500; }}
  .timestamp {{ color: #6c757d; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>Session Recording Report</h1>
<div class="meta">
  <span>Session: <strong>{session_id}</strong></span>
  <span>Schema: {schema_version}</span>
  <span>Actions: {action_count}</span>
  <span>Errors: {error_count}</span>
  <span>Duration: {duration_ms} ms</span>
</div>
<table>
  <thead>
    <tr>
      <th>#</th>
      <th>Timestamp</th>
      <th>Action</th>
      <th>URL</th>
      <th>Title</th>
      <th>Params</th>
      <th>Status</th>
      <th>Error</th>
      <th>Duration (ms)</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
</body>
</html>"""
