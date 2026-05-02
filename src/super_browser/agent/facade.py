"""SuperBrowser facade — primary entry point for all browser automation."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Optional, TYPE_CHECKING

from super_browser.agent.config import SuperBrowserConfig
from super_browser.agent.delegator import SubagentDelegator
from super_browser.agent.loop import AgentLoop
from super_browser.agent.loop_detector import ActionLoopDetector
from super_browser.agent.registry import ToolRegistry
from super_browser.agent.types import DelegationResult
from super_browser.browser.config import SessionConfig
from super_browser.browser.session import BrowserSession
from super_browser.interaction.controller import MultimodalController
from super_browser.results import (
    ActionMethod,
    ActionResult,
    CompletionReason,
    DelegatedResult,
    ExtractResult,
    NavigateResult,
    action_result,
    timed_action_result,
)

if TYPE_CHECKING:
    from super_browser.agent.llm.protocol import LLMClient

logger = logging.getLogger(__name__)


class SuperBrowser:

    def __init__(
        self,
        config: Optional[SuperBrowserConfig] = None,
        *,
        tool_registry: Optional[ToolRegistry] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        self._config = config or SuperBrowserConfig()
        self._registry = tool_registry or ToolRegistry()
        self._llm_client = llm_client
        self._session: Optional[BrowserSession] = None
        self._controller: Optional[MultimodalController] = None
        self._page: Any = None
        self._abort_signal = asyncio.Event()
        self._running = False
        self._coordinator: Any = None
        self._budget_client: Any = None
        self._flow_logger: Any = None
        self._security_manager: Any = None
        self._vision_controller: Any = None
        self._stealth_manager: Any = None
        self._skill_registry: Any = None

    # -- Lifecycle --

    async def start(self) -> None:
        self._session = BrowserSession(SessionConfig(headless=True))
        await self._session.start()
        self._page = await self._session.new_page()
        self._controller = MultimodalController(self._page, self._page.cdp)
        self._running = True
        self._configure_verification()
        self._configure_vision()
        self._configure_stealth()
        self._configure_skills()
        if self._config.enable_recovery:
            from super_browser.recovery import RecoveryCoordinator
            self._coordinator = RecoveryCoordinator(
                session=self._session, controller=self._controller,
            )
            await self._coordinator.start()
        if self._config.enable_budget:
            from super_browser.budget import (
                BudgetAwareLLMClient,
                CircuitBreaker,
                ContextCompressor,
                CredentialPool,
                ModelCascade,
                TokenBudgetGovernor,
            )
            governor = TokenBudgetGovernor()
            cascade = ModelCascade(governor=governor)
            pool = CredentialPool()
            cb = CircuitBreaker()
            comp = ContextCompressor()
            self._budget_client = BudgetAwareLLMClient(governor, cascade, pool, cb, comp)
        if self._config.trace_enabled:
            from super_browser.tracing import FlowLogger
            from super_browser.tracing.sinks import ConsoleSink
            sinks = [ConsoleSink()]
            if self._config.trace_output_dir:
                from pathlib import Path
                from super_browser.tracing.sinks import FileSink
                path = Path(self._config.trace_output_dir) / "trace.jsonl"
                sinks.append(FileSink(path))
            self._flow_logger = FlowLogger(sinks=sinks)
            await self._flow_logger.start()
        if self._config.enable_security:
            from super_browser.security import SecurityManager, SecurityConfig
            sec_config = SecurityConfig()
            self._security_manager = SecurityManager(sec_config)
        logger.info("SuperBrowser started")

    async def stop(self) -> None:
        self._running = False
        if self._flow_logger:
            await self._flow_logger.stop()
            self._flow_logger = None
        if self._coordinator:
            await self._coordinator.stop()
            self._coordinator = None
        if self._session:
            await self._session.stop()
            self._session = None
        self._controller = None
        self._page = None
        logger.info("SuperBrowser stopped")

    async def __aenter__(self) -> SuperBrowser:
        await self.start()
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.stop()

    # -- Facade methods --

    async def navigate(self, url: str, *, wait_until: str = "domcontentloaded") -> ActionResult:
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=__import__("super_browser.results", fromlist=["ActionError"]).ActionError(__import__("super_browser.results", fromlist=["ErrorCategory"]).ErrorCategory.BROWSER_CRASH, "Not started"))
        await self._page.goto(url, wait_until=wait_until)
        final_url = self._page.url
        title = await self._page.title()
        skills_data = {}
        if self._skill_registry:
            try:
                discovered = await self._skill_registry.auto_discover(url)
                skills_data = {"skills": [{"id": s.skill_id, "name": s.name} for s in discovered]}
            except Exception:
                pass
        return timed_action_result(
            ok=True,
            start_ns=start,
            data=NavigateResult(url=url, final_url=final_url, title=title),
            method=ActionMethod.SELECTOR,
        )

    async def click(self, target: str, *, description: Optional[str] = None) -> ActionResult:
        if not self._controller:
            return action_result(ok=False)
        return await self._controller.click(target, description=description)

    async def fill(self, target: str, value: str, *, clear_first: bool = True, description: Optional[str] = None) -> ActionResult:
        if not self._controller:
            return action_result(ok=False)
        return await self._controller.fill(target, value, clear_first=clear_first, description=description)

    async def act(self, instruction: str, *, max_steps: int = 50) -> ActionResult:
        if not self._controller:
            return action_result(ok=False)

        if self._llm_client is None:
            raise ConfigurationError(
                "No LLM client configured. Pass llm_client= to SuperBrowser()."
            )

        loop = AgentLoop(
            controller=self._controller,
            registry=self._registry,
            llm_client=self._llm_client,
            max_steps=max_steps,
            recovery_coordinator=self._coordinator,
            budget_client=self._budget_client,
            flow_logger=self._flow_logger,
            security_manager=self._security_manager,
            stealth_manager=getattr(self, '_stealth_manager', None),
        )
        result = await loop.run(instruction)
        return action_result(
            ok=result.completion_reason == "success",
            data=DelegatedResult(
                instruction=instruction,
                completion_reason=CompletionReason.SUCCESS if result.completion_reason == "success" else CompletionReason.ERROR,
                summary=f"Completed in {result.total_steps} steps",
                steps_executed=result.total_steps,
                budget_remaining=self._budget_client._governor.daily_remaining if self._budget_client else 0.0,
                execution_history=[{"step": s.step_number, "action": s.action_name} for s in result.steps],
            ),
        )

    async def extract(self, query: str, *, selector: Optional[str] = None, schema: Optional[dict] = None) -> ActionResult:
        start = time.monotonic()
        if not self._controller:
            return action_result(ok=False)

        if selector:
            result = await self._controller._cdp.evaluate(
                f'(function(){{ var el = document.querySelector("{selector}"); '
                f'return el ? el.textContent : null; }})()'
            )
            extracted = result.data.get("result", {}).get("value") if result.ok else None
        else:
            snap = await self._controller.capture_ax_snapshot()
            extracted = snap.to_compact_str()

        return timed_action_result(
            ok=True,
            start_ns=start,
            data=ExtractResult(selector=selector or query, extracted=extracted, element_count=0),
            method=ActionMethod.SELECTOR,
        )

    async def observe(self) -> ActionResult:
        start = time.monotonic()
        if not self._controller:
            return action_result(ok=False)

        url = self._page.url
        title = await self._page.title()
        snap = await self._controller.capture_ax_snapshot()
        interactive_count = sum(1 for n in snap.nodes.values() if n.is_interactive)

        return timed_action_result(
            ok=True,
            start_ns=start,
            data={"url": url, "title": title, "interactive_elements": interactive_count, "total_elements": len(snap.nodes)},
        )

    # -- Delegation --

    async def delegate(self, tasks: list[str], *, max_concurrency: int = 4) -> DelegationResult:
        if not self._session:
            return DelegationResult(tasks=[], total_duration_ms=0, completed_count=0, failed_count=len(tasks), cancelled_count=0)
        delegator = SubagentDelegator(
            self._session, self._registry, self._llm_client,
            max_concurrency=max_concurrency,
            recovery_coordinator=self._coordinator,
            budget_client=self._budget_client,
            flow_logger=self._flow_logger,
            security_manager=self._security_manager,
            stealth_manager=self._stealth_manager,
        )
        return await delegator.delegate(tasks, max_concurrency=max_concurrency)

    # -- Tool management --

    def tools(self, *, toolset: Optional[str] = None) -> str:
        return self._registry.build_tool_api_description(toolset=toolset)

    def register_tool(self, func: Callable, *, toolsets: tuple[str, ...] = ()) -> None:
        self._registry.register(func, toolsets=toolsets)

    # -- Abort --

    def abort(self) -> None:
        self._abort_signal.set()

    # -- Verification --

    def configure_verification(self, config: Any = None) -> None:
        from super_browser.verification import VerifierConfig, VisualVerifier
        from super_browser.verification.types import VerifierConfig as VC
        vconfig = config or VC()
        verifier = VisualVerifier(
            cdp=self._page.cdp,
            snapshot_provider=self._controller._snapshot_provider,
            config=vconfig,
        )
        self._controller.enable_verification(verifier)

    def _configure_verification(self) -> None:
        pass

    def _configure_vision(self) -> None:
        if not self._config.enable_vision:
            return
        from super_browser.vision import VisionController, VisionCache, VisionProviderFactory
        from pathlib import Path
        factory = VisionProviderFactory.from_env()
        cache_dir = Path(self._config.vision_cache_dir) if self._config.vision_cache_dir else None
        cache = VisionCache(cache_dir=cache_dir)
        self._vision_controller = VisionController(factory=factory, cache=cache)
        self._controller._vision_controller = self._vision_controller

    def _configure_stealth(self) -> None:
        if not self._config.enable_stealth:
            return
        from super_browser.stealth import StealthManager, StealthConfig
        stealth_config = StealthConfig()
        self._stealth_manager = StealthManager(stealth_config, cdp=self._page.cdp)
        self._loop_stealth = self._stealth_manager

    def _configure_skills(self) -> None:
        if not self._config.enable_skills:
            return
        from pathlib import Path
        from super_browser.skills import SkillRegistry
        skills_dir = Path(self._config.skills_dir) if self._config.skills_dir else None
        self._skill_registry = SkillRegistry(skills_dir=skills_dir)
        if self._page and hasattr(self._page, "cdp"):
            self._skill_registry.set_cdp(self._page.cdp)

    async def learn_from_trajectory(
        self, domain: str, task_description: str, actions_taken: list[str],
        selectors_used: dict[str, str], *, preferred_tier: Optional[dict[str, str]] = None,
    ) -> Any:
        if not self._skill_registry:
            return None
        return await self._skill_registry.learn_from_trajectory(
            domain, task_description, actions_taken, selectors_used,
            preferred_tier=preferred_tier,
        )

    @property
    def is_running(self) -> bool:
        return self._running


class ConfigurationError(Exception):
    """Raised when SuperBrowser is used without required configuration."""
