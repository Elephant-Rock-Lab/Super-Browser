# E2B (SRC-064) -- SUPER-BROWSER Gap Analysis

> **Source**: `C:\Next AI\ref\E2B-main`
> **Type**: TypeScript/Python sandboxed execution platform
> **Version**: JS SDK 2.19.0, Python SDK 2.20.0, CLI 2.9.0
> **License**: MIT
> **Date**: 2026-04-23

---

## 1. Executive Summary

E2B is a production-grade, cloud-native sandboxed execution platform for AI agents. It provides secure, isolated cloud environments (sandboxes) that AI agents can programmatically create, control, and tear down. The system is built on a **three-layer architecture**: (1) a cloud orchestration API (OpenAPI/REST), (2) an in-sandbox daemon called **envd** communicating via ConnectRPC/protobuf, and (3) dual SDKs (TypeScript + Python) that expose a clean facade over both layers.

The repository contains the **SDK layer and CLI tooling** only -- the actual sandbox infrastructure (container orchestration, Firecracker VMs, networking) lives in a separate `e2b-dev/infra` repo.

### Key Architectural Patterns Extracted

1. **Session-oriented sandbox lifecycle** -- create, pause, resume, snapshot, kill
2. **Process isolation via gRPC streaming** -- envd exposes Process and Filesystem services via protobuf
3. **Token-based access control** -- envd access tokens, traffic tokens, HMAC-signed file URLs
4. **Network policy enforcement** -- allow/deny CIDR outbound rules, public traffic toggle
5. **Dual sync/async SDK surface** -- identical API shape in both modes (Python) or single Promise-based API (JS)
6. **Template/Dockerfile build system** -- custom Dockerfile + TOML config for sandbox images
7. **MCP server integration** -- Model Context Protocol gateway for agent tool access

---

## 2. Subsystem Catalog

| # | Subsystem | Location | Description |
|---|-----------|----------|-------------|
| S1 | **JS SDK Core** | `packages/js-sdk/src/sandbox/` | Sandbox class, filesystem, commands, PTY, git, network, MCP |
| S2 | **Python SDK Core** | `packages/python-sdk/e2b/sandbox_async/`, `sandbox_sync/` | AsyncSandbox + Sandbox with commands, filesystem, git, PTY |
| S3 | **envd Protocol (Protobuf)** | `spec/envd/` | ConnectRPC service definitions for Process and Filesystem |
| S4 | **envd RPC Transport** | `packages/*/src/envd/` | ConnectRPC client transport, authentication headers, error mapping |
| S5 | **API Client (REST/OpenAPI)** | `packages/*/src/api/`, `packages/python-sdk/e2b/api/client/` | Auto-generated OpenAPI client for sandbox CRUD, templates, volumes |
| S6 | **Connection Config** | `packages/*/src/connectionConfig.ts`, `connection_config.py` | API key, domain, proxy, request timeout, debug mode |
| S7 | **Signature/URL Auth** | `packages/*/src/sandbox/signature.*` | HMAC-SHA256 signed file download/upload URLs |
| S8 | **CLI** | `packages/cli/src/` | Auth, sandbox CRUD, template build, exec |
| S9 | **Template Build System** | `packages/cli/src/commands/template/`, `templates/` | Dockerfile + TOML template definition, build/publish pipeline |
| S10 | **Volume System** | `packages/*/src/volume/` | Persistent volume creation, mount, file CRUD |
| S11 | **MCP Integration** | `packages/*/src/sandbox/mcp.*` | MCP gateway configuration, 130+ pre-built MCP server types |
| S12 | **Exception/Error Taxonomy** | `packages/*/src/errors.*`, `exceptions.py` | Structured error hierarchy with gRPC-to-domain mapping |
| S13 | **Paginator** | `packages/*/src/sandbox/sandboxApi.*` | Cursor-based pagination for sandbox/snapshot listing |

---

## 3. Scoring (D1-D4)

### D1: Production Readiness (weight 0.30)

| Criterion | Score | Evidence |
|-----------|-------|----------|
| Test coverage | **8/10** | Integration tests, runtime tests (browser/bun/deno), vitest+pytest |
| Error handling | **9/10** | Comprehensive exception hierarchy, gRPC code mapping, HTTP status mapping, typed errors |
| API stability | **9/10** | v2.x, typed API surface, OpenAPI codegen, versioned envd with feature flags |
| Documentation | **7/10** | Good docstrings, CLAUDE.md, but no inline architecture docs |
| CI/CD | **7/10** | GitHub workflows present, changeset-based versioning |

**D1 = 8.0 / 10**

### D2: Novelty (weight 0.20)

| Criterion | Score | Evidence |
|-----------|-------|----------|
| Architecture | **7/10** | Three-layer (API -> envd -> SDK) is well-executed but not novel |
| Protocol design | **8/10** | ConnectRPC/protobuf for in-sandbox control with streaming is a strong choice |
| Sandbox-as-session | **8/10** | Pause/resume/snapshot lifecycle is well beyond typical container APIs |
| MCP integration | **9/10** | 130+ pre-typed MCP server configs with gateway process is highly novel |
| Token-signed URLs | **7/10** | HMAC file URL signing is solid but established pattern |

**D2 = 7.8 / 10**

### D3: Composability (weight 0.25)

| Criterion | Score | Evidence |
|-----------|-------|----------|
| SDK surface | **9/10** | Property-based modules (files, commands, pty, git) compose naturally |
| Template system | **9/10** | Dockerfile + TOML allows arbitrary sandbox images |
| Volume mounts | **8/10** | Persistent volumes mountable at arbitrary paths |
| Network config | **8/10** | CIDR allow/deny rules compose with public traffic toggle |
| Dual-language parity | **9/10** | JS and Python SDKs expose identical API shapes |

**D3 = 8.6 / 10**

### D4: Depth (weight 0.25)

| Criterion | Score | Evidence |
|-----------|-------|----------|
| Process management | **9/10** | Start, connect, list, kill, signal, stdin/stdout/stderr streaming, PTY resize |
| Filesystem ops | **8/10** | Read/write/list/stat/move/remove/mkdir/watch with user impersonation |
| Security | **8/10** | Access tokens, HMAC signatures, network policies, user isolation |
| Lifecycle | **9/10** | Create/pause/resume/snapshot/kill with auto-resume and timeout management |
| Observability | **7/10** | Metrics (CPU/mem/disk), logs API, but no distributed tracing |

**D4 = 8.2 / 10**

### Weighted Composite

| Dimension | Weight | Score | Weighted |
|-----------|--------|-------|----------|
| D1 Production | 0.30 | 8.0 | 2.40 |
| D2 Novelty | 0.20 | 7.8 | 1.56 |
| D3 Composability | 0.25 | 8.6 | 2.15 |
| D4 Depth | 0.25 | 8.2 | 2.05 |
| **Total** | **1.00** | | **8.16 / 10** |

---

## 4. Tier Classification

| Subsystem | Tier | Rationale |
|-----------|------|-----------|
| S1 JS SDK Core | **Tier 1** | Directly reusable facade pattern for SUPER-BROWSER agent orchestration |
| S2 Python SDK Core | **Tier 1** | Primary reference for Python SDK architecture -- class hierarchy, module decomposition |
| S3 envd Protocol | **Tier 1** | Protobuf service definitions are the gold standard for in-sandbox control plane |
| S4 envd RPC Transport | **Tier 1** | gRPC error mapping, auth headers, streaming -- directly applicable to CDP transport |
| S5 API Client | **Tier 2** | OpenAPI codegen pattern is useful but the specific API surface is E2B-specific |
| S6 Connection Config | **Tier 2** | Config management pattern is solid and reusable |
| S7 Signature/URL Auth | **Tier 1** | HMAC signing pattern directly applicable to SUPER-BROWSER secure file access |
| S8 CLI | **Tier 3** | CLI commands are E2B-specific, not relevant to browser automation |
| S9 Template Build | **Tier 2** | Dockerfile + config pattern useful for browser profile templates |
| S10 Volume System | **Tier 2** | Persistent storage pattern applicable to browser profile persistence |
| S11 MCP Integration | **Tier 2** | MCP gateway concept maps to browser tool orchestration but is secondary |
| S12 Error Taxonomy | **Tier 1** | Error hierarchy design is directly transferable |
| S13 Paginator | **Tier 3** | Utility, not critical |

---

## 5. Gap Mapping -- E2B Patterns to SUPER-BROWSER

### Gap #10: Security Envelope -- Sandboxing, Permissions (PRIMARY MATCH)

**Relevance: 9/10 -- E2B is the strongest reference for this gap.**

E2B's entire architecture IS a security envelope. The extractable patterns are:

| E2B Pattern | SUPER-BROWSER Adaptation |
|-------------|--------------------------|
| **Token-based envd access** (`envd_access_token`, `X-Access-Token` header) | Each browser session gets a scoped access token; all CDP/WebSocket communication requires it |
| **HMAC-SHA256 signed URLs** (`signature.py` -- `v1_` prefix + base64(SHA256(path:op:user:token[:exp]))` | Generate time-limited signed URLs for browser screenshot streams, file downloads from sandbox |
| **Network policy enforcement** (`SandboxNetworkOpts` -- allow_out/deny_out CIDR lists) | Browser sessions can be restricted to specific domains or IP ranges; deny_out blocks tracker/ad networks |
| **User isolation** (per-operation `user` param, default user vs root) | Browser actions execute under scoped permissions; file downloads run as restricted user |
| **`secure=True` default** (sandbox creation enforces auth) | Browser sessions default to secure mode with authenticated CDP connections |
| **`allow_internet_access=False` option** | Browser can be locked to intranet/offline mode for sensitive operations |
| **`allow_public_traffic` toggle** | Control whether browser debug URLs are publicly accessible or auth-gated |

**Key Code Reference** -- Token signing (`signature.py`):
```python
raw = f"{path}:{operation}:{user}:{envd_access_token}:{expiration}"
digest = hashlib.sha256(raw.encode("utf-8")).digest()
encoded = base64.b64encode(digest).rstrip(b"=").decode("ascii")
return {"signature": f"v1_{encoded}", "expiration": expiration}
```

**Key Code Reference** -- Network policy (`sandbox_api.py`):
```python
class SandboxNetworkOpts(TypedDict):
    allow_out: NotRequired[List[str]]   # CIDR allowlist
    deny_out: NotRequired[List[str]]    # CIDR denylist
    allow_public_traffic: NotRequired[bool]
    mask_request_host: NotRequired[str]
```

**Key Code Reference** -- Error-based permission enforcement (`rpc.py`):
```python
_DEFAULT_RPC_ERROR_MAP = {
    Code.unauthenticated: AuthenticationException,
    Code.permission_denied: ...,
    Code.resource_exhausted: RateLimitException,
}
```

### Gap #4: Self-Healing & Session Recovery (STRONG MATCH)

**Relevance: 8/10**

E2B's sandbox lifecycle management provides a direct blueprint for browser session recovery:

| E2B Pattern | SUPER-BROWSER Adaptation |
|-------------|--------------------------|
| **Pause/Resume** (`post_sandboxes_sandbox_id_pause`, `post_sandboxes_sandbox_id_connect`) | Browser session can be paused (browser remains alive but inactive), resumed on reconnect |
| **Snapshot system** (`create_snapshot`, `SnapshotInfo`) | Save complete browser state (cookies, localStorage, DOM) as a restorable snapshot; create new sessions from snapshots |
| **Auto-resume** (`SandboxLifecycle.auto_resume`) | When a paused browser session receives a request, auto-resume it without manual intervention |
| **Timeout management** (`set_timeout`, `SandboxLifecycle.on_timeout`) | Browser sessions auto-expire after inactivity; choose kill vs pause behavior |
| **Connection recovery** (`Sandbox.connect()` -- reconnects by ID) | Reconnect to browser session by session ID from any process/machine |
| **Health checking** (`is_running()` -- GET `/health` endpoint) | Periodic health check for browser process; detect crashed sessions |
| **Version-gated features** (`envd_version` checks) | Feature capability detection -- graceful degradation when browser version lacks features |

**Key Code Reference** -- Lifecycle config:
```python
class SandboxLifecycle(TypedDict):
    on_timeout: Literal["pause", "kill"]
    auto_resume: NotRequired[bool]  # Activity triggers resume
```

**Key Code Reference** -- Connect (resume) flow:
```python
res = await post_sandboxes_sandbox_id_connect.asyncio_detailed(
    sandbox_id, body=ConnectSandbox(timeout=timeout))
# Returns fresh envd_access_token + domain for reconnection
```

### Gap #7: Agent Orchestration & Facade (STRONG MATCH)

**Relevance: 8/10**

E2B's SDK facade pattern is a textbook example of how to expose a complex multi-layer system through a clean agent interface:

| E2B Pattern | SUPER-BROWSER Adaptation |
|-------------|--------------------------|
| **Property-based module decomposition** (`sandbox.files`, `sandbox.commands`, `sandbox.pty`, `sandbox.git`) | Browser facade exposes `browser.page`, `browser.network`, `browser.dom`, `browser.interaction` as property modules |
| **Base class hierarchy** (`SandboxBase` -> `SandboxApi` -> `AsyncSandbox`) | BrowserBase -> BrowserApi -> Browser with shared config, lifecycle, and module initialization |
| **Class method variants** (`@class_method_variant` decorator) | Allow both instance and static usage: `browser.navigate(url)` and `Browser.navigate(session_id, url)` |
| **Connection config propagation** | All modules receive shared `ConnectionConfig` -- browser modules share auth, proxy, timeout settings |
| **Dual sync/async** (identical API shape) | Offer both sync and async browser interfaces for different use cases |
| **Context manager** (`async with AsyncSandbox.create() as sb:`) | `async with BrowserSession.create() as browser:` for automatic cleanup |
| **Paginator pattern** (cursor-based listing) | List browser sessions, list snapshots, list actions with pagination |

**Key Code Reference** -- Module facade pattern:
```python
class AsyncSandbox(SandboxApi):
    @property
    def files(self) -> Filesystem: return self._filesystem
    @property
    def commands(self) -> Commands: return self._commands
    @property
    def pty(self) -> Pty: return self._pty
    @property
    def git(self) -> Git: return self._git
```

**Key Code Reference** -- Constructor initialization:
```python
def __init__(self, **opts):
    super().__init__(**opts)
    self._transport = get_transport(self.connection_config)
    self._envd_api = httpx.AsyncClient(...)
    self._filesystem = Filesystem(envd_api_url, envd_version, ...)
    self._commands = Commands(envd_api_url, connection_config, ...)
    self._pty = Pty(envd_api_url, connection_config, ...)
    self._git = Git(self._commands)  # Git composes over Commands
```

### Gap #11: Tracing & Observability (MODERATE MATCH)

**Relevance: 6/10**

| E2B Pattern | SUPER-BROWSER Adaptation |
|-------------|--------------------------|
| **Metrics API** (`get_metrics` -- CPU/mem/disk time series) | Browser resource metrics: tab memory, JS heap, network bytes, rendering FPS |
| **Sandbox logs** (`get_sandboxes_sandbox_id_logs`) | Structured action logs per browser session |
| **RPC logger interceptor** (`createRpcLogger` in JS SDK) | Intercept all CDP commands for tracing -- log request/response pairs |
| **Keepalive ping headers** (`KEEPALIVE_PING_INTERVAL_SEC = 50`) | WebSocket keepalive for browser session liveness |

### Gap #12: Structured Action Results (MODERATE MATCH)

**Relevance: 7/10**

| E2B Pattern | SUPER-BROWSER Adaptation |
|-------------|--------------------------|
| **CommandResult** (`stdout`, `stderr`, `exit_code`) | Browser action result with `output`, `screenshot`, `dom_snapshot`, `status` |
| **EntryInfo** (typed file metadata with permissions, owner, size) | Typed DOM element info with attributes, bounds, visibility state |
| **WriteInfo** (write operation confirmation) | Action confirmation with before/after state |
| **ProcessInfo** (running process metadata) | Running browser tab info with URL, title, loading state |
| **Typed exception hierarchy** (`SandboxException` -> `FileNotFoundException`, `TimeoutException`, etc.) | Browser-specific exceptions: `NavigationTimeout`, `ElementNotFound`, `SessionExpired`, `CDPConnectionLost` |

### Gap #1: Browser Session & CDP Integration (MODERATE MATCH)

**Relevance: 6/10**

| E2B Pattern | SUPER-BROWSER Adaptation |
|-------------|--------------------------|
| **envd daemon** (in-sandbox control plane via gRPC) | Browser "envd" equivalent = CDP protocol adapter running inside browser context |
| **ConnectRPC streaming** (`rpc Start(StartRequest) returns (stream StartResponse)`) | CDP event streaming maps directly to gRPC streaming pattern |
| **Process selector** (by PID or tag) | Browser tab/target selector (by target ID or name) |
| **Health endpoint** (`/health`) | Browser session health: `/health` returns browser process status |

### Gap #8: Stealth & Anti-Bot Layer (INDIRECT MATCH)

**Relevance: 4/10**

| E2B Pattern | SUPER-BROWSER Adaptation |
|-------------|--------------------------|
| **Network policy** (CIDR deny_out) | Block known bot-detection endpoints; deny tracking pixels |
| **`mask_request_host`** (custom host header) | Mask browser fingerprint in request headers |
| **Template system** (custom Dockerfile) | Build browser images with pre-configured stealth patches |

---

## 6. Architectural Blueprint -- Transferable Patterns

### 6.1 The Three-Layer Architecture (CRITICAL)

E2B's architecture maps almost 1:1 to what SUPER-BROWSER needs:

```
E2B Architecture:                         SUPER-BROWSER Architecture:
========================                  ============================
[Cloud API]                               [Session Orchestrator]
  - Create/kill/pause/resume               - Create/kill/pause/resume browser
  - OpenAPI REST                           - REST or gRPC API
       |                                        |
[envd Daemon]                             [CDP Bridge Daemon]
  - In-sandbox process                     - In-browser context (CDP adapter)
  - ConnectRPC/protobuf                   - WebSocket/CDP protocol
  - Filesystem + Process services          - DOM + Network + Interaction services
       |                                        |
[SDK Facade]                              [Python SDK Facade]
  - Sandbox.files / .commands / .pty       - Browser.page / .network / .interaction
  - ConnectionConfig propagation            - SessionConfig propagation
  - Dual sync/async                        - Dual sync/async
```

### 6.2 Error Mapping Strategy (HIGH VALUE)

E2B maps two distinct error domains into a unified exception hierarchy:

```
gRPC Codes (envd) -> Domain Exceptions         HTTP Status (API) -> Domain Exceptions
NOT_FOUND -> FileNotFoundException               404 -> SandboxNotFoundException
UNAUTHENTICATED -> AuthenticationException       401 -> AuthenticationException
UNAVAILABLE -> TimeoutException                  502 -> TimeoutException
INVALID_ARGUMENT -> InvalidArgumentException      400 -> InvalidArgumentException
RESOURCE_EXHAUSTED -> RateLimitException         429 -> RateLimitException
```

SUPER-BROWSER should apply the same pattern:
```
CDP Errors -> Domain Exceptions                  HTTP Errors -> Domain Exceptions
Target closed -> SessionExpired                   404 -> SessionNotFoundException
Navigation timeout -> NavigationTimeout           401 -> AuthenticationException
Node not found -> ElementNotFound                 429 -> RateLimitException
```

### 6.3 Version-Gated Feature Detection (REUSABLE)

E2B uses version comparison to gate features gracefully:

```python
if self._envd_version < Version("0.1.4"):
    raise TemplateException("Rebuild template for recursive watch")
if self._envd_version < Version("0.2.4"):
    logger.warning("Disk metrics not supported, rebuild template")
```

SUPER-BROWSER should do the same with browser version/Chrome version to gracefully degrade when CDP features are unavailable.

### 6.4 Session Lifecycle State Machine (REUSABLE)

```
[Creating] -> [Running] -> [Paused] -> [Running]  (resume)
                  |           |
                  v           v
              [Killed]    [Killed]
                  |
                  v
           [Snapshot] -> [Creating from Snapshot]
```

SUPER-BROWSER sessions should follow the same state machine with identical transitions.

---

## 7. Actionable Recommendations

### For Gap #10 (Security Envelope)

1. **Adopt E2B's token hierarchy**: Generate `envd_access_token` (for CDP commands) and `traffic_access_token` (for screenshot/file streams) per session
2. **Implement HMAC-signed URLs**: Use the `signature.py` pattern for time-limited browser screenshot and file download URLs
3. **Port network policies**: Implement `allow_out`/`deny_out` CIDR lists to restrict browser navigation to allowed domains
4. **Default to `secure=True`**: All browser sessions should require authentication by default

### For Gap #4 (Self-Healing & Session Recovery)

1. **Implement pause/resume**: Pause browser sessions (keep browser process alive, stop page execution) instead of killing them
2. **Build snapshot system**: Serialize browser state (cookies, localStorage, sessionStorage, IndexedDB, service workers) into restorable snapshots
3. **Add auto-resume**: When a paused session receives a request, automatically resume it
4. **Implement health checks**: Periodic `/health` endpoint for browser process liveness

### For Gap #7 (Agent Orchestration & Facade)

1. **Copy the class hierarchy**: `BrowserBase` -> `BrowserApi` -> `AsyncBrowser` with property-based modules
2. **Use `@class_method_variant` pattern**: Allow both `browser.navigate(url)` and `Browser.navigate(session_id, url)` calling styles
3. **Propagate `SessionConfig`**: All modules (page, network, dom, interaction) receive shared config
4. **Add context manager**: `async with BrowserSession.create() as browser:` for automatic cleanup

### For Gap #12 (Structured Action Results)

1. **Define typed result classes**: `ActionResult` (status, output, screenshot, timing), `NavigateResult` (url, title, redirect_chain), `ClickResult` (element, coordinates, success)
2. **Port the exception hierarchy**: Map CDP errors and HTTP errors into a unified exception tree

---

## 8. Limitations & Gaps NOT Addressed by E2B

| SUPER-BROWSER Gap | E2B Coverage | Notes |
|-------------------|--------------|-------|
| #2 Three-Tier Interaction Engine | **None** | E2B has no visual/semantic/dom interaction layers |
| #3 Visual Verification System | **None** | No screenshot comparison or visual assertion capabilities |
| #5 Domain Skill Registry | **None** | No domain-specific knowledge or site adaptation |
| #6 Vision-Based Element Location | **None** | No computer vision or AI-based element detection |
| #9 Token Budget & Cost Control | **None** | E2B has usage metrics but no token-level budgeting |

These gaps must be filled from other sources.

---

## 9. File Index (Key Reference Files)

| File | Purpose |
|------|---------|
| `packages/python-sdk/e2b/sandbox_async/main.py` | AsyncSandbox facade -- full lifecycle, create/connect/kill/pause |
| `packages/python-sdk/e2b/sandbox_async/sandbox_api.py` | SandboxApi -- REST API calls for sandbox CRUD |
| `packages/python-sdk/e2b/sandbox/main.py` | SandboxBase -- shared state, URL generation, config |
| `packages/python-sdk/e2b/sandbox/signature.py` | HMAC-SHA256 signed URL generation |
| `packages/python-sdk/e2b/sandbox/sandbox_api.py` | Dataclasses: SandboxInfo, SandboxMetrics, SnapshotInfo, lifecycle types |
| `packages/python-sdk/e2b/sandbox/network.py` | Network configuration helpers |
| `packages/python-sdk/e2b/sandbox_async/filesystem/filesystem.py` | Filesystem module -- read/write/list/watch/remove/mkdir |
| `packages/python-sdk/e2b/sandbox_async/commands/command.py` | Commands module -- run/kill/list/connect/send_stdin |
| `packages/python-sdk/e2b/connection_config.py` | ConnectionConfig -- API key, domain, proxy, timeout |
| `packages/python-sdk/e2b/envd/rpc.py` | RPC error mapping -- gRPC codes to exceptions |
| `packages/python-sdk/e2b/envd/api.py` | HTTP error mapping -- status codes to exceptions |
| `packages/python-sdk/e2b/envd/versions.py` | Feature version gates |
| `packages/python-sdk/e2b/exceptions.py` | Full exception hierarchy |
| `packages/python-sdk/e2b/sandbox/mcp.py` | MCP server type definitions (130+ integrations) |
| `packages/js-sdk/src/sandbox/index.ts` | JS Sandbox class -- full facade with ConnectRPC transport |
| `packages/js-sdk/src/sandbox/sandboxApi.ts` | JS SandboxApi -- REST calls, paginators, lifecycle |
| `spec/envd/process/process.proto` | Process service protobuf definition |
| `spec/envd/filesystem/filesystem.proto` | Filesystem service protobuf definition |
| `templates/base/e2b.Dockerfile` | Base sandbox Dockerfile |
| `templates/base/e2b.toml` | Template configuration |
