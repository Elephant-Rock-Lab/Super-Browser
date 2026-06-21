# Super Browser MCP Server

Super Browser exposes its browser inspection and control surface over the
[Model Context Protocol](https://modelcontextprotocol.io) so that AI coding
agents (Claude, Cursor, etc.) can observe and interact with a page without
scripting Python.

The stdio server advertises **six read-only tools** by default. When
constructed with a write-enabled `MCPSessionPolicy`, it advertises **seven
additional side-effecting tools**; each write call is still checked by
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
superbrowser-mcp
python -m super_browser.mcp_server
```

Both start a **stdio** server. The default server advertises 6 read-only
tools and recognizes (but refuses) write-tool calls with a structured policy
refusal.

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

## Tools

All tools return structured JSON (`{"ok": bool, ...}`) as `TextContent`. The
screenshot tool additionally returns an `ImageContent` block.

### Read-only tools (always advertised)

| Tool | Args | Behavior | Lazy-starts browser? |
|---|---|---|---|
| `browser_status` | none | Runtime status (running, backend). | No |
| `current_url` | none | Current URL, or a structured "not started" state. | No |
| `observe` | none | Page state: URL, title, interactive/total element counts. | Yes |
| `extract_text` | `query` (required), `selector` (optional) | Text content, optionally scoped to a CSS selector. | Yes |
| `screenshot` | `full_page` (optional, default `false`) | Base64 PNG of the viewport or full page. | Yes |
| `list_tabs` | none | Snapshot of open tabs. | Yes |

### Write tools (advertised when writes are enabled)

| Tool | Args | Security level |
|---|---|---|
| `navigate` | `url` (required), `wait_until` (optional) | SENSITIVE — URL passed to `SecurityManager` for domain allow/block enforcement |
| `scroll` | `direction` (optional), `amount` (optional) | SENSITIVE |
| `press_key` | `key` (required) | SENSITIVE |
| `click` | `target` (required), `description` (optional) | SENSITIVE |
| `fill` | `target` (required), `value` (required), `clear_first` (optional), `description` (optional) | SENSITIVE |
| `open_tab` | `url` (optional) | SENSITIVE — URL passed to `SecurityManager` when provided |
| `close_tab` | `tab_id` (required) | SENSITIVE |

`fill` sends only the literal value supplied by the caller. It does not
retrieve, infer, store, or auto-fill credentials.

### Asymmetric default behavior

The default server behavior is intentionally asymmetric:

- **`list_tools()`** advertises only the 6 read-only tools.
- **`call_tool()`** still recognizes write-tool names and returns a structured
  policy refusal (`refusal.reason = "writes are disabled"`), not an "Unknown
  tool" error.

This means clients don't see write tools by default, but manual or
unadvertised write calls are handled cleanly rather than misclassified.

### Permission model (write tools)

Every write-tool call passes through a central authorization path before
reaching the browser:

1. **Write-enabled check** — `MCPSessionPolicy.allow_writes` must be `True`
2. **Action-count check** — `actions_used` must not exceed `max_actions`
3. **Timeout-budget check** — session elapsed time must not exceed `timeout_seconds`
4. **`SecurityManager.check_action()`** — domain allow/block lists, action policy, injection detection, redaction
5. **Audit log** — every write attempt (allowed or denied) is recorded

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
  (`observe`, `extract_text`, `screenshot`, `list_tabs`, or any write tool
  that reaches the facade after authorization).
- `browser_status` and `current_url` are safe to call before startup and do
  **not** force a launch.
- On server close, the runtime calls `SuperBrowser.stop()` to tear down.

## Still excluded

The following are not implemented and will return a structured "Unknown tool"
error:

`download`, `upload`, `act`, arbitrary JS execution.

`act` (the LLM agent loop) is the highest-side-effect tool and will require
a separate design pass before implementation.

## Errors

Errors are returned as structured JSON, never raised across the MCP boundary:

```json
{"ok": false, "error": "Unknown tool: '__missing__'. Available: [...]" }
```

Argument-validation errors use the `invalid_arguments` key:

```json
{"ok": false, "invalid_arguments": "'query' is required and must be a non-empty string"}
```

## Reference

- Design: [RFC #178](https://github.com/Octo-Lex/Super-Browser/issues/178)
- The deleted prior server (`a370cf9`) is recoverable from git history for
  reference — it shipped 10 tools including 6 side-effecting ones with no
  permission model and no tests. The current server is the deliberate
  correction: tested, permissioned, with structured refusals and audit logging.
