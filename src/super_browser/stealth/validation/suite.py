"""FingerprintValidationSuite — runs all consistency checks and produces a report."""

from __future__ import annotations

import datetime

from super_browser.stealth.consistency.matrix import FingerprintMatrix
from super_browser.stealth.profiles.schema import DeviceProfile

from .checks import ALL_CHECKS
from .report import CheckResult, ValidationReport

__all__ = ["FingerprintValidationSuite"]


class FingerprintValidationSuite:
    """Run all registered consistency checks against a matrix + profile pair."""

    def run(self, matrix: FingerprintMatrix, profile: DeviceProfile) -> ValidationReport:
        """Execute every check and return an aggregated :class:`ValidationReport`.

        Parameters
        ----------
        matrix:
            The derived fingerprint matrix to validate.
        profile:
            The source device profile the matrix was derived from.

        Returns
        -------
        ValidationReport
            Frozen report with individual check results and an aggregate score.
        """
        results: list[CheckResult] = []
        for chk in ALL_CHECKS:
            results.append(chk.check(matrix, profile))

        passed_count = sum(1 for r in results if r.passed)
        total = len(results)
        score = (passed_count / total) * 100 if total else 0.0

        return ValidationReport(
            profile_id=profile.id,
            seed=matrix.seed,
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            checks=tuple(results),
            passed=passed_count == total,
            score=score,
        )
