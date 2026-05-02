# UI-TARS (Model Core)

> ByteDance Seed team's inference SDK and deployment companion for UI-TARS VLM — action parser (526 lines), system prompts for desktop/mobile/grounding, coordinate normalization between Qwen2-VL and Qwen2.5-VL, and pyautogui code generation. The actual model is a Qwen2.5-VL fine-tune on HuggingFace.
> Source ID: SRC-UI-TARS
> Language: Python (622 LOC source), Markdown (907 LOC docs), JSON (data/examples)
> Scale: 28 files, ~1,667 total LOC — small focused repository
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Action Parser & Coordinate Engine | Processing & Logic | `ui_tars/action_parser.py` (526 lines) | 4 | 3 | 4 | 3 | 3.46 | 2 | Primary #6 |
| 2 | System Prompt Templates | Integration & Extension | `ui_tars/prompt.py` (60 lines) | 4 | 3 | 4 | 2 | 3.13 | 2 | Partial #6 |
| 3 | Image Resizing & Coordinate Processing | Perception & Input | `action_parser.py:7-143` | 4 | 3 | 4 | 3 | 3.46 | 2 | Primary #6 |
| 4 | PyAutoGUI Code Generation | Runtime & Execution | `action_parser.py:279-499` | 4 | 2 | 3 | 3 | 2.91 | 3 | Partial #2 |
| 5 | Training Data Format | Data & Storage | `data/training_example.json` (72 lines) | 3 | 3 | 4 | 2 | 2.91 | 3 | No mapping |
| 6 | Deployment Configuration | Integration & Extension | `README_deploy.md` (118), `README_v1.md` (484) | 5 | 1 | 4 | 3 | 2.78 | 3 | No mapping |

Tier 1 count: 0 | Tier 2 count: 3 | Tier 3 count: 3

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ◐ Partial | Shallow | Training data multi-turn format | Gap — action history only in conversation context |
| 2. Reasoning | ◐ Partial | Shallow | `prompt.py` Thought/Action format | Gap — VLM-native, no scaffolding |
| 3. Multi-Agent Coordination | ○ None | — | — | N/A |
| 4. Perception | ◐ Partial | Medium | `smart_resize()` image pipeline | Gap — image processing only, no capture |
| 5. Goal Management | ○ None | — | — | N/A |
| 6. Autonomy | ◐ Partial | Shallow | `wait()`, `finished()` actions | Gap — minimal autonomy control |
| 7. Knowledge Representation | ○ None | — | — | N/A |
| 8. Self-Improvement | ○ None | — | — | N/A |
| 9. Metacognition | ◐ Partial | Shallow | `Reflection:` output format | Gap — reflection in output format only |
| 10. World Modeling | ○ None | — | — | N/A |
| 11. Plugin & Extension | ○ None | — | — | N/A |
| 12. Runtime & Execution | ◐ Partial | Medium | PyAutoGUI code generation | Gap — desktop execution only |
| 13. Provider & Model Management | ◐ Partial | Medium | OpenAI-compatible API deployment docs | Comparable — HuggingFace TGI + vLLM |
| 14. Value Alignment | ○ None | — | — | N/A |

## What to Adopt

### 1. smart_resize Image Pipeline with Factor Divisibility

- **Pattern**: Resize screenshot dimensions to be divisible by 28 (vision transformer patch factor) while preserving aspect ratio, staying within pixel bounds (78,400–12,845,056). Beta-scaling shrinks or expands to fit, then rounds to nearest factor multiple.
- **Subsystem**: #3 (Image Resizing)
- **Intrinsic score**: 3.46
- **Source file**: `ui_tars/action_parser.py:115-143`
- **Evidence**: Verified in code
- **What it does**: `smart_resize(height, width, factor=28, min_pixels=78400, max_pixels=12845056)` ensures the image dimensions work with Qwen2.5-VL's vision encoder. If the aspect ratio exceeds `MAX_RATIO`, it raises an error. If pixels exceed `max_pixels`, it scales down by `beta = sqrt(pixels / max_pixels)` and floors to factor. If below `min_pixels`, it scales up.
- **Integration target**: Gap #6 (Vision-Based Element Location) — any VLM-based vision tier needs to resize screenshots to the model's expected input dimensions. This algorithm handles the math correctly.
- **Overlap**: Agent-S does simple coordinate resizing via division. UI-TARS handles factor-divisibility and pixel bounds. More complete.
- **Quality**: Production-ready
- **Effort**: Low — ~30 lines of Python, directly portable

### 2. Dual Coordinate System (Absolute vs Relative)

- **Pattern**: Qwen2.5-VL (UI-TARS-1.5) outputs absolute pixel coordinates in resized image space. Qwen2-VL (UI-TARS-1.0) outputs relative coordinates normalized to [0, 1000]. The parser handles both by dividing by the appropriate dimension (resized width/height for absolute, factor=1000 for relative).
- **Subsystem**: #1 (Action Parser)
- **Intrinsic score**: 3.46
- **Source file**: `ui_tars/action_parser.py:164-266`
- **Evidence**: Verified in code
- **What it does**: After extracting numbers from the model output (e.g., `<point>197 525</point>` or `start_box='(100,200)'`), coordinates are normalized: for `qwen25vl`, divide by `smart_resize_height/width`; for `qwen2vl`, divide by `factor=1000`. A 2-coordinate point is expanded to a 4-coordinate box `[x, y, x, y]`. The center of the box becomes the click point.
- **Integration target**: Gap #6 (Vision-Based Element Location) — Super Browser's VisionController needs to handle different VLM coordinate systems. This dual-system approach covers the two most common patterns.
- **Overlap**: UI-TARS-desktop handles 4+ coordinate formats with a more robust parser. This Python SDK handles 2 formats with simpler logic. The desktop version is more complete; this one is more portable.
- **Quality**: Production-ready
- **Effort**: Low — directly portable Python code

### 3. System Prompts for Desktop, Mobile, and Grounding

- **Pattern**: Three prompt templates: `COMPUTER_USE_DOUBAO` (desktop: click, drag, hotkey, type, scroll, wait, finished), `MOBILE_USE_DOUBAO` (mobile: click, long_press, type, scroll, open_app, drag, press_home, press_back, finished), `GROUNDING_DOUBAO` (grounding-only: just `click(point=...)` with no Thought). All use `{language}` and `{instruction}` placeholders.
- **Subsystem**: #2 (System Prompts)
- **Intrinsic score**: 3.13
- **Source file**: `ui_tars/prompt.py` (60 lines)
- **Evidence**: Verified in code
- **What it does**: The desktop prompt defines a 9-action space with `Thought: ... Action: ...` output format. The mobile prompt adapts for touch interactions (long_press, open_app, press_home/back). The grounding prompt strips the Thought section for single-step coordinate prediction.
- **Integration target**: Gap #6 (Vision-Based Element Location) — the action space definition and output format specification for VLM-based interaction. The grounding-only prompt is useful for Super Browser's Tier 3 when only coordinate prediction is needed.
- **Overlap**: Agent-S uses a different action space with `@agent_action` decorator. UI-TARS's prompt approach is simpler but VLM-specific.
- **Quality**: Production-ready (used in OSWorld/AndroidWorld benchmarks)
- **Effort**: Low — 60 lines of template strings

## Unguided Findings

### Training Data Format with loss_mask (composite: 2.91)

- **What it does**: Multi-turn conversation format where intermediate actions have `loss_mask: 0` and only the final action (after seeing all context images) has `loss_mask: 1`. This means the model is trained to predict only the next action given full history context.
- **Why it matters**: If Super Browser ever fine-tunes its own grounding model, this training format is directly applicable. The `loss_mask` pattern for selective training on action tokens is a practical contribution.
- **Key files**: `data/training_example.json`
- **Adoption feasibility**: Medium — only relevant if fine-tuning a model

## Notable Code

smart_resize with factor divisibility:

```python
# ui_tars/action_parser.py:115-143
def smart_resize(height, width, factor=28, min_pixels=78400, max_pixels=12845056):
    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = floor_by_factor(height / beta, factor)
        w_bar = floor_by_factor(width / beta, factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
    return h_bar, w_bar
```

Dual coordinate system parsing:

```python
# ui_tars/action_parser.py:164-266 (pattern)
if model_type == "qwen25vl":
    # Absolute pixels in resized image → normalize by resized dimensions
    float_numbers = [float(num / smart_resize_height) if (i+1) % 2 == 0
                     else float(num / smart_resize_width) for i, num in enumerate(numbers)]
else:
    # Relative [0, 1000] → normalize by factor
    float_numbers = [float(num) / factor for num in numbers]
```

Desktop system prompt action space:

```python
# ui_tars/prompt.py
COMPUTER_USE_DOUBAO = """...
## Action Space
click(point='<point>x1 y1</point>')
left_double(point='<point>x1 y1</point>')
right_single(point='<point>x1 y1</point>')
drag(start_point='<point>x1 y1</point>', end_point='<point>x2 y2</point>')
hotkey(key='ctrl c')
type(content='xxx')
scroll(point='<point>x1 y1</point>', direction='down or up')
wait()
finished(content='xxx')
..."""
```

## Thin Project Disposition

**Applicable — focused inference SDK.** UI-TARS has 0 Tier 1 and 3 Tier 2 subsystems. It is a thin wrapper around the model: action parsing + prompts + deployment docs. The real value is the model itself (a Qwen2.5-VL fine-tune hosted on HuggingFace), not this codebase.

**However**, the Python action parser is directly portable to Super Browser's VisionController and is more convenient than porting the TypeScript parser from UI-TARS-desktop. The `smart_resize` algorithm and dual coordinate system are self-contained and reusable.

**Recommendation**: Adopt the `smart_resize` function and coordinate normalization logic directly. For the full action parsing chain (6-format fallback), use UI-TARS-desktop's TypeScript implementation as the reference and port to Python.

**Unique contribution**: The canonical Python implementation of UI-TARS coordinate parsing with `smart_resize` factor-divisibility. The training data format with `loss_mask` is a reference for future fine-tuning. For Super Browser, this repo provides the thin Python layer that bridges VLM output to executable browser actions in Gap #6.
