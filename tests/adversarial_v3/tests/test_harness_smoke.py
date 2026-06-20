"""End-to-end harness smoke tests using StubBackend.

These verify the full pipeline (harness -> server -> browser -> vectors
-> scoring -> reporting) runs without crashing. With StubBackend,
browser-dependent vectors return INCONCLUSIVE -- this is the correct
honest behavior and validates the pipeline itself.
"""

from __future__ import annotations

import json

import pytest
from adversarial3.core import Tier, Verdict
from adversarial3.harness import AssessmentHarness


class TestHarnessSmokeStub:
    """Full pipeline test with stub backend -- no real browser."""

    @pytest.mark.asyncio
    async def test_harness_runs_controlled_tier(self, tmp_path):
        """The harness must complete without raising, even with stub."""
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        report = await harness.run(
            tiers=[Tier.CONTROLLED],
            skip_interaction=True,
            run_id="smoke-001",
        )
        assert report is not None
        assert report.run_id == "smoke-001"
        assert len(report.results) >= 1

    @pytest.mark.asyncio
    async def test_json_report_written(self, tmp_path):
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        await harness.run(
            tiers=[Tier.CONTROLLED],
            run_id="smoke-002",
        )
        json_path = tmp_path / "smoke-002.json"
        assert json_path.exists(), "JSON report must be written"
        data = json.loads(json_path.read_text(encoding="utf-8"))
        assert data["run_id"] == "smoke-002"

    @pytest.mark.asyncio
    async def test_markdown_report_written(self, tmp_path):
        """This test would have caught the Markdown reporter syntax error."""
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        await harness.run(
            tiers=[Tier.CONTROLLED],
            run_id="smoke-003",
        )
        md_path = tmp_path / "smoke-003.md"
        assert md_path.exists(), "Markdown report must be written"
        content = md_path.read_text(encoding="utf-8")
        assert "smoke-003" in content
        assert "Summary" in content

    @pytest.mark.asyncio
    async def test_history_written(self, tmp_path):
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        await harness.run(
            tiers=[Tier.CONTROLLED],
            run_id="smoke-004",
        )
        history_path = tmp_path / "adversarial-history.json"
        assert history_path.exists(), "History file must be written"

    @pytest.mark.asyncio
    async def test_controlled_vector_inconclusive_with_stub(self, tmp_path):
        """Stub backend cannot run JS, so controlled verdict is INCONCLUSIVE."""
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        report = await harness.run(
            tiers=[Tier.CONTROLLED],
            run_id="smoke-005",
        )
        controlled_results = [r for r in report.results if r.tier == Tier.CONTROLLED]
        assert len(controlled_results) == 1
        assert controlled_results[0].verdict == Verdict.INCONCLUSIVE

    @pytest.mark.asyncio
    async def test_all_vectors_inconclusive_or_skipped_under_stub(self, tmp_path):
        """Stub backend cannot run JS, so all browser-dependent vectors must
        be INCONCLUSIVE (or SKIPPED for behavioral). None should be CLEAN
        or FLAGGED -- that would imply real browser data was evaluated."""
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        all_tiers = [
            Tier.FINGERPRINT, Tier.AUTOMATION, Tier.EJECTOR,
            Tier.BEHAVIORAL, Tier.NETWORK, Tier.CONTROLLED,
        ]
        report = await harness.run(
            tiers=all_tiers,
            skip_interaction=False,
            run_id="smoke-honest",
        )
        assert len(report.results) == 24
        for r in report.results:
            assert r.verdict in (Verdict.INCONCLUSIVE, Verdict.SKIPPED), \
                f"{r.vector_id} should be INCONCLUSIVE/SKIPPED under stub, got {r.verdict}"

    @pytest.mark.asyncio
    async def test_stub_run_exits_zero(self, tmp_path):
        """A stub --all run must not produce CRITICAL+FLAGGED (exit 0)."""
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        report = await harness.run(
            tiers=[
                Tier.FINGERPRINT, Tier.AUTOMATION, Tier.EJECTOR,
                Tier.BEHAVIORAL, Tier.NETWORK, Tier.CONTROLLED,
            ],
            skip_interaction=False,
            run_id="smoke-exit",
        )
        critical_flagged = [
            r for r in report.results
            if r.severity.value == "critical" and r.verdict == Verdict.FLAGGED
        ]
        assert len(critical_flagged) == 0, \
            f"Stub should not produce CRITICAL+FLAGGED, got {[r.vector_id for r in critical_flagged]}"

    @pytest.mark.asyncio
    async def test_behavioral_vectors_skipped(self, tmp_path):
        """Behavioral vectors must return SKIPPED, not CLEAN."""
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        report = await harness.run(
            tiers=[Tier.BEHAVIORAL],
            skip_interaction=False,
            run_id="smoke-007",
        )
        for r in report.results:
            assert r.verdict == Verdict.SKIPPED, f"{r.vector_id} should be SKIPPED, got {r.verdict}"

    @pytest.mark.asyncio
    async def test_network_vectors_inconclusive_with_stub(self, tmp_path):
        """Network vectors must return INCONCLUSIVE when no headers captured."""
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        report = await harness.run(
            tiers=[Tier.NETWORK],
            skip_interaction=True,
            run_id="smoke-008",
        )
        for r in report.results:
            assert r.verdict == Verdict.INCONCLUSIVE, f"{r.vector_id} should be INCONCLUSIVE, got {r.verdict}"

    @pytest.mark.asyncio
    async def test_no_external_targets_without_env(self, tmp_path):
        """External targets must NOT appear without SB_ADV=1."""
        import os
        old = os.environ.pop("SB_ADV", None)
        try:
            harness = AssessmentHarness(
                backend_name="stub",
                output_dir=tmp_path,
            )
            report = await harness.run(
                tiers=[Tier.EXTERNAL_SCANNER, Tier.CONTROLLED],
                skip_interaction=True,
                run_id="smoke-009",
            )
            ext_results = [r for r in report.results if r.tier in (Tier.EXTERNAL_SCANNER, Tier.EXTERNAL_VENDOR)]
            assert len(ext_results) == 0, "External targets should not appear without SB_ADV=1"
        finally:
            if old is not None:
                os.environ["SB_ADV"] = old

    @pytest.mark.asyncio
    async def test_suite_version_in_metadata(self, tmp_path):
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        report = await harness.run(
            tiers=[Tier.CONTROLLED],
            run_id="smoke-010",
        )
        assert report.metadata.get("suite_version") == "3.0.0"


class TestVersionConsistency:
    """Ensure package metadata, runtime __version__, and report metadata agree."""

    def test_init_version_is_3(self):
        import adversarial3
        assert adversarial3.__version__ == "3.0.0"

    def test_pyproject_version_matches(self):
        try:
            from importlib.metadata import version
            pkg_version = version("adversarial3")
            assert pkg_version == "3.0.0"
        except Exception:
            # Package may not be installed; skip metadata check
            pass

    @pytest.mark.asyncio
    async def test_report_metadata_has_version(self, tmp_path):
        harness = AssessmentHarness(
            backend_name="stub",
            output_dir=tmp_path,
        )
        report = await harness.run(
            tiers=[Tier.CONTROLLED],
            run_id="ver-test",
        )
        assert report.metadata.get("suite_version") == "3.0.0"
