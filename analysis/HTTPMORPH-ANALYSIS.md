# httpmorph

> High-performance Python HTTP client with exact Chrome TLS/HTTP2 fingerprinting (JA4/JA3N/Akamai), built on BoringSSL with C core and Cython bindings
> Source ID: SRC-HTTPMORPH
> Language: C (core, ~10K LOC), Cython (bindings), Python (API, ~1.5K LOC)
> Scale: ~13,400 total source lines, ~40 source files
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Browser Profile Engine (Chrome 127-143) | Perception & Input | `src/tls/browser_profiles.c` (391 lines) | 5 | 5 | 4 | 4 | 4.55 | 1 | Primary #8 |
| 2 | TLS Engine (BoringSSL) | Processing & Logic | `src/core/tls.c` (751 lines), `src/core/boringssl_wrapper.cc` | 5 | 4 | 4 | 4 | 4.20 | 1 | Primary #8 |
| 3 | HTTP/2 Protocol Engine | Processing & Logic | `src/core/http2_logic.c` (875 lines), `src/core/http2_session_manager.c` (412 lines) | 5 | 4 | 4 | 4 | 4.20 | 1 | Primary #8 |
| 4 | Connection Pool (Thread-Safe) | Runtime & Execution | `src/core/connection_pool.c` (674 lines), `src/core/buffer_pool.c` (249 lines) | 4 | 4 | 4 | 4 | 4.00 | 1 | Partial #1 |
| 5 | I/O Engine (epoll/kqueue/IOCP) | Runtime & Execution | `src/core/io_engine.c` (691 lines), `src/core/async_request.c` (2175 lines) | 5 | 4 | 3 | 3 | 3.65 | 2 | Partial #1 |
| 6 | Session & Client Management | Integration & Extension | `src/core/session.c` (256 lines), `src/httpmorph/_client_c.py` (1057 lines) | 4 | 4 | 4 | 4 | 4.00 | 1 | Partial #8 |
| 7 | Cython Bindings | Integration & Extension | `src/bindings/_httpmorph.pyx` (724 lines) | 5 | 4 | 4 | 3 | 3.90 | 2 | No mapping |
| 8 | Python API Layer (requests-compatible) | Integration & Extension | `src/httpmorph/_client_c.py`, `src/httpmorph/_async_client.py` | 4 | 4 | 4 | 4 | 4.00 | 1 | Partial #8 |
| 9 | HTTP/1.1 Protocol Engine | Processing & Logic | `src/core/http1.c` (619 lines) | 4 | 3 | 4 | 4 | 3.70 | 2 | No mapping |
| 10 | Network & DNS Layer | Runtime & Execution | `src/core/network.c` (539 lines) | 4 | 3 | 4 | 4 | 3.65 | 2 | Partial #1 |
| 11 | Proxy Engine (CONNECT tunneling) | Runtime & Execution | `src/core/proxy.c` (131 lines) | 3 | 3 | 4 | 4 | 3.40 | 2 | Partial #8 |
| 12 | Cookie Management | Data & Storage | `src/core/cookies.c` (161 lines) | 3 | 3 | 3 | 3 | 3.00 | 2 | No mapping |
| 13 | Compression (gzip/deflate/brotli) | Processing & Logic | `src/core/compression.c` (211 lines) | 3 | 3 | 3 | 3 | 3.00 | 2 | No mapping |
| 14 | String Interning & Request Builder | Runtime & Execution | `src/core/string_intern.c` (96 lines), `src/core/request_builder.c` (174 lines) | 3 | 3 | 4 | 4 | 3.35 | 2 | No mapping |
| 15 | URL Parser | Runtime & Execution | `src/core/url.c` (67 lines) | 3 | 2 | 4 | 4 | 3.15 | 3 | No mapping |
| 16 | Async Client (asyncio integration) | Runtime & Execution | `src/httpmorph/_async_client.py` (377 lines) | 4 | 4 | 3 | 3 | 3.40 | 2 | Partial #1 |

Tier 1 count: 6 | Tier 2 count: 9 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ○ None | — | — | N/A — stateless HTTP client |
| 2. Reasoning | ○ None | — | — | N/A |
| 3. Multi-Agent Coordination | ○ None | — | — | N/A |
| 4. Perception | ◐ Partial | Production | Browser profile engine (TLS fingerprint perception) | Gap — network-level perception only |
| 5. Goal Management | ○ None | — | — | N/A |
| 6. Autonomy | ○ None | — | — | N/A |
| 7. Knowledge Representation | ○ None | — | — | N/A |
| 8. Self-Improvement | ○ None | — | — | N/A |
| 9. Metacognition | ○ None | — | — | N/A |
| 10. World Modeling | ○ None | — | — | N/A |
| 11. Plugin & Extension | ◐ Partial | Production | Python API, Cython bindings, async client | Gap — library, not plugin system |
| 12. Runtime & Execution | ● Full | Production | Connection pool, I/O engine, async state machine | Better than Super Browser — cross-platform high-perf I/O |
| 13. Provider & Model Management | ○ None | — | — | N/A |
| 14. Value Alignment | ◐ Partial | Research | TLS verification, cookie security | Gap — basic transport security only |

## What to Adopt

### 1. Browser Fingerprint Profile System

- **Pattern**: Compile-time static structs encoding every TLS and HTTP/2 parameter for Chrome 127-143 exact JA4 fingerprint matching. Macro template generates 17 Chrome profiles from a single definition. Variant generator randomizes GREASE values and cipher ordering for unique but realistic fingerprints.
- **Subsystem**: #1 (Browser Profile Engine)
- **Intrinsic score**: 4.55
- **Source file**: `src/tls/browser_profiles.c` (391 lines)
- **Evidence**: Verified in code
- **What it does**: Each Chrome version is defined as a `browser_profile_t` struct with cipher suites, TLS extensions, curves (including post-quantum X25519MLKEM768), signature algorithms, ALPN, GREASE values, HTTP/2 SETTINGS frame (`1:65536;2:0;4:6291456;6:262144`), window update (15663105), and per-OS User-Agent strings. The `CHROME_127_143_PROFILE(ver, build)` macro generates all profiles from a template. `browser_profile_get("chrome")` resolves to the latest. Variant generator creates unique fingerprints via GREASE randomization.
- **Integration target**: Gap #8 (Stealth & Anti-Bot) — the network-level stealth complement to Patchright's browser-level stealth. Super Browser needs both: Patchright for the browser instance, httpmorph for any HTTP requests made outside the browser (API calls, pre-fetching, health checks).
- **Overlap**: Firecrawl has TLS client engine for similar purposes. httpmorph is more complete with exact JA4 matching and post-quantum crypto.
- **Quality**: Production-ready
- **Effort**: Medium — use as dependency, not reimplement

### 2. Chrome Default Headers with Client Hints

- **Pattern**: Pre-configured dict of Chrome 143 default headers including `sec-ch-ua` client hints, `sec-fetch-*` metadata, HTTP/2 priority hints, merged with per-request overrides.
- **Subsystem**: #6 (Session & Client)
- **Intrinsic score**: 4.00
- **Source file**: `src/httpmorph/_client_c.py:657-676`
- **Evidence**: Verified in code
- **What it does**: Session ships with Chrome 143 default headers: `sec-ch-ua` (`"Chromium";v="143", "Google Chrome";v="143", "Not-A.Brand";v="24"`), `sec-fetch-dest/mode/site/user`, `priority: "u=0, i"`, standard Accept/Accept-Language, `upgrade-insecure-requests`. Session headers merge with per-request headers so callers can override while keeping Chrome-realistic defaults.
- **Integration target**: Gap #8 (Stealth & Anti-Bot) — HTTP header consistency for any requests that need to appear browser-like.
- **Overlap**: Patchright handles headers within the browser. httpmorph handles headers for external HTTP requests. Complementary.
- **Quality**: Production-ready
- **Effort**: Low — a Python dict

### 3. Platform-Adaptive I/O with Async State Machine

- **Pattern**: Runtime selection of epoll (Linux), kqueue (macOS), or IOCP (Windows). Async requests modeled as 9-state machine (INIT→DNS→CONNECT→TLS→SEND→RECV_HEADERS→RECV_BODY→COMPLETE). Python AsyncClient integrates with asyncio via `add_reader`/`add_writer` on C-level file descriptors.
- **Subsystem**: #5 (I/O Engine)
- **Intrinsic score**: 3.65
- **Source file**: `src/core/io_engine.c` (691 lines), `src/core/async_request.c` (2175 lines)
- **Evidence**: Verified in code
- **What it does**: The I/O engine selects the best platform-native multiplexing at runtime. Async requests traverse 9 states with non-blocking operations at every stage including TLS handshake. The Python AsyncClient integrates directly with asyncio's event loop, avoiding thread pool overhead. Enables 10K+ concurrent connections with ~320KB per request vs ~8MB per OS thread.
- **Integration target**: Gap #1 (Browser Session & CDP) — the connection management pattern for CDP sessions. The async state machine pattern is applicable to CDP WebSocket management.
- **Overlap**: browser-harness uses synchronous Unix socket. browser-use uses cdp-use async client. httpmorph's I/O engine is more sophisticated but overkill for CDP (which is single-connection per browser).
- **Quality**: Production-ready
- **Effort**: High — 2175 lines of C code

## Unguided Findings

### Connection Pool with Slab Allocator (composite: 4.00)

- **What it does**: Thread-safe connection pool with per-host limits, idle timeout, reference counting, and graceful cleanup. Buffer pool uses 4-tier slab allocator (4KB/16KB/64KB/256KB) for response body buffers, reducing malloc/free churn. Cross-platform mutex (pthread/CRITICAL_SECTION).
- **Why it matters**: For Super Browser's HTTP infrastructure (API calls, pre-fetching), the connection pool pattern with slab allocation is directly applicable.
- **Key files**: `src/core/connection_pool.c`, `src/core/buffer_pool.c`
- **Adoption feasibility**: Medium — C code, would need Python reimplementation

### Per-Request Timing Data (composite: 3.40)

- **What it does**: Every response includes microsecond-precision timing: `connect_time_us`, `tls_time_us`, `first_byte_time_us`, `total_time_us`. Also reports TLS version, cipher, and JA3 fingerprint.
- **Why it matters**: For Super Browser's tracing (Gap #11), this level of timing detail is valuable for performance analysis and cost tracking.
- **Key files**: Response object in `_client_c.py`
- **Adoption feasibility**: High — the timing fields are simple to add to any HTTP client

## Notable Code

Browser profile macro template:

```c
// src/tls/browser_profiles.c (pattern)
#define CHROME_127_143_PROFILE(ver, build) \
const browser_profile_t PROFILE_CHROME_##ver = { \
    .name = "chrome" #ver, \
    .cipher_suites = { 0x1301, 0x1302, 0x1303, 0xc02b, 0xc02f, ... }, \
    .curves = { 0x11ec, 0x001d, 0x0017, 0x0018 }, /* X25519MLKEM768 PQ */ \
    .http2 = { .settings = {{1,65536},{2,0},{4,6291456},{6,262144}}, \
               .window_update = 15663105 }, \
    .ja3_hash = "ad39201d5fec29cb6a0bfe632d59781b", \
};
```

Chrome default headers:

```python
# src/httpmorph/_client_c.py:657-676
_CHROME_DEFAULT_HEADERS = {
    "sec-ch-ua": '"Chromium";v="143", "Google Chrome";v="143", "Not-A.Brand";v="24"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"macOS"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "none",
    "sec-fetch-user": "?1",
    "priority": "u=0, i",
}
```

Platform I/O engine selection:

```c
// src/core/io_engine.c (pattern)
const char* io_engine_type_name(io_engine_type_t type) {
    switch (type) {
        case IO_ENGINE_EPOLL:  return "epoll";
        case IO_ENGINE_KQUEUE: return "kqueue";
        case IO_ENGINE_IOCP:   return "iocp";
        default:               return "unknown";
    }
}
```

## Thin Project Disposition

Not applicable — httpmorph has 6 Tier 1 and 9 Tier 2 subsystems despite being a focused library.

**Unique contribution**: The most complete open-source Chrome TLS/HTTP2 fingerprinting implementation. Exact JA4/JA3N/Akamai fingerprint matching for Chrome 127-143 with post-quantum crypto support. Complements Patchright (browser-level stealth) with network-level stealth. For Super Browser, httpmorph addresses the HTTP transport layer of Gap #8 — any requests made outside the browser (API calls, health checks, pre-fetching) should use httpmorph to maintain stealth consistency.
