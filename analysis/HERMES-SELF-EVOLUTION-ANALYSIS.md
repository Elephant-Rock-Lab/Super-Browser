# Hermes Agent Self-Evolution

> DSPy-based evolutionary optimization engine for agent skills, with GEPA trace-reflective mutation and multi-source session mining
> Source ID: SRC-013
> Language: Python
> Scale: ~2,800 lines across 10 source files (4 phases implemented, Phase 5 planned)
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | External Session Import Pipeline (3 sources) | Integration & Extension | `core/external_importers.py` (786 lines) | 5 | 4 | 5 | 4 | 4.50 | 1 | Partial #10, #11 |
| 2 | Optimization Engine & DSPy Integration | Processing & Logic | `skills/skill_module.py` (124 lines), `skills/evolve_skill.py` (324 lines) | 3 | 5 | 4 | 3 | 3.75 | 1 | Partial #5 |
| 3 | Evaluation Dataset Generation | Data & Storage | `core/dataset_builder.py` (202 lines) | 4 | 3 | 4 | 3 | 3.40 | 2 | Partial #5 |
| 4 | Fitness & Multi-Dimensional Scoring | Governance & Quality | `core/fitness.py` (147 lines) | 3 | 3 | 4 | 3 | 3.20 | 2 | Partial #9, #12 |
| 5 | Constraint Validation & Guardrails | Governance & Quality | `core/constraints.py` (175 lines) | 4 | 2 | 4 | 3 | 3.15 | 2 | Partial #10 |
| 6 | Skill Module Abstraction (DSPy) | Knowledge & Representation | `skills/skill_module.py` (124 lines) | 4 | 3 | 5 | 2 | 3.35 | 2 | Partial #5 |
| 7 | Evolution Orchestration Pipeline | Coordination | `skills/evolve_skill.py` (324 lines) | 4 | 3 | 3 | 3 | 3.20 | 2 | Partial #5 |
| 8 | Reporting & Metrics | Data & Storage | `generate_report.py` (505 lines) | 4 | 2 | 3 | 3 | 2.95 | 2 | No mapping |
| 9 | Configuration & Discovery | Processing & Logic | `core/config.py` (73 lines) | 4 | 1 | 4 | 2 | 2.60 | 3 | No mapping |
| 10 | Continuous Improvement Loop (Phase 5) | Autonomy & Scheduling | Planned only (empty `__init__.py`) | 1 | 3 | 2 | 1 | 1.65 | 3 | Partial #4 |

Tier 1 count: 2 | Tier 2 count: 6 | Tier 3 count: 2

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ◐ Partial | Research | `core/dataset_builder.py` (eval datasets) | Gap — eval memory only, no runtime memory |
| 2. Reasoning | ◐ Partial | Research | `core/fitness.py` (LLM judge rubric) | Gap — rubric-based evaluation, not action reasoning |
| 3. Multi-Agent Coordination | ○ None | — | — | N/A |
| 4. Perception | ○ None | — | — | N/A — no browser perception |
| 5. Goal Management | ◐ Partial | Research | `skills/evolve_skill.py` (10-step pipeline) | Gap — optimization goals, not task goals |
| 6. Autonomy | ◐ Partial | Concept | Phase 5 plan (cron-based optimization) | Gap — planned but not implemented |
| 7. Knowledge Representation | ◐ Partial | Production | `skills/skill_module.py` (skills as DSPy modules) | Gap — unique skill-as-parameter pattern |
| 8. Self-Improvement | ● Full | Production | Full pipeline (optimize → evaluate → constrain → deploy) | Better than Super Browser — the only project with automated skill evolution |
| 9. Metacognition | ◐ Partial | Research | `core/fitness.py` (multi-dimensional self-assessment) | Gap — post-hoc evaluation, not real-time |
| 10. World Modeling | ○ None | — | — | N/A |
| 11. Plugin & Extension | ◐ Partial | Production | `core/external_importers.py` (3 session sources) | Gap — import pipeline, not runtime plugin system |
| 12. Runtime & Execution | ◐ Partial | Research | CLI entry via Click | Gap — CLI tool, not runtime |
| 13. Provider & Model Management | ◐ Partial | Research | DSPy LM contexts | Gap — relies on DSPy's provider layer |
| 14. Value Alignment | ◐ Partial | Production | `core/constraints.py` (guardrails), secret detection | Gap — constraint validation for evolved artifacts |

## What to Adopt

### 1. External Session Mining Pipeline

- **Pattern**: Three importers mining real usage data from Claude Code (`~/.claude/history.jsonl`), GitHub Copilot (`~/.copilot/session-state/*/events.jsonl`), and Hermes Agent (`~/.hermes/sessions/*.json`). Two-stage relevance filtering: heuristic pre-filter → LLM scoring. Comprehensive secret detection with 20+ regex patterns.
- **Subsystem**: #1 (External Session Import)
- **Intrinsic score**: 4.50
- **Source file**: `core/external_importers.py` (786 lines)
- **Evidence**: Verified in code
- **What it does**: Three importers mine session history from real agent usage. `RelevanceFilter` uses cheap heuristics first (keyword overlap, length thresholds), then expensive LLM scoring on candidates. `SECRET_PATTERNS` regex catches Anthropic keys, OpenRouter keys, GitHub tokens, passwords, and PEM keys while minimizing false positives (short "sk" prefixes, prose containing "key" or "bearer"). CLI entry via Click for batch import.
- **Integration target**: Gap #10 (Security Envelope) — the secret detection system. Gap #11 (Tracing) — mining usage traces for self-improvement.
- **Overlap**: No other reference project mines real agent session data. browser-harness relies on agent-written skills. browser-use has no session mining.
- **Quality**: Production-ready
- **Effort**: Low — the secret detection regex is directly portable

### 2. Skill-as-Optimizable-Parameter Pattern

- **Pattern**: `SkillModule(dspy.Module)` wraps SKILL.md text as an optimizable DSPy parameter. GEPA optimizer mutates the skill body while preserving YAML frontmatter. Multi-dimensional fitness (correctness 50%, procedure_following 30%, conciseness 20%) with length penalty ramp.
- **Subsystem**: #2 (Optimization Engine)
- **Intrinsic score**: 3.75
- **Source file**: `skills/skill_module.py`, `skills/evolve_skill.py`
- **Evidence**: Verified in code
- **What it does**: A SKILL.md file becomes a DSPy module where the skill text is the parameter GEPA can mutate. The `TaskWithSkill` signature takes `skill_instructions + task_input → output`. GEPA (ICLR 2026 Oral, trace-reflective prompt evolution) runs optimization, extracting evolved parameters. `FitnessScore` provides numeric score AND textual feedback that GEPA uses for reflective mutation. Length penalty ramps from 0 at 90% of max to 0.3 at 100%+. `reassemble_skill()` preserves YAML frontmatter while replacing the body.
- **Integration target**: Gap #5 (Domain Skill Registry) — the skill evolution mechanism. Super Browser's domain skills could evolve via this pattern.
- **Overlap**: No other reference project has automated skill evolution. browser-harness has agent-editable skills but no automated optimization.
- **Quality**: Needs adaptation — depends on DSPy and GEPA
- **Effort**: High — DSPy integration required

### 3. Constraint Validation Guardrails

- **Pattern**: `ConstraintValidator` enforces hard constraints on evolved artifacts: size limits per type (15KB skills, 500-char tool descriptions), growth limits vs baseline (+20% max), non-empty checks, YAML frontmatter integrity, and optional pytest execution gate.
- **Subsystem**: #5 (Constraint Validation)
- **Intrinsic score**: 3.15
- **Source file**: `core/constraints.py` (175 lines)
- **Evidence**: Verified in code
- **What it does**: After skill evolution, `ConstraintValidator.validate_all()` checks: size within limits, growth within +20% of baseline, non-empty body, valid YAML frontmatter (name + description fields), and optionally runs pytest with 300s timeout. `ConstraintResult` provides detailed pass/fail reporting. Prevents regressions from automated evolution.
- **Integration target**: Gap #10 (Security Envelope) — the quality gate for evolved artifacts.
- **Overlap**: browser-use has no constraint validation. browser-harness has no automated evolution to guard against.
- **Quality**: Production-ready
- **Effort**: Low

## Unguided Findings

### GEPA Trace-Reflective Mutation (composite: 3.75)

- **What it does**: Uses GEPA (Gradient-free Evolutionary Prompt Adaptation, ICLR 2026 Oral paper) for skill optimization. GEPA performs trace-reflective mutation — it analyzes execution traces to understand WHY a skill performed poorly, then mutates accordingly. This is more sophisticated than random or gradient-based prompt optimization.
- **Why it matters**: This is the state-of-the-art in automated prompt/skill optimization. For Super Browser's domain skills (Gap #5), this could enable skills that automatically improve based on real usage data.
- **Architecture**: DSPy's `GEPA` optimizer with `max_steps` iterations. Falls back to `MIPROv2` if GEPA unavailable.
- **Key files**: `skills/evolve_skill.py:156-178`
- **Adoption feasibility**: Medium — requires DSPy dependency and eval dataset

### Multi-Source Eval Data Cold-Start Solution (composite: 3.40)

- **What it does**: The three importers (Claude Code, GitHub Copilot, Hermes Agent) solve the eval data cold-start problem — how to get enough training data for skill optimization without manual annotation. Combined with `SyntheticDatasetBuilder` (LLM-generated test cases from skill text), this provides a multi-source data pipeline.
- **Why it matters**: For Super Browser's domain skills, evaluation data is essential for measuring skill quality. The cold-start solution is directly applicable.
- **Architecture**: Three importers → relevance filter → eval dataset → train/val/holdout split.
- **Key files**: `core/external_importers.py`, `core/dataset_builder.py`
- **Adoption feasibility**: Medium — the import patterns are specific to each source

## Notable Code

Secret detection patterns:

```python
# core/external_importers.py:45-70
SECRET_PATTERNS = re.compile(
    r'('
    r'sk-ant-api\S+'           # Anthropic API keys
    r'|sk-or-v1-\S+'          # OpenRouter API keys
    r'|sk-\S{20,}'            # Generic OpenAI-style keys (20+ chars)
    r'|ghp_\S+'               # GitHub personal access tokens
    r'|\bpassword\s*[=:]\s*\S+' # password assignments
    r'|-----BEGIN\s+(RSA\s+)?PRIVATE\sKEY-----'
    r')', re.IGNORECASE,
)
```

Skill-as-optimizable-parameter:

```python
# skills/skill_module.py:84-114
class SkillModule(dspy.Module):
    class TaskWithSkill(dspy.Signature):
        skill_instructions: str = dspy.InputField()
        task_input: str = dspy.InputField()
        output: str = dspy.OutputField()

    def __init__(self, skill_text: str):
        super().__init__()
        self.skill_text = skill_text
        self.predictor = dspy.ChainOfThought(self.TaskWithSkill)

    def forward(self, task_input: str) -> dspy.Prediction:
        result = self.predictor(skill_instructions=self.skill_text, task_input=task_input)
        return dspy.Prediction(output=result.output)
```

Length penalty ramp:

```python
# core/fitness.py:93-96
if ratio > 0.9:
    length_penalty = min(0.3, (ratio - 0.9) * 3.0)
```

Optimizer fallback:

```python
# skills/evolve_skill.py:156-178
try:
    optimizer = dspy.GEPA(metric=skill_fitness_metric, max_steps=iterations)
    optimized_module = optimizer.compile(baseline_module, trainset=trainset, valset=valset)
except Exception as e:
    optimizer = dspy.MIPROv2(metric=skill_fitness_metric, auto="light")
    optimized_module = optimizer.compile(baseline_module, trainset=trainset)
```

## Thin Project Disposition

Not applicable — Hermes Self-Evolution has 2 Tier 1 and 6 Tier 2 subsystems. The project is narrow (focused on skill optimization) but deep (sophisticated optimization pipeline).

**Unique contribution**: The only reference project implementing automated skill evolution. The external session mining pipeline (4.50) and GEPA-based optimization (3.75) are novel patterns not found elsewhere in the corpus.
