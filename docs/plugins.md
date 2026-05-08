# Plugins & Hooks

> Extend Super Browser with custom lifecycle hooks, event handlers, and tools.

Super Browser v1.3 introduces a plugin system built on top of the `EventBus`. You can hook into browser lifecycle events using decorators or programmatic registration.

---

## Quick Example

```python
from super_browser.plugins import hook

@hook("before_navigate")
def log_navigation(ctx):
    print(f"About to navigate to: {ctx['url']}")

@hook("after_action")
def track_performance(ctx):
    print(f"Action: {ctx['action']} took {ctx.get('duration_ms', 0):.0f}ms")
```

That's it — when a `SuperBrowser` instance starts, all globally registered hooks are automatically installed on its internal `EventBus`.

---

## Lifecycle Events

Seven lifecycle event types are available:

| Event | Context Keys | When Fired |
|-------|-------------|------------|
| `before_navigate` | `url` | Before a navigation begins |
| `after_navigate` | `url`, `final_url`, `title`, `ok` | After navigation completes |
| `before_action` | `action`, `target`, `step` | Before any browser action |
| `after_action` | `action`, `target`, `step`, `ok`, `duration_ms` | After any browser action completes |
| `on_error` | `action`, `error`, `category`, `step` | When an error occurs |
| `on_loop_detected` | `level`, `message`, `repetition_count`, `repeated_action` | When the agent loop detects repetition |
| `on_budget_alert` | `level`, `usage_pct`, `remaining` | When budget thresholds are crossed |

---

## The `@hook()` Decorator

The primary way to register hooks. Import and use at module level:

```python
from super_browser.plugins import hook

@hook("after_navigate")
def on_page_loaded(ctx):
    """Fires after every navigation."""
    if ctx.get("ok"):
        print(f"✓ Loaded: {ctx['title']}")
    else:
        print(f"✗ Failed: {ctx.get('url')}")
```

### Multiple Hooks on the Same Event

You can register multiple handlers for the same event:

```python
@hook("after_action")
def log_to_console(ctx):
    print(f"[{ctx['action']}] ok={ctx['ok']}")

@hook("after_action")
def log_to_file(ctx):
    with open("audit.log", "a") as f:
        f.write(f"{ctx}\n")
```

### Hook for Multiple Events

Register the same function on different events:

```python
@hook("before_navigate")
@hook("after_navigate")
def track_nav_timing(ctx):
    # Track both start and end of navigations
    pass
```

---

## Programmatic Registration

If you need to register hooks dynamically (e.g., inside a function or class):

```python
from super_browser.plugins import register_hook

def my_handler(ctx):
    print(f"Event: {ctx}")

# Register at runtime
register_hook("after_action", my_handler)
```

### Listing Registered Hooks

```python
from super_browser.plugins import get_registered_hooks

hooks = get_registered_hooks()
for event_type, handlers in hooks.items():
    print(f"{event_type}: {len(handlers)} handler(s)")
```

---

## Using `sb.event_bus` Directly

For advanced use cases, access the `EventBus` directly on a `SuperBrowser` instance:

```python
from super_browser import SuperBrowser
from super_browser.testing import MockLLMClient

sb = SuperBrowser(llm_client=MockLLMClient())
await sb.start()

# Access the event bus
bus = sb.event_bus

# Subscribe with an async handler
async def async_handler(ctx):
    await some_async_operation(ctx)

bus.subscribe("after_navigate", async_handler)

# Emit custom events
bus.emit("after_navigate", {"url": "https://example.com", "ok": True})

# Unsubscribe when done
sub_id = bus.subscribe("on_error", error_handler)
# ... later ...
bus.unsubscribe(sub_id)
```

### Sync vs Async Handlers

The `EventBus` supports both sync and async handlers:

- `bus.emit()` — Calls handlers synchronously. Async handlers receive a warning.
- `await bus.emit_async()` — Properly awaits async handlers.

---

## Custom Tools via Plugin Hooks

Combine hooks with the tool registry to add custom browser tools:

```python
from super_browser import SuperBrowser
from super_browser.plugins import hook

# Track analytics for all actions
@hook("after_action")
def analytics_tracker(ctx):
    """Send action metrics to your analytics service."""
    metrics = {
        "action": ctx.get("action"),
        "ok": ctx.get("ok"),
        "duration_ms": ctx.get("duration_ms"),
    }
    # Send to your analytics endpoint
    print(f"[Analytics] {metrics}")

# Register a custom tool on the browser
def custom_scroll_tool(direction: str, pixels: int = 500) -> dict:
    """Scroll the page in a direction by a number of pixels."""
    return {"scrolled": direction, "pixels": pixels}

sb = SuperBrowser()
sb.register_tool(custom_scroll_tool, toolsets=("navigation",))
```

---

## Event Bus Guarantees

1. **Never raises** — `emit()` catches all handler exceptions and logs them. Your hook cannot crash the browser session.
2. **Read-only context** — The context dict passed to handlers is frozen (`MappingProxyType`). Handlers cannot mutate it.
3. **Order** — Handlers are called in registration order.
4. **Thread-safe** — The EventBus is designed for single-thread async usage.

---

## API Reference

### `hook(event_type: str) → Callable`

Decorator that registers a function as a lifecycle hook handler.

### `register_hook(event_type: str, handler: Handler) → None`

Programmatically register a handler for an event type.

### `get_registered_hooks() → dict[str, list[Handler]]`

Return a shallow copy of the global hook registry.

### `EventBus.subscribe(event_type: str, handler: Handler) → str`

Subscribe to an event on a specific bus instance. Returns a subscription ID.

### `EventBus.unsubscribe(subscription_id: str) → None`

Remove a handler by its subscription ID.

### `EventBus.emit(event_type: str, context: dict) → None`

Emit an event synchronously. Never raises.

### `EventBus.emit_async(event_type: str, context: dict) → None`

Emit an event asynchronously, properly awaiting async handlers.
