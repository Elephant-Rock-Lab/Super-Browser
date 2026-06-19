"""JSON report formatter."""

from __future__ import annotations

import json

from adversarial3.core import AssessmentReport, BaseReporter


class JSONReporter(BaseReporter):
    """Format assessment reports as JSON."""

    def render(self, report: AssessmentReport) -> str:
        return report.to_json(indent=2)

    def extension(self) -> str:
        return "json"
