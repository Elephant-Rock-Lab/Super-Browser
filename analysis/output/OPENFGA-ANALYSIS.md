# OpenFGA Analysis (SRC-068)

**Project**: openfga -- Go high-performance fine-grained authorization engine (Google Zanzibar-inspired), CNCF sandbox project
**Repository**: `github.com/openfga/openfga` (Go server), `github.com/openfga/python-sdk` (Python SDK v0.10.0)
**Date**: 2026-04-23
**Analyst**: Claude Opus 4.7
**Scope**: Authorization type system, permission check engine, Python SDK -- patterns applicable to browser automation security
**Relevant Gaps**: #10 (Security Envelope / permissions & action gating), #12 (Structured Results -- typed API responses)

---

## Subsystem Inventory

| # | Subsystem | Path | Language | Description | D1 Prod | D2 Novel | D3 Compose | D4 Depth | Composite | Tier |
|---|-----------|------|----------|-------------|---------|----------|------------|----------|-----------|------|
| S1 | Authorization Type System | `pkg/typesystem/` | Go | Declarative authorization modeling language: type definitions, relations, userset rewrite rules (union/intersection/difference), computed usersets, tuple-to-userset resolution. Validates models, resolves relational references, enforces type bounds. | 0.95 | 0.90 | 0.90 | 0.95 | **0.93** | 1 |
| S2 | Permission Check Engine | `pkg/server/`, `internal/server/` | Go | Recursive permission evaluation: Check (single), Batch Check (parallel), List Objects, List Users, List Relations, Expand. Handles userset rewriting, cycle detection, contextual tuples, condition evaluation. | 0.95 | 0.85 | 0.90 | 0.95 | **0.92** | 1 |
| S3 | Condition Evaluator (ABAC) | `pkg/typesystem/compile.go`, `internal/conditions/` | Go | CEL-based condition expressions for attribute-based access: temporal grants, IP allowlists, usage-based policies. Supports int, uint, double, bool, string, duration, timestamp, any, list\<T\>, map\<T\>, ipaddress. Compiled at model-write time, evaluated at check time. | 0.90 | 0.85 | 0.85 | 0.85 | **0.86** | 1 |
| S4 | Tuple Store & Storage Abstraction | `pkg/storage/`, `internal/server/store.go` | Go | Pluggable storage interface for relationship tuples (user-relation-object). PostgreSQL, MySQL, memory backends. Tuple-level CRUD, pagination, Chen notations. Changelog tracking. Store-level multi-tenancy. | 0.90 | 0.60 | 0.85 | 0.80 | **0.80** | 1 |
| S5 | Python SDK (openfga-sdk) | `openfga_sdk/`, `openfga_sdk/sync/` | Python | Official Python SDK: async (`OpenFgaClient`) and sync (`SyncOpenFgaClient`) clients. Client configuration with API Token / Client Credentials / No Auth. Auto-retry on 429/5xx. OpenTelemetry tracing. Full API surface: check, batch_check, list_objects, list_users, list_relations, expand, write, read, read_changes, write_authorization_model, read_authorization_model. | 0.90 | 0.55 | 0.90 | 0.80 | **0.80** | 1 |
| S6 | Userset Rewrite Engine | `pkg/typesystem/` (resolve.go, userset.go) | Go | Recursive userset resolution: computed usersets, tuple-to-userset (from-relation), union/intersection/difference operators. This is the core of Zanzibar's relation-based access -- it resolves "who has this permission?" by traversing relationship graphs. | 0.90 | 0.90 | 0.85 | 0.90 | **0.89** | 1 |
| S7 | Contextual Tuples | `pkg/server/` (check handlers) | Go | Runtime-only relationship tuples passed at check time without persistence. Enables ephemeral permission evaluation: "would this access be granted if X were a viewer?" without mutating state. Critical for pre-flight checks. | 0.85 | 0.75 | 0.80 | 0.75 | **0.79** | 1 |
| S8 | Store Management & Multi-Tenancy | `pkg/server/stores.go`, `internal/server/` | Go | Multi-tenant store isolation: each store has its own authorization models and tuples. CRUD for stores, model versioning, model ID isolation. Enables per-tenant authorization namespaces. | 0.85 | 0.55 | 0.80 | 0.70 | **0.73** | 2 |
| S9 | gRPC + HTTP API Layer | `pkg/server/`, `api/openfga/` | Go | Dual-protocol API: gRPC (high-perf) and HTTP/JSON (interoperable). Protobuf service definitions, request/response validation, middleware chain (auth, logging, metrics). | 0.90 | 0.40 | 0.75 | 0.70 | **0.70** | 2 |
| S10 | OpenTelemetry Instrumentation | `telemetry/`, `pkg/server/` (middleware) | Go | Full OTEL integration: HTTP/gRPC stats handlers, span creation for check/write/list operations, metrics for latency/throughput, configurable exporters. | 0.85 | 0.45 | 0.75 | 0.65 | **0.68** | 2 |
| S11 | List Objects / List Users Resolution | `pkg/server/list_objects.go`, `pkg/server/list_users.go` | Go | Reverse permission resolution: "what objects can user X access?" and "who can access object Y?" Streamed results with continuation tokens. Uses Check internally for each candidate. | 0.90 | 0.70 | 0.75 | 0.80 | **0.80** | 1 |
| S12 | Authorization Model DSL | `pkg/typesystem/` (validation), `.fga` format | Go + DSL | Human-readable DSL for authorization models: `type`, `relations`, `define`, `condition` keywords. Schema versioning (1.0, 1.1). Example: `define viewer: [user with non_expired_grant]` | 0.85 | 0.75 | 0.70 | 0.75 | **0.76** | 1 |

**Scoring Key**: D1 Production Grade (0.30), D2 Novelty (0.20), D3 Composability (0.25), D4 Depth (0.25)

**Tier Classification**:
- **Tier 1** (composite >= 0.75): S1, S2, S3, S4, S5, S6, S7, S11, S12 -- 9 subsystems
- **Tier 2** (composite >= 0.60): S8, S9, S10 -- 3 subsystems

---

## Pillar Coverage

| Pillar | Coverage | Key Subsystems |
|--------|----------|----------------|
| **Authorization & Permissions** | Very High | S1 (Type System), S2 (Check Engine), S3 (Conditions), S6 (Userset Rewrites), S7 (Contextual Tuples), S11 (List Objects/Users) |
| **Policy Modeling** | High | S1 (Type System), S3 (Conditions), S12 (DSL) |
| **Structured API Responses** | High | S2 (Check returns `allowed: bool`), S5 (Python SDK typed responses), S11 (Streamed lists) |
| **Multi-Tenancy** | Medium | S4 (Storage), S8 (Store Management) |
| **Observability** | Medium | S5 (Python OTEL), S10 (Server OTEL) |

---

## What to Adopt (Per-Gap)

### Gap #10: Security Envelope -- Permissions & Action Gating

**OpenFGA's approach**: OpenFGA implements Google Zanzibar's relationship-based access control (ReBAC) with ABAC extensions. Authorization is modeled as typed relationship tuples (`user:anne` `viewer` `document:1`), resolved through userset rewrite rules (union/intersection/difference), and evaluated at runtime via recursive graph traversal. Conditions add attribute-based constraints (time, IP, usage count). The entire system is composable: any new resource type just needs a model definition.

#### 10a. Authorization Model -- Declarative Permission Definitions

**Files**:
- `pkg/typesystem/` (Go) -- Type system validation, relation resolution, userset rewriting
- `pkg/typesystem/compile.go` -- Condition compilation from CEL to evaluable form
- Authorization model DSL (`.fga` format)

**What to adopt**:
```
model schema 1.1
type user

type browser_action
  relations
    define allowed: [user with session_active]
    define owner: [user]
    define can_execute: allowed or owner

type page
  relations
    define viewer: [user with ip_allowed]
    define editor: [user with session_active]
    define can_navigate: viewer or editor
    define can_scrape: editor
    define can_interact: editor

condition session_active(current_time: timestamp, session_start: timestamp, session_timeout: duration) {
  current_time < session_start + session_timeout
}

condition ip_allowed(source_ip: ipaddress, allowed_cidrs: list<string>) {
  source_ip.in_cidr_list(allowed_cidrs)
}
```

```python
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

class Permission(Enum):
    """Browser action permissions -- maps to OpenFGA relations."""
    CAN_NAVIGATE = "can_navigate"
    CAN_SCRAPE = "can_scrape"
    CAN_INTERACT = "can_interact"
    CAN_EXECUTE = "can_execute"
    CAN_DOWNLOAD = "can_download"
    CAN_UPLOAD = "can_upload"

@dataclass
class AuthorizationTuple:
    """Mirrors OpenFGA's relationship tuple: user-relation-object."""
    user: str          # e.g. "user:agent_1", "role:admin"
    relation: str      # e.g. "viewer", "editor", "owner"
    object: str        # e.g. "page:example.com", "action:download"
    condition: Optional[str] = None  # CEL expression name

@dataclass
class CheckRequest:
    """Mirrors OpenFGA's ClientCheckRequest."""
    user: str
    permission: Permission
    object: str
    context: dict = field(default_factory=dict)  # runtime attributes for conditions

@dataclass
class CheckResponse:
    """Mirrors OpenFGA's check response."""
    allowed: bool
    resolution_time_ms: float = 0.0
    resolving_tuples: list[AuthorizationTuple] = field(default_factory=list)
```

**Key insight**: OpenFGA separates *modeling* (what permissions exist and how they compose) from *data* (who has what relation to what object) from *evaluation* (check at runtime). This three-way separation is exactly what SUPER-BROWSER's Security Envelope needs: (1) define what browser actions require permissions, (2) assign permissions to agents/sessions, (3) check before every action. The `computed userset` pattern (`can_view: viewer or editor or owner`) means permissions compose -- you never need to enumerate all allowed users for every action.

#### 10b. Permission Check Engine -- Action Gating

**Files**:
- `pkg/server/` (Go) -- Check, Batch Check, List Objects, List Users, Expand API handlers
- `internal/server/` -- Server implementation with middleware
- Python SDK: `openfga_sdk/client/client.py` -- `check()`, `batch_check()` methods

**What to adopt**:
```python
from typing import Protocol, Callable, Awaitable
import asyncio

class PermissionChecker(Protocol):
    """Protocol for permission evaluation -- mirrors OpenFGA's Check API."""
    async def check(self, request: CheckRequest) -> CheckResponse: ...
    async def batch_check(self, requests: list[CheckRequest]) -> list[CheckResponse]: ...

class OpenFGAPermissionChecker:
    """Live OpenFGA-backed permission checker for production use."""

    def __init__(self, api_url: str, store_id: str, model_id: str,
                 auth_token: str | None = None):
        from openfga_sdk import ClientConfiguration, OpenFgaClient
        self._config = ClientConfiguration(
            api_url=api_url,
            store_id=store_id,
            authorization_model_id=model_id,
        )
        if auth_token:
            self._config.credentials = {"api_token": auth_token}
        self._client: OpenFgaClient | None = None

    async def __aenter__(self):
        from openfga_sdk import OpenFgaClient
        self._client = OpenFgaClient(self._config)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *args):
        if self._client:
            await self._client.__aexit__(*args)

    async def check(self, request: CheckRequest) -> CheckResponse:
        from openfga_sdk import ClientCheckRequest
        body = ClientCheckRequest(
            user=request.user,
            relation=request.permission.value,
            object=request.object,
            context=request.context or None,
        )
        response = await self._client.check(body)
        return CheckResponse(
            allowed=response.allowed,
            resolution_time_ms=response.resolution_time or 0.0,
        )

    async def batch_check(self, requests: list[CheckRequest]) -> list[CheckResponse]:
        from openfga_sdk import ClientCheckRequest, ClientBatchCheckRequest
        checks = [
            ClientCheckRequest(
                user=r.user,
                relation=r.permission.value,
                object=r.object,
                context=r.context or None,
            )
            for r in requests
        ]
        response = await self._client.batch_check(
            ClientBatchCheckRequest(checks=checks)
        )
        return [
            CheckResponse(allowed=r.allowed, resolution_time_ms=r.resolution_time or 0.0)
            for r in response
        ]


class LocalPermissionChecker:
    """In-process permission checker for offline/testing -- no OpenFGA server needed.
    Implements the same check/batch_check protocol using in-memory tuples."""

    def __init__(self):
        self._tuples: list[AuthorizationTuple] = []
        self._policies: dict[str, Callable[[dict], bool]] = {}  # condition_name -> evaluator

    def add_tuple(self, tuple_: AuthorizationTuple) -> None:
        self._tuples.append(tuple_)

    def add_condition(self, name: str, evaluator: Callable[[dict], bool]) -> None:
        self._policies[name] = evaluator

    async def check(self, request: CheckRequest) -> CheckResponse:
        # Direct tuple match
        for t in self._tuples:
            if t.user == request.user and t.relation == request.permission.value and t.object == request.object:
                if t.condition and t.condition in self._policies:
                    if not self._policies[t.condition](request.context):
                        continue
                return CheckResponse(allowed=True)
        return CheckResponse(allowed=False)

    async def batch_check(self, requests: list[CheckRequest]) -> list[CheckResponse]:
        return await asyncio.gather(*[self.check(r) for r in requests])
```

**Python SDK usage pattern** (from `openfga_sdk`):
```python
# Direct integration with OpenFGA server via Python SDK
from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.client import ClientCheckRequest, ClientWriteRequest, ClientTuple

configuration = ClientConfiguration(
    api_url="http://localhost:8080",
    store_id="01H0H015178Y2V4CX10C2KGHF4",
    authorization_model_id="01G5JAVJMG2NT0CHEDN4FEHK4",
)

async with OpenFgaClient(configuration) as fga_client:
    # Check if agent can scrape a page
    response = await fga_client.check(
        ClientCheckRequest(
            user="agent:scraper_1",
            relation="can_scrape",
            object="page:example.com",
            context={"current_time": "2026-04-23T10:00:00Z"},
        )
    )
    if response.allowed:
        # Proceed with scrape
        pass

    # Batch check multiple permissions at once
    from openfga_sdk.client.client import ClientBatchCheckRequest
    checks = [
        ClientCheckRequest(user="agent:1", relation="can_navigate", object="page:example.com"),
        ClientCheckRequest(user="agent:1", relation="can_scrape", object="page:example.com"),
        ClientCheckRequest(user="agent:1", relation="can_interact", object="page:example.com"),
    ]
    results = await fga_client.batch_check(ClientBatchCheckRequest(checks=checks))

    # List all pages an agent can scrape
    from openfga_sdk.client.client import ClientListObjectsRequest
    pages = await fga_client.list_objects(
        ClientListObjectsRequest(
            user="agent:1",
            relation="can_scrape",
            type="page",
        )
    )
    # pages.objects = ["page:example.com", "page:wikipedia.org", ...]
```

**Key insight**: The `batch_check` API is the critical adoption point for SUPER-BROWSER. Before executing a multi-step automation sequence, batch-check all required permissions in one round-trip. This eliminates per-action latency while maintaining strict action gating. The `list_objects` API enables capability discovery -- "what pages can this agent access?" -- without pre-enumeration. OpenFGA's typical check latency is under 10ms with PostgreSQL backend, making it viable for inline permission checks.

#### 10c. Conditions (ABAC) -- Contextual Permission Constraints

**Files**:
- `pkg/typesystem/compile.go` (Go) -- CEL condition compilation
- `internal/conditions/` (Go) -- Condition evaluation engine
- Docs: `openfga.dev/docs/modeling/conditions`

**What to adopt**:
```python
from dataclasses import dataclass
from typing import Any, Callable
from datetime import datetime, timedelta
import ipaddress

@dataclass
class PermissionCondition:
    """Mirrors OpenFGA's condition system for attribute-based constraints."""
    name: str
    parameters: dict[str, type]           # e.g. {"current_time": datetime, "max_count": int}
    evaluator: Callable[[dict[str, Any]], bool]

# Pre-built conditions for browser automation
def session_not_expired(context: dict) -> bool:
    """Condition: session must still be active."""
    current = datetime.fromisoformat(context["current_time"])
    started = datetime.fromisoformat(context["session_start"])
    timeout = timedelta(seconds=context.get("session_timeout_seconds", 3600))
    return current < started + timeout

def ip_in_allowlist(context: dict) -> bool:
    """Condition: request must come from allowed IP range."""
    source = ipaddress.ip_address(context["source_ip"])
    return any(
        source in ipaddress.ip_network(cidr)
        for cidr in context["allowed_cidrs"]
    )

def under_usage_limit(context: dict) -> bool:
    """Condition: usage count must be below threshold."""
    return context.get("usage_count", 0) < context.get("max_usage", 1000)

def time_in_window(context: dict) -> bool:
    """Condition: current time must be within allowed hours."""
    current = datetime.fromisoformat(context["current_time"])
    start_hour = context.get("start_hour", 0)
    end_hour = context.get("end_hour", 24)
    return start_hour <= current.hour < end_hour

# Registry
BROWSER_CONDITIONS: dict[str, PermissionCondition] = {
    "session_not_expired": PermissionCondition(
        name="session_not_expired",
        parameters={"current_time": str, "session_start": str, "session_timeout_seconds": int},
        evaluator=session_not_expired,
    ),
    "ip_in_allowlist": PermissionCondition(
        name="ip_in_allowlist",
        parameters={"source_ip": str, "allowed_cidrs": list},
        evaluator=ip_in_allowlist,
    ),
    "under_usage_limit": PermissionCondition(
        name="under_usage_limit",
        parameters={"usage_count": int, "max_usage": int},
        evaluator=under_usage_limit,
    ),
    "time_in_window": PermissionCondition(
        name="time_in_window",
        parameters={"current_time": str, "start_hour": int, "end_hour": int},
        evaluator=time_in_window,
    ),
}
```

**Key insight**: OpenFGA compiles CEL conditions at model-write time and evaluates them at check time. This means conditions are type-checked once when the authorization model is created, not on every check. For SUPER-BROWSER, adopt this two-phase approach: validate condition signatures when registering a permission policy, then evaluate them at check time with runtime context. The supported types (timestamp, duration, ipaddress) map directly to browser automation concerns: temporal access windows, session durations, IP-based scoping.

#### 10d. Contextual Tuples -- Ephemeral Permission Evaluation

**Files**:
- `pkg/server/` (Go) -- Check handlers accept `contextual_tuples` field
- Python SDK: `ClientCheckRequest.contextual_tuples`

**What to adopt**:
```python
@dataclass
class ContextualCheckRequest:
    """Pre-flight permission check with hypothetical tuples -- no state mutation."""
    base_request: CheckRequest
    hypothetical_tuples: list[AuthorizationTuple]  # ephemeral, not persisted

async def preflight_check(
    checker: PermissionChecker,
    request: CheckRequest,
    would_grant: list[AuthorizationTuple] | None = None,
) -> CheckResponse:
    """Check if an action would be allowed with hypothetical permissions.

    Use case: Before creating a new session, check if the session WOULD have
    the required permissions without actually granting them yet.
    """
    # If using OpenFGA server, pass contextual_tuples in the check request
    # If using LocalPermissionChecker, temporarily add tuples, check, remove
    if would_grant:
        if isinstance(checker, LocalPermissionChecker):
            for t in would_grant:
                checker.add_tuple(t)
            result = await checker.check(request)
            checker._tuples = checker._tuples[:-len(would_grant)]  # rollback
            return result
    return await checker.check(request)
```

**Key insight**: Contextual tuples are OpenFGA's mechanism for "what-if" authorization checks. They allow evaluating permissions with hypothetical relationship tuples that are not persisted. For SUPER-BROWSER, this enables: (1) pre-flight checks before granting a new permission -- "would this agent be able to access X if I made it an editor?", (2) temporary elevation checks -- "would this session still be valid if I added this domain to its allowed list?", (3) dry-run policy changes. This is critical for safe permission management in a multi-agent environment.

#### 10e. Action Gate Decorator -- Integrating Permission Checks into Browser Operations

**What to adopt** (synthesized from OpenFGA patterns, no direct file):
```python
import functools
from typing import Callable, Any

def requires_permission(permission: Permission, object_type: str = "page"):
    """Decorator that gates browser actions behind permission checks.

    Inspired by OpenFGA's Check API pattern: every operation is authorized
    before execution. The decorator resolves the object from the action context.
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Resolve the target object (page URL, action name, etc.)
            target = kwargs.get("url") or kwargs.get("target") or args[0] if args else "*"

            # Build check request
            check_req = CheckRequest(
                user=f"agent:{self.agent_id}",
                permission=permission,
                object=f"{object_type}:{target}",
                context={
                    "current_time": datetime.utcnow().isoformat(),
                    "source_ip": getattr(self, "_source_ip", "127.0.0.1"),
                    "session_start": getattr(self, "_session_start", datetime.utcnow().isoformat()),
                    **getattr(self, "_permission_context", {}),
                },
            )

            # Evaluate permission
            if hasattr(self, "_permission_checker"):
                response = await self._permission_checker.check(check_req)
                if not response.allowed:
                    raise PermissionDeniedError(
                        f"Agent {self.agent_id} lacks {permission.value} "
                        f"on {object_type}:{target}"
                    )

            return await func(self, *args, **kwargs)
        return wrapper
    return decorator


class PermissionDeniedError(Exception):
    """Raised when a permission check fails -- mirrors OpenFGA's denied response."""
    def __init__(self, message: str, user: str = "", permission: str = "", object_: str = ""):
        super().__init__(message)
        self.user = user
        self.permission = permission
        self.object = object_


# Usage example:
class BrowserAutomation:
    def __init__(self, agent_id: str, permission_checker: PermissionChecker):
        self.agent_id = agent_id
        self._permission_checker = permission_checker

    @requires_permission(Permission.CAN_NAVIGATE, "page")
    async def navigate(self, url: str) -> None:
        # Permission check happens automatically before execution
        ...

    @requires_permission(Permission.CAN_SCRAPE, "page")
    async def scrape(self, url: str) -> str:
        ...

    @requires_permission(Permission.CAN_INTERACT, "page")
    async def click(self, selector: str, url: str = "") -> None:
        ...

    @requires_permission(Permission.CAN_EXECUTE, "browser_action")
    async def execute_script(self, script: str) -> Any:
        ...
```

**Key insight**: The decorator pattern decouples permission enforcement from business logic. Every browser action has a declared permission requirement, but the permission checker is injected and swappable. In tests, use `LocalPermissionChecker` (no server needed). In production, use `OpenFGAPermissionChecker` (centralized, auditable, multi-tenant). The permission context (IP, session time, usage count) flows through automatically.

### Gap #12: Structured Action Results -- Typed API Responses

**OpenFGA's approach**: Every API response is a strongly-typed protobuf message translated to Python dataclasses. Check returns `{allowed: bool, resolution_time: duration}`. List operations return streamed results with continuation tokens. Write returns `{writes: {tokens}, deletes: {tokens}}`. Batch check returns per-check results with correlation IDs.

#### 12a. Typed Permission Responses

**Files**:
- Python SDK: `openfga_sdk/models/` -- Auto-generated response models
- Python SDK: `openfga_sdk/client/client.py` -- Typed return values

**What to adopt**:
```python
from dataclasses import dataclass, field
from typing import Generic, TypeVar, Any

T = TypeVar('T')

@dataclass
class ActionResult(Generic[T]):
    """Structured result envelope inspired by OpenFGA's typed API responses.

    Every browser operation returns a consistent structure:
    - allowed/was_successful: boolean outcome
    - data: typed payload (page content, screenshot bytes, etc.)
    - metadata: timing, permissions used, resolution details
    - error: structured error if failed
    """
    success: bool
    data: T | None = None
    error: ActionError | None = None
    metadata: ActionMetadata = field(default_factory=ActionMetadata)

@dataclass
class ActionError:
    """Structured error -- mirrors OpenFGA's error response pattern."""
    code: str           # e.g. "PERMISSION_DENIED", "ELEMENT_NOT_FOUND"
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    retryable: bool = False

@dataclass
class ActionMetadata:
    """Execution metadata -- mirrors OpenFGA's resolution_time, continued_at."""
    duration_ms: float = 0.0
    permission_checked: str | None = None
    permission_allowed: bool | None = None
    attempt: int = 1
    trace_id: str | None = None
```

**Key insight**: OpenFGA's response model is notable for including *resolution metadata* alongside the yes/no answer. Every check response tells you not just whether access is allowed, but how long resolution took and which tuples were involved. SUPER-BROWSER should adopt this pattern: every action result should include the permission that was checked, whether it was allowed, how long the action took, and a trace ID for debugging.

---

## Gap Coverage Summary

| Gap | Coverage | Key Subsystems | Adoption Priority |
|-----|----------|----------------|-------------------|
| **G10: Security Envelope** | **Very High** | S1, S2, S3, S5, S6, S7 | Primary target -- OpenFGA is purpose-built for this gap |
| **G12: Structured Results** | **High** | S5 (typed SDK responses), S2 (structured check responses) | Strong typed response patterns |
| **G4: Self-Healing** | **Low** | None -- OpenFGA does not address session recovery | Not applicable |
| **G7: Agent Orchestration** | **Low** | S11 (List Objects for capability discovery) | Marginal -- permission-aware routing only |
| **G11: Tracing** | **Medium** | S5 (Python SDK OTEL), S10 (Server OTEL) | Moderate -- permission check tracing |

**Gaps where OpenFGA provides no value**: G1 (DOM State Extraction), G2 (Multi-Tab Orchestration), G3 (Smart Waiting), G5 (Domain Skill Registry), G6 (Plugin System), G8 (Stealth/Anti-Bot), G9 (Token Budget).

---

## Adoption Path

### Phase 1: Local Permission Model (No external dependency)
1. Port the `AuthorizationTuple` and `CheckRequest`/`CheckResponse` dataclasses
2. Implement `LocalPermissionChecker` with in-memory tuple storage
3. Add `@requires_permission` decorator to all browser action methods
4. Define browser-specific conditions (session timeout, IP allowlist, usage limit)
5. Write authorization model for browser automation (actions, pages, roles)

### Phase 2: OpenFGA Integration (Production hardening)
1. Deploy OpenFGA server (Docker: `openfga/openfga:latest`)
2. Create store and authorization model for SUPER-BROWSER
3. Replace `LocalPermissionChecker` with `OpenFGAPermissionChecker`
4. Use `batch_check` for pre-flight multi-permission validation
5. Use `list_objects` for agent capability discovery
6. Use `contextual_tuples` for dry-run policy changes
7. Enable OTEL tracing in Python SDK for permission audit trail

### Phase 3: Advanced Patterns
1. Multi-tenant stores for per-customer isolation
2. ABAC conditions for rate-limited access (usage_count < threshold)
3. Temporal conditions for scheduled automation windows
4. Expand API for permission debugging ("why was this denied?")
5. Write audit logging via tuple changelog

---

## Notable Design Decisions

1. **Separation of model from data**: Authorization models (what permissions exist) are versioned and independent from relationship tuples (who has what). This means SUPER-BROWSER can evolve its permission schema without migrating existing permission grants.

2. **Recursive resolution with cycle detection**: The userset rewrite engine handles circular references gracefully. SUPER-BROWSER can define complex permission hierarchies (page -> site -> project -> organization) without fear of infinite loops.

3. **Condition compilation at model-write time**: CEL expressions are parsed and type-checked when the authorization model is created, not on every check. This makes per-check evaluation extremely fast -- critical for inline action gating.

4. **Python SDK dual-mode (async/sync)**: The SDK provides both `openfga_sdk` (async) and `openfga_sdk.sync` (synchronous) with identical APIs. SUPER-BROWSER can use async for production and sync for testing/scripts.

5. **Batch operations**: `batch_check` evaluates multiple permission checks in parallel with a single round-trip. This is essential for pre-flight validation of multi-step automation sequences.
