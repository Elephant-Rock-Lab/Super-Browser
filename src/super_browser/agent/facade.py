"""SuperBrowser facade — primary entry point for all browser automation."""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING, Any, Optional

from super_browser.agent.config import SuperBrowserConfig
from super_browser.agent.delegator import SubagentDelegator
from super_browser.agent.loop import AgentLoop
from super_browser.agent.registry import ToolRegistry
from super_browser.agent.types import DelegationResult
from super_browser.browser.config import SessionConfig
from super_browser.browser.engine import _detect_backend
from super_browser.browser.session import BrowserSession
from super_browser.browser.tabs import TabManager, TabSnapshot
from super_browser.config import Config
from super_browser.interaction.controller import MultimodalController
from super_browser.results import (
    ActionError,
    ActionMethod,
    ActionResult,
    CompletionReason,
    DelegatedResult,
    DownloadResult,
    ErrorCategory,
    ExtractResult,
    NavigateResult,
    NetworkInterceptResult,
    ShadowQueryResult,
    UploadResult,
    action_result,
    timed_action_result,
)
from super_browser.security.types import SecurityConfig
from super_browser.stealth.types import StealthConfig

if TYPE_CHECKING:
    from super_browser.agent.llm.protocol import LLMClient
    from super_browser.memory.store import MemoryStore

logger = logging.getLogger(__name__)


class SuperBrowser:

    _legacy_core: Optional[SuperBrowserConfig]  # set in __init__, None for Config users

    def __init__(
        self,
        config: Optional[Config | SuperBrowserConfig] = None,
        *,
        tool_registry: Optional[ToolRegistry] = None,
        llm_client: Optional[LLMClient] = None,
    ) -> None:
        if config is None:
            self._config = Config()
            self._legacy_core = None
        elif isinstance(config, SuperBrowserConfig):
            self._config = Config.from_legacy(config)
            self._legacy_core = config
        else:
            self._config = config
            self._legacy_core = None
        self._registry = tool_registry or ToolRegistry()
        self._llm_client = llm_client
        self._session: Optional[BrowserSession] = None
        self._engine: Any = None
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
        self._tab_manager: Optional[TabManager] = None
        self._frame_stack: list[Any] = []  # stack of Frame objects
        self._network_interceptors: list[Any] = []
        self._recorder: Any = None  # Optional[SessionRecorder]
        self._event_bus: Any = None  # Optional[EventBus]
        self._memory_store: Optional[MemoryStore] = None  # Set via enable_memory()

    # -- Lifecycle --

    async def start(self) -> None:
        cfg = self._config
        # -- Determine backend & session config from composition root --
        backend_name = _detect_backend(cfg)
        session_config = cfg.browser if isinstance(cfg, Config) else SessionConfig(headless=True)
        if backend_name == "patchright":
            from super_browser.browser.backends.patchright_backend import PatchrightEngine
            self._engine = PatchrightEngine(session_config)
            await self._engine.start()
            self._session = self._engine.session
            self._page = await self._engine.new_page()
        else:
            self._session = BrowserSession(session_config)
            await self._session.start()
            self._page = await self._session.new_page()
        self._controller = MultimodalController(self._page, self._page.engine_page.cdp)
        self._running = True
        self._configure_verification()
        self._configure_vision()
        self._configure_stealth()
        self._configure_skills()
        # -- Recovery (legacy bridge) --
        if self._legacy_core and self._legacy_core.enable_recovery:
            from super_browser.recovery import RecoveryCoordinator
            self._coordinator = RecoveryCoordinator(
                session=self._session, controller=self._controller,
            )
            await self._coordinator.start()
        # -- Budget (legacy bridge) --
        if self._legacy_core and self._legacy_core.enable_budget:
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
        # -- Tracing --
        trace_on = self._legacy_core.trace_enabled if self._legacy_core else cfg.tracing.enabled
        if trace_on:
            from super_browser.tracing import FlowLogger
            from super_browser.tracing.sinks import ConsoleSink
            sinks = [ConsoleSink()]
            trace_dir = self._legacy_core.trace_output_dir if self._legacy_core else ""
            if trace_dir:
                from pathlib import Path

                from super_browser.tracing.sinks import FileSink
                path = Path(trace_dir) / "trace.jsonl"
                sinks.append(FileSink(path))
            self._flow_logger = FlowLogger(sinks=sinks)
            await self._flow_logger.start()
        # -- Security (from composition root) --
        sec_on = self._legacy_core.enable_security if self._legacy_core else False
        if sec_on:
            from super_browser.security import SecurityManager
            sec_config = cfg.security if isinstance(cfg, Config) else SecurityConfig()
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
                skills_data = {"skills": [{"id": s.skill_id, "name": s.name} for s in discovered]}  # noqa: F841
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
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started. Call await sb.start() first."))
        return await self._controller.click(target, description=description)

    async def fill(self, target: str, value: str, *, clear_first: bool = True, description: Optional[str] = None) -> ActionResult:
        if not self._controller:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started. Call await sb.start() first."))
        return await self._controller.fill(target, value, clear_first=clear_first, description=description)

    async def act(self, instruction: str, *, max_steps: int = 50) -> ActionResult:
        if not self._controller:
            return action_result(ok=False)

        if self._llm_client is None:
            raise ConfigurationError(
                "No LLM client configured. Pass llm_client= to SuperBrowser()."
            )

        if not self._controller:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started. Call await sb.start() first."))

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
            debug_config=getattr(self._config, 'debug_config', None),
            retry_budget=getattr(self._config, 'retry_budget', None),
        )
        # Wire memory into the loop if enabled
        if self._memory_store is not None and self._page:
            try:
                current_url = self._page.url
            except Exception:
                current_url = ""
            loop.set_memory_store(self._memory_store, current_url=current_url)
        result = await loop.run(instruction)
        return action_result(
            ok=result.completion_reason == "success",
            data=DelegatedResult(
                instruction=instruction,
                completion_reason=CompletionReason.SUCCESS if result.completion_reason == "success" else CompletionReason.ERROR,
                summary=f"Completed in {result.total_steps} steps",
                steps_executed=result.total_steps,
                budget_remaining=self._budget_client.budget_remaining if self._budget_client else 0.0,
                execution_history=[{"step": s.step_number, "action": s.action_name} for s in result.steps],
            ),
        )

    async def extract(self, query: str, *, selector: Optional[str] = None, schema: Optional[dict] = None) -> ActionResult:
        """Extract content from the current page.

        :param query: Description of what to extract.
        :param selector: Optional CSS selector for targeted extraction.
        :param schema: Optional JSON schema to validate/structure the output.
        :returns: ActionResult with data=ExtractResult.
        """
        import json as _json
        start = time.monotonic()
        if not self._controller:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started. Call await sb.start() first."))

        if selector:
            # Use CDP Runtime.evaluate with expression argument to avoid injection
            # We escape the selector for safe embedding in a JS string literal
            safe_selector = selector.replace('\\', '\\\\').replace("'", "\\'").replace('\n', '\\n').replace('\r', '\\r')
            result = await self._controller._cdp.evaluate(
                f"(function() {{ var el = document.querySelector('{safe_selector}');"
                f" return el ? el.textContent : null; }})()"
            )
            if result.ok and 'exceptionDetails' not in result.data:
                extracted = result.data.get("result", {}).get("value")
            else:
                extracted = None
        else:
            snap = await self._controller.capture_ax_snapshot()
            extracted = snap.to_compact_str()

        # Schema validation
        if schema and extracted is not None:
            try:
                import jsonschema
                # If extracted is a string, try to parse as JSON
                if isinstance(extracted, str):
                    try:
                        parsed = _json.loads(extracted)
                    except (_json.JSONDecodeError, ValueError):
                        parsed = {"text": extracted}
                else:
                    parsed = extracted
                jsonschema.validate(parsed, schema)
            except ImportError:
                # jsonschema not installed — skip validation
                pass
            except Exception as e:
                return timed_action_result(
                    ok=False, start_ns=start,
                    error=ActionError(ErrorCategory.SELECTOR_NOT_FOUND, f"Schema validation failed: {e}"),
                )

        return timed_action_result(
            ok=True,
            start_ns=start,
            data=ExtractResult(selector=selector or query, extracted=extracted, element_count=0),
            method=ActionMethod.SELECTOR,
        )

    async def observe(self) -> ActionResult:
        start = time.monotonic()
        if not self._controller:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started. Call await sb.start() first."))

        url = self._page.url
        title = await self._page.title()
        snap = await self._controller.capture_ax_snapshot()
        interactive_count = sum(1 for n in snap.nodes.values() if n.is_interactive)

        return timed_action_result(
            ok=True,
            start_ns=start,
            data={"url": url, "title": title, "interactive_elements": interactive_count, "total_elements": len(snap.nodes)},
        )

    # -- Tab helper (CHK-07) --

    async def _attach_page(self, page_obj: Any) -> None:
        """Wire a raw Playwright Page into the facade's _page and _controller.

        Shared by :meth:`open_tab` and :meth:`switch_tab`.
        """
        ctx = self._engine.context
        if ctx is None:
            raise RuntimeError("Browser context not available — engine not started?")
        from super_browser.browser.page import PageHandle
        cdp_session = await ctx.new_cdp_session(page_obj)
        from super_browser.browser.cdp import CDPBridge
        from super_browser.browser.config import SessionConfig as _SC
        cdp = CDPBridge(cdp_session, _SC())
        self._page = PageHandle(page_obj, cdp)
        self._controller = MultimodalController(self._page, self._page.engine_page.cdp)

    # -- Multi-Tab --

    async def open_tab(self, url: Optional[str] = None) -> ActionResult:
        """Open a new browser tab, optionally navigating to a URL.

        :param url: Optional URL to navigate to.
        :returns: ActionResult with data=TabHandle.
        """
        start = time.monotonic()
        if not self._session:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started"))
        ctx = self._engine.context
        if ctx is None:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser context not available"))
        if self._tab_manager is None:
            self._tab_manager = TabManager(ctx)
        try:
            tab = await self._tab_manager.open_tab(url)
            # Update page reference and controller to new tab
            page_obj = self._tab_manager.get_page(tab.tab_id)
            await self._attach_page(page_obj)
            return timed_action_result(ok=True, start_ns=start, data=tab)
        except Exception as e:
            return timed_action_result(ok=False, start_ns=start, error=ActionError(ErrorCategory.NAVIGATION, str(e)))

    async def switch_tab(self, tab_id: int) -> ActionResult:
        """Switch to a different tab by ID.

        :param tab_id: The tab ID from open_tab().
        :returns: ActionResult with data=TabHandle.
        """
        start = time.monotonic()
        if not self._tab_manager:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "No tabs open"))
        try:
            tab = await self._tab_manager.switch_tab(tab_id)
            page_obj = self._tab_manager.get_page(tab_id)
            await self._attach_page(page_obj)
            return timed_action_result(ok=True, start_ns=start, data=tab)
        except KeyError as e:
            return timed_action_result(ok=False, start_ns=start, error=ActionError(ErrorCategory.SELECTOR_NOT_FOUND, str(e)))

    async def close_tab(self, tab_id: int) -> ActionResult:
        """Close a tab by ID.

        :param tab_id: The tab ID to close.
        """
        start = time.monotonic()
        if not self._tab_manager:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "No tabs open"))
        try:
            await self._tab_manager.close_tab(tab_id)
            return timed_action_result(ok=True, start_ns=start, data={"closed_tab": tab_id})
        except KeyError as e:
            return timed_action_result(ok=False, start_ns=start, error=ActionError(ErrorCategory.SELECTOR_NOT_FOUND, str(e)))

    async def list_tabs(self) -> ActionResult:
        """List all open tabs."""
        start = time.monotonic()
        if not self._tab_manager:
            return timed_action_result(ok=True, start_ns=start, data=TabSnapshot())
        snap = await self._tab_manager.list_tabs()
        return timed_action_result(ok=True, start_ns=start, data=snap)

    # -- File I/O --

    async def upload_file(self, selector: str, file_path: str) -> ActionResult:
        """Upload a file to an <input type='file'> element.

        :param selector: CSS selector for the file input.
        :param file_path: Absolute or relative path to the file.
        :returns: ActionResult with data=UploadResult.
        """
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started"))
        try:
            await self._page.engine_page.set_input_files(selector, file_path)
            import os
            fname = os.path.basename(file_path)
            return timed_action_result(
                ok=True, start_ns=start,
                data=UploadResult(selector=selector, file_path=file_path, file_name=fname),
            )
        except Exception as e:
            return timed_action_result(
                ok=False, start_ns=start,
                error=ActionError(ErrorCategory.SELECTOR_NOT_FOUND, f"Upload failed: {e}"),
            )

    async def download(self, url_or_selector: str, *, save_path: Optional[str] = None) -> ActionResult:
        """Download a file by clicking a link or navigating to a URL.

        :param url_or_selector: URL to download from, or selector for a download link.
        :param save_path: Optional directory to save the file.
        :returns: ActionResult with data=DownloadResult.
        """
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started"))
        try:
            # Start listening for download
            async with self._page.engine_page.expect_download() as download_info:
                if url_or_selector.startswith("http"):
                    await self._page.engine_page.evaluate(
                        "(url) => { const a = document.createElement('a'); a.href = url; a.download = ''; a.click(); }",
                        url_or_selector,
                    )
                else:
                    await self._page.engine_page.click(url_or_selector)
            download = await download_info.value
            suggested = download.suggested_filename
            if save_path:
                import os
                dest = os.path.join(save_path, suggested)
                await download.save_as(dest)
            else:
                dest = await download.path()
            file_size = 0
            import os
            if dest and os.path.exists(dest):
                file_size = os.path.getsize(dest)
            return timed_action_result(
                ok=True, start_ns=start,
                data=DownloadResult(
                    url=url_or_selector,
                    file_path=str(dest) if dest else "",
                    file_size_bytes=file_size,
                    suggested_filename=suggested,
                ),
            )
        except Exception as e:
            return timed_action_result(
                ok=False, start_ns=start,
                error=ActionError(ErrorCategory.NAVIGATION, f"Download failed: {e}"),
            )

    # -- iframe --

    async def enter_frame(self, selector: str) -> ActionResult:
        """Enter an iframe, scoping subsequent interactions to it.

        :param selector: CSS selector for the iframe element.
        :returns: ActionResult indicating success.
        """
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started"))
        try:
            frame = self._page.engine_page.frame_locator(selector)
            self._frame_stack.append(frame)
            return timed_action_result(ok=True, start_ns=start, data={"frame": selector, "depth": len(self._frame_stack)})
        except Exception as e:
            return timed_action_result(ok=False, start_ns=start, error=ActionError(ErrorCategory.SELECTOR_NOT_FOUND, f"Frame not found: {e}"))

    async def exit_frame(self) -> ActionResult:
        """Exit the current iframe, returning to the parent frame."""
        start = time.monotonic()
        if self._frame_stack:
            self._frame_stack.pop()
            return timed_action_result(ok=True, start_ns=start, data={"depth": len(self._frame_stack)})
        return timed_action_result(ok=True, start_ns=start, data={"depth": 0})

    def _current_frame(self) -> Any:
        """Get the current frame (top of stack) or the raw page."""
        if self._frame_stack:
            return self._frame_stack[-1]
        return self._page.engine_page.raw_page if self._page else None
        # NOTE: Returns underlying Playwright Page for backward compat.

    # -- Shadow DOM --

    async def query_shadow(self, host_selector: str, inner_selector: str) -> ActionResult:
        """Query an element inside a Shadow DOM.

        :param host_selector: CSS selector for the custom element (shadow host).
        :param inner_selector: CSS selector inside the shadow root.
        :returns: ActionResult with data=ShadowQueryResult.
        """
        start = time.monotonic()
        if not self._controller:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started"))
        try:
            import json as _json
            host_json = _json.dumps(host_selector)
            inner_json = _json.dumps(inner_selector)
            expr = (
                '(function() {'
                '  var host = document.querySelector(JSON.parse(' + host_json + '));'
                '  if (!host || !host.shadowRoot) return JSON.stringify({found: false});'
                '  var el = host.shadowRoot.querySelector(JSON.parse(' + inner_json + '));'
                '  if (!el) return JSON.stringify({found: false});'
                '  var rect = el.getBoundingClientRect();'
                '  return JSON.stringify({'
                '    found: true,'
                '    text: el.textContent || "",'
                '    bounds: {x: rect.x, y: rect.y, w: rect.width, h: rect.height}'
                '  });'
                '})()'
            )
            result = await self._controller._cdp.evaluate(expr)
            if result.ok and result.data:
                val = result.data.get("result", {}).get("value")
                if val:
                    import json
                    parsed = json.loads(val)
                    return timed_action_result(
                        ok=True, start_ns=start,
                        data=ShadowQueryResult(
                            host_selector=host_selector,
                            inner_selector=inner_selector,
                            text=parsed.get("text"),
                            bounds=parsed.get("bounds"),
                            found=parsed.get("found", False),
                        ),
                    )
            return timed_action_result(
                ok=True, start_ns=start,
                data=ShadowQueryResult(host_selector=host_selector, inner_selector=inner_selector, found=False),
            )
        except Exception as e:
            return timed_action_result(
                ok=False, start_ns=start,
                error=ActionError(ErrorCategory.SELECTOR_NOT_FOUND, f"Shadow query failed: {e}"),
            )

    # -- Network Interception --

    async def intercept_requests(self, pattern: str = "*", *, action: str = "log") -> ActionResult:
        """Enable network request interception.

        :param pattern: URL glob pattern to match (e.g. "**/api/**").
        :param action: "log", "block", or "mock".
        :returns: ActionResult with data=NetworkInterceptResult.
        """
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started"))
        try:
            intercepted = []

            async def handle_route(route: Any) -> None:
                req = route.request
                intercepted.append({"url": req.url, "method": req.method})
                if action == "block":
                    await route.abort()
                else:
                    await route.continue_()

            await self._page.engine_page.route(pattern, handle_route)
            self._network_interceptors.append({"pattern": pattern, "action": action, "requests": intercepted})

            return timed_action_result(
                ok=True, start_ns=start,
                data=NetworkInterceptResult(pattern=pattern, action=action),
            )
        except Exception as e:
            return timed_action_result(
                ok=False, start_ns=start,
                error=ActionError(ErrorCategory.SECURITY, f"Interception failed: {e}"),
            )

    async def block_requests(self, pattern: str = "*") -> ActionResult:
        """Block all requests matching a URL pattern.

        :param pattern: URL glob pattern to block.
        """
        return await self.intercept_requests(pattern, action="block")

    async def mock_response(self, pattern: str, body: str, *, content_type: str = "application/json", status: int = 200) -> ActionResult:
        """Mock a network response for matching requests.

        :param pattern: URL glob pattern to match.
        :param body: Response body to return.
        :param content_type: Content-Type header.
        :param status: HTTP status code.
        """
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started"))
        try:
            async def handle_mock(route: Any) -> None:
                await route.fulfill(
                    status=status,
                    headers={"Content-Type": content_type},
                    body=body,
                )

            await self._page.engine_page.route(pattern, handle_mock)
            self._network_interceptors.append({"pattern": pattern, "action": "mock", "body": body})

            return timed_action_result(
                ok=True, start_ns=start,
                data=NetworkInterceptResult(pattern=pattern, action="mock"),
            )
        except Exception as e:
            return timed_action_result(
                ok=False, start_ns=start,
                error=ActionError(ErrorCategory.SECURITY, f"Mock failed: {e}"),
            )

    async def clear_interceptions(self) -> ActionResult:
        """Remove all network request interceptions."""
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started"))
        try:
            await self._page.engine_page.unroute_all()
            self._network_interceptors.clear()
            return timed_action_result(ok=True, start_ns=start, data={"cleared": True})
        except Exception as e:
            return timed_action_result(ok=False, start_ns=start, error=ActionError(ErrorCategory.SECURITY, str(e)))

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
        from super_browser.verification import VisualVerifier
        from super_browser.verification.types import VerifierConfig as VC
        vconfig = config or VC()
        verifier = VisualVerifier(
            cdp=self._page.engine_page.cdp,
            snapshot_provider=self._controller._snapshot_provider,
            config=vconfig,
        )
        self._controller.enable_verification(verifier)

    def _configure_verification(self) -> None:
        pass

    def _configure_vision(self) -> None:
        _lc = getattr(self, "_legacy_core", None)
        vis_on = _lc.enable_vision if _lc else False
        if not vis_on:
            return
        from pathlib import Path

        from super_browser.vision import VisionCache, VisionController, VisionProviderFactory
        factory = VisionProviderFactory.from_env()
        cache_dir_str = _lc.vision_cache_dir if _lc else ""
        cache_dir = Path(cache_dir_str) if cache_dir_str else None
        cache = VisionCache(cache_dir=cache_dir)
        self._vision_controller = VisionController(factory=factory, cache=cache)
        self._controller._vision_controller = self._vision_controller

    def _configure_stealth(self) -> None:
        _lc = getattr(self, "_legacy_core", None)
        _cfg = getattr(self, "_config", None)
        stl_on = _lc.enable_stealth if _lc else getattr(_cfg, "enable_stealth", False)
        if not stl_on:
            return
        from super_browser.stealth import StealthManager
        stealth_config = self._config.stealth if isinstance(self._config, Config) else StealthConfig()
        stealth_bridge = getattr(self._page.engine_page, "stealth_bridge", None)
        self._stealth_manager = StealthManager(
            stealth_config,
            stealth_bridge=stealth_bridge,
            cdp=self._page.engine_page.cdp if stealth_bridge is None else None,
            page=self._page.engine_page,
        )
        self._loop_stealth = self._stealth_manager

    def _configure_skills(self) -> None:
        _lc = getattr(self, "_legacy_core", None)
        sk_on = _lc.enable_skills if _lc else False
        if not sk_on:
            return
        from pathlib import Path

        from super_browser.skills import SkillRegistry
        skills_dir_str = _lc.skills_dir if _lc else ""
        skills_dir = Path(skills_dir_str) if skills_dir_str else None
        self._skill_registry = SkillRegistry(skills_dir=skills_dir)
        if self._page and hasattr(self._page, "cdp"):
            self._skill_registry.set_cdp(self._page.engine_page.cdp)

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

    # -- Session Persistence --

    async def save_session(self, path: str) -> ActionResult:
        """Save cookies and session state to a JSON file.

        Serializes all browser cookies via StealthBridge along with
        metadata (URL, timestamp, version). Works across all backends.

        :param path: File path to write the session JSON.
        :returns: ActionResult with data containing the session metadata.
        """
        import json
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started."))
        stealth_bridge = getattr(self._page.engine_page, "stealth_bridge", None)
        if stealth_bridge is None:
            return action_result(ok=False, error=ActionError(ErrorCategory.VALIDATION, "No stealth bridge available for cookie access."))
        try:
            cookies = await stealth_bridge.get_all_cookies()
            session_data = {
                "version": "1.0",
                "timestamp": time.time(),
                "url": str(self._page.url) if hasattr(self._page, "url") else "",
                "cookies": cookies,
            }
            from pathlib import Path as _Path
            target = _Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(session_data, indent=2), encoding="utf-8")
            return timed_action_result(
                ok=True,
                start_ns=start,
                data={"path": str(target), "cookie_count": len(cookies)},
                method=ActionMethod.SELECTOR,
            )
        except Exception as exc:
            return timed_action_result(
                ok=False,
                start_ns=start,
                error=ActionError(ErrorCategory.BROWSER_CRASH, f"save_session failed: {exc}"),
            )

    async def load_session(self, path: str) -> ActionResult:
        """Load cookies and session state from a JSON file.

        Reads a session JSON previously saved by :meth:`save_session`,
        validates the version, and restores cookies via StealthBridge.

        :param path: File path to read the session JSON from.
        :returns: ActionResult with data containing restored cookie count.
        """
        import json
        start = time.monotonic()
        if not self._page:
            return action_result(ok=False, error=ActionError(ErrorCategory.BROWSER_CRASH, "Browser not started."))
        stealth_bridge = getattr(self._page.engine_page, "stealth_bridge", None)
        if stealth_bridge is None:
            return action_result(ok=False, error=ActionError(ErrorCategory.VALIDATION, "No stealth bridge available for cookie access."))
        try:
            from pathlib import Path as _Path
            source = _Path(path)
            if not source.exists():
                return action_result(ok=False, error=ActionError(ErrorCategory.VALIDATION, f"Session file not found: {path}"))
            session_data = json.loads(source.read_text(encoding="utf-8"))
            version = session_data.get("version", "")
            if version != "1.0":
                return action_result(ok=False, error=ActionError(ErrorCategory.VALIDATION, f"Unsupported session format version: {version}"))
            cookies = session_data.get("cookies", [])
            if not cookies:
                return timed_action_result(
                    ok=True,
                    start_ns=start,
                    data={"path": str(source), "cookie_count": 0, "message": "No cookies to restore."},
                    method=ActionMethod.SELECTOR,
                )
            await stealth_bridge.set_cookies(cookies)
            return timed_action_result(
                ok=True,
                start_ns=start,
                data={"path": str(source), "cookie_count": len(cookies)},
                method=ActionMethod.SELECTOR,
            )
        except json.JSONDecodeError as exc:
            return timed_action_result(
                ok=False,
                start_ns=start,
                error=ActionError(ErrorCategory.VALIDATION, f"Invalid JSON in session file: {exc}"),
            )
        except Exception as exc:
            return timed_action_result(
                ok=False,
                start_ns=start,
                error=ActionError(ErrorCategory.BROWSER_CRASH, f"load_session failed: {exc}"),
            )

    # -- Recording --

    def enable_recording(self, *, max_screenshots: int = 100) -> None:
        """Enable session recording. Call before or after start()."""
        from super_browser.events.bus import EventBus
        from super_browser.recording.recorder import SessionRecorder

        if self._event_bus is None:
            self._event_bus = EventBus()
        cdp = None
        if self._page and hasattr(self._page, "engine_page"):
            cdp = self._page.engine_page.cdp
        self._recorder = SessionRecorder(
            self._event_bus, cdp, max_screenshots=max_screenshots,
        )

    @property
    def recording(self) -> Any:
        """Access the active SessionRecorder, or None if recording is not enabled."""
        return self._recorder

    @property
    def event_bus(self) -> Any:
        """Access the EventBus, or None if not initialized."""
        return self._event_bus

    async def replay(self, path: str, *, delay_ms: float = 100) -> ActionResult:
        """Load a recording from *path* and replay it against this browser.

        :param path: Path to a recording JSON file.
        :param delay_ms: Delay between actions in milliseconds.
        :returns: ActionResult with data=ReplayReport.
        """
        start = time.monotonic()
        try:
            from super_browser.recording.persistence import load as load_recording
            from super_browser.recording.replayer import RecordingReplayer

            recording = load_recording(path)
            replayer = RecordingReplayer(self)
            report = await replayer.replay(recording, delay_ms=delay_ms)
            return timed_action_result(
                ok=True,
                start_ns=start,
                data=report,
            )
        except Exception as exc:
            return timed_action_result(
                ok=False,
                start_ns=start,
                error=ActionError(ErrorCategory.BROWSER_CRASH, f"Replay failed: {exc}"),
            )

    @property
    def is_running(self) -> bool:
        return self._running

    # -- Stealth Backend --

    @property
    def stealth_backend(self) -> str:
        """Name of the active stealth backend ('cloak' or 'patchright')."""
        if self._session is not None:
            return self._session.stealth_backend
        return "patchright"

    @property
    def cloak_config(self) -> Any:
        """The CloakConfig if CloakBrowser is available, else None."""
        if self._session is not None and self._engine is not None:
            return self._engine.cloak_config
        return None

    # -- Memory --

    def enable_memory(
        self,
        *,
        memory_dir: str = "~/.config/super-browser/memory",
        ttl_days: int = 30,
    ) -> None:
        """Enable per-domain memory persistence (opt-in).

        Call before or after :meth:`start`.
        """
        from super_browser.memory.integration import create_memory_store
        self._memory_store = create_memory_store(
            memory_enabled=True,
            memory_dir=memory_dir,
            ttl_days=ttl_days,
        )

    @property
    def memory(self) -> Optional[MemoryStore]:
        """Access the active MemoryStore, or None if memory is not enabled."""
        return self._memory_store


class ConfigurationError(Exception):
    """Raised when SuperBrowser is used without required configuration."""
