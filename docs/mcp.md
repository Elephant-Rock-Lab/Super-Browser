# Super Browser MCP Server (Phase 1 — read-only)

Super Browser exposes a subset of its browser inspection surface over the
[Model Context Protocol](https://modelcontextprotocol.io) so that AI coding
agents (Claude, Cursor, etc.) can observe a page without scripting Python.

**Phase 1 is read-only.** There are no navigation, click, fill, or arbitrary-JS
tools. Side-effecting tools are deferred to Phase 2, where they will sit behind
the SDK's `SecurityManager` (allowed/blocked origins, confirmation, audit log).
See [RFC #178](https://github.com/Octo-Lex/Super-Browser/issues/178) for the
design and phasing.

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
superbrowser-mcp
python -m super_browser.mcp_server
```

Both start a **stdio** server (no HTTP/SSE in Phase 1).

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

## Phase 1 tools

All tools return structured JSON (`{"ok": bool, ...}`) as `TextContent`. The
screenshot tool additionally returns an `ImageContent` block.

| Tool | Args | Behavior | Lazy-starts browser? |
|---|---|---|---|
| `browser_status` | none | Runtime status (running, backend). | No |
| `current_url` | none | Current URL, or a structured "not started" state. | No |
| `observe` | none | Page state: URL, title, interactive/total element counts. | Yes |
| `extract_text` | `query` (required), `selector` (optional) | Text content, optionally scoped to a CSS selector. | Yes |
| `screenshot` | `full_page` (optional, default `false`) | Base64 PNG of the viewport or full page. | Yes |
| `list_tabs` | none | Snapshot of open tabs. | Yes |

### Lifecycle

- One browser per server process.
- The browser lazy-starts on the first browser-dependent tool call
  (`observe`, `extract_text`, `screenshot`, `list_tabs`).
- `browser_status` and `current_url` are safe to call before startup and do
  **not** force a launch.
- On server close, the runtime calls `SuperBrowser.stop()` to tear down.

## What's not here (Phase 2+)

The following are **deliberately absent** from Phase 1 and will return a
structured "Unknown tool" error if invoked:

`navigate`, `click`, `fill`, `scroll`, `press_key`, `open_tab`, `close_tab`,
`download`, `upload`, `act`, arbitrary JS execution.

Phase 2 will add the write/navigation tools behind the SDK's existing
`SecurityManager` (domain allow/block lists, action policy, confirmation
callback, redaction, dangerous-command approval) — there is intentionally no
MCP-specific permission layer.

## Errors

Errors are returned as structured JSON, never raised across the MCP boundary:

```json
{"ok": false, "error": "Unknown tool: 'navigate'. Available: [...]" }
```

Argument-validation errors use the `invalid_arguments` key:

```json
{"ok": false, "invalid_arguments": "'query' is required and must be a non-empty string"}
```

## Reference

- Design: [RFC #178](https://github.com/Octo-Lex/Super-Browser/issues/178)
- The deleted prior server (`a370cf9`) is recoverable from git history for
  reference — it shipped 10 tools including 6 side-effecting ones with no
  permission model and no tests. This Phase 1 server is the deliberate
  correction: read-only first, tested, permissioned later.
