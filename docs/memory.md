# Memory Store

> Per-domain memory persistence for browser automation tasks.

Super Browser v1.3 introduces a memory system that persists successful action sequences, working CSS selectors, and site preferences per domain. Memory is **opt-in** and designed to speed up repeated tasks on the same sites.

---

## Quick Example

```python
from super_browser import SuperBrowser
from super_browser.testing import MockLLMClient

sb = SuperBrowser(llm_client=MockLLMClient())
await sb.start()

# Enable memory (opt-in)
sb.enable_memory(memory_dir="~/.config/super-browser/memory", ttl_days=30)

# Use the browser — successful tasks are automatically recorded
await sb.navigate("https://shop.example.com")
await sb.click("#add-to-cart")

# Access the memory store
store = sb.memory
context = store.get_context_for_prompt("shop.example.com")
print(context)
# Previous successful action sequences on this domain:
#   - Task: Add item to cart | Actions: navigate, click
```

---

## Enabling Memory

### On a SuperBrowser Instance

```python
sb = SuperBrowser(llm_client=MockLLMClient())
await sb.start()

# Enable with default settings (30-day TTL)
sb.enable_memory()

# Or with custom settings
sb.enable_memory(
    memory_dir="~/.config/super-browser/memory",
    ttl_days=14,
)
```

Memory is **opt-in** (HB-25-01). It does nothing until you call `enable_memory()`.

### Access the Store

```python
store = sb.memory  # Returns MemoryStore or None
```

---

## What Gets Stored

Memory stores three types of information per domain:

### 1. Action Sequences

Successful task sequences — what actions were taken to complete a task:

```python
store.record_sequence(
    domain="shop.example.com",
    task="Add item to cart",
    actions=[
        {"action": "navigate", "url": "https://shop.example.com/product/123"},
        {"action": "click", "target": "#add-to-cart"},
        {"action": "fill", "target": "#qty", "value": "2"},
    ],
    success=True,  # Only successful sequences are stored
)
```

### 2. CSS Selectors

Working CSS selectors for specific elements:

```python
store.record_selector("shop.example.com", "Add to Cart Button", "#add-to-cart")
store.record_selector("shop.example.com", "Search Input", "#search-q")
```

### 3. Preferences

Site-specific preferences:

```python
memory = store.load("shop.example.com")
memory.preferences["currency"] = "USD"
memory.preferences["language"] = "en"
store.save("shop.example.com", memory)
```

---

## Memory File Format

Memory is stored as JSON at `<memory_dir>/<domain>.json`:

```json
{
  "domain": "shop.example.com",
  "sequences": [
    {
      "task": "Add item to cart",
      "actions": [
        {"action": "navigate", "url": "https://shop.example.com/product/123"},
        {"action": "click", "target": "#add-to-cart"}
      ],
      "success": true,
      "created_at": 1715136000.0,
      "used_count": 0
    }
  ],
  "selectors": {
    "Add to Cart Button": "#add-to-cart",
    "Search Input": "#search-q"
  },
  "preferences": {
    "currency": "USD"
  },
  "created_at": 1715136000.0,
  "updated_at": 1715140000.0
}
```

---

## Loading & Querying

### Load Domain Memory

```python
memory = store.load("shop.example.com")
print(f"Sequences: {len(memory.sequences)}")
print(f"Selectors: {memory.selectors}")
```

If no memory file exists, returns an empty `DomainMemory` without errors.

### List All Domains

```python
domains = store.list_domains()
# ["shop.example.com", "docs.python.org", "github.com"]
```

### Get Context for LLM Prompts

The primary use case — inject memory context into your agent's prompt:

```python
context = store.get_context_for_prompt("shop.example.com")
```

Output example:

```
Previous successful action sequences on this domain:
  - Task: Add item to cart | Actions: navigate, click, fill

Working CSS selectors on this domain:
  - Add to Cart Button: #add-to-cart
  - Search Input: #search-q

Known preferences for this domain:
  - currency: USD
  - language: en
```

### Integration with Agent Loop

When memory is enabled, `SuperBrowser.act()` automatically:
1. Loads memory for the current domain before each task
2. Injects context into the LLM prompt
3. Saves successful sequences after task completion

---

## TTL Pruning

Memory entries expire after the configured TTL (default 30 days):

```python
# Prune expired entries across all domains
removed = store.prune()
print(f"Removed {removed} expired sequences")
```

Expired action sequences are removed. If a domain has no remaining data, its file is deleted.

---

## Clearing Memory

### Clear a Single Domain

```python
store.clear("shop.example.com")
```

### Clear All Memory

```python
for domain in store.list_domains():
    store.clear(domain)
```

---

## CLI Commands

Memory can be managed from the command line:

```bash
# List all domains with stored memory
super-browser memory list

# Show memory for a specific domain
super-browser memory show shop.example.com

# Clear memory for a domain
super-browser memory clear shop.example.com

# Prune expired entries
super-browser memory prune
```

---

## Security

### Credential Filtering

Sensitive field values are automatically redacted before storage:

```python
# These patterns are redacted: api_key, password, secret, token,
# auth, credential, private_key
store.record_sequence(
    "example.com",
    "Login",
    [{"action": "fill", "target": "#password", "password": "s3cret123"}],
    success=True,
)
# Stored as: {"action": "fill", "target": "#password", "password": "***REDACTED***"}
```

### Failed Sequences Not Saved

Only **successful** task sequences are persisted. This prevents the agent from learning from failures:

```python
store.record_sequence("example.com", "Login", actions, success=False)
# Nothing is saved — the method returns immediately
```

---

## API Reference

### `MemoryStore(memory_dir: Path, ttl_days: int = 30)`

| Method | Description |
|--------|-------------|
| `save(domain, memory) → None` | Persist domain memory to disk |
| `load(domain) → DomainMemory` | Load domain memory (empty if not found) |
| `list_domains() → list[str]` | List domains with stored memory |
| `clear(domain) → None` | Delete memory for a domain |
| `prune() → int` | Remove expired entries, return count removed |
| `record_sequence(domain, task, actions, success) → None` | Record an action sequence |
| `record_selector(domain, element, selector) → None` | Record a working CSS selector |
| `get_context_for_prompt(domain) → str` | Generate LLM prompt context |

### `DomainMemory`

| Field | Type | Description |
|-------|------|-------------|
| `domain` | `str` | Domain name |
| `sequences` | `list[ActionSequence]` | Recorded action sequences |
| `selectors` | `dict[str, str]` | Element → CSS selector mappings |
| `preferences` | `dict[str, Any]` | Site-specific preferences |
| `created_at` | `float` | Creation timestamp |
| `updated_at` | `float` | Last update timestamp |

### `ActionSequence`

| Field | Type | Description |
|-------|------|-------------|
| `task` | `str` | Task description |
| `actions` | `list[dict]` | List of action dicts |
| `success` | `bool` | Whether the task succeeded |
| `created_at` | `float` | Creation timestamp |
| `used_count` | `int` | Times this sequence was reused |
