"""TEST-25-02-*: Memory-aware agent loop integration tests."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from super_browser.agent.loop import AgentLoop
from super_browser.agent.registry import ToolRegistry
from super_browser.memory.integration import (
    build_memory_context,
    create_memory_store,
    extract_domain_from_url,
    record_selector_result,
    record_task_result,
)
from super_browser.memory.store import MemoryStore

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeLLM:
    """Minimal LLM client that returns a done response."""

    async def propose_action(self, prompt: str) -> dict:
        return {"done": True}

    async def create_plan(self, instruction: str, tool_api: str) -> list[dict]:
        return [{"description": instruction}]

    async def replan(self, **kwargs: Any) -> list[dict]:
        return [{"description": "replanned"}]


class FakeLLMWithActions:
    """LLM that returns a click action then done."""

    def __init__(self) -> None:
        self._call = 0

    async def propose_action(self, prompt: str) -> dict:
        self._call += 1
        if self._call == 1:
            return {"action": "click", "params": {"target": "#btn"}}
        return {"done": True}

    async def create_plan(self, instruction: str, tool_api: str) -> list[dict]:
        return [{"description": instruction}]

    async def replan(self, **kwargs: Any) -> list[dict]:
        return [{"description": "replanned"}]


class FakeLLMFail:
    """LLM that causes an error."""

    async def propose_action(self, prompt: str) -> dict:
        raise RuntimeError("LLM failure")

    async def create_plan(self, instruction: str, tool_api: str) -> list[dict]:
        raise RuntimeError("plan failure")

    async def replan(self, **kwargs: Any) -> list[dict]:
        return []


# ---------------------------------------------------------------------------
# TEST-25-02-01: Successful task saves action sequence
# ---------------------------------------------------------------------------

class TestSuccessfulTaskSaves:
    @pytest.mark.asyncio
    async def test_successful_task_saves_to_memory(self, tmp_path):
        """TEST-25-02-01: Successful task saves action sequence to memory."""
        store = MemoryStore(tmp_path / "memory")

        registry = ToolRegistry()
        # Register a click tool
        async def click_handler(target: str = "") -> Any:
            from super_browser.results import action_result
            return action_result(ok=True)

        registry.register(click_handler)

        controller = MagicMock()
        controller._page = MagicMock()
        controller._page.url = "https://shop.example.com/products"

        llm = FakeLLM()
        loop = AgentLoop(
            controller=controller,
            registry=registry,
            llm_client=llm,
            max_steps=5,
        )
        loop.set_memory_store(store, current_url="https://shop.example.com/products")
        result = await loop.run("buy product")
        assert result.completion_reason == "success"

        # Verify memory was saved
        loaded = store.load("shop.example.com")
        assert len(loaded.sequences) >= 1
        assert loaded.sequences[0].task == "buy product"

    @pytest.mark.asyncio
    async def test_successful_with_actions_saves(self, tmp_path):
        """Action sequence includes actual actions taken."""
        store = MemoryStore(tmp_path / "memory")

        registry = ToolRegistry()
        async def click_handler(target: str = "") -> Any:
            from super_browser.results import action_result
            return action_result(ok=True)

        registry.register(click_handler)

        controller = MagicMock()
        controller._page = MagicMock()
        controller._page.url = "https://app.example.com"

        llm = FakeLLMWithActions()
        loop = AgentLoop(
            controller=controller,
            registry=registry,
            llm_client=llm,
            max_steps=5,
        )
        loop.set_memory_store(store, current_url="https://app.example.com")
        result = await loop.run("click button")
        assert result.completion_reason == "success"

        loaded = store.load("app.example.com")
        assert len(loaded.sequences) >= 1
        # Should have recorded the click action
        actions = loaded.sequences[0].actions
        assert any(a.get("action") == "click" for a in actions)


# ---------------------------------------------------------------------------
# TEST-25-02-02: Failed task does NOT save sequence
# ---------------------------------------------------------------------------

class TestFailedTaskNoSave:
    @pytest.mark.asyncio
    async def test_failed_task_not_saved(self, tmp_path):
        """TEST-25-02-02: Failed tasks do not save sequences to memory."""
        store = MemoryStore(tmp_path / "memory")

        controller = MagicMock()
        controller._page = MagicMock()
        controller._page.url = "https://fail.example.com"

        registry = ToolRegistry()
        llm = FakeLLMFail()

        loop = AgentLoop(
            controller=controller,
            registry=registry,
            llm_client=llm,
            max_steps=1,
        )
        loop.set_memory_store(store, current_url="https://fail.example.com")
        result = await loop.run("do something impossible")  # noqa: F841
        # The loop should complete (with error) but NOT save to memory
        loaded = store.load("fail.example.com")
        assert len(loaded.sequences) == 0


# ---------------------------------------------------------------------------
# TEST-25-02-03: Memory context injected into LLM prompt
# ---------------------------------------------------------------------------

class TestMemoryContextInjection:
    @pytest.mark.asyncio
    async def test_memory_context_in_prompt(self, tmp_path):
        """TEST-25-02-03: Memory context is injected into the LLM prompt."""
        store = MemoryStore(tmp_path / "memory")
        # Pre-populate memory
        store.record_sequence(
            "ctx.example.com",
            "search products",
            [{"action": "click"}, {"action": "fill"}],
            success=True,
        )

        prompts_seen: list[str] = []

        class CaptureLLM:
            async def propose_action(self, prompt: str) -> dict:
                prompts_seen.append(prompt)
                return {"done": True}

            async def create_plan(self, instruction: str, tool_api: str) -> list[dict]:
                return [{"description": instruction}]

        controller = MagicMock()
        controller._page = MagicMock()

        registry = ToolRegistry()
        llm = CaptureLLM()

        loop = AgentLoop(
            controller=controller,
            registry=registry,
            llm_client=llm,
            max_steps=5,
        )
        loop.set_memory_store(store, current_url="https://ctx.example.com/page")
        await loop.run("search for widgets")

        assert len(prompts_seen) >= 1
        assert "Previous successful" in prompts_seen[0]


# ---------------------------------------------------------------------------
# TEST-25-02-04: Working selector saved to selector map
# ---------------------------------------------------------------------------

class TestSelectorRecording:
    def test_record_selector_result(self, tmp_path):
        """TEST-25-02-04: Working selectors are recorded via integration."""
        store = MemoryStore(tmp_path / "memory")
        record_selector_result(
            store,
            "https://sel.example.com",
            "login_button",
            "#login-btn",
        )
        loaded = store.load("sel.example.com")
        assert loaded.selectors["login_button"] == "#login-btn"

    def test_record_selector_with_none_store(self):
        """No error when store is None."""
        record_selector_result(None, "https://x.com", "btn", "#b")


# ---------------------------------------------------------------------------
# TEST-25-02-05: sb.memory returns MemoryStore
# ---------------------------------------------------------------------------

class TestFacadeMemoryProperty:
    def test_memory_property_returns_store(self):
        """TEST-25-02-05: sb.memory returns MemoryStore when enabled."""
        from super_browser.agent.facade import SuperBrowser

        sb = SuperBrowser()
        assert sb.memory is None

        sb.enable_memory()
        assert isinstance(sb.memory, MemoryStore)

    def test_memory_disabled_by_default(self):
        """Memory is None when not explicitly enabled."""
        from super_browser.agent.facade import SuperBrowser

        sb = SuperBrowser()
        assert sb.memory is None


# ---------------------------------------------------------------------------
# Integration helpers
# ---------------------------------------------------------------------------

class TestIntegrationHelpers:
    def test_create_memory_store_enabled(self, tmp_path):
        """create_memory_store returns a store when enabled."""
        store = create_memory_store(
            memory_enabled=True,
            memory_dir=str(tmp_path / "mem"),
        )
        assert isinstance(store, MemoryStore)

    def test_create_memory_store_disabled(self):
        """create_memory_store returns None when disabled."""
        store = create_memory_store(memory_enabled=False)
        assert store is None

    def test_extract_domain(self):
        """extract_domain_from_url parses correctly."""
        assert extract_domain_from_url("https://shop.example.com/path") == "shop.example.com"
        assert extract_domain_from_url("http://localhost:8080") == "localhost"
        assert extract_domain_from_url("not-a-url") == "unknown"

    def test_build_memory_context_empty(self):
        """build_memory_context returns empty string for None store."""
        assert build_memory_context(None, "https://x.com") == ""

    def test_record_task_result_skips_none(self):
        """record_task_result does nothing when store is None."""
        record_task_result(None, "https://x.com", "task", [], True)
        # No error = pass
