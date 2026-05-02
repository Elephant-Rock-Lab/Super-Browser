# Tool Benchmark Assessment: ToolBench & ToolLLM

**Date:** 2026-04-23
**Relevance to SUPER-BROWSER gaps:** #7 (Agent Orchestration -- tool registry, tool calling), #5 (Domain Skill Registry)
**Sources:** SRC-026 (ToolBench), SRC-027 (ToolLLM)

---

## Project 1: ToolBench (SRC-026)

**Location:** `C:\Next AI\ref\ToolBench-master`

### Verdict: THIN DISPOSITION

ToolBench is an academic research project (OpenBMB, paper: arXiv 2307.16789) for generating instruction-tuning data to train LLMs on tool use. It is not a production tool-calling library. The entire codebase is an evaluation harness wrapped around RapidAPI: it collects 16,464 REST API specs from RapidAPI, generates synthetic instruction-following data via ChatGPT, trains ToolLLaMA models, and evaluates them with pass-rate/preference metrics against GPT-based judges.

Nothing in this project is extractable for SUPER-BROWSER's tool registry or agent orchestration layer:
- **API interaction** is done through a hardcoded RapidAPI proxy server (`http://8.130.32.149:8080/rapidapi`) -- not a reusable HTTP client.
- **Tool discovery** is offline: tools are pre-collected JSON files on disk, indexed by category. There is no runtime registry, no dynamic tool loading, no skill-based organization.
- **Tool calling** uses OpenAI function-call format (`api_json_to_openai_json`) but only to feed prompts to LLMs for benchmark evaluation -- not as an executable tool-dispatch runtime.
- **Conversation template** (`tool_conversation.py`) is a fork of FastChat's prompt templating with no tool-execution semantics.

### Notable Patterns (reference only, not for adoption)

1. **DFSDT (Depth-First Search Decision Tree):** A tree-search algorithm that explores multiple reasoning paths for multi-tool tasks. Interesting as a planning pattern for complex multi-step browser automation, but the implementation is tightly coupled to the eval harness and LLaMA generation. The concept (branching tool-use plans with backtracking) is worth remembering for SUPER-BROWSER's agent orchestrator design, but no code is reusable.

2. **Finish-function convention:** Every tool-use session must end with a `Finish` function call (with `give_answer` or `give_up_and_restart` modes). This is a simple but effective control-flow pattern for agent termination that SUPER-BROWSER could adopt conceptually.

3. **Observation compression:** Methods for truncating/filtering API responses before feeding back to the LLM (`truncate`, `filter`, `random`). Relevant idea for managing context in browser automation, but the implementation is trivial.

---

## Project 2: ToolLLM (SRC-027)

**Location:** `C:\Next AI\ref\ToolLLM-master`

### Verdict: THIN DISPOSITION

ToolLLM is the same project as ToolBench at a slightly later version (2024-08 update vs 2023-08). The codebases are structurally identical -- `diff -rq` shows only minor file-level differences:
- Updated server URLs and API handling in `server.py`, `toolbench_server.py`
- Additional GPT-4 evaluator configs in `tooleval/`
- Minor model updates in LLM adapters
- A `StableToolBench` variant that uses API response simulation instead of live RapidAPI calls

All the same THIN DISPOSITION applies: this is an LLM training/evaluation pipeline, not a production tool-calling framework. No reusable infrastructure for SUPER-BROWSER's tool registry or agent orchestration.

### Notable Patterns (reference only)

1. **StableToolBench (simulated API responses):** The 2024 update introduces API response simulation for stable evaluation. This is conceptually similar to mocking browser actions for testing -- potentially relevant to SUPER-BROWSER's testing strategy, but no code is shared or usable.

2. **ToolRetriever (sentence-transformer based):** Uses embedding-based retrieval to select relevant tools from a large pool given a user query. The idea of semantic tool/skill matching is directly relevant to SUPER-BROWSER's Domain Skill Registry (#5), but the implementation is a thin wrapper around `sentence-transformers` that SUPER-BROWSER could replicate in a few dozen lines if needed.

---

## Summary

| Project    | Verdict | Reason                                                                 |
|------------|---------|------------------------------------------------------------------------|
| ToolBench  | THIN    | Academic eval harness for LLM tool-use training. No production runtime.|
| ToolLLM    | THIN    | Same project, slightly newer version. Identical disposition.           |

**Actionable takeaways for SUPER-BROWSER:**
- **Zero code to extract.** Both are LLM-training pipelines, not tool-execution runtimes.
- **Conceptual borrow:** The "Finish function" termination pattern and the DFSDT branching-search idea are worth noting for orchestrator design.
- **Conceptual borrow:** Semantic skill matching (embedding-based tool retrieval) aligns with Gap #5 but is trivially reimplementable.
- **Skip deeper analysis.** No production infrastructure, no novel tool-discovery protocols, no executable tool registries.
