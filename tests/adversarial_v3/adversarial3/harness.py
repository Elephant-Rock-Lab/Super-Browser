"""Assessment harness: orchestrates server, browser, vectors, scoring, and reporting.

Pipeline:
  1. Start ControlledDetectionServer (local, CI-safe)
  2. Create browser backend
  3. Navigate one page to the server (captures request headers + triggers JS verdict)
  4. Evaluate all selected vectors with the shared page + captured headers
  5. Optionally evaluate external targets (scanners/vendors) on separate pages
  6. Score all results and write JSON + Markdown + history reports
"""

from __future__ import annotations

import asyncio
import os
import time
import uuid
from pathlib import Path
from typing import Any

from adversarial3.backends import create_backend
from adversarial3.core import (
    AssessmentReport,
    BrowserBackend,
    EvaluationContext,
    JSUnsupportedError,
    Page,
    Severity,
    Tier,
    VectorResult,
    Verdict,
)
from adversarial3.engines.scoring import ScoringConfig, WeightedScoringEngine
from adversarial3.reporters.history import HistoryTracker
from adversarial3.reporters.json_reporter import JSONReporter
from adversarial3.reporters.markdown_reporter import MarkdownReporter
from adversarial3.server import ControlledDetectionServer
from adversarial3.vectors import ALL_VECTORS
from adversarial3.vectors.external import (
    ExternalTarget,
    get_external_targets,
)


class AssessmentHarness:
    """Orchestrates the full adversarial assessment pipeline."""

    def __init__(
        self,
        *,
        backend_name: str = "auto",
        server_port: int = 0,
        output_dir: Path | str = "adversarial-results",
        scoring_config: ScoringConfig | None = None,
    ) -> None:
        self.backend_name = backend_name
        self.server_port = server_port
        self.output_dir = Path(output_dir)
        self.scoring_config = scoring_config or ScoringConfig()
        self.scoring_engine = WeightedScoringEngine(self.scoring_config)
        self.server: ControlledDetectionServer | None = None

    async def run(
        self,
        *,
        tiers: list[Tier] | None = None,
        vectors: list[str] | None = None,
        skip_interaction: bool = True,
        record_behavior: bool = False,
        run_id: str | None = None,
    ) -> AssessmentReport:
        run_id = run_id or str(uuid.uuid4())[:8]
        sep = "=" * 60
        print("Adversarial Assessment v3 -- Run " + run_id)
        print(sep)

        self.server = ControlledDetectionServer(port=self.server_port)
        self.server.__enter__()
        server_url = self.server.base_url
        print("Controlled server: " + server_url)

        try:
            backend = create_backend(self.backend_name)
            print("Browser backend: " + backend.__class__.__name__)

            async with backend:
                # When the caller asks to record behavioral telemetry, include
                # the interaction-requiring vectors regardless of the default
                # skip_interaction filter. The two concerns (record? filter?)
                # stay explicit: without record_behavior the default behavior
                # is unchanged and behavioral vectors stay SKIPPED.
                effective_skip_interaction = (
                    False if record_behavior else skip_interaction
                )
                selected = self._select_vectors(
                    tiers, vectors, effective_skip_interaction,
                )
                print("Vectors to run: " + str(len(selected)))
                if record_behavior:
                    print("Behavioral telemetry recording: enabled")

                # --- Phase 1: Navigate to controlled server ---
                # This captures request headers (for network vectors) and
                # triggers the page JS to POST signals to /api/verdict
                # (for the controlled vector).
                page: Page | None = None
                captured_headers: dict[str, Any] = {}
                controlled_verdict: dict[str, Any] | None = None
                behavioral_telemetry: Any = None

                needs_browser = any(v.requires_browser for v in selected)
                if needs_browser:
                    try:
                        page = await backend.new_page()
                        await page.goto(server_url, wait_until="networkidle", timeout=10000)
                        await asyncio.sleep(0.5)

                        if self.server.request_log:
                            last_req = self.server.request_log[-1]
                            captured_headers = dict(last_req.headers)
                            captured_headers["__header_order"] = list(last_req.header_order)

                        controlled_verdict = self.server.last_verdict
                        if controlled_verdict:
                            print("Controlled verdict: " + str(controlled_verdict.get("verdict", "?")))
                        else:
                            print("Controlled verdict: (no JS response -- backend may not execute JS)")
                    except Exception as e:
                        print("Browser navigation failed: " + str(e))

                # --- Phase 1.5: Record behavioral telemetry (opt-in) ---
                # Only when the caller requested it AND a real page exists.
                # Under a stub (no page) this is skipped, leaving telemetry
                # as None so behavioral vectors return SKIPPED -- preserving
                # the honest-stub invariant.
                if record_behavior and page is not None:
                    try:
                        from adversarial3.behavioral_telemetry import record_telemetry

                        behavioral_telemetry = await record_telemetry(page)
                        event_counts = (
                            len(behavioral_telemetry.mouse),
                            len(behavioral_telemetry.keystrokes),
                            len(behavioral_telemetry.scroll),
                        )
                        print(
                            "Behavioral telemetry captured: "
                            + str(event_counts[0]) + " mouse, "
                            + str(event_counts[1]) + " keys, "
                            + str(event_counts[2]) + " scroll events"
                        )
                    except Exception as e:
                        print("Behavioral telemetry recording failed: " + str(e))

                # --- Phase 2: Evaluate vectors ---
                results: list[VectorResult] = []
                for vector in selected:
                    ctx = EvaluationContext(
                        page=page,
                        browser=backend,
                        server_url=server_url,
                        headers=captured_headers,
                        metadata={
                            "controlled_verdict": controlled_verdict,
                            "behavioral_telemetry": behavioral_telemetry,
                        },
                    )
                    result = await self._evaluate_vector(vector, ctx)
                    results.append(result)
                    status = (
                        "PASS" if result.verdict == Verdict.CLEAN
                        else "FAIL" if result.verdict == Verdict.FLAGGED
                        else "SKIP" if result.verdict == Verdict.SKIPPED
                        else "?"
                    )
                    print(f"  [{status}] {vector.vector_id}: {result.verdict.value} ({int(result.duration_ms)}ms)")

                if page:
                    await page.close()

                # --- Phase 3: External targets ---
                ext_targets = self._get_external_targets(tiers)
                if ext_targets:
                    print("\nExternal targets: " + str(len(ext_targets)))
                    for ext in ext_targets:
                        print("  [" + ext.target_id + "] " + ext.url + " ...", flush=True)
                        ext_result = await self._evaluate_external(ext, backend)
                        results.append(ext_result)
                        status = "PASS" if ext_result.verdict == Verdict.CLEAN else "FAIL" if ext_result.verdict == Verdict.FLAGGED else "?"
                        print(f"  [{status}] {ext.target_id}: {ext_result.verdict.value}")
                        await asyncio.sleep(ext.min_interval_s)

                # --- Phase 4: Score and report ---
                report = self.scoring_engine.compute(results)
                report = AssessmentReport(
                    run_id=run_id,
                    timestamp=report.timestamp,
                    overall_score=report.overall_score,
                    tier_summaries=report.tier_summaries,
                    results=report.results,
                    metadata={
                        **report.metadata,
                        "backend": backend.__class__.__name__,
                        "server_url": server_url,
                        "vectors_run": len(results),
                        "suite_version": "3.0.0",
                    },
                )

                self._write_reports(report)

                passed = sum(1 for r in results if r.verdict == Verdict.CLEAN)
                flagged = sum(1 for r in results if r.verdict == Verdict.FLAGGED)
                challenged = sum(1 for r in results if r.verdict == Verdict.CHALLENGED)
                inconclusive = sum(1 for r in results if r.verdict == Verdict.INCONCLUSIVE)
                skipped = sum(1 for r in results if r.verdict == Verdict.SKIPPED)
                print("")
                print(sep)
                print("Overall Score: " + str(round(report.overall_score * 100, 1)) + "%")
                print("Passed: " + str(passed) + "/" + str(len(results)))
                print("Flagged: " + str(flagged))
                print("Challenged: " + str(challenged))
                print("Inconclusive: " + str(inconclusive))
                print("Skipped: " + str(skipped))
                print(sep)

                return report

        finally:
            if self.server:
                self.server.__exit__(None, None, None)

    # ------------------------------------------------------------------
    # Vector evaluation
    # ------------------------------------------------------------------

    async def _evaluate_vector(self, vector: Any, ctx: EvaluationContext) -> VectorResult:
        start = time.perf_counter()
        try:
            result = await vector.evaluate(ctx)
        except JSUnsupportedError as e:
            result = VectorResult(
                vector_id=vector.vector_id,
                tier=vector.tier,
                name=vector.name,
                verdict=Verdict.INCONCLUSIVE,
                score=0.0,
                details={"reason": "Backend does not support JavaScript execution", "backend_error": str(e)},
                severity=vector.severity,
                duration_ms=(time.perf_counter() - start) * 1000,
            )
        except Exception as e:
            result = VectorResult(
                vector_id=vector.vector_id,
                tier=vector.tier,
                name=vector.name,
                verdict=Verdict.INCONCLUSIVE,
                score=0.0,
                details={"error": str(e)},
                severity=vector.severity,
                duration_ms=(time.perf_counter() - start) * 1000,
                error=str(e),
            )

        if result.duration_ms == 0.0:
            result = VectorResult(
                vector_id=result.vector_id,
                tier=result.tier,
                name=result.name,
                verdict=result.verdict,
                score=result.score,
                details=result.details,
                severity=result.severity,
                duration_ms=(time.perf_counter() - start) * 1000,
                error=result.error,
            )
        return result

    # ------------------------------------------------------------------
    # External targets
    # ------------------------------------------------------------------

    async def _evaluate_external(self, ext: ExternalTarget, backend: BrowserBackend) -> VectorResult:
        """Evaluate an external target (scanner or vendor demo) on its own page."""
        start = time.perf_counter()
        try:
            page = await backend.new_page()
            try:
                await page.goto(ext.url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(ext.settle_ms / 1000.0)

                probe_results: dict[str, Any] = {}
                for name, expr in ext.probes.items():
                    try:
                        probe_results[name] = await page.evaluate(expr)
                    except Exception:
                        probe_results[name] = None

                result = ext.parser(target_id=ext.target_id, **probe_results)
                return VectorResult(
                    vector_id=result.vector_id,
                    tier=ext.tier,
                    name=result.name,
                    verdict=result.verdict,
                    score=result.score,
                    details=result.details,
                    severity=result.severity,
                    duration_ms=(time.perf_counter() - start) * 1000,
                )
            finally:
                await page.close()
        except Exception as e:
            return VectorResult(
                vector_id=ext.target_id,
                tier=ext.tier,
                name=ext.target_id,
                verdict=Verdict.INCONCLUSIVE,
                score=0.0,
                details={"error": str(e)},
                severity=Severity.INFO,
                duration_ms=(time.perf_counter() - start) * 1000,
                error=str(e),
            )

    def _get_external_targets(self, tiers: list[Tier] | None) -> list[ExternalTarget]:
        """External targets require both explicit tier selection AND env gate.

        This prevents SB_ADV=1 from injecting external navigation when the
        operator only requested the controlled tier.
        """
        adv_on = os.environ.get("SB_ADV", "").strip() == "1"
        if not adv_on:
            return []

        tier_set = set(tiers) if tiers else set()
        include_scanners = Tier.EXTERNAL_SCANNER in tier_set
        include_vendors = (
            Tier.EXTERNAL_VENDOR in tier_set
            and os.environ.get("SB_ADV_VENDORS", "").strip() == "1"
            and os.environ.get("SB_ADV_VENDORS_ACK", "").strip() == "1"
        )
        return get_external_targets(
            include_scanners=include_scanners,
            include_vendors=include_vendors,
        )

    # ------------------------------------------------------------------
    # Vector selection
    # ------------------------------------------------------------------

    def _select_vectors(
        self,
        tiers: list[Tier] | None,
        vector_ids: list[str] | None,
        skip_interaction: bool,
    ) -> list[Any]:
        candidates = list(ALL_VECTORS)
        if tiers:
            candidates = [v for v in candidates if v.tier in tiers]
        if vector_ids:
            candidates = [v for v in candidates if v.vector_id in vector_ids]
        if skip_interaction:
            candidates = [v for v in candidates if not v.requires_interaction]
        return candidates

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def _write_reports(self, report: AssessmentReport) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        json_path = self.output_dir / (report.run_id + ".json")
        JSONReporter().write(report, json_path)
        print("JSON: " + str(json_path))
        md_path = self.output_dir / (report.run_id + ".md")
        MarkdownReporter().write(report, md_path)
        print("Markdown: " + str(md_path))
        history = HistoryTracker(self.output_dir / "adversarial-history.json")
        history.append(report)
        print("History: " + str(history.path))
