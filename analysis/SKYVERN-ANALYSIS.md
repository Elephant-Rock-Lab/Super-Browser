# Skyvern

> Vision-first browser automation platform using LLMs and computer vision
> Source ID: SRC-004
> Language: Python
> Scale: ~500+ files, ~100K+ LOC estimated
> Last Verified: 2026-04-22
> Verification Status: Metadata Refreshed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Vision-First Agent Loop | Processing & Logic | `skyvern/forge/agent.py` | 4 | 4 | 3 | 4 | 3.80 | 1 | Partial #2, Partial #7 |
| 2 | Workflow Engine | Coordination | `skyvern/forge/sdk/workflow/models/block.py` | 4 | 3 | 3 | 5 | 3.75 | 1 | No mapping |
| 3 | Browser Control (webeye) | Perception & Input | `skyvern/webeye/` | 4 | 2 | 3 | 4 | 3.30 | 2 | Partial #1, Partial #8 |
| 4 | Multi-Provider LLM Registry | Integration & Extension | `skyvern/forge/sdk/api/llm/config_registry.py` | 4 | 2 | 4 | 4 | 3.45 | 2 | Partial #9 |
| 5 | Block-Based Workflow Composition | Coordination | `skyvern/forge/sdk/workflow/models/block.py` (7206 lines) | 4 | 3 | 2 | 5 | 3.40 | 2 | No mapping |
| 6 | DOM Scraper with Element Tagging | Perception & Input | `skyvern/webeye/scraper/scraper.py`, `scraped_page.py` | 3 | 2 | 3 | 3 | 2.75 | 2 | Partial #2 |
| 7 | Task Management (v1+v2) | Goal & Planning | `skyvern/services/task_v1_service.py`, `task_v2_service.py` | 4 | 3 | 2 | 4 | 3.25 | 2 | Partial #7 |
| 8 | Failure Classification | Governance & Quality | `skyvern/forge/failure_classifier.py`, `skyvern/services/error_detection_service.py` | 3 | 3 | 3 | 3 | 3.00 | 2 | Partial #4 |
| 9 | Credential Vault | Governance & Quality | `skyvern/forge/sdk/services/` (Bitwarden, Azure, custom) | 4 | 2 | 3 | 4 | 3.25 | 2 | Partial #10 |
| 10 | Prompt Template Engine | Processing & Logic | `skyvern/forge/prompts.py` | 3 | 1 | 2 | 3 | 2.25 | 3 | No mapping |

Tier 1 count: 2 | Tier 2 count: 7 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 2. Reasoning | ◐ Partial | Production | `skyvern/forge/agent.py` | Gap — Skyvern has vision-first reasoning loop |
| 4. Perception | ● Full | Production | `skyvern/webeye/`, `skyvern/forge/agent.py` | Gap — Skyvern has screenshot + DOM perception |
| 5. Goal Management | ◐ Partial | Production | `skyvern/services/task_v2_service.py` | Spec'd — Roadmap has goal decomposition |
| 8. Self-Improvement | ○ None | — | — | Gap |
| 9. Metacognition | ◐ Partial | Production | `skyvern/forge/sdk/api/llm/config_registry.py` (per-role LLM handlers) | Gap — Skyvern has specialized LLM per agent role |
| 11. Plugin & Extension | ◐ Partial | Production | `skyvern/forge/sdk/workflow/models/block.py` (block types as extensibility) | Gap |
| 12. Runtime & Execution | ◐ Partial | Production | `skyvern/webeye/browser_factory.py` (proxy, CDP) | Gap |
| 13. Provider & Model Management | ● Full | Production | `skyvern/forge/sdk/api/llm/` (LiteLLM-based, multi-provider) | Gap — Skyvern has comprehensive provider routing |
| 14. Value Alignment | ◐ Partial | Production | `skyvern/forge/sdk/core/` (security, rate limiting) | Gap |

## What to Adopt

### 1. Vision-First Agent Loop Architecture

- **Pattern**: Scrape page → screenshot → LLM call → parse actions → execute → repeat
- **Subsystem**: #1 (Vision-First Agent Loop)
- **Intrinsic score**: 3.80
- **Source file**: `skyvern/forge/agent.py`
- **Evidence**: Verified in code
- **What it does**: Each agent step captures a full page state (DOM element tree + screenshot), sends both to a vision-capable LLM with the task objective, and receives structured action output. The LLM decides actions by "seeing" the page, not just parsing DOM.
- **Integration target**: `control/multimodal.py` (the three-tier engine's vision fallback)
- **Overlap**: Super Browser's roadmap specifies vision as Tier 3 fallback; Skyvern uses vision as the primary method. Worth adopting the screenshot+prompt pattern for Super Browser's Tier 3.
- **Quality**: Needs adaptation
- **Effort**: Medium

### 2. Specialized LLM Handlers Per Agent Role

- **Pattern**: Separate LLM handlers for select, click, input, extraction, and script generation tasks
- **Subsystem**: #4 (Multi-Provider LLM Registry)
- **Intrinsic score**: 3.45
- **Source file**: `skyvern/forge/sdk/api/llm/api_handler_factory.py`, `skyvern/forge/forge_app.py`
- **Evidence**: Verified in code
- **What it does**: `ForgeApp` configures separate LLM handlers: `SELECT_AGENT_LLM_API_HANDLER`, `SINGLE_CLICK_AGENT_LLM_API_HANDLER`, `EXTRACTION_LLM_API_HANDLER`, etc. This enables using cheaper models for simple tasks and expensive models for complex reasoning — the model cascade pattern Super Browser's roadmap specifies.
- **Integration target**: Provider/model routing layer for Tier 1/2/3 model selection
- **Overlap**: Roadmap specifies GPT-4o Mini → Sonnet → Opus cascade; Skyvern implements per-role routing.
- **Quality**: Production-ready
- **Effort**: Low

### 3. Task v2 LLM-Planned Execution

- **Pattern**: Task decomposition via LLM "thoughts" with mini-goals
- **Subsystem**: #7 (Task Management v1+v2)
- **Intrinsic score**: 3.25
- **Source file**: `skyvern/services/task_v2_service.py`
- **Evidence**: Verified in code
- **What it does**: Task v2 uses an LLM to plan and decompose goals into actionable steps, supporting complex reasoning with a configurable max iterations cap (default 50). This is the "Supervisor" layer from Super Browser's architecture.
- **Integration target**: `super_browser.py` facade — the goal decomposition before action execution
- **Overlap**: Roadmap specifies a Supervisor that decomposes goals; Skyvern implements this.
- **Quality**: Needs adaptation
- **Effort**: Medium

### 4. Failure Classification System

- **Pattern**: LLM-based failure reason classification after action errors
- **Subsystem**: #8 (Failure Classification)
- **Intrinsic score**: 3.00
- **Source file**: `skyvern/forge/failure_classifier.py`, `skyvern/services/error_detection_service.py`
- **Evidence**: Verified in code
- **What it does**: After a task fails, the failure classifier uses an LLM to categorize the failure reason (e.g., navigation error, element not found, CAPTCHA, auth required). This feeds into recovery decisions — a key part of Super Browser's self-healing.
- **Integration target**: `healing/session_recovery.py` — failure classification before recovery strategy selection
- **Overlap**: Roadmap specifies recovery strategies per failure type; Skyvern classifies failures to inform recovery.
- **Quality**: Needs adaptation
- **Effort**: Low

## Unguided Findings

### Workflow Engine (composite: 3.75)

- **What it does**: A block-based workflow composition system with 20+ block types (TaskBlock, ForLoopBlock, ConditionalBlock, CodeBlock, LoginBlock, ExtractionBlock, NavigationBlock, etc.) that chain together to build complex multi-step browser workflows.
- **Why it matters**: While Super Browser's roadmap doesn't specify a workflow engine, the ability to compose actions into reusable workflows is a natural evolution. The block composition pattern (parameter wiring, context management, block execution) is sophisticated and production-tested.
- **Architecture**: Each block type has an `execute()` method. `WorkflowRunContext` manages parameter values and block outputs. `WorkflowContextManager` handles setup and state. Blocks can be nested (ForLoop over TaskBlocks).
- **Key files**: `skyvern/forge/sdk/workflow/models/block.py` (7206 lines), `skyvern/forge/sdk/workflow/context_manager.py`
- **Adoption feasibility**: Medium — the block pattern is sound but the 7200-line file and Pydantic-heavy implementation would need significant adaptation.

### Block-Based Workflow Composition (composite: 3.40)

- **What it does**: The specific block types provide reusable workflow primitives: TaskBlock (browser task), NavigationBlock (goto URL), ExtractionBlock (data extraction), LoginBlock (auth automation), ForLoopBlock (iteration), ConditionalBlock (branching), CodeBlock (arbitrary code), etc.
- **Why it matters**: Super Browser's domain skills (Phase 4) could evolve into block-based compositions. The LoginBlock and ExtractionBlock patterns are directly relevant.
- **Architecture**: Block inheritance hierarchy with shared parameter wiring. Each block declares inputs/outputs via Pydantic models.
- **Key files**: `skyvern/forge/sdk/workflow/models/block.py`
- **Adoption feasibility**: Low directly, but the concept is worth noting for future evolution.

## Notable Code

The workflow block hierarchy demonstrates the composition pattern:

```python
# skyvern/forge/sdk/workflow/models/block.py (simplified)
class TaskBlock(BaseBlock):
    task_type: Literal["task"] = "task"
    url: str | None = None
    navigation_goal: str | None = None
    data_extraction_goal: str | None = None
    # ... extensive configuration fields

class ForLoopBlock(BaseBlock):
    loop_type: Literal["for_loop"] = "for_loop"
    loop_over: BlockParam | list[BlockParam] | None = None
    loop_blocks: list[BlockType] = []
    # ... loop control fields
```

The ForgeAgent step loop:

```python
# skyvern/forge/agent.py (simplified pattern)
class ForgeAgent:
    async def execute_step(self, task: Task, step: Step) -> Action:
        scraped_page = await self.scrape_page(task)
        screenshot = await self.take_screenshot(task)
        actions = await self.llm_handler.get_actions(
            objective=task.navigation_goal,
            scraped_page=scraped_page,
            screenshot=screenshot,
            previous_actions=task.action_history,
        )
        return actions
```

## Thin Project Disposition

Not applicable — Skyvern has 2 Tier 1 and 7 Tier 2 subsystems.
