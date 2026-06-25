# Design Note: Shared Inspect-Output Redaction

> **Status:** Design proposal for review. No implementation yet.
> **Scope:** P2.3 — define the redaction boundary before more default-readable MCP surfaces are added.
> **Date:** 2026-06-25

## Problem

The inspect-tier MCP tools return raw page/browser content to the agent with no
redaction:

- `extract_text` — returns page text as-is
- `observe` — returns URL, title, element counts (text in serialized form)
- `get_console_messages` — returns console output as-is
- `get_page_errors` — returns error messages + stack traces as-is
- `list_requests` / `get_request` — returns header **names** only (by P2 design),
  but URLs, failure text, and console/error content are unredacted
- `get_network_errors` — returns failed request URLs + failure text as-is

This is consistent today (all inspect tools have the same "no redaction"
posture), and it was the deliberate P2 decision: ship diagnostics unredacted for
parity with `extract_text`, then unify redaction across all inspect tools as a
follow-up. **This document is that follow-up.**

The risk: console messages, page errors, and URLs routinely contain secrets
(API keys in console logs, tokens in redirect URLs, credentials in error
messages). An agent that reads these via MCP and passes them to an LLM leaks
secrets into the model context.

## Existing machinery (reuse, don't rebuild)

The codebase already has a complete redaction layer:

| Component | Location | What it does |
|---|---|---|
| `SecretRedactor` | `security/redactor.py:61` | Pattern-based redaction of secrets in text (API keys, tokens, passwords, JWTs, etc.) |
| `redact_args()` | `security/action_redaction.py:55` | Key-name + value-pattern redaction on dicts |
| `redact_result_dict()` | `security/action_redaction.py:108` | Redacts `ActionResult.to_dict()` output (`data` + `error` fields) |
| `redact_context()` | `security/action_redaction.py:81` | Scrubs sensitive query params from URLs |
| `_SENSITIVE_KEYS` | `security/action_redaction.py:12` | Frozenset of sensitive key names (password, token, secret, cookie, auth, etc.) |
| `configure_redaction()` | `security/action_redaction.py:45` | Sets the default redactor from a `SecurityConfig` |
| `SecurityManager.check_action()` | `security/manager.py:111` | Runs redaction on action params when `redaction_enabled=True` (default) |

**Critical gap:** `redact_result_dict()` is wired into `ActionResult.to_dict()`
(`results/types.py:235`) — the **Python SDK serialization path**. But the MCP
server's `_serialize_action_result()` (`mcp_server.py:432`) manually builds a
payload from `ok`/`data`/`error`/`meta` and does **not** call
`ActionResult.to_dict()` or `redact_result_dict()`. So the same `ActionResult`
is redacted when serialized via the Python SDK but **not** when returned via
MCP. Additionally, the diagnostics handlers (`_tool_get_console_messages`, etc.)
and `_tool_current_url` build response dicts directly, bypassing
`ActionResult` and `_serialize_action_result()` entirely.

## Design principles

1. **Do not destroy utility by default.** Redaction should mask known secret
   patterns, not collapse all text. A redacted console message should still
   show the message structure with secrets replaced by the existing markers
   (`[REDACTED:{secret_type}:{hash6}]` or `[REDACTED:query_param]`).

2. **Policy-driven, not always-on.** Redaction should be controlled by the
   `SecurityConfig` (which is already `redaction_enabled=True` by default). The
   MCP server constructs a `SecurityManager` in `run_server()`; the same config
   should govern inspect-output redaction. An operator who wants raw output
   (e.g. for debugging) can set `redaction_enabled=False`.

3. **Redact at the MCP serialization boundary, not inside the browser.** The
   browser captures raw content; redaction happens when the MCP server
   serializes the response for the agent. This keeps the SDK fast path
   unredacted (Python SDK consumers get raw data) while the agent-facing MCP
   boundary applies the policy.

4. **Masking format is documented and stable.** The existing redaction
   machinery emits two marker formats, both preserved as-is:
   - `SecretRedactor`: `[REDACTED:{secret_type}:{hash6}]` — e.g.
     `[REDACTED:openai_key:abc123]` (includes the secret type and a 6-char
     SHA-256 prefix for deduplication).
   - `redact_context()`: `[REDACTED:query_param]` — for sensitive query
     parameter values.
   Agents can detect that redaction occurred without seeing the secret.

5. **No output-shape change.** Redaction replaces string values in place; it
   does not add, remove, or rename keys. A redacted `get_console_messages`
   response has the same `{ok, messages, count}` shape — only `messages[i].text`
   values may be masked.

## Scope: which tools, what content

### In scope (redaction applied)

| Tool | Content to redact | Mechanism |
|---|---|---|
| `extract_text` | extracted text body | `SecretRedactor.redact()` on the text string |
| `observe` | title, URL | URL redaction (see below); `SecretRedactor.redact()` on title |
| `current_url` | page URL | URL redaction (see below) |
| `list_tabs` | tab URLs, tab titles | URL redaction on each tab URL; `SecretRedactor.redact()` on titles |
| `get_console_messages` | `text` field per entry | `SecretRedactor.redact()` on each `text` |
| `get_page_errors` | `message`, `stack` fields | `SecretRedactor.redact()` on each |
| `get_network_errors` | `url`, `failure_text` | URL redaction on URL; `SecretRedactor.redact()` on failure_text |
| `list_requests` | `url` per entry | URL redaction on each URL |
| `get_request` | `url`, `failure_text` | URL redaction on URL; `SecretRedactor.redact()` on failure_text |

**URL redaction** (two-pass, applied to all URL fields):
1. `redact_context(url)` — redacts query parameters whose key names match
   `_SENSITIVE_KEYS` (token, access_token, api_key, cookie, etc.).
2. `SecretRedactor.redact(result_url)` — pattern-scans the remaining URL for
   secret substrings in non-sensitive query keys, fragments, or URL-like
   strings (e.g. `?code=sk-...`, `?next=https://...token...`).
3. Preserve scheme, host, and path where possible; redact only secret
   substrings and sensitive query values.

This two-pass approach is necessary because `redact_context()` alone only
catches secrets in *named* sensitive parameters. Secrets in innocuously-named
query values (`?code=sk-...`) or embedded in redirect URLs would leak through
without the `SecretRedactor` pattern scan.

### Already redacted (no change)

| Content | Current state |
|---|---|
| Request/response header values | Not exposed (P2: `header_names` keys only) |
| Response bodies | Not exposed (P2: excluded) |
| Navigate URL/params | Redacted by `SecurityManager.check_action()` (navigation-tier) |
| Action tool arguments | Redacted by `SecurityManager.check_action()` (action-tier) |

### Out of scope

- **`browser_status`** — returns runtime status (running, backend name). No
  sensitive page content expected.
- **`screenshot`** — visual content; secret-detection in image data is a
  different problem (OCR + pattern matching). Deferred.
- **Redaction of element HTML/attributes in `observe`.** `observe` returns
  counts and metadata, not raw HTML. If a future tool exposes HTML, it joins
  this scope.
- **Per-tool redaction policy overrides.** All inspect tools share one policy
  (the `SecurityConfig`). Per-tool granular control is deferred.

## Architecture

### Option A (recommended): shared MCP redaction helper

Add a single helper in `mcp_server.py` that applies redaction to any
inspect-tier response dict before serialization:

```python
def _redact_inspect_output(payload: dict[str, Any]) -> dict[str, Any]:
    """Apply redaction policy to inspect-tier tool output.

    Redacts string values in known-sensitive fields (text, message, url, etc.)
    using the server's SecurityConfig. No-op if redaction is disabled or no
    SecurityManager is configured.
    """
```

Each inspect handler calls `_redact_inspect_output(payload)` before returning.
The helper uses the existing `SecretRedactor` + `redact_context()` machinery —
no new redaction logic.

**Why this over alternatives:** it's the narrowest change (one helper, called
from each handler), it reuses all existing machinery, and it keeps redaction at
the MCP boundary (principle #3).

### Option B (not recommended): wire `redact_result_dict` into `_serialize_action_result`

This would redact any `ActionResult` returned via MCP. But most inspect tools
don't return an `ActionResult` (they build dicts directly), so it wouldn't cover
`get_console_messages`, `list_requests`, etc. Incomplete.

### Option C (not recommended): redact inside `DiagnosticsBuffer` / the facade

This would redact at capture time, contaminating the buffer with masked values.
An SDK consumer using `sb.diagnostics` directly would get redacted data even if
they want raw. Violates principle #3.

## Sensitive classes (what gets redacted)

Reuse the existing `SecretRedactor` pattern set (`security/redactor.py`), which
covers:

- API keys (Anthropic, OpenAI, OpenRouter, GitHub, AWS, Google, Slack, Stripe)
- JWTs
- Passwords
- PEM/private keys
- Database URLs
- Generic tokens

Plus `_SENSITIVE_KEYS` for key-name matching (cookie, auth, session_id, etc.).

### Not redacted (by default)

- **Emails and phone numbers.** Not secrets in the same risk class as API keys.
  Can be added as a configurable pattern layer if needed, but deferred to avoid
  false positives that break utility.
- **IP addresses.** Same reasoning — operational data, not credentials.
- **Payment card numbers (PAN).** The `SecretRedactor` does not currently detect
  these. Could be added as a custom pattern via `SecurityConfig.custom_secret_patterns`.

## Compatibility

- **Default behavior changes:** with `redaction_enabled=True` (the default),
  inspect output now has secrets masked. This is a **behavior change** for
  existing MCP consumers who relied on raw output. Documented in CHANGELOG.
- **Output shape unchanged:** same keys, same structure. Only string values may
  contain redaction markers (`[REDACTED:{secret_type}:{hash6}]` from
  `SecretRedactor`, or `[REDACTED:query_param]` from `redact_context()`).
- **Disabling:**
  - **Current programmatic path:** pass
    `SecurityManager(SecurityConfig(redaction_enabled=False))` into
    `run_server(..., security_manager=...)`. Note that `run_server()` accepts a
    `SecurityManager`, not a `SecurityConfig`; `_build_default_security_manager()`
    constructs a default `SecurityConfig` internally using only domain
    allow/block lists from env.
  - **Proposed operator/CLI path:** add `SB_MCP_REDACTION=0|false|off` env
    toggle in the implementation PR, parsed by `_build_default_security_manager()`
    alongside the existing domain-list env vars. This gives operators a simple
    opt-out without constructing a custom `SecurityManager`.
- **Backward-compat for SDK consumers:** Python SDK users calling
  `sb.extract()` / `sb.observe()` directly are unaffected — redaction applies
  only at the MCP serialization boundary.

## Test plan

### Unit tests (shared helper)

- `_redact_inspect_output` masks a known API key in a text field
- `_redact_inspect_output` masks a token in a URL query param
- `_redact_inspect_output` is a no-op when redaction is disabled
- `_redact_inspect_output` is a no-op when no secret patterns are present
- Output shape preserved (same keys, same structure)

### Tool-specific fixture tests

- `extract_text`: fixture with an API key in the text → redacted in response
- `observe`: fixture with a secret in title → redacted; URL query param redacted
- `current_url`: fixture/current page URL with a token query param → URL redacted
- `list_tabs`: fixture/tab list with secret-bearing URL/title → URL/title redacted
- `get_console_messages`: fixture with a token in console text → redacted
- `get_page_errors`: fixture with a secret in error message → redacted
- `get_network_errors`: fixture with failed request URL + failure_text secret → both redacted
- `list_requests`: fixture with a secret in URL query param → URL redacted
- `get_request`: fixture with a secret in failure_text → redacted

### Negative tests

- Non-secret text passes through unchanged (no false positives on normal prose)
- Redaction disabled → raw output (existing behavior)

## Implementation order (after design approval)

```text
1. Add _redact_inspect_output() helper in mcp_server.py
2. Wire into the 9 inspect-tier handlers (extract_text, observe, current_url,
   list_tabs, 5 diagnostics)
3. Add SB_MCP_REDACTION env toggle (proposed in this design)
4. Unit tests for the helper
5. Fixture tests per tool
6. CHANGELOG [Unreleased] — behavior change note
7. Verify: real-browser e2e with a test page that logs a fake API key
```

## Resolved questions (from design review)

1. **Should `observe`'s URL be redacted?** **Yes.** Apply the two-pass URL
   redaction (query-param names + secret pattern scan) while preserving scheme,
   host, and path. The same policy applies to `current_url`, `list_tabs`,
   diagnostics request URLs, and any future inspect-tier URL fields.

2. **Should redaction be on by default in the MCP server?** **Yes.** Default-on
   matches the existing `SecurityConfig(redaction_enabled=True)` default and is
   the safer boundary for agent-facing MCP output. A documented opt-out is
   required (both programmatic and env-based), because this is a behavior
   change for MCP consumers.

3. **Should console stack traces be truncated?** **No.** Use pattern-only
   redaction by default. Preserve paths, line numbers, and stack structure;
   redact detected secret substrings only. Truncation would hurt diagnostic
   utility and should be a separate optional limit, not the default.
