"""Stealth regression harness — baseline capture, load, and regression detection."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path

from super_browser.stealth.consistency.matrix import FingerprintMatrix
from super_browser.stealth.profiles.schema import DeviceProfile

from .report import CheckResult, ValidationReport
from .suite import FingerprintValidationSuite

__all__ = ["BaselineResult", "StealthRegressionHarness"]

_DEFAULT_BASELINE_DIR = Path.home() / ".config" / "super-browser" / "baselines"


@dataclass(frozen=True)
class BaselineResult:
    """Snapshot of a validated baseline for a (profile, seed) pair."""

    profile_id: str
    seed: str
    captured_at: str
    matrix_hash: str
    check_results: tuple[CheckResult, ...]


def _matrix_hash(matrix: FingerprintMatrix) -> str:
    """Compute a stable SHA-256 hash over the matrix fingerprint fields."""
    hasher = hashlib.sha256()
    # Hash key surface fields deterministically
    fields = (
        matrix.user_agent,
        str(matrix.hardware_concurrency),
        str(matrix.device_memory),
        matrix.webgl_unmasked_vendor,
        matrix.webgl_unmasked_renderer,
        str(matrix.device_pixel_ratio),
        matrix.timezone,
        matrix.locale,
        str(matrix.webdriver),
        ",".join(matrix.fonts),
    )
    for f in fields:
        hasher.update(f.encode("utf-8"))
    return hasher.hexdigest()


class StealthRegressionHarness:
    """Capture baselines and detect regressions between runs."""

    def __init__(self, baseline_dir: Path | str | None = None) -> None:
        self._dir = Path(baseline_dir) if baseline_dir else _DEFAULT_BASELINE_DIR
        self._dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def capture_baseline(
        self,
        profile: DeviceProfile,
        seed: str,
        matrix: FingerprintMatrix,
        report: ValidationReport,
    ) -> BaselineResult:
        """Create, persist, and return a baseline result."""
        baseline = BaselineResult(
            profile_id=profile.id,
            seed=seed,
            captured_at=datetime.now(UTC).isoformat(),
            matrix_hash=_matrix_hash(matrix),
            check_results=report.checks,
        )
        self._write(baseline)
        return baseline

    def load_baseline(self, profile_id: str) -> BaselineResult:
        """Load a previously captured baseline from disk.

        Raises ``FileNotFoundError`` if no baseline exists for *profile_id*.
        """
        path = self._dir / f"{profile_id}.json"
        if not path.is_file():
            raise FileNotFoundError(
                f"No baseline found for profile '{profile_id}' at {path}"
            )
        raw = json.loads(path.read_text(encoding="utf-8"))
        return BaselineResult(
            profile_id=raw["profile_id"],
            seed=raw["seed"],
            captured_at=raw["captured_at"],
            matrix_hash=raw["matrix_hash"],
            check_results=tuple(
                CheckResult(**cr) for cr in raw["check_results"]
            ),
        )

    def detect_regression(
        self,
        current_report: ValidationReport,
        baseline: BaselineResult,
    ) -> Sequence[CheckResult]:
        """Return checks that regressed (were passing, now failing)."""
        baseline_pass_set = {
            cr.check_id for cr in baseline.check_results if cr.passed
        }
        regressed: list[CheckResult] = []
        for cr in current_report.checks:
            if cr.check_id in baseline_pass_set and not cr.passed:
                regressed.append(cr)
        return regressed

    def run_ci(
        self,
        profile: DeviceProfile,
        seed: str,
    ) -> int:
        """Run a full CI cycle: derive → validate → compare → report.

        Returns 0 on pass, 1 if regressions are detected.

        Raises ``FileNotFoundError`` if no baseline exists for the profile.
        """
        from super_browser.stealth.consistency.derive import derive_matrix

        matrix = derive_matrix(profile, seed)
        suite = FingerprintValidationSuite()
        report = suite.run(matrix, profile)
        baseline = self.load_baseline(profile.id)
        regressed = self.detect_regression(report, baseline)
        if regressed:
            for cr in regressed:
                print(
                    f"REGRESSION: {cr.check_id} ({cr.name}) — "
                    f"expected pass, got fail: {cr.actual}",
                    file=__import__("sys").stderr,
                )
            return 1
        return 0

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _write(self, baseline: BaselineResult) -> None:
        path = self._dir / f"{baseline.profile_id}.json"
        payload = {
            "profile_id": baseline.profile_id,
            "seed": baseline.seed,
            "captured_at": baseline.captured_at,
            "matrix_hash": baseline.matrix_hash,
            "check_results": [asdict(cr) for cr in baseline.check_results],
        }
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
