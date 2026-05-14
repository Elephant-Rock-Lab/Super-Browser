# Agent Reliability

Super Browser v1.7.0 introduces structured result categories, automatic stale-ref recovery, and secret redaction — making it the most agent-friendly browser automation library.

## Result Categories

Every `ActionResult` now carries machine-readable categories so consuming agents can branch on enums instead of parsing prose.

### Success Categories

```python
from super_browser.results import SuccessCategory

class SuccessCategory(StrEnum):
    NAVIGATION = "navigation"    # Page navigated to new URL
    MUTATION = "mutation"        # DOM changed without navigation
    INSPECTION = "inspection"    # Read-only query (snapshot, eval)
    ARTIFACT = "artifact"        # Screenshot/download produced
    UNCHANGED = "unchanged"      # Action succeeded, no page change
```

### Failure Categories

```python
from super_browser.results import FailureCategory

# 13 values — strict superset of ErrorCategory:
# Original 8: TIMEOUT, SELECTOR_NOT_FOUND, NAVIGATION, SECURITY,
#             BROWSER_CRASH, VALIDATION, CONTEXT_OVERFLOW, UNKNOWN
# New 5:
STALE_REF        = "stale_ref"         # Element ref expired
ELEMENT_OBSCURED = "element_obscured"  # Element covered by overlay
FRAME_DETACHED   = "frame_detached"    # iframe removed during action
AUTH_REQUIRED    = "auth_required"     # Login/auth wall
RATE_LIMITED     = "rate_limited"      # Server returned 429
```

### Next Actions

Every failed action can include structured recovery guidance:

```python
result = await browser.click("@e5")
if not result.ok and result.failure_category == FailureCategory.STALE_REF:
    for action in result.next_actions:
        print(f"{action.action_id}: {action.description}")
    # refresh_snapshot: Re-run snapshot to refresh element refs
    # retry_with_selector: Retry click with fresh selector from new snapshot
    # fallback_to_coordinate: Fall back to coordinate-based click
```

## Page Change Summaries

After each action, the agent loop computes a lightweight page-change summary:

```python
from super_browser.results import PageChangeSummary, compute_page_change
from super_browser.results import PageFingerprint

before = PageFingerprint(url="https://x.com", title="X", node_count=42, interactive_count=5)
after = PageFingerprint(url="https://x.com/page2", title="Page 2", node_count=38, interactive_count=4)

summary = compute_page_change(before, after)
# PageChangeSummary(change_type="navigation", summary="Navigated to https://x.com/page2",
#                   title="Page 2", url="https://x.com/page2")
```

The `change_type` is one of:
- `"navigation"` — URL changed
- `"mutation"` — DOM changed without navigation
- `"unchanged"` — No observable change

## Stale Reference Recovery

The #1 agent failure mode is stale element references — the agent targets `@e5` but the page re-rendered and the ref is gone. Super Browser now handles this automatically:

1. **Detection**: 8 error signatures are recognized as stale refs
2. **Auto-retry**: The controller refreshes the accessibility snapshot and retries the cascade
3. **Structured failure**: If retry also fails, the result includes `FailureCategory.STALE_REF` and 3 `NextAction` hints

```python
from super_browser.interaction.recovery import StaleRefDetector

# Check if an error is a stale ref
StaleRefDetector.is_stale(Exception("waiting for selector"))  # True
StaleRefDetector.is_stale(Exception("Network error"))         # False

# Get recovery guidance
actions = StaleRefDetector.get_next_actions("click", "@e5")
# [NextAction(action_id="refresh_snapshot", ...),
#  NextAction(action_id="retry_with_selector", ...),
#  NextAction(action_id="fallback_to_coordinate", ...)]
```

## Secret Redaction

### Automatic Redaction

Configure once at startup, then all `ActionResult.to_dict()` output is automatically redacted:

```python
from super_browser.security import configure_redaction
from super_browser.security.types import SecurityConfig

configure_redaction(SecurityConfig())

result = await browser.fill("#password", "my-secret-password")
data = result.to_dict()
# data["data"]["password"] == "[REDACTED:password]"
```

### Manual Redaction

```python
from super_browser.security import redact_args, redact_context

# Redact action parameters
redact_args({"username": "alice", "password": "secret"})
# {"username": "alice", "password": "[REDACTED:password]"}

# Redact URLs with sensitive query params
redact_context("https://api.example.com?token=abc123&user=alice")
# "https://api.example.com?token=[REDACTED:query_param]&user=alice"
```

### How It Works

`redact_args()` uses a two-pass algorithm:
1. **Key-name matching**: 20+ sensitive key patterns (password, token, api_key, secret, auth, cookie, etc.)
2. **Value-pattern matching**: Leverages the existing `SecretRedactor` with 40+ regex patterns (API keys, JWTs, database URLs, etc.)

`redact_context()` is a standalone URL scrubber that identifies sensitive query parameters by key name.

## Action Presets

### BrowserJob — Declarative Step Sequences

```python
from super_browser.interaction.presets import BrowserJob

job = BrowserJob(steps=[
    {"action": "open", "url": "https://example.com"},
    {"action": "assert_text", "text": "Example Domain"},
    {"action": "fill", "target": "#search", "value": "test"},
    {"action": "click", "target": "#submit"},
    {"action": "screenshot", "path": "result.png"},
], name="search_test")

compiled = job.compile()
# [CompiledStep(action="open", params={"url": "..."}, description="..."), ...]
```

### QASmoke — Diagnostic Smoke Test

```python
from super_browser.interaction.presets import QASmoke

qa = QASmoke(url="https://example.com", assert_text="Example")
compiled = qa.compile()
# 5 steps: open → wait(2s) → assert_text → network_check → screenshot
```

## Agent Efficiency Benchmark

```bash
python scripts/agent_efficiency_benchmark.py --json report.json --md report.md
python scripts/agent_efficiency_benchmark.py --compare baseline.json
```

The benchmark measures 4 representative workflows:
- **navigate_and_extract**: navigate → observe → extract → screenshot
- **form_fill**: navigate → fill → fill → click → assert
- **qa_smoke**: open → wait → assert → network → screenshot
- **error_recovery**: stale click → retry → success click → verify

Metrics: call count, output bytes, stale-ref rate, category distribution.
