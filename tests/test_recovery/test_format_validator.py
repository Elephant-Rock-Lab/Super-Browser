"""Tests for FormatValidator — structural and semantic validation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock

from super_browser.recovery.format_validator import FormatValidator
from super_browser.recovery.types import ValidationLevel


class TestValidateStructural:
    def test_valid_json_action(self):
        v = FormatValidator()
        result = v.validate_structural('{"action": "click", "params": {"target": "#btn"}}')
        assert result.valid
        assert result.level == ValidationLevel.STRUCTURAL

    def test_valid_done_response(self):
        v = FormatValidator()
        result = v.validate_structural('{"done": true}')
        assert result.valid

    def test_empty_output_invalid(self):
        v = FormatValidator()
        result = v.validate_structural("")
        assert not result.valid

    def test_invalid_json_invalid(self):
        v = FormatValidator()
        result = v.validate_structural("not json at all")
        assert not result.valid

    def test_code_block_valid(self):
        v = FormatValidator()
        result = v.validate_structural('```json\n{"action": "click"}\n```')
        assert result.valid

    def test_json_object_valid(self):
        v = FormatValidator()
        result = v.validate_structural('{"action": "fill", "params": {"target": "#x"}}')
        assert result.valid

    def test_errors_populated(self):
        v = FormatValidator()
        result = v.validate_structural("random text with no structure")
        assert len(result.errors) > 0


class TestValidateSemantic:
    def test_no_selector_passes(self):
        async def _test():
            v = FormatValidator()
            action = {"params": {}}
            result = await v.validate_semantic(action, None)
            assert result.valid
        asyncio.run(_test())

    def test_ref_selector_passes(self):
        async def _test():
            v = FormatValidator()
            action = {"params": {"target": "@e0"}}
            result = await v.validate_semantic(action, None)
            assert result.valid
        asyncio.run(_test())

    def test_selector_exists(self):
        async def _test():
            v = FormatValidator()
            cdp = MagicMock()
            cdp_result = MagicMock()
            cdp_result.ok = True
            cdp_result.data = {"result": {"value": True}}
            cdp.evaluate = AsyncMock(return_value=cdp_result)
            page = MagicMock()
            page.cdp = cdp
            action = {"params": {"target": "#btn"}}
            result = await v.validate_semantic(action, page)
            assert result.valid
        asyncio.run(_test())

    def test_selector_not_found(self):
        async def _test():
            v = FormatValidator()
            cdp = MagicMock()
            cdp_result = MagicMock()
            cdp_result.ok = True
            cdp_result.data = {"result": {"value": False}}
            cdp.evaluate = AsyncMock(return_value=cdp_result)
            page = MagicMock()
            page.cdp = cdp
            action = {"params": {"target": "#missing"}}
            result = await v.validate_semantic(action, page)
            assert not result.valid
            assert "not found" in result.errors[0].lower()
        asyncio.run(_test())


class TestBuildRepromptMessage:
    def test_includes_errors(self):
        v = FormatValidator()
        from super_browser.recovery.types import ValidationLevel, ValidationResult
        validation = ValidationResult(
            valid=False, level=ValidationLevel.STRUCTURAL,
            errors=["Missing action field", "Invalid JSON"],
        )
        msg = v.build_reprompt_message(validation)
        assert "Missing action field" in msg
        assert "Invalid JSON" in msg

    def test_includes_selectors(self):
        v = FormatValidator()
        from super_browser.recovery.types import ValidationLevel, ValidationResult
        validation = ValidationResult(valid=False, level=ValidationLevel.SEMANTIC, errors=["bad"])
        msg = v.build_reprompt_message(validation, available_selectors=["#btn", "#link"])
        assert "#btn" in msg
