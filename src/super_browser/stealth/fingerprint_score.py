"""FingerprintScorer — composite stealth fingerprint scoring.

Translates raw diagnostic check results into a 0-100 composite score
with letter grades, enabling quick assessment of how detectable a browser
configuration is.

Weights:
    - webdriver        25%
    - plugins/mimetypes 15%
    - user_agent        15%
    - headers           20%
    - TLS               15%
    - misc              10%
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class FingerprintGrade(StrEnum):
    """Letter grade for fingerprint score."""

    A = "A"
    B = "B"
    C = "C"
    D = "D"


@dataclass(frozen=True)
class FingerprintScoreResult:
    """Result of fingerprint scoring."""

    score: int
    grade: FingerprintGrade
    deductions: list[str]
    category_scores: dict[str, int]


class FingerprintScorer:
    """Computes a composite stealth fingerprint score from check results.

    Parameters
    ----------
    checks:
        Dict of check categories to their results.  Expected keys:
        ``webdriver``, ``plugins_mimetypes``, ``user_agent``, ``headers``,
        ``tls``, ``misc``.  Each value should be a dict with at minimum
        a ``passed`` (bool) key.  Additional ``detail`` (str) is optional.
    """

    # Category weights (must sum to 1.0)
    WEIGHTS: dict[str, float] = {
        "webdriver": 0.25,
        "plugins_mimetypes": 0.15,
        "user_agent": 0.15,
        "headers": 0.20,
        "tls": 0.15,
        "misc": 0.10,
    }

    def score_from_checks(self, checks: dict[str, dict[str, Any]]) -> FingerprintScoreResult:
        """Compute composite score and grade from *checks*.

        Parameters
        ----------
        checks:
            Mapping of category → result dict.  Each result dict has
            ``passed`` (bool) and optional ``detail`` (str).

        Returns
        -------
        FingerprintScoreResult
            Score (0-100), grade, deductions list, and per-category scores.
        """
        total = 0.0
        deductions: list[str] = []
        category_scores: dict[str, int] = {}

        for category, weight in self.WEIGHTS.items():
            check = checks.get(category, {})
            passed = check.get("passed", False)
            detail = check.get("detail", "")

            if passed:
                category_score = 100
            else:
                category_score = 0
                deductions.append(f"{category}: {detail}" if detail else f"{category}: failed")

            category_scores[category] = category_score
            total += weight * category_score

        score = int(round(total))
        score = max(0, min(100, score))  # clamp

        grade = self._grade(score)

        logger.info("Fingerprint score: %d/100 (grade %s)", score, grade)

        return FingerprintScoreResult(
            score=score,
            grade=grade,
            deductions=deductions,
            category_scores=category_scores,
        )

    @staticmethod
    def _grade(score: int) -> FingerprintGrade:
        """Map numeric *score* to letter grade."""
        if score >= 90:
            return FingerprintGrade.A
        if score >= 75:
            return FingerprintGrade.B
        if score >= 60:
            return FingerprintGrade.C
        return FingerprintGrade.D
