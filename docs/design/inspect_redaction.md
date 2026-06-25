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
server's `_serialize_action_result()` (`mcp_server.py`) does **not** call it.
So the same `ActionResult` is redacted when used via the Python SDK but **not**
when returned via MCP. The inspect tools bypass `ActionResult` entirely (they
build response dicts directly).

## Design principles

1. **Do not destroy utility by default.** Redaction should mask known secret
   patterns, not collapse all text. A redacted console message should still
   show the message structure with secrets replaced by `[REDACTED:type]`.

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

4. **Masking format is documented and stable.** `[REDACTED:type]` (e.g.
   `[REDACTED:api_key]`, `[REDACTED:token]`, `[REDACTED:query_param]`). Agents
   can detect that redaction occurred without seeing the secret.

5. **No output-shape change.** Redaction replaces string values in place; it
   does not add, remove, or rename keys. A redacted `get_console_messages`
   response has the same `{ok, messages, count}` shape — only `messages[i].text`
   values may be masked.

## Scope: which tools, what content

### In scope (redaction applied)

| Tool | Content to redact | Mechanism |
|---|---|---|
| `extract_text` | extracted text body | `SecretRedactor.redact()` on the text string |
| `observe` | title, URL | `redact_context()` on URL; `SecretRedactor.redact()` on title |
| `get_console_messages` | `text` field per entry | `SecretRedactor.redact()` on each `text` |
| `get_page_errors` | `message`, `stack` fields | `SecretRedactor.redact()` on each |
| `get_network_errors` | `url`, `failure_text` | `redact_context()` on URL; `redact()` on failure_text |
| `list_requests` | `url` per entry | `redact_context()` on each URL |
| `get_request` | `url`, `failure_text` | `redact_context()` on URL; `redact()` on failure_text |

### Already redacted (no change)

| Content | Current state |
|---|---|
| Request/response header values | Not exposed (P2: `header_names` keys only) |
| Response bodies | Not exposed (P2: excluded) |
| Navigate URL/params | Redacted by `SecurityManager.check_action()` (navigation-tier) |
| Action tool arguments | Redacted by `SecurityManager.check_action()` (action-tier) |

### Out of scope

- **Redaction of `screenshot` images.** Screenshots are visual; secret-detection
  in image content is a different problem (OCR + pattern matching). Deferred.
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
  contain `[REDACTED:type]` markers.
- **Disabling:** set `redaction_enabled=False` in the `SecurityConfig` passed to
  `run_server()` / `_build_default_security_manager()`. The MCP env-var path
  (`SB_MCP_REDACTION=0` or similar) can be added if operators need a simple
  toggle.
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
- `get_console_messages`: fixture with a token in console text → redacted
- `get_page_errors`: fixture with a secret in error message → redacted
- `list_requests`: fixture with a secret in URL query param → URL redacted
- `get_request`: fixture with a secret in failure_text → redacted
- `observe`: fixture with a secret in title → redacted

### Negative tests

- Non-secret text passes through unchanged (no false positives on normal prose)
- Redaction disabled → raw output (existing behavior)

## Implementation order (after design approval)

```text
1. Add _redact_inspect_output() helper in mcp_server.py
2. Wire into the 7 inspect-tier handlers (extract_text, observe, 5 diagnostics)
3. Add SB_MCP_REDACTION env toggle (optional, if operators need it)
4. Unit tests for the helper
5. Fixture tests per tool
6. CHANGELOG [Unreleased] — behavior change note
7. Verify: real-browser e2e with a test page that logs a fake API key
```

## Open questions for review

1. **Should `observe`'s URL be redacted?** The current page URL may contain
   secrets (e.g. `?token=...`). `redact_context()` handles this, but an agent
   needs the URL for navigation context. Recommendation: redact query params
   only (via `redact_context`), preserve the path/host.

2. **Should redaction be on by default in the MCP server?** The
   `SecurityConfig` default is `redaction_enabled=True`, and `_build_default_security_manager()`
   uses defaults. So yes, by default. But this is a behavior change — confirm
   this is acceptable.

3. **Console messages with stack traces.** Stack traces can contain file paths,
   line numbers, and variable values. Should only secret *patterns* be redacted
   (leaving paths/lines intact), or should stack traces be truncated? Recommendation:
   pattern-only (leave structure intact).
