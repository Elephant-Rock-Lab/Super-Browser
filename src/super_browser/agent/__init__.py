"""GAP-07: Agent Orchestration & Facade."""

from super_browser.agent.config import SuperBrowserConfig
from super_browser.agent.types import (
    ChildTask,
    DelegationResult,
    DelegationStatus,
    LoopNudge,
    LoopResult,
    PlanItem,
    PlanStatus,
    PluginSlotKey,
    StepEvent,
    StepResult,
)
from super_browser.agent.loop_detector import ActionLoopDetector
from super_browser.agent.registry import ToolDefinition, ToolParameter, ToolRegistry, Toolset
from super_browser.agent.loop import AgentLoop
from super_browser.agent.facade import SuperBrowser
from super_browser.agent.delegator import SubagentDelegator
from super_browser.agent.plugins import PluginRegistry, PluginSlot
from super_browser.agent.llm import LLMClient, create_llm

__all__ = [
    "SuperBrowserConfig",
    "ChildTask", "DelegationResult", "DelegationStatus",
    "LoopNudge", "LoopResult",
    "PlanItem", "PlanStatus", "PluginSlotKey",
    "StepEvent", "StepResult",
    "ActionLoopDetector",
    "ToolDefinition", "ToolParameter", "ToolRegistry", "Toolset",
    "AgentLoop",
    "SuperBrowser",
    "SubagentDelegator",
    "PluginRegistry", "PluginSlot",
    "LLMClient", "create_llm",
]
