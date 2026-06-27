# Super Browser MCP Server

Super Browser exposes its browser inspection and control surface over the
[Model Context Protocol](https://modelcontextprotocol.io) so that AI coding
agents (Claude, Cursor, etc.) can observe and interact with a page without
scripting Python.

The stdio server advertises **seventeen tools by default** (six inspect + five
diagnostics + six navigation) — enough to read a URL end-to-end and explain
why a read failed. When action mode is enabled, it advertises **twelve additional
action tools**; every action call is checked by
`MCPSessionPolicy` and `SecurityManager` before it can reach the browser.

See [RFC #178](https://github.com/Octo-Lex/Super-Browser/issues/178) for the
design history.

> `screenshot` captures the rendered page contents as the browser sees them. There is no automatic redaction; callers decide when to invoke it.

## Install

```bash
pip install 'superbrowser-sdk[mcp,patchright]'
python -m patchright install chromium
```

`[mcp]` pulls the lightweight `mcp` SDK (no browser deps of its own).
`[patchright]` provides the browser backend the server drives.

## Run

Either of:

```bash
superbrowser-mcp                       # default: 17 tools (inspect + diagnostics + navigation)
superbrowser-mcp --allow-actions       # 29 tools (adds the action tier)
python -m super_browser.mcp_server
```

Both start a **stdio** server. The default server advertises 17 tools and
recognizes (but refuses) action-tool calls with a structured policy refusal.

Action mode can also be enabled via the environment:

```bash
SB_MCP_ALLOW_ACTIONS=1 superstl-browser-mcp
```

Accepted truthy values: `1`, `true`, `yes`, `on` (case-insensitive).

## Client configuration

### Claude Desktop / Claude Code

Add to your MCP config (`claude_desktop_config.json` or the equivalent):

```json
{
  "mcpServers": {
    "super-browser": {
      "command": "superbrowser-mcp"
    }
  }
}
```

Or, if you prefer the module form:

```json
{
  "mcpServers": {
    "super-browser": {
      "command": "python",
      "args": ["-m", "super_browser.mcp_server"]
    }
  }
}
```

To enable action tools:

```json
{
  "mcpServers": {
    "super-browser": {
      "command": "superbrowser-mcp",
      "args": ["--allow-actions"]
    }
  }
}
```

### Cursor

```json
{
  "mcpServers": {
    "super-browser": {
      "command": "superbrowser-mcp"
    }
  }
}
```

## Tools

All tools return structured JSON (`{"ok": bool, ...}`) as `TextContent`. The
screenshot tool additionally returns an `ImageContent` block.

The tool surface is partitioned into four tiers. The first two are always
advertised; the third requires action mode; the fourth is not implemented.

### Inspect tier (always advertised)

| Tool | Args | Behavior | Lazy-starts browser? |
|---|---|---|---|
| `browser_status` | none | Runtime status (running, backend). | No |
| `current_url` | none | Current URL, or a structured "not started" state. | No |
| `observe` | none | Page state: URL, title, interactive/total element counts, a `targets` array of actionable element references (capped at 50), and an `images` array of image-element metadata (capped at 50). Each target includes `target` (a ref like `@e0`, usable as the `target` argument for coordinate-tier action tools: `click`, `fill`, `type_text`, `hover`, `select_option`), `role`, `name`, and `action_hint`. Each image includes `ref`, `role`, `name`, `alt` (the image's alt text or AX name), and optionally `bounds`. Non-interactive images are metadata-only and never appear in `targets`. | Yes |
| `extract_text` | `query` (required), `selector` (optional) | Text content, optionally scoped to a CSS selector. | Yes |
| `screenshot` | `full_page` (optional, default `false`), `format` (optional, `"png"` \| `"jpeg"`, default `"png"`), `quality` (optional, 1-100, jpeg only) | Base64 image of the viewport or full page. Default: lossless PNG. Request `format="jpeg"` with a `quality` value (e.g. 70) to produce a smaller image that fits under host inline limits (typical hosts inline images up to ~200 KiB; a JPEG at quality 70 is often 5-10x smaller than the equivalent PNG). | Yes |
| `list_tabs` | none | Snapshot of open tabs. | Yes |
| `get_console_messages` | `level` (optional), `limit` (optional, default 100) | Buffered browser console messages (snapshot, non-destructive). | Yes |
| `get_page_errors` | `limit` (optional, default 100) | Buffered uncaught page errors with stack traces. | Yes |
| `get_network_errors` | `url_filter` (optional), `limit` (optional, default 100) | Requests that failed (status ≥ 400, no response, or net error). | Yes |
| `list_requests` | `url_filter` (optional), `resource_type` (optional), `limit` (optional, default 100) | All buffered request summaries; returns `request_id` for `get_request`. | Yes |
| `get_request` | `request_id` (required) | One request's metadata (method, url, status, `header_names` — keys only, no values, no body). | Yes |

The five diagnostics tools read from a session-wide ring buffer that captures
console messages, page errors, and network requests via page-event listeners.
Reads are **snapshots** (non-destructive): the buffer is not cleared on read.
Diagnostics entries carry a monotonic `seq`, a `timestamp_ms`, and the
`page_url` at the time of the event. Request records use a stable `request_id`
(assigned by the buffer); a URL can have multiple requests, so always retrieve
via `request_id` from `list_requests`, not by URL. **No response bodies and no
raw header values** are returned — `get_request` exposes `header_names` (keys)
only.

### Navigation tier (always advertised)

Navigation mutates browser state (page/context acquisition) but is
default-allowed because reading requires page/context acquisition. `navigate`
is checked and audited at the MCP boundary when a SecurityManager is
configured. `switch_tab` delegates to the facade, which applies its configured
facade security policy. Navigation tools do **not** consume the action budget
and do **not** require action mode.

| Tool | Args | Behavior |
|---|---|---|
| `navigate` | `url` (required), `wait_until` (optional) | Go to a URL. URL is passed to `SecurityManager` for injection detection, secret redaction, and domain allow/block enforcement. |
| `wait_for` | exactly one of `selector` / `text` / `url` / `load_state`; `timeout_ms` (optional, 100–60000, default 10000) | Wait for a page condition before the next read. |
| `switch_tab` | `tab_id` (required, integer) | Switch the active browser tab by ID (from `list_tabs`). Changes the page the agent reads from. Diagnostics remain session-wide after switching; per-tab diagnostics are not supported yet. |
| `reload` | `wait_until` (optional) | Reload the current page. Returns the URL after reload. |
| `go_back` | `wait_until` (optional) | Go back one step in browser history. Returns a structured error if there is no previous entry. |
| `go_forward` | `wait_until` (optional) | Go forward one step in browser history. Returns a structured error if there is no next entry. |

`wait_for` accepts exactly one condition per call (deterministic single
results; compound waits can be added later as an explicit AND mode).

#### Read workflow

```text
navigate → wait_for → observe / extract_text / screenshot
```

This is the default-mode loop an agent uses to read a page. `observe` returns
actionable targets (`@e0` refs) that can be passed directly as the `target`
argument to coordinate-tier action tools (`click`, `fill`, `type_text`,
`hover`, `select_option`):

```text
navigate → wait_for → observe → click(target="@e0")
```

The `targets` array is capped at 50; `targets_truncated` indicates whether more
interactive elements exist. Target names are subject to inspect-output redaction.

#### Debugging workflow

When a read returns unexpected or empty content, the diagnostics tools explain
why — without expanding the action surface:

```text
navigate → wait_for → extract_text / observe
        ↓ (unexpected / empty / errored)
get_console_messages → get_page_errors → get_network_errors
        ↓ (inspect the evidence)
list_requests → get_request(request_id=...)   (drill into one request)
        ↓
adjust selector / report failure / retry
```

Diagnostics are inspect-tier: no `--allow-actions`, no action budget, no audit
entry, no side effects.

### Action tier (advertised when action mode is enabled)

| Tool | Args | Security level |
|---|---|---|
| `scroll` | `direction` (optional), `amount` (optional) | SENSITIVE |
| `press_key` | `key` (required) | SENSITIVE |
| `click` | `target` (required), `description` (optional) | SENSITIVE |
| `fill` | `target` (required), `value` (required), `clear_first` (optional), `description` (optional) | SENSITIVE |
| `open_tab` | `url` (optional) | SENSITIVE — URL passed to `SecurityManager` when provided |
| `close_tab` | `tab_id` (required) | SENSITIVE |
| `hover` | `target` (required), `description` (optional) | SENSITIVE |
| `select_option` | `target` (required), `option` (required), `by` (optional: text/value/label), `description` (optional) | SENSITIVE |
| `check` | `target` (required), `description` (optional) | SENSITIVE |
| `uncheck` | `target` (required), `description` (optional) | SENSITIVE |
| `focus` | `target` (required), `description` (optional) | SENSITIVE |
| `type_text` | `target` (required), `text` (required), `delay_ms` (optional, 0–1000), `description` (optional) | SENSITIVE |

`fill` sends only the literal value supplied by the caller. It does not
retrieve, infer, store, or auto-fill credentials. `type_text` types
character-by-character (per-keystroke), triggering JS key listeners — unlike
`fill` which sets the value atomically.

#### Action workflow

```bash
superbrowser-mcp --allow-actions
```

Action calls pass through the full authorization path (action gate →
action-count budget → timeout budget → `SecurityManager` → audit) before
reaching the browser.

### High-risk tier (not implemented)

`download`, `upload`, `act` (the LLM agent loop), and arbitrary JS execution
are not implemented. They will return a structured "Unknown tool" error and
will require a separate design pass before implementation.

## Domain filtering

Navigation is always security-checked, but domain allow/block enforcement is
**opt-in** via environment variables. With neither set, the domain filter is
allow-all (injection detection and secret redaction still run).

```bash
# Block specific hosts (comma- or whitespace-separated; glob patterns allowed)
SB_MCP_DOMAIN_BLOCKLIST="evil.com, *.test" superstl-browser-mcp

# Restrict to an allowlist (anything not matching is denied)
SB_MCP_DOMAIN_ALLOWLIST="example.com, docs.example.com" superstl-browser-mcp
```

When both are set, the blocklist is evaluated first; the allowlist then
restricts the survivors.

## Four-tier tool model

The default server behavior partitions the surface by risk:

- **`list_tools()`** advertises only the Inspect + Navigation tiers (17 tools).
- **`call_tool()`** still recognizes action-tool names and returns a structured
  policy refusal (`refusal.reason = "actions are disabled"`), not an "Unknown
  tool" error.

This means clients don't see action tools by default, but manual or
unadvertised action calls are handled cleanly rather than misclassified.

### Permission model (action tools)

Every action-tier call passes through a central authorization path before
reaching the browser:

1. **Action-enabled check** — `MCPSessionPolicy.allow_actions` must be `True`
2. **Action-count check** — `actions_used` must not exceed `max_actions`
3. **Timeout-budget check** — session elapsed time must not exceed `timeout_seconds`
4. **`SecurityManager.check_action()`** — domain allow/block lists, action policy, injection detection, redaction
5. **Audit log** — every action attempt (allowed or denied) is recorded

Navigation-tier calls use a lighter path: argument validation →
`SecurityManager.check_action()` (navigate only) → audit (both approvals and
denials) → handler. They bypass the action gate, action-count budget, and
timeout budget.

All denials return structured JSON as normal MCP content, never raised:

```json
{
  "ok": false,
  "refusal": {
    "tool": "navigate",
    "blocked_by": "security_manager",
    "reason": "domain_filter",
    "security_level": "sensitive"
  }
}
```

### Lifecycle

- One browser per server process.
- The browser lazy-starts on the first browser-dependent tool call
  (`navigate`, `wait_for`, `observe`, `extract_text`, `screenshot`,
  `list_tabs`, or any action tool that reaches the facade after authorization).
- `browser_status` and `current_url` are safe to call before startup and do
  **not** force a launch.
- On server close, the runtime calls `SuperBrowser.stop()` to tear down.

## Errors

Errors are returned as structured JSON, never raised across the MCP boundary:

```json
{"ok": false, "error": "Unknown tool: '__missing__'. Available: [...]" }
```

Argument-validation errors use the `invalid_arguments` key:

```json
{"ok": false, "invalid_arguments": "'query' is required and must be a non-empty string"}
```

`wait_for` timeouts return a structured timeout result:

```json
{"ok": false, "timeout": true, "reason": "Timeout 10000ms exceeded"}
```

## Behavior changes

### `superbrowser-sdk` 2.4 — navigation tier

Prior to 2.4, the default MCP server advertised 6 read-only tools and gated
**all** side-effecting tools (including `navigate`) behind `allow_writes=True`.

In 2.4 the tool surface was re-partitioned into four tiers:

- `navigate` moved into a default-allowed **Navigation tier** (reading requires
  page acquisition). It is still `SecurityManager`-checked and audited.
- `wait_for` was added (navigation tier).
- The former "write tools" became the **Action tier**, gated by
  `allow_actions` (`--allow-actions` / `SB_MCP_ALLOW_ACTIONS`).
- The action-gate refusal message changed from `"writes are disabled"` to
  `"actions are disabled"`. Clients pattern-matching the old string must update.

`allow_writes` remains as a backward-compatibility alias for `allow_actions`
in `MCPSessionPolicy`; existing callers using `MCPSessionPolicy(allow_writes=True)`
continue to work.

## Reference

- Design: [RFC #178](https://github.com/Octo-Lex/Super-Browser/issues/178)
- The deleted prior server (`a370cf9`) is recoverable from git history for
  reference — it shipped 10 tools including 6 side-effecting ones with no
  permission model and no tests. The current server is the deliberate
  correction: tested, permissioned, tiered, with structured refusals and audit logging.
