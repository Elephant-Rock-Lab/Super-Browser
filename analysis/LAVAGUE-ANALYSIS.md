# LaVague

> Large Action Model framework for AI web agents using RAG-based action generation
> Source ID: SRC-005
> Language: Python
> Scale: ~200+ files, monorepo with 10+ packages
> Last Verified: 2026-04-22
> Verification Status: Metadata Refreshed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | RAG-Based Action Generation Pipeline | Processing & Logic | `lavague-core/lavague/core/navigation.py`, `retrievers.py` | 4 | 4 | 3 | 4 | 3.70 | 1 | Partial #2 |
| 2 | World Model (Multimodal Reasoning) | Processing & Logic | `lavague-core/lavague/core/world_model.py` | 3 | 4 | 3 | 4 | 3.45 | 2 | Partial #7 |
| 3 | Three-Engine Dispatch (Nav/Python/Controls) | Coordination | `lavague-core/lavague/core/action_engine.py` | 3 | 3 | 3 | 4 | 3.25 | 2 | Partial #7 |
| 4 | Interactive Element Detection (JS Injection) | Perception & Input | `lavague-core/lavague/core/base_driver.py` (JS_GET_INTERACTIVES) | 3 | 3 | 3 | 3 | 3.00 | 2 | Partial #2 |
| 5 | Anti-Hallucination Validation | Governance & Quality | `lavague-core/lavague/core/navigation.py` (_verify_llm_response) | 3 | 4 | 3 | 2 | 2.95 | 2 | No mapping |
| 6 | Context System (Multi-Provider) | Integration & Extension | `lavague-core/lavague/core/context.py`, integrations/contexts/ | 3 | 2 | 4 | 4 | 3.15 | 2 | Partial #9 |
| 7 | Driver Abstraction (Selenium/Playwright) | Integration & Extension | `lavague-core/lavague/core/base_driver.py`, integrations/drivers/ | 3 | 1 | 4 | 4 | 2.85 | 2 | Partial #1 |
| 8 | Short-Term Memory | Data & Storage | `lavague-core/lavague/core/memory.py` | 2 | 1 | 3 | 2 | 1.95 | 3 | No mapping |

Tier 1 count: 1 | Tier 2 count: 6 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 2. Reasoning | ● Full | Production | `world_model.py`, `navigation.py` | Gap — LaVague's World Model is a reasoning orchestrator |
| 4. Perception | ◐ Partial | Production | `base_driver.py` (JS interactives, screenshots) | Gap — LaVague uses DOM-first with screenshot supplementation |
| 7. Knowledge Representation | ◐ Partial | Research | `retrievers.py` (HTML→chunks→embeddings→ranking) | Gap — RAG pipeline for HTML understanding |
| 9. Metacognition | ◐ Partial | Production | `world_model.py` (engine selection) | Gap — World Model decides which engine to call |
| 11. Plugin & Extension | ● Full | Production | `integrations/` (drivers, contexts, retrievers) | Gap — Clean plugin architecture |
| 13. Provider & Model Management | ◐ Partial | Production | `integrations/contexts/` (OpenAI, Anthropic, Gemini, etc.) | Gap — Multi-provider context system |

## What to Adopt

### 1. RAG-Based Action Generation Pipeline

- **Pattern**: Extract interactable HTML → expand context around elements → embed and rank chunks → send top-k to LLM → extract structured YAML actions → validate xpaths → execute
- **Subsystem**: #1 (RAG-Based Action Generation Pipeline)
- **Intrinsic score**: 3.70
- **Source file**: `lavague-core/lavague/core/navigation.py:1-300`, `lavague-core/lavague/core/retrievers.py:1-400`
- **Evidence**: Verified in code
- **What it does**: Instead of sending full HTML to the LLM, LaVague uses a 3-stage retrieval pipeline: (1) `InteractiveXPathRetriever` injects JS to find all interactable elements and their xpaths, (2) `FromXPathNodesExpansionRetriever` expands context around each element up to chunk_size (750 chars), (3) `SemanticRetriever` embeds chunks and ranks by relevance to the instruction, keeping top_k (10). This dramatically reduces token usage while preserving action-relevant context.
- **Integration target**: The selector tier of Super Browser's three-tier engine. The RAG pipeline produces candidate selectors with relevance scores.
- **Overlap**: Super Browser uses direct selector matching at Tier 1; LaVague's RAG pipeline is an alternative approach for element discovery that could enhance Tier 1 effectiveness.
- **Quality**: Needs adaptation
- **Effort**: High

### 2. Anti-Hallucination Validation

- **Pattern**: Verify LLM-generated xpaths exist in the provided HTML context before execution
- **Subsystem**: #5 (Anti-Hallucination Validation)
- **Intrinsic score**: 2.95
- **Source file**: `lavague-core/lavague/core/navigation.py` (_verify_llm_response)
- **Evidence**: Verified in code
- **What it does**: After the LLM generates YAML actions with xpaths, `_verify_llm_response` checks that each xpath actually exists in the HTML context that was provided. If an xpath doesn't exist, it raises `HallucinatedException` or `ElementOutOfContextException`. This prevents executing actions based on LLM hallucinations.
- **Integration target**: The structured action result envelope — add a validation step before action execution
- **Overlap**: Super Browser's roadmap specifies structured action results with {ok, data, error, meta}; adding hallucination checking to the validation step would improve reliability.
- **Quality**: Needs adaptation
- **Effort**: Low

### 3. World Model Engine Selection

- **Pattern**: Multimodal LLM receives screenshots + HTML + instruction history and decides which sub-engine to call
- **Subsystem**: #2 (World Model)
- **Intrinsic score**: 3.45
- **Source file**: `lavague-core/lavague/core/world_model.py`
- **Evidence**: Verified in code
- **What it does**: The `WorldModel` uses a multimodal LLM (GPT-4o) to analyze the current page state and decide: (a) is the objective complete? (b) if not, which engine should handle the next step (Navigation, Python, or Controls)? and (c) what instruction to give it? This is a metacognitive layer that selects the appropriate action strategy.
- **Integration target**: The Supervisor/Facade layer — the decision point for which tier to use
- **Overlap**: Super Browser's three-tier fallback is mechanical (try selector, fall back to coordinate, fall back to vision). LaVague's approach is cognitive (LLM decides which strategy to use). The cognitive approach is more flexible but more expensive.
- **Quality**: Needs adaptation
- **Effort**: Medium

## Unguided Findings

### RAG Pipeline for HTML Chunking (composite: 3.70)

- **What it does**: The three-stage retrieval pipeline (interactable detection → context expansion → semantic ranking) is a novel approach to the "too much HTML for LLM context" problem. It's specifically designed for action generation, not general RAG.
- **Why it matters**: This pattern is unique to browser automation — no other analyzed project uses RAG specifically for action element retrieval. Most projects send full DOM or accessibility trees. The RAG approach could significantly reduce Tier 1 token costs.
- **Architecture**: Three chained retriever classes, each implementing a common interface. `InteractiveXPathRetriever` uses injected JS (`JS_GET_INTERACTIVES`) to identify all interactable elements. `FromXPathNodesExpansionRetriever` expands HTML context symmetrically around each element. `SemanticRetriever` uses vector similarity to rank.
- **Key files**: `lavague-core/lavague/core/retrievers.py`
- **Adoption feasibility**: Medium — the retriever chain is well-designed but depends on llama-index for embedding/vector operations.

## Notable Code

The three-stage retriever pipeline:

```python
# lavague-core/lavague/core/retrievers.py (pattern)
class InteractiveXPathRetriever:
    """Injects JS to find all interactable elements and compute xpaths."""
    async def retrieve(self, html: str, query: str) -> list[DOMNode]:
        # Injects JS_GET_INTERACTIVES into the page
        # Returns list of DOMNode with xpath attributes

class FromXPathNodesExpansionRetriever:
    """Expands HTML context around interactable elements."""
    def retrieve(self, nodes: list[DOMNode], chunk_size: int = 750) -> list[str]:
        # Symmetrically expands around each node up to chunk_size

class SemanticRetriever:
    """Ranks expanded chunks by semantic similarity to query."""
    def retrieve(self, chunks: list[str], query: str, top_k: int = 10) -> list[str]:
        # Uses embeddings + VectorStoreIndex for ranking
```

Anti-hallucination validation:

```python
# lavague-core/lavague/core/navigation.py
def _verify_llm_response(self, action: dict, context_html: str) -> None:
    """Verify xpaths in LLM response exist in provided context."""
    xpath = action.get("action_xpath")
    if xpath and xpath not in context_html:
        raise HallucinatedException(f"LLM generated non-existent xpath: {xpath}")
```

## Thin Project Disposition

Not applicable — LaVague has 1 Tier 1 and 6 Tier 2 subsystems.
