# Agent-S

> Desktop GUI automation agent achieving 72.6% on OSWorld (first above human performance) via UI-TARS visual grounding, @agent_action decorator pattern, format-validation self-correction, reflection agent, and Behavior Best-of-N trajectory selection
> Source ID: SRC-AGENT-S
> Language: Python (100%), 19,745 LOC across 88 files
> Scale: ~14,200 LOC core (S1: ~4,700 / S2: ~4,100 / S2.5: ~2,300 / S3: ~3,100)
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Visual Grounding (UI-TARS + OCR) | Perception & Input | `s3/agents/grounding.py` (666 lines) | 4 | 5 | 4 | 4 | 4.12 | 1 | Primary #2, #6 |
| 2 | @agent_action Decorator & Action API | Integration & Extension | `s3/agents/grounding.py:25-28`, `s3/memory/procedural_memory.py:78-89` | 4 | 5 | 5 | 3 | 4.12 | 1 | Primary #2, #7 |
| 3 | Format Validation Self-Correction | Governance & Quality | `s3/utils/common_utils.py:59-127`, `s3/utils/formatters.py` (58 lines) | 4 | 4 | 4 | 4 | 4.00 | 1 | Primary #4 |
| 4 | Procedural Memory & Prompt Construction | Data & Storage | `s3/memory/procedural_memory.py` (395 lines) | 4 | 4 | 4 | 4 | 4.00 | 1 | Partial #5 |
| 5 | Behavior Best-of-N (bBoN) | Processing & Logic | `s3/bbon/behavior_narrator.py` (273), `s3/bbon/comparative_judge.py` (149) | 3 | 5 | 3 | 5 | 3.91 | 2 | Partial #3, #7 |
| 6 | Reflection Agent | Processing & Logic | `s3/agents/worker.py:125-178` | 3 | 4 | 3 | 3 | 3.22 | 2 | Partial #4 |
| 7 | Code Execution Agent | Runtime & Execution | `s3/agents/code_agent.py` (333 lines), `s3/utils/local_env.py` (77 lines) | 3 | 4 | 3 | 4 | 3.46 | 2 | Partial #12 |
| 8 | Multi-Provider LLM Engine (8 backends) | Integration & Extension | `s3/core/engine.py` (445 lines), `s3/core/mllm.py` (305 lines) | 4 | 2 | 4 | 3 | 3.13 | 2 | Partial #7 |
| 9 | Hierarchical Planner (DAG) | Processing & Logic | `s1/core/Manager.py` (280), `s2/agents/manager.py` (321) | 3 | 4 | 3 | 4 | 3.46 | 2 | Partial #7 |
| 10 | Knowledge RAG (Narrative + Episodic) | Data & Storage | `s1/core/Knowledge.py` (250), `s2/core/knowledge.py` (420) | 3 | 3 | 3 | 3 | 3.00 | 2 | No mapping |
| 11 | Platform ACI Adapters (Linux/macOS/Win) | Perception & Input | `s1/aci/LinuxOSACI.py` (846), `s1/aci/MacOSACI.py` (572), `s1/aci/WindowsOSACI.py` (532) | 3 | 3 | 3 | 3 | 3.00 | 2 | Partial #2 |
| 12 | Worker Agent Core | Processing & Logic | `s3/agents/worker.py` (355 lines) | 3 | 3 | 3 | 4 | 3.22 | 2 | Partial #7 |
| 13 | LMMAgent Message Handler | Integration & Extension | `s3/core/mllm.py` (305 lines) | 4 | 3 | 3 | 3 | 3.16 | 2 | No mapping |
| 14 | Screenshot Processing Pipeline | Perception & Input | `s3/agents/grounding.py:229-245`, `s3/bbon/behavior_narrator.py` | 4 | 3 | 3 | 3 | 3.16 | 2 | Partial #3 |
| 15 | CLI Inference Loop | Runtime & Execution | `s3/cli_app.py` (398 lines) | 4 | 2 | 3 | 3 | 2.91 | 3 | No mapping |
| 16 | OpenClaw Integration Wrapper | Integration & Extension | `integrations/openclaw/agent_s_wrapper.py` (182 lines) | 3 | 3 | 4 | 2 | 2.91 | 3 | No mapping |

Tier 1 count: 4 | Tier 2 count: 10 | Tier 3 count: 2

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ◐ Partial | Medium | `s3/memory/procedural_memory.py`, `s1/core/Knowledge.py` | Gap — procedural prompts only in S3; S1/S2 have embedding-based RAG |
| 2. Reasoning | ◐ Partial | Medium | `s3/agents/worker.py`, `s3/agents/code_agent.py` | Gap — chain-of-thought in prompts, no explicit reasoning framework |
| 3. Multi-Agent Coordination | ◐ Partial | Medium | `s2/agents/agent_s.py`, `s3/bbon/` pipeline | Gap — Manager-Worker in S2, flat in S3 |
| 4. Perception | ● Full | Deep | `s3/agents/grounding.py` (666), `s1/aci/LinuxOSACI.py` (846) | Better than Super Browser — dual visual+OCR grounding |
| 5. Goal Management | ◐ Partial | Shallow | `s2/agents/manager.py` (321) | Gap — DAG decomposition in S2, no goal tracking in S3 |
| 6. Autonomy | ● Full | Deep | `s3/cli_app.py` (398) | Better — fully autonomous 15-step loop with self-termination |
| 7. Knowledge Representation | ◐ Partial | Medium | `s2/core/knowledge.py` (420) | Gap — embedding-indexed JSON, no structured graph |
| 8. Self-Improvement | ◐ Partial | Medium | `s1/core/AgentS.py`, bBoN pipeline | Gap — offline trajectory selection, no online learning |
| 9. Metacognition | ◐ Partial | Shallow | `s3/agents/worker.py:125-178` | Gap — reflection classifies trajectory state only |
| 10. World Modeling | ○ None | — | — | N/A |
| 11. Plugin & Extension | ◐ Partial | Medium | `s3/core/engine.py` (8 backends), `@agent_action` decorator | Gap — action registration is elegant but not a full plugin system |
| 12. Runtime & Execution | ● Full | Deep | `s3/cli_app.py`, `s3/utils/local_env.py` | Comparable — full screenshot→LLM→action→exec loop |
| 13. Provider & Model Management | ● Full | Deep | `s3/core/engine.py` (445), `s3/core/mllm.py` (305) | Comparable — 8 LLM backends with unified interface |
| 14. Value Alignment | ○ None | — | — | N/A — no safety guardrails |

## What to Adopt

### 1. @agent_action Decorator with Dynamic Prompt Construction

- **Pattern**: A minimal decorator (`func.is_agent_action = True`) marks action methods. Procedural memory construction iterates all class methods via `dir()`/`getattr()`, extracts `inspect.signature()` for exact parameter names/types and `__doc__` for descriptions, then assembles the complete action API into the system prompt dynamically. Zero hand-maintained API documentation.
- **Subsystem**: #2 (@agent_action Action API)
- **Intrinsic score**: 4.12
- **Source file**: `s3/agents/grounding.py:25-28`, `s3/memory/procedural_memory.py:78-89`
- **Evidence**: Verified in code
- **What it does**: The OSWorldACI class defines 15 action methods (`click`, `type`, `drag_and_drop`, `scroll`, `hotkey`, `wait`, `done`, `fail`, `save_to_knowledge`, `call_code_agent`, etc.), each decorated with `@agent_action`. At initialization, `construct_simple_worker_procedural_memory()` discovers all marked methods, reads their signatures and docstrings, and generates the LLM-facing API description. Actions can be conditionally hidden via `skipped_actions` (e.g., `call_code_agent` hidden when no local env, `set_cell_values` hidden on non-Linux).
- **Integration target**: Gap #2 (Three-Tier Interaction Engine) — the action registration pattern. Gap #7 (Agent Orchestration) — the dynamic tool description pattern. Every browser action (click, type, scroll, navigate) becomes one `@agent_action` method.
- **Overlap**: Hermes tool registry uses AST auto-discovery. Agent-S uses runtime introspection. Complementary approaches — Hermes is more structured (thread-safe, toolsets), Agent-S is more ergonomic (decorator + signature).
- **Quality**: Production-ready
- **Effort**: Low — 20 lines of Python

### 2. Format Validation Self-Correction Loop

- **Pattern**: When the LLM produces malformed output, the system appends the bad response as an assistant message, adds specific error feedback as a user message ("Your previous response was not formatted correctly..."), and retries up to 3 times. Two validation levels: structural (exactly one `agent.xxx()` call) and semantic (actually eval the code against the grounding agent to verify it produces valid output).
- **Subsystem**: #3 (Format Validation)
- **Intrinsic score**: 4.00
- **Source file**: `s3/utils/common_utils.py:59-127`, `s3/utils/formatters.py:10-41`
- **Evidence**: Verified in code
- **What it does**: `call_llm_formatted()` wraps every LLM call with format checkers. `SINGLE_ACTION_FORMATTER` verifies exactly one agent action call exists. `CODE_VALID_FORMATTER` actually evaluates the parsed code against the grounding agent to verify it produces valid pyautogui output. On failure, the original LLM response is appended as assistant, a `FORMATTING_FEEDBACK_PROMPT` with specific errors is appended as user, and the LLM is called again. This achieves self-correction without external intervention.
- **Integration target**: Gap #4 (Self-Healing & Session Recovery) — LLM output validation. This pattern should wrap every agent→LLM→action cycle: validate the LLM's proposed action is syntactically valid and semantically plausible before execution.
- **Overlap**: Hermes has `call_llm_safe` with retry on API errors. Agent-S validates the *output format*, not the API call. browser-use validates xpath existence. Complementary.
- **Quality**: Production-ready
- **Effort**: Low — 70 lines of Python

### 3. Dual Visual Grounding Pipeline (UI-TARS + OCR)

- **Pattern**: Two parallel grounding paths: (1) Visual grounding via UI-TARS 7B model — screenshot + natural language referring expression → pixel coordinates with coordinate resizing from model resolution to screen resolution. (2) OCR text grounding via pytesseract — word-level bounding boxes → LLM-based phrase-to-word matching → bounding box center coordinates.
- **Subsystem**: #1 (Visual Grounding)
- **Intrinsic score**: 4.12
- **Source file**: `s3/agents/grounding.py` (666 lines)
- **Evidence**: Verified in code
- **What it does**: `generate_coords()` sends the full screenshot and a natural language query to UI-TARS, which outputs pixel coordinates. Coordinates are resized via `resize_coordinates()` from the grounding model's input resolution to the actual screen dimensions. The OCR path uses `pytesseract.image_to_data()` for word-level bounding boxes, then an LLM matches a text phrase to a specific word ID, computing coordinates from the OCR element's bounding box. Each action method (e.g., `click(ref_expr: str, obs: dict)`) calls `generate_coords()` internally to resolve the referring expression to coordinates.
- **Integration target**: Gap #6 (Vision-Based Element Location) — the visual grounding approach for the vision tier. Super Browser's Tier 3 (vision) can use the same UI-TARS pattern: screenshot + element description → pixel coordinates. The OCR path handles text-based element finding.
- **Overlap**: Stagehand uses CUA providers (Anthropic, OpenAI) for vision. Agent-S uses a dedicated UI-TARS model (7B, local). Skyvern uses screenshot+DOM→LLM. Agent-S's approach is more lightweight (single dedicated model vs. heavy CUA API).
- **Quality**: Research-grade (SOTA on OSWorld)
- **Effort**: Medium — requires UI-TARS model deployment

### 4. Reflection Agent with Trajectory Monitoring

- **Pattern**: A separate reflection LLM agent maintains a parallel conversation tracking the full trajectory. At each step, it classifies the trajectory into one of three cases: (1) off-track/cycling, (2) on-track, or (3) completed. The reflection output is injected into the worker agent's next message as corrective context.
- **Subsystem**: #6 (Reflection Agent)
- **Intrinsic score**: 3.22
- **Source file**: `s3/agents/worker.py:125-178`
- **Evidence**: Verified in code
- **What it does**: The worker maintains a `reflection_agent` with its own message history. At turn 0, it receives the task description and initial screenshot. At subsequent turns, it receives the worker's last action and the new screenshot. It classifies the trajectory (cycle detection, progress affirmation, or completion) and produces a structured reflection. The reflection is appended to the worker's next generator message: `REFLECTION: You may use this reflection on the previous action and overall trajectory: {reflection}`.
- **Integration target**: Gap #4 (Self-Healing) — trajectory-level monitoring. Complements browser-use's watchdog framework (event-level) with trajectory-level assessment.
- **Overlap**: browser-use has loop detection via SHA-256 action hashing. Agent-S's reflection is more nuanced (3-case classification with natural language reasoning). Hermes has error classification (16 types). These are complementary layers.
- **Quality**: Production-ready
- **Effort**: Low — 55 lines of Python

### 5. Behavior Best-of-N Trajectory Selection

- **Pattern**: Multi-stage offline evaluation pipeline: (1) BehaviorNarrator annotates before/after screenshots with action markers and zoomed crops, generates structured fact captions via VLM. (2) ComparativeJudge presents all N trajectories' initial+final screenshots and fact captions to a VLM, which selects the best trajectory. (3) Task classifier separates constant (same result) from variance (different) tasks — only variance tasks are judged.
- **Subsystem**: #5 (bBoN)
- **Intrinsic score**: 3.91
- **Source file**: `s3/bbon/behavior_narrator.py` (273), `s3/bbon/comparative_judge.py` (149)
- **Evidence**: Verified in code
- **What it does**: The BehaviorNarrator marks the before-screenshot with colored annotations (red circle for clicks, blue for moveTo, green line for drags), extracts a 300×300 zoomed crop at the action location upscaled 4× with denoising, and sends both to an LLM for structured comparison. The ComparativeJudge takes N complete trajectories, presents their fact captions and initial/final screenshots side-by-side, and asks the VLM to select the best. This achieved 72.6% on OSWorld with 3 rollouts.
- **Integration target**: Gap #3 (Visual Verification) — the BehaviorNarrator pattern of annotating before/after screenshots with action markers and zoomed crops is directly applicable to browser visual verification. Gap #7 — the bBoN pipeline is a quality-gating pattern for multi-try execution.
- **Overlap**: Skyvern uses screenshot comparison. Agent-S's approach is more structured (visual annotations + zoomed crops + fact captions). No other reference project implements trajectory-level comparison.
- **Quality**: Research-grade (SOTA)
- **Effort**: High — requires VLM for judging, multi-rollout infrastructure

## Unguided Findings

### Procedural Memory with Dynamic API Construction (composite: 4.00)

- **What it does**: Static class `PROCEDURAL_MEMORY` containing all system prompts. The `construct_simple_worker_procedural_memory()` method dynamically assembles the system prompt by introspecting the grounding agent class: discovers `@agent_action` methods, reads `inspect.signature()` for parameter names/types, reads `__doc__` for descriptions, and builds a formatted function API section. Platform-specific actions are hidden via `skipped_actions`.
- **Why it matters**: This pattern eliminates prompt documentation drift — the LLM always sees an API that exactly matches the available actions. For Super Browser, this would ensure the browser action API in the agent's prompt is always synchronized with the actual implementation.
- **Key files**: `s3/memory/procedural_memory.py` (395 lines)
- **Adoption feasibility**: High — directly portable pattern

### Screenshot Annotation for Visual Verification (composite: 3.60)

- **What it does**: The BehaviorNarrator annotates screenshots before sending to the LLM: draws red circles at click coordinates, blue dots at moveTo coordinates, green lines for drag operations. Extracts 300×300 zoomed crops at action locations, upscaled 4× with PIL denoising. Creates side-by-side before/after comparison images.
- **Why it matters**: For Super Browser's visual verification (Gap #3), the screenshot annotation pattern is valuable for "did the action succeed" verification. Annotating the screenshot with what the agent did (click here, typed there) provides rich context for the verification LLM.
- **Key files**: `s3/bbon/behavior_narrator.py:172-273`
- **Adoption feasibility**: Medium — requires PIL/matplotlib for annotation

### Code Execution Agent with Budget Control (composite: 3.46)

- **What it does**: A separate agent that executes Python/Bash code in a subprocess with a step budget. The worker delegates complex multi-step operations to the code agent. The code agent returns a structured result dict with `task_instruction`, `completion_reason`, `summary`, `execution_history`, `steps_executed`, and `budget` remaining.
- **Why it matters**: For Super Browser, the code agent pattern enables the browser agent to delegate complex data processing (parsing, transformation, file operations) to a code execution sandbox rather than trying to do everything through browser interactions.
- **Key files**: `s3/agents/code_agent.py` (333 lines)
- **Adoption feasibility**: Medium — code execution agent is directly portable

## Notable Code

@agent_action decorator with dynamic prompt construction:

```python
# s3/agents/grounding.py:25-28
def agent_action(func):
    func.is_agent_action = True
    return func

# s3/memory/procedural_memory.py:78-89
for attr_name in dir(agent_class):
    if attr_name in skipped_actions:
        continue
    attr = getattr(agent_class, attr_name)
    if callable(attr) and hasattr(attr, "is_agent_action"):
        signature = inspect.signature(attr)
        procedural_memory += f"""
def {attr_name}{signature}:
'''{attr.__doc__}'''
    """
```

Format validation self-correction loop:

```python
# s3/utils/common_utils.py:59-127 (pattern)
def call_llm_formatted(generator, format_checkers, **kwargs):
    max_retries = 3
    while attempt < max_retries:
        response = call_llm_safe(generator, messages=messages, **kwargs)
        feedback_msgs = []
        for format_checker in format_checkers:
            success, feedback = format_checker(response)
            if not success:
                feedback_msgs.append(feedback)
        if not feedback_msgs:
            break
        messages.append({"role": "assistant", "content": response})
        messages.append({"role": "user", "content": formatting_feedback})
        attempt += 1
```

Visual grounding via UI-TARS:

```python
# s3/agents/grounding.py:229-245
def generate_coords(self, ref_expr: str, obs: Dict) -> List[int]:
    self.grounding_model.reset()
    prompt = f"Query:{ref_expr}\nOutput only the coordinate of one point in your response.\n"
    self.grounding_model.add_message(
        text_content=prompt, image_content=obs["screenshot"], put_text_last=True
    )
    response = call_llm_safe(self.grounding_model)
    numericals = re.findall(r"\d+", response)
    return [int(numericals[0]), int(numericals[1])]
```

Reflection agent trajectory monitoring:

```python
# s3/agents/worker.py:125-178 (pattern)
def _generate_reflection(self, instruction, obs):
    if self.turn_count == 0:
        self.reflection_agent.add_message(
            text_content="The initial screen is provided. No action has been taken yet.",
            image_content=obs["screenshot"])
    else:
        self.reflection_agent.add_message(
            text_content=self.worker_history[-1],
            image_content=obs["screenshot"])
    full_reflection = call_llm_safe(self.reflection_agent)
    # Inject into worker's next message:
    # "REFLECTION: You may use this reflection on the previous action..."
```

## Thin Project Disposition

Not applicable — Agent-S has 4 Tier 1 and 10 Tier 2 subsystems despite being a focused research artifact.

**Unique contribution**: The @agent_action decorator + inspect.signature pattern for dynamically constructing LLM-facing action APIs. The format validation self-correction loop (check-reprompt with semantic validation). Behavior Best-of-N trajectory selection with visual annotation. Agent-S's desktop automation patterns (visual grounding, reflection, format validation) transfer directly to Super Browser's interaction engine (Gap #2) and self-healing (Gap #4). The project proves that vision-based grounding with dedicated models (UI-TARS) achieves SOTA performance — supporting Super Browser's Tier 3 vision approach.
