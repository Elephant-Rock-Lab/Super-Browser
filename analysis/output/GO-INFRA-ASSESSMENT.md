# Go Infrastructure Assessment -- gvisor, temporal, openfga

Assessment date: 2026-04-23
Context: Evaluating relevance to SUPER-BROWSER (Python browser automation library) for gaps #4 (Self-Healing/Session Recovery), #7 (Agent Orchestration), #10 (Security Envelope), #12 (Structured Action Results).

---

## gvisor

- **Relevance:** Low
- **Python path:** No -- gVisor is a Linux-only application kernel written entirely in Go. It compiles to the `runsc` OCI runtime binary. There are no Python bindings, APIs, or SDKs. It operates at the syscall/kernel level, far below any Python integration point. SUPER-BROWSER could only use gVisor indirectly by running inside a gVisor-sandboxed container, which is an ops concern, not a library concern.
- **Top relevant subsystems (for reference only):**
  1. `pkg/sentry/` -- the application kernel implementing Linux syscalls in userspace (the sandboxing core)
  2. `pkg/sentry/checkpoint/` and `pkg/sentry/fscheckpoint/` -- state checkpoint/restore for sandboxed processes (conceptually relevant to Gap #4, but implemented as Linux kernel state serialization, not browser session checkpointing)
  3. `pkg/seccomp/` -- seccomp-BPF filter generation (system-level sandboxing)
  4. `pkg/sentry/seccheck/` -- security event checking/auditing framework
- **Disposition:** Thin Disposition
- **Rationale:** gVisor is kernel-level infrastructure. Its sandboxing approach (reimplementing Linux syscalls in a memory-safe userspace kernel) is fundamentally tied to OS-level container isolation. The patterns are not portable to Python -- you cannot replicate a syscall-interception sandbox in a Python browser automation library. The checkpoint/restore subsystem (`sentry/checkpoint`) is the closest conceptual match to Gap #4, but it serializes kernel-level process state (file descriptors, memory maps, thread state), which has no analog in browser session management. There is no API surface, SDK, or protocol that SUPER-BROWSER could consume. At most, gVisor's existence argues for running browser automation workers inside sandboxed containers as a deployment pattern, but that is infrastructure, not a library feature.

---

## temporal

- **Relevance:** High
- **Python path:** Yes -- Temporal has a first-class Python SDK (`temporalio` pip package) that supports workflows, activities, and workers natively in Python. The SDK is mature and actively maintained. SUPER-BROWSER could directly import and use it.
- **Top relevant subsystems:**
  1. `service/history/` -- the workflow execution engine that handles event sourcing, state machine transitions, and checkpoint-based recovery. This is the core of durable execution and directly maps to Gap #4 (Self-Healing/Session Recovery). The event-sourcing pattern here -- where every state change is an immutable event, and state is reconstructed by replay -- is directly adoptable in Python.
  2. `common/persistence/` -- the abstraction layer for durable state storage (Cassandra, SQL, Elasticsearch). The interface design for checkpoint serialization and state versioning is a reference pattern for SUPER-BROWSER's session persistence.
  3. `common/retrypolicy/` and `common/backoff/` -- structured retry and exponential backoff with jitter. Directly relevant to Gap #7 (Agent Orchestration) for resilient tool execution.
  4. `common/failure/` -- structured failure types and error propagation across workflow/activity boundaries. Directly relevant to Gap #12 (Structured Action Results) -- Temporal's approach to typed, serializable failure objects is a strong pattern.
  5. `service/matching/` -- task queue matching and dispatch for activity workers. Relevant to Gap #7 for understanding how to build a tool/task dispatch system with load balancing and sticky routing.
- **Disposition:** Deep Analysis
- **Subsystems to analyze in depth:**
  - `service/history/` -- event sourcing, state machines, checkpoint recovery (Gap #4)
  - `common/persistence/` -- durable state interfaces, serialization contracts (Gap #4)
  - `common/failure/` -- structured error types, failure propagation (Gap #12)
  - `common/retrypolicy/` + `common/backoff/` -- retry strategies (Gap #7)
  - `service/matching/` -- task dispatch and queue management (Gap #7)
  - `temporal/` (server wiring) -- how components are composed via dependency injection (architectural pattern)

---

## openfga

- **Relevance:** Medium-High
- **Python path:** Yes -- OpenFGA has an official Python SDK (`openfga-sdk` on GitHub at `openfga/python-sdk`, listed in their README). It communicates via HTTP/gRPC APIs, making it language-agnostic. SUPER-BROWSER could use the Python SDK directly or implement the same API patterns.
- **Top relevant subsystems:**
  1. `pkg/server/` -- the authorization server core, handling check, list-objects, and write requests. The request/response patterns and middleware chain are relevant to Gap #10 (Security Envelope) for building a permission-enforcement layer.
  2. `pkg/typesystem/` -- the authorization model type system (based on Google Zanzibar). Defines how relations, permissions, and type bounds are modeled and validated. This is the core of fine-grained authorization and directly applicable to Gap #10.
  3. `pkg/tuple/` -- the tuple-based relation store (user-relation-object). The data model for representing and querying permission relationships.
  4. `pkg/check/` and `pkg/listobjects/` -- the authorization check and object-listing evaluation engines. These implement the recursive resolution of permission queries and are the performance-critical paths.
  5. `internal/authz/` and `internal/authn/` -- server-level authentication and authorization middleware patterns.
- **Disposition:** Deep Analysis
- **Subsystems to analyze in depth:**
  - `pkg/typesystem/` -- authorization modeling language and validation (Gap #10)
  - `pkg/check/` -- permission evaluation engine (Gap #10)
  - `pkg/server/` + middleware patterns -- request auth/authz pipeline (Gap #10)
  - `pkg/storage/` -- storage abstraction for authorization tuples (Gap #10, persistence patterns)
  - Python SDK API surface -- how the Python SDK exposes check/write/expand operations, for direct integration feasibility

---

## Summary Table

| Project | Relevance | Python Path | Disposition | Key Gap Coverage |
|---------|-----------|-------------|-------------|-----------------|
| gvisor   | Low         | No  | Thin            | None applicable |
| temporal | High        | Yes | Deep Analysis   | Gap #4, #7, #12 |
| openfga  | Medium-High | Yes | Deep Analysis   | Gap #10         |

**Recommended next steps:**
1. Deep analysis of **temporal** -- focus on event sourcing (history service), structured failures, and retry policies. The Python SDK makes this directly usable.
2. Deep analysis of **openfga** -- focus on authorization modeling (type system, check engine) and the Python SDK integration patterns. SUPER-BROWSER could embed an OpenFGA server or replicate its authorization model.
3. Skip **gvisor** -- no Python integration path. If sandboxing is needed for SUPER-BROWSER, the recommendation is to use gVisor at the deployment/container level, not as a library feature.
