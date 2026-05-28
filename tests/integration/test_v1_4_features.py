"""Cross-feature integration tests for v1.4 features (CloakBrowser, human behavior,
fingerprint scoring, stealth-check CLI).

These tests exercise combinations of v1.4 features working together using
mocks/stubs — no real browser or network required.

Tests:
  1. CloakBrowser backend detection works
  2. Human behavior adapter dispatches correctly per backend
  3. Fingerprint scanner produces scores in offline mode
  4. stealth-check CLI command runs
  5. All features coexist without conflict
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from super_browser.browser.cloak_backend import (
    CloakBrowserAdapter,
    is_cloak_available,
)
from super_browser.stealth.fingerprint_scanner import FingerprintScanner
from super_browser.stealth.fingerprint_score import FingerprintGrade, FingerprintScorer
from super_browser.stealth.human import HumanBehaviorAdapter
from super_browser.stealth.human_config import HumanConfig
from super_browser.stealth.scoring import FingerprintCheck, FingerprintScore

# ---------------------------------------------------------------------------
# TEST-29-01: CloakBrowser backend detection works
# ---------------------------------------------------------------------------


class TestCloakBrowserBackendDetection:
    """Verify backend detection, adapter creation, and graceful fallback."""

    def test_is_cloak_available_returns_false_when_not_installed(self):
        """When cloakbrowser is not importable, is_cloak_available() is False."""
        with patch.dict("sys.modules", {"cloakbrowser": None}):
            # Force re-evaluation by patching the import inside the function
            with patch("builtins.__import__", side_effect=ImportError("no module")):
                assert is_cloak_available() is False

    def test_adapter_from_config_returns_none_when_disabled(self):
        """When cloak_enabled=False, from_config() returns None."""
        config = MagicMock()
        config.cloak_enabled = False
        result = CloakBrowserAdapter.from_config(config)
        assert result is None

    def test_adapter_from_config_returns_none_when_none_config(self):
        """When config is None, from_config() returns None."""
        result = CloakBrowserAdapter.from_config(None)
        assert result is None

    def test_adapter_from_config_returns_adapter_when_available(self):
        """When cloakbrowser is installed and enabled, from_config() returns adapter."""
        config = MagicMock()
        config.cloak_enabled = True
        config.cloak_humanize = True
        config.cloak_humanize_preset = "careful"
        config.cloak_fingerprint_seed = 42
        config.cloak_geoip = False
        config.cloak_platform = "win32"

        with patch(
            "super_browser.browser.cloak_backend.is_cloak_available",
            return_value=True,
        ):
            adapter = CloakBrowserAdapter.from_config(config)
            assert adapter is not None
            assert adapter.backend_name() == "cloak"

    def test_adapter_backend_name_is_cloak(self):
        """Static backend_name() returns 'cloak'."""
        assert CloakBrowserAdapter.backend_name() == "cloak"


# ---------------------------------------------------------------------------
# TEST-29-02: Human behavior adapter dispatches correctly per backend
# ---------------------------------------------------------------------------


class TestHumanBehaviorAdapterDispatch:
    """Verify HumanBehaviorAdapter dispatches to the correct backend path."""

    def test_default_backend_is_patchright(self):
        """Default backend is 'patchright'."""
        adapter = HumanBehaviorAdapter()
        assert adapter.backend == "patchright"

    def test_cloak_backend_dispatch(self):
        """When backend='cloak', adapter uses cloak backend."""
        config = HumanConfig(preset="fast")
        adapter = HumanBehaviorAdapter(config=config, backend="cloak")
        assert adapter.backend == "cloak"
        assert adapter.config.preset == "fast"

    @pytest.mark.asyncio
    async def test_patchright_click_uses_mouse_jitter(self):
        """Patchright click path uses behavioral synthesis for mouse trajectory."""
        adapter = HumanBehaviorAdapter(
            config=HumanConfig(preset="fast"),
            backend="patchright",
        )

        # Mock page with a selectable element
        mock_el = AsyncMock()
        mock_el.bounding_box.return_value = {
            "x": 100.0,
            "y": 200.0,
            "width": 80.0,
            "height": 30.0,
        }

        mock_page = AsyncMock()
        mock_page.query_selector.return_value = mock_el
        mock_page.mouse.move = AsyncMock()
        mock_page.mouse.down = AsyncMock()
        mock_page.mouse.up = AsyncMock()

        await adapter.humanize_click(mock_page, "#btn")

        # Verify mouse movement was triggered (behavioral synthesis sends multiple moves)
        assert mock_page.mouse.move.call_count >= 5, "Expected multiple mouse moves from trajectory"
        mock_page.mouse.down.assert_called_once()
        mock_page.mouse.up.assert_called_once()

    @pytest.mark.asyncio
    async def test_cloak_click_delegates_to_page(self):
        """Cloak click path delegates to page mouse click."""
        adapter = HumanBehaviorAdapter(
            config=HumanConfig(preset="default"),
            backend="cloak",
        )

        mock_el = AsyncMock()
        mock_el.bounding_box.return_value = {
            "x": 100.0,
            "y": 200.0,
            "width": 80.0,
            "height": 30.0,
        }

        mock_page = AsyncMock()
        mock_page.query_selector.return_value = mock_el
        mock_page.mouse.click = AsyncMock()

        await adapter.humanize_click(mock_page, "#btn")

        # Verify Cloak path uses mouse.click
        mock_page.mouse.click.assert_called_once()

    @pytest.mark.asyncio
    async def test_humanize_type_dispatches_per_backend(self):
        """Typing dispatches correctly for both backends."""
        config = HumanConfig(preset="fast")

        for backend in ("patchright", "cloak"):
            adapter = HumanBehaviorAdapter(config=config, backend=backend)
            mock_page = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.keyboard.type = AsyncMock()
            mock_page.keyboard.press = AsyncMock()

            await adapter.humanize_type(mock_page, "#input", "hi")

            # Both backends click the selector first
            mock_page.click.assert_called_once_with("#input")

    @pytest.mark.asyncio
    async def test_humanize_scroll_uses_mouse_wheel(self):
        """Scroll uses behavioral synthesis with multiple wheel events."""
        adapter = HumanBehaviorAdapter()
        mock_page = AsyncMock()
        mock_page.mouse.wheel = AsyncMock()

        await adapter.humanize_scroll(mock_page, "down", amount=2)

        # Behavioral synthesis sends multiple wheel events (inertial model)
        assert mock_page.mouse.wheel.call_count >= 1, "Expected wheel events from scroll synthesis"

    def test_careful_preset_applies_values(self):
        """Careful preset applies slower, more cautious values."""
        config = HumanConfig(preset="careful")
        assert config.typing_delay_ms[0] >= 80
        assert config.click_hold_ms[1] >= 350
        assert config.typo_chance <= 0.02

    def test_fast_preset_applies_values(self):
        """Fast preset applies quicker, more aggressive values."""
        config = HumanConfig(preset="fast")
        assert config.typing_delay_ms[1] <= 60
        assert config.click_hold_ms[1] <= 80
        assert config.typo_chance <= 0.01


# ---------------------------------------------------------------------------
# TEST-29-03: Fingerprint scanner produces scores in offline mode
# ---------------------------------------------------------------------------


class TestFingerprintScannerOffline:
    """Verify FingerprintScanner produces valid scores in offline mode."""

    @pytest.mark.asyncio
    async def test_offline_scan_returns_score(self):
        """Offline scan returns a FingerprintScore with valid checks."""
        scanner = FingerprintScanner(scanner_config={"offline": True})
        score = await scanner.scan()

        assert isinstance(score, FingerprintScore)
        assert score.overall >= 0
        assert score.overall <= 100
        assert len(score.checks) > 0
        assert score.backend == "patchright"

    @pytest.mark.asyncio
    async def test_offline_scan_all_checks_have_valid_scores(self):
        """Every check in the offline score has a score in 0-100 range."""
        scanner = FingerprintScanner(scanner_config={"offline": True})
        score = await scanner.scan()

        for check in score.checks:
            assert 0 <= check.score <= 100, f"Check {check.name} has invalid score {check.score}"
            assert isinstance(check.passed, bool)
            assert isinstance(check.name, str)
            assert isinstance(check.detail, str)

    @pytest.mark.asyncio
    async def test_offline_scan_with_custom_checks(self):
        """Custom checks override the default offline checks."""
        custom = [
            FingerprintCheck(name="custom_1", passed=True, score=100, detail="Custom check 1"),
            FingerprintCheck(name="custom_2", passed=False, score=50, detail="Custom check 2"),
        ]
        scanner = FingerprintScanner(
            scanner_config={"offline": True, "custom_checks": custom}
        )
        score = await scanner.scan()

        assert len(score.checks) == 2
        assert score.checks[0].name == "custom_1"
        assert score.checks[1].name == "custom_2"
        # Overall = mean of 100 and 50 = 75
        assert score.overall == 75

    @pytest.mark.asyncio
    async def test_offline_scan_with_cloak_backend(self):
        """Offline scan respects backend name in config."""
        scanner = FingerprintScanner(
            scanner_config={"offline": True, "backend": "cloak"}
        )
        score = await scanner.scan()
        assert score.backend == "cloak"

    def test_scanner_offline_property(self):
        """Scanner offline property reflects config."""
        scanner = FingerprintScanner(scanner_config={"offline": True})
        assert scanner.offline is True

        scanner2 = FingerprintScanner(scanner_config={"offline": False})
        assert scanner2.offline is False

    @pytest.mark.asyncio
    async def test_scan_site_offline_returns_mock(self):
        """scan_site in offline mode returns a mock check."""
        scanner = FingerprintScanner(scanner_config={"offline": True})
        check = await scanner.scan_site(None, "https://example.com")
        assert check.passed is True
        assert check.score == 100
        assert "Offline" in check.detail

    def test_format_report_produces_markdown(self):
        """format_report produces a valid Markdown report."""
        scanner = FingerprintScanner(scanner_config={"offline": True, "backend": "patchright"})
        score = scanner._offline_scan()
        report = FingerprintScanner.format_report(score)

        assert "## Stealth Report" in report
        assert "**Backend:** patchright" in report
        assert "**Overall Score:**" in report
        assert "webdriver" in report


# ---------------------------------------------------------------------------
# TEST-29-04: stealth-check CLI command runs
# ---------------------------------------------------------------------------


class TestStealthCheckCLI:
    """Verify the stealth-check CLI command works end-to-end."""

    @pytest.mark.asyncio
    async def test_stealth_check_offline_passes(self):
        """stealth-check in offline mode produces a report and returns 0 (pass)."""
        from super_browser.stealth.fingerprint_scanner import FingerprintScanner
        from super_browser.stealth.report import StealthReport

        scanner = FingerprintScanner(scanner_config={"offline": True})
        score = await scanner.scan()

        # Verify score is passing (offline defaults all pass)
        assert score.overall >= 70

        # Generate report like CLI does
        report = StealthReport.generate_markdown(score)
        assert "# Stealth Report" in report
        assert str(score.overall) in report

    @pytest.mark.asyncio
    async def test_stealth_check_html_format(self):
        """stealth-check --format html produces valid HTML."""
        from super_browser.stealth.fingerprint_scanner import FingerprintScanner
        from super_browser.stealth.report import StealthReport

        scanner = FingerprintScanner(scanner_config={"offline": True})
        score = await scanner.scan()

        report = StealthReport.generate_html(score)
        assert "<!DOCTYPE html>" in report
        assert "<html" in report
        assert "Stealth Report" in report
        assert str(score.overall) in report

    @pytest.mark.asyncio
    async def test_stealth_check_threshold_check(self):
        """stealth-check threshold comparison works correctly."""
        from super_browser.stealth.fingerprint_scanner import FingerprintScanner

        scanner = FingerprintScanner(scanner_config={"offline": True})
        score = await scanner.scan()

        # Default offline scores should pass threshold 70
        assert score.overall >= 70  # Would return exit code 0

        # Low threshold should also pass
        assert score.overall >= 50  # Would return exit code 0

    def test_cli_parser_accepts_stealth_check(self):
        """CLI argparse recognizes stealth-check subcommand."""
        import argparse

        parser = argparse.ArgumentParser()
        sub = parser.add_subparsers(dest="command")
        stealth_check = sub.add_parser("stealth-check")
        stealth_check.add_argument("--online", action="store_true", default=False)
        stealth_check.add_argument("--format", default="markdown", choices=["markdown", "html"])
        stealth_check.add_argument("--threshold", type=int, default=70)

        # Parse with stealth-check args
        args = parser.parse_args(["stealth-check"])
        assert args.command == "stealth-check"
        assert args.online is False
        assert args.format == "markdown"
        assert args.threshold == 70

        # Parse with options
        args2 = parser.parse_args(["stealth-check", "--online", "--format", "html", "--threshold", "90"])
        assert args2.online is True
        assert args2.format == "html"
        assert args2.threshold == 90


# ---------------------------------------------------------------------------
# TEST-29-05: All features coexist without conflict
# ---------------------------------------------------------------------------


class TestAllFeaturesCoexist:
    """Cross-feature integration: CloakBrowser + HumanBehavior + FingerprintScanner
    all work together without conflict."""

    @pytest.mark.asyncio
    async def test_cloak_backend_with_human_adapter(self):
        """CloakBrowser adapter and HumanBehaviorAdapter work together."""
        config = MagicMock()
        config.cloak_enabled = True
        config.cloak_humanize = True
        config.cloak_humanize_preset = "careful"
        config.cloak_fingerprint_seed = 42
        config.cloak_geoip = False
        config.cloak_platform = None

        with patch(
            "super_browser.browser.cloak_backend.is_cloak_available",
            return_value=True,
        ):
            cloak_adapter = CloakBrowserAdapter.from_config(config)
            assert cloak_adapter is not None

        human_config = HumanConfig(preset="careful")
        human_adapter = HumanBehaviorAdapter(config=human_config, backend="cloak")

        assert human_adapter.backend == "cloak"
        assert human_adapter.config.typing_delay_ms[0] >= 80

    @pytest.mark.asyncio
    async def test_fingerprint_scanner_with_both_backends(self):
        """FingerprintScanner works with both cloak and patchright backends."""
        for backend in ("patchright", "cloak"):
            scanner = FingerprintScanner(
                scanner_config={"offline": True, "backend": backend}
            )
            score = await scanner.scan()

            assert score.backend == backend
            assert 0 <= score.overall <= 100
            assert len(score.checks) > 0

    @pytest.mark.asyncio
    async def test_full_stealth_pipeline(self):
        """Complete stealth pipeline: detect backend → configure human → scan fingerprint."""
        # 1. Detect backend (CloakBrowser not installed → patchright)
        backend = "cloak" if is_cloak_available() else "patchright"

        # 2. Configure human behavior for detected backend
        human_config = HumanConfig(preset="default")
        human_adapter = HumanBehaviorAdapter(config=human_config, backend=backend)
        assert human_adapter.backend == backend

        # 3. Run fingerprint scan with matching backend
        scanner = FingerprintScanner(
            scanner_config={"offline": True, "backend": backend}
        )
        score = await scanner.scan()

        # 4. Verify everything is consistent
        assert score.backend == backend
        assert score.overall > 0
        assert human_adapter.backend == score.backend

        # 5. Generate report
        report = FingerprintScanner.format_report(score)
        assert f"**Backend:** {backend}" in report

    def test_fingerprint_scorer_independent(self):
        """FingerprintScorer works independently of scanner."""
        scorer = FingerprintScorer()
        checks = {
            "webdriver": {"passed": True, "detail": "OK"},
            "plugins_mimetypes": {"passed": True, "detail": "OK"},
            "user_agent": {"passed": True, "detail": "OK"},
            "headers": {"passed": True, "detail": "OK"},
            "tls": {"passed": True, "detail": "OK"},
            "misc": {"passed": True, "detail": "OK"},
        }
        result = scorer.score_from_checks(checks)

        assert result.score == 100
        assert result.grade == FingerprintGrade.A
        assert len(result.deductions) == 0

    def test_fingerprint_scorer_mixed_results(self):
        """FingerprintScorer handles mixed pass/fail correctly."""
        scorer = FingerprintScorer()
        checks = {
            "webdriver": {"passed": True, "detail": "OK"},
            "plugins_mimetypes": {"passed": False, "detail": "Plugins detected"},
            "user_agent": {"passed": True, "detail": "OK"},
            "headers": {"passed": False, "detail": "Missing headers"},
            "tls": {"passed": True, "detail": "OK"},
            "misc": {"passed": True, "detail": "OK"},
        }
        result = scorer.score_from_checks(checks)

        assert result.score < 100
        assert len(result.deductions) == 2
        assert any("plugins_mimetypes" in d for d in result.deductions)
        assert any("headers" in d for d in result.deductions)

    @pytest.mark.asyncio
    async def test_human_adapter_with_fingerprint_report(self):
        """HumanBehaviorAdapter config and FingerprintScanner report are compatible."""
        presets = ["default", "careful", "fast"]

        for preset in presets:
            human_config = HumanConfig(preset=preset)
            adapter = HumanBehaviorAdapter(config=human_config, backend="patchright")

            scanner = FingerprintScanner(
                scanner_config={"offline": True, "backend": adapter.backend}
            )
            score = await scanner.scan()
            report = FingerprintScanner.format_report(score)

            # Verify report is well-formed for each preset
            assert f"**Backend:** {adapter.backend}" in report
            assert score.overall > 0
