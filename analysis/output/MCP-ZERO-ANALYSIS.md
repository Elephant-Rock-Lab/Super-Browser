# MCP-Zero (SRC-033) -- SUPER-BROWSER Gap Analysis

**Project**: MCP-Zero -- "Active Tool Discovery for Autonomous LLM Agents"
**Source**: `C:\Next AI\ref\MCP-Zero-master`
**Paper**: arXiv:2506.01056
**Verdict**: Thin Project Disposition

---

## Summary

MCP-Zero is a research artifact (paper + experiment code) that demonstrates embedding-based tool discovery across MCP server registries. It is **not a runtime or framework** -- it produces no running agent, manages no connections, and implements zero MCP protocol logic. Its entire value to SUPER-BROWSER is a single algorithmic idea: two-stage embedding retrieval (server-level then tool-level) using cosine similarity over pre-computed text-embedding-3-large vectors.

---

## What It Contains

| Component | Path | Description |
|-----------|------|-------------|
| `matcher.py` | `MCP-zero/matcher.py` | `ToolMatcher` class -- cosine-similarity over pre-computed embeddings (3072-dim). Two-stage: `match_servers()` then `match_tools()`. Returns ranked `(server, tool)` tuples. |
| `sampler.py` | `MCP-zero/sampler.py` | `ToolSampler` -- randomly samples N tools from a JSON dataset, selects a target tool for needle-in-haystack testing. |
| `reformatter.py` | `MCP-zero/reformatter.py` | Converts MCP tool descriptions into OpenAI function-calling `<function>` XML tags. |
| `experiment_mcptools.py` | `MCP-zero/experiment_mcptools.py` | Grid-search experiment: positions a target tool in a pool, asks GPT-4.1/Claude-3.5 to identify it, then uses `ToolMatcher` to verify. |
| `experiment_apibank.py` | `MCP-zero/experiment_apibank.py` | APIBank benchmark experiment. |
| Dataset | `MCP-tools/` | 308 servers, 2,797 tools with pre-computed embeddings. JSON file. |
| `prompt_guide/` | `MCP-zero/prompt_guide/` | System/user prompts for the LLM-based retrieval step. |

---

## Gap-by-Gap Assessment

| # | Gap | Relevance | Harvestable |
|---|-----|-----------|-------------|
| 1 | Browser Session & CDP | None | -- |
| 2 | Three-Tier Interaction | None | -- |
| 3 | Visual Verification | None | -- |
| 4 | Self-Healing | None | -- |
| 5 | Domain Skill Registry | **Low** | The dataset schema (server_name, server_summary, description_embedding, tools[]) is a primitive skill registry. The two-stage retrieval idea (find server first, then tool) is a useful pattern for SUPER-BROWSER's domain skill lookup. However, the implementation is tightly coupled to OpenAI embeddings and static JSON -- no runtime registration, no CRUD, no namespacing. |
| 6 | Vision Location | None | -- |
| 7 | Agent Orchestration | **None** | No MCP client, no server, no protocol handling, no tool calling. The code never connects to an MCP server -- it only matches against a static JSON file. |
| 8 | Stealth | None | -- |
| 9 | Token Budget | None | -- |
| 10 | Security Envelope | None | -- |
| 11 | Tracing | None | -- |
| 12 | Structured Results | None | -- |

---

## Key Patterns to Harvest

### 1. Two-Stage Embedding Retrieval (for Gap #5 Domain Skill Registry)

```
Stage 1: match_servers(query)  -- cosine similarity on server description/summary embeddings
Stage 2: match_tools(filtered_servers, query) -- cosine similarity on tool description embeddings
Score: (server_score * tool_score) * max(server_score, tool_score)
```

This pattern is relevant if SUPER-BROWSER builds a Domain Skill Registry that maps websites to skill sets. The idea of "first find the right domain/server, then find the right tool within it" maps directly.

### 2. Tool Description Reformatting (for Gap #7)

`reformatter.py` converts MCP tool metadata into `<function>` XML tags compatible with OpenAI function-calling. This is a simple but useful pattern for injecting tool descriptions into LLM prompts.

---

## What Cannot Be Harvested

- No MCP protocol implementation (no client, server, transport, or session management)
- No agent loop, no tool execution, no result handling
- No dynamic tool discovery -- relies entirely on pre-computed static embeddings
- No browser-related code of any kind

---

## Thin Project Disposition

MCP-Zero is a research paper's companion code, not an engineering project. It proves that two-stage embedding retrieval can locate the right MCP tool from a large pool, but provides no runtime infrastructure. For SUPER-BROWSER, the sole harvestable artifact is the two-stage retrieval algorithm pattern and the dataset schema shape (server + tools + embeddings). Everything else -- agent orchestration, MCP protocol, tool calling, session management -- must come from elsewhere. **Estimated integration effort for the retrieval idea: low (algorithm fits in ~200 lines). Estimated value: marginal.**
