"""Tests for @agent_action decorator and build_action_api_description."""

import inspect
from unittest.mock import MagicMock

from super_browser.interaction.decorator import agent_action, build_action_api_description


class TestAgentActionDecorator:
    def test_marks_function(self):
        @agent_action
        async def my_action(self, x: int) -> None:
            """Do something."""
        assert my_action.is_agent_action is True

    def test_non_decorated_lacks_attribute(self):
        async def plain(self): ...
        assert not getattr(plain, "is_agent_action", False)

    def test_preserves_signature(self):
        @agent_action
        async def my_action(self, target: str, *, button: str = "left") -> None:
            """Click."""
        sig = inspect.signature(my_action)
        assert "target" in sig.parameters
        assert sig.parameters["button"].default == "left"


class TestBuildActionAPIDescription:
    def _make_controller(self):
        class FakeController:
            @agent_action
            async def click(self, target: str) -> None:
                """Click on element."""

            @agent_action
            async def fill(self, target: str, value: str) -> None:
                """Fill text input."""

            def not_an_action(self):
                pass

        return FakeController()

    def test_contains_all_action_methods(self):
        ctrl = self._make_controller()
        desc = build_action_api_description(ctrl)
        assert "click" in desc
        assert "fill" in desc
        assert "not_an_action" not in desc

    def test_contains_docstrings(self):
        ctrl = self._make_controller()
        desc = build_action_api_description(ctrl)
        assert "Click on element." in desc
        assert "Fill text input." in desc

    def test_contains_signatures(self):
        ctrl = self._make_controller()
        desc = build_action_api_description(ctrl)
        assert "target: str" in desc

    def test_empty_controller(self):
        class EmptyController:
            pass
        desc = build_action_api_description(EmptyController())
        assert desc.startswith("Available browser actions:")
