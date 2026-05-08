# Session Recording

> Record, save, replay, and audit browser sessions.

Super Browser v1.3 introduces session recording: capture every browser action (navigate, click, fill, scroll, extract) into a structured JSON file, then replay it later or generate HTML audit reports.

---

## Quick Example

```python
import asyncio
from super_browser import SuperBrowser
from super_browser.testing import MockLLMClient

async def main():
    sb = SuperBrowser(llm_client=MockLLMClient())
    await sb.start()

    # Enable recording
    sb.enable_recording()

    # Perform actions — all are captured
    await sb.navigate("https://example.com")
    await sb.click("a")
    await sb.extract("page heading", selector="h1")

    # Stop and save
    recorder = sb.recording
    session = recorder.stop()
    recorder.save("my_session.json")  # or use persistence module directly

    await sb.stop()

asyncio.run(main())
```

---

## Enabling Recording

### On a SuperBrowser Instance

```python
sb = SuperBrowser(llm_client=MockLLMClient())
await sb.start()

# Enable with default settings
sb.enable_recording()

# Or with a screenshot limit
sb.enable_recording(max_screenshots=50)
```

Recording subscribes to all lifecycle events on the internal `EventBus`:
- `before_navigate`, `after_navigate`
- `before_action`, `after_action`
- `on_error`

### Access the Recorder

```python
recorder = sb.recording  # Returns SessionRecorder or None
```

---

## Recording Data

Each recorded session contains an ordered list of `ActionRecord` entries:

```json
{
  "session_id": "a1b2c3d4...",
  "started_at": 1715136000.0,
  "schema_version": "1.0",
  "actions": [
    {
      "index": 0,
      "timestamp": 1715136001.0,
      "action": "before_navigate",
      "params": {"url": "https://example.com", "action": "navigate", "step": 1},
      "url": "https://example.com",
      "title": "",
      "ok": true,
      "duration_ms": 0.0
    }
  ],
  "metadata": {
    "action_count": 1,
    "error_count": 0,
    "duration_ms": 1500.0,
    "schema_version": "1.0"
  }
}
```

### ActionRecord Fields

| Field | Type | Description |
|-------|------|-------------|
| `index` | `int` | Sequential action number |
| `timestamp` | `float` | `time.monotonic()` value |
| `action` | `str` | Event type or action name |
| `params` | `dict` | Event context (sensitive values redacted) |
| `url` | `str` | Page URL at time of action |
| `title` | `str` | Page title |
| `screenshot_before` | `str \| None` | Base64 JPEG (if CDP available) |
| `screenshot_after` | `str \| None` | Base64 JPEG (if CDP available) |
| `ok` | `bool` | Whether the action succeeded |
| `error` | `str \| None` | Error message if failed |
| `duration_ms` | `float` | Action duration in milliseconds |

---

## Saving & Loading

### Using the Persistence Module

```python
from super_browser.recording.persistence import save, load

# Save a recording session to disk
save(session, "recordings/my_session.json")

# Load a recording from disk
session = load("recordings/my_session.json")
print(f"Loaded {len(session.actions)} actions")
```

The `save()` function creates parent directories automatically. The `load()` function raises `FileNotFoundError` if the file doesn't exist or `ValueError` if the JSON is not a valid recording.

### Using the Recorder

```python
recorder = sb.recording
json_str = recorder.export_json()  # Get JSON string without saving
```

---

## Replaying Recordings

### Via SuperBrowser

```python
sb = SuperBrowser(llm_client=MockLLMClient())
await sb.start()

# Replay a saved recording
result = await sb.replay("recordings/my_session.json", delay_ms=100)

if result.ok:
    report = result.data
    print(f"Total actions: {report.total_actions}")
    print(f"Matched: {report.matched}")
    print(f"Mismatches: {len(report.mismatches)}")
    print(f"Duration: {report.duration_ms:.0f}ms")
```

### Via RecordingReplayer

```python
from super_browser.recording.replayer import RecordingReplayer
from super_browser.recording.persistence import load

recording = load("recordings/my_session.json")
replayer = RecordingReplayer(sb)
report = await replayer.replay(recording, delay_ms=50)
```

### ReplayReport

| Field | Type | Description |
|-------|------|-------------|
| `total_actions` | `int` | Number of actions replayed |
| `matched` | `int` | Actions that matched the original |
| `mismatches` | `list[MismatchRecord]` | Actions that differed |
| `duration_ms` | `float` | Total replay duration |

### Mismatch Detection

The replayer compares each action's result against the original recording:

- **OK status mismatch** — Original succeeded but replay failed
- **URL mismatch** — Navigated to a different URL than recorded

```python
for mismatch in report.mismatches:
    print(f"Step {mismatch.index}: {mismatch.reason}")
    print(f"  Expected: {mismatch.expected}")
    print(f"  Actual: {mismatch.actual}")
```

---

## HTML Audit Reports

Generate a self-contained HTML report from any recording:

```python
from super_browser.recording.report import export_html, save_html

# Get HTML string
html = export_html(session)

# Or save directly to file
save_html(session, "reports/session_report.html")
```

The HTML report includes:
- Session metadata (ID, duration, action/error counts)
- Action table with timestamps, params, URLs, and status
- Color-coded status indicators (green = OK, red = FAIL)

---

## Security

### Sensitive Value Redaction

Recorded parameters are automatically filtered to remove credentials:

```python
# These keys are always redacted: api_key, token, secret, password,
# credential, authorization, cookie, session_id
```

Example:

```python
bus.emit("before_action", {"action": "fill", "target": "#password", "password": "s3cret"})
# Recorded as: {"action": "fill", "target": "#password", "password": "[REDACTED]"}
```

### Screenshot Capture Failures

Screenshot capture failures never block the recording (HB-23-02). If CDP is unavailable or the screenshot limit is reached, recordings continue without screenshots.

---

## CLI Script Mode

When running scripts via the CLI, recording can be enabled programmatically:

```python
from super_browser.cli.script import run_script

# Run a YAML script — actions are recorded if recording is enabled
results = await run_script("scripts/my_task.yaml", output_path="results.json")
```

---

## API Reference

### `SessionRecorder(event_bus, cdp_bridge=None, *, max_screenshots=100)`

| Method | Description |
|--------|-------------|
| `start()` | Begin recording (subscribe to lifecycle events) |
| `stop() → RecordingSession` | Stop recording and return the session |
| `export_json() → str` | Export recording as JSON string |

### `save(recording, path) → None`

Write a `RecordingSession` to a JSON file.

### `load(path) → RecordingSession`

Load a `RecordingSession` from a JSON file.

### `RecordingReplayer(sb)`

| Method | Description |
|--------|-------------|
| `replay(recording, *, delay_ms=100) → ReplayReport` | Replay all actions and return a report |

### `export_html(recording) → str`

Generate an HTML audit report string.

### `save_html(recording, path) → None`

Write an HTML audit report to a file.
