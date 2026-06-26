# Design Note: MCP Tool Metadata Unification

> **Status:** Design note. No implementation.
> **Decision:** Defer full unification. Document the metadata contract; keep
> `mcp_server.py` as the MCP source of truth until pressure justifies change.
> **Date:** 2026-06-26

## Core question

Should Super-Browser extend `ToolDefinition` to become the single source of
truth for MCP schemas, tiers, validation, and docs — or should MCP remain
hand-curated until there is stronger pressure?

## Current state (v2.8.0)

The MCP server advertises **29 tools** in action mode (17 default). Tool
metadata is maintained in three parallel places:

```text
1. ToolRegistry / ToolDefinition / ToolParameter  (agent-loop path)
   - src/super_browser/agent/registry.py
   - Typed specs, handlers, JSON schemas, toolsets, security_level
   - Used by AgentLoop for the embedded act() path

2. MCP types.Tool definitions + _tool_* handlers   (MCP path)
   - src/super_browser/mcp_server.py
   - Hand-maintained lists: PHASE1_TOOLS, NAVIGATION_AUX_TOOLS,
     DIAGNOSTICS_TOOLS, INTERACTION_TOOLS, PHASE2B_TOOLS, PHASE2B_WAVE2_TOOLS
   - Handlers wired by name-string convention: getattr(self, f"_tool_{name}")

3. MCP tier/security maps + validation               (MCP path)
   - INSPECT_TOOL_NAMES, NAVIGATION_TOOL_NAMES, ACTION_TOOL_NAMES frozensets
   - WRITE_TOOL_SECURITY_LEVELS / NAVIGATION_SECURITY_LEVELS dicts
   - _validate_navigation_args / _validate_action_args (hand-written Python)
```

These three sources are synchronized manually. Tests assert advertised counts
and tier membership, but there is no compile-time guarantee they agree.

## Problem

Duplication is growing. Each new MCP tool requires:

- A `types.Tool` definition (schema, description)
- A `_tool_*` handler method
- An entry in the right `*_TOOLS` list (which determines tier membership)
- An entry in `_validate_action_args` or `_validate_navigation_args` (hand-written validation)
- An entry in the `ACTION_TOOL_NAMES` / `NAVIGATION_TOOL_NAMES` frozenset
- Updates to count assertions across 4+ test files
- Updates to `docs/mcp.md` (tool table + counts)
- Updates to `CHANGELOG.md`

That is 8 touch points per tool. With 29 tools now and P3.1B/P4/P5 ahead,
the maintenance surface is real.

## Why current ToolDefinition cannot serve as MCP source of truth

Fact-checked against `src/super_browser/agent/registry.py` (lines 17-63):

### 1. Schema expressiveness is too flat

`ToolDefinition.to_json_schema()` produces a flat type system:
`str→string, int→integer, float→number, bool→boolean`. It cannot express:

- **Enums** — used heavily: `scroll.direction`, `wait_for.load_state`,
  `select_option.by`, `reload.wait_until`
- **Defaults** — MCP uses `"default": false`, `"default": 10000`;
  `ToolParameter` stores a default but `to_json_schema()` never emits it
- **Numeric ranges** — `wait_for.timeout_ms` (100–60000),
  `type_text.delay_ms` (0–1000)
- **Bool-as-int rejection** — MCP validation explicitly rejects `bool` where
  `int` is expected; `ToolParameter` has no concept of this
- **Nested objects / arrays** — MCP `inputSchema.properties` can nest

### 2. Tier metadata is a different axis

`ToolDefinition.security_level` takes values `safe`/`sensitive`/`dangerous`
(a risk scale). MCP tiers are `inspect`/`navigation`/`action` (permission
buckets, assigned by list membership). There is no automatic mapping:

- `navigate` is `sensitive` but navigation-tier (default-allowed)
- `scroll` is `safe` but action-tier (gated)
- `screenshot` is `sensitive` but inspect-tier (no security check)

`ToolDefinition` has no `tier` field. Its `toolsets` field is a grouping
concept unrelated to MCP permission tiers.

### 3. Validation hooks are hand-written Python

MCP argument validation (`_validate_navigation_args`,
`validate_action_args`) contains logic that no schema can express:
non-empty string checks, bool-as-int rejection, range bounds, exactly-one-
condition constraints (`wait_for`). This logic cannot be generated from any
data structure — it requires executable validation hooks.

### 4. Handler dispatch is name-string convention

MCP dispatches via `getattr(self, f"_tool_{name}")`. This is a runtime
convention with no type safety. `ToolDefinition.handler` is a callable
reference, but the MCP path doesn't use it — it uses its own dispatch table.

## What MCP metadata would need (the full contract)

```text
Per-tool metadata required:
  - tool name (str)
  - tier: inspect | navigation | action | high_risk
  - advertised_by_default: bool (derived from tier)
  - security_level: safe | sensitive | dangerous
  - action_budget: consumes | does_not_consume
  - input schema:
      - parameter name
      - type (str, int, bool, str-enum, ...)
      - required: bool
      - default value
      - enum values (where applicable)
      - numeric range (min, max)
      - reject_bool_as_int: bool
  - validation hook: callable(args) -> error | None
  - handler binding: callable or name convention
  - description (for MCP tool listing)
  - redaction policy: which output fields to redact, text vs URL
```

This is substantially richer than what `ToolDefinition` carries today.

## Decision: defer full unification

```text
Do not implement automatic MCP schema generation now.

Reasons:
  1. Current ToolDefinition cannot express MCP metadata without lossy flattening.
  2. Forcing MCP schemas through it would damage validation, enums, ranges.
  3. The maintenance pain (8 touch points per tool) is real but manageable
     at 29 tools.
  4. A partial generator that can't express tier/validation/security
     faithfully is worse than hand-curated — it would create a false sense
     of single-source-of-truth while silently diverging.
```

## What to do instead

### Now (no code change)

Keep `mcp_server.py` as the MCP source of truth. Document this design note
as the contract for what a future unification would require.

### Trigger conditions for revisiting

Re-evaluate when any of these become true:

```text
1. MCP tool count exceeds ~40 (currently 29)
2. A tool is added with the wrong tier and isn't caught until production
3. Validation logic is duplicated between MCP and SDK paths
4. A third consumer (e.g. external-agent API) needs the same metadata
```

### Future options (when triggered)

```text
Option A — MCPToolDefinition wrapper:
  A new dataclass that wraps ToolDefinition and adds MCP-specific fields
  (tier, advertised_by_default, validation_hook, redaction_policy).
  Pro: doesn't pollute the SDK registry.
  Con: still two definitions per tool.

Option B — Extend ToolDefinition:
  Add tier, enum_constraints, defaults, ranges, validation_hook fields.
  Pro: true single source of truth.
  Con: makes the SDK registry awkward for non-MCP consumers; schema migration.

Option C — Generate MCP from a new tool-spec module:
  A dedicated mcp_tools.py that defines tool specs with full metadata,
  generates types.Tool objects, validation functions, and docs entries.
  Pro: MCP owns its own metadata; no SDK pollution.
  Con: doesn't unify with the SDK registry (but that may be acceptable).
```

The design note recommends **Option C** if/when triggered — it keeps MCP
and SDK concerns separate while reducing MCP's internal duplication.

## Comparison to existing inspect-redaction design

The P2.3 redaction design (`docs/design/inspect_redaction.md`) took a
similar approach: document the boundary, reuse existing machinery, defer
per-tool overrides. This note follows the same pattern for tool metadata.

## Summary

```text
Problem:   8 touch points per MCP tool; metadata in 3+ places.
Root cause: ToolDefinition is too flat for MCP's needs.
Decision:  Defer unification. Keep hand-curated MCP.
Trigger:   ~40 tools, or a tier-mismatch production incident.
Preferred future path: Option C (dedicated MCP tool-spec module).
```
