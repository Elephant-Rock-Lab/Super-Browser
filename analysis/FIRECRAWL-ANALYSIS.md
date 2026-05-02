# Firecrawl

> Production web scraping platform with 12-engine waterfall, NuQ custom job queue, multi-provider search, and AI-driven extraction pipeline
> Source ID: SRC-009
> Language: TypeScript
> Scale: ~300+ source files, monorepo with apps/ and packages/
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Engine Waterfall (12 Engines) | Processing & Logic | `scraper/scrapeURL/index.ts`, `engines/index.ts` | 5 | 4 | 4 | 5 | 4.50 | 1 | Primary #4, Partial #2 |
| 2 | NuQ Custom Job Queue | Coordination | `services/worker/nuq.ts` (1700 lines) | 5 | 4 | 3 | 5 | 4.25 | 1 | Partial #7 |
| 3 | Extract Pipeline (LLM-Powered) | Processing & Logic | `lib/extract/extraction-service.ts` (1100 lines) | 4 | 4 | 3 | 4 | 3.70 | 1 | Partial #12 |
| 4 | Self-Healing Retry Tracker | Autonomy & Scheduling | `scraper/scrapeURL/retryTracker.ts` | 5 | 4 | 4 | 4 | 4.20 | 1 | Primary #4 |
| 5 | Deep Research Agent | Autonomy & Scheduling | `lib/deep-research/deep-research-service.ts` (460 lines) | 4 | 4 | 3 | 3 | 3.40 | 2 | Partial #7 |
| 6 | Browser Agent (Scrape-Interact) | Perception & Input | `lib/scrape-interact/browser-agent.ts` (470 lines) | 3 | 4 | 4 | 4 | 3.65 | 2 | Partial #2, #6 |
| 7 | Web Crawler / Link Discovery | Perception & Input | `scraper/WebScraper/crawler.ts` (~1000 lines) | 5 | 2 | 3 | 4 | 3.35 | 2 | Partial #2 |
| 8 | Authentication & Rate Limiting | Governance & Quality | `controllers/auth.ts` (~600 lines) | 5 | 2 | 3 | 4 | 3.30 | 2 | Partial #10 |
| 9 | Billing & Credit System | Governance & Quality | `services/billing/`, `lib/cost-tracking.ts` | 5 | 2 | 3 | 3 | 3.15 | 2 | Partial #9 |
| 10 | Observability (Sentry + Prometheus) | Governance & Quality | `lib/otel-tracer.ts`, metrics files | 4 | 2 | 4 | 3 | 3.15 | 2 | Partial #11 |
| 11 | Stealth & Anti-Bot | Perception & Input | Engine stealth flags, TLS client, proxy system | 4 | 3 | 3 | 4 | 3.45 | 2 | Primary #8 |
| 12 | Playwright Microservice | Perception & Input | `apps/playwright-service-ts/api.ts` (~480 lines) | 4 | 2 | 3 | 3 | 2.90 | 2 | Partial #1 |

Tier 1 count: 4 | Tier 2 count: 8 | Tier 3 count: 0

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ○ None | — | — | Gap |
| 2. Reasoning | ◐ Partial | Research | `deep-research-service.ts` (iterative research) | Gap — research loop only |
| 3. Multi-Agent Coordination | ○ None | — | — | Gap |
| 4. Perception | ● Full | Production | 12 engines, browser agent, web crawler | Better than Super Browser — most comprehensive scraping |
| 5. Goal Management | ◐ Partial | Research | `deep-research-service.ts` (depth/URL limits) | Gap — research goals only |
| 6. Autonomy | ◐ Partial | Production | `deep-research-service.ts`, `browser-agent.ts` | Gap — research/crawl autonomy only |
| 7. Knowledge Representation | ○ None | — | — | Gap |
| 8. Self-Improvement | ◐ Partial | Research | Engine waterfall with quality scoring | Gap — engine selection adapts but no learning |
| 9. Metacognition | ○ None | — | — | Gap |
| 10. World Modeling | ○ None | — | — | Gap |
| 11. Plugin & Extension | ◐ Partial | Production | Engine registry, transformer pipeline | Gap — pluggable engines but no general plugin system |
| 12. Runtime & Execution | ● Full | Production | `harness.ts`, NuQ workers, BullMQ | Better than Super Browser — full production infrastructure |
| 13. Provider & Model Management | ◐ Partial | Production | LLM clients in extract pipeline | Gap — extract-only, not general |
| 14. Value Alignment | ◐ Partial | Production | Auth, rate limiting, SSRF, robots.txt | Gap — operational safety, not agent alignment |

## What to Adopt

### 1. Engine Waterfall with Dynamic Feature Toggling

- **Pattern**: 12 engines with quality scores, feature capability matrices, and fallback ordering. Engines race concurrently with waterfall timeouts. Dynamic feature toggling (add stealth proxy on 401/403/429, remove PDF flags on failure).
- **Subsystem**: #1 (Engine Waterfall)
- **Intrinsic score**: 4.50
- **Source file**: `scraper/scrapeURL/index.ts`, `engines/index.ts`
- **Evidence**: Verified in code
- **What it does**: The engine waterfall races multiple scraping engines concurrently. Each engine declares capabilities via a feature flag matrix. The fallback list builder scores engines by feature support. When an engine fails with proxy-related errors (401/403/429), `AddFeatureError` dynamically adds `stealthProxy` to feature flags and retries with a higher-quality engine. `RemoveFeatureError` drops problematic features (PDF, document) to retry with simpler scraping. The retry tracker manages multi-dimensional attempt budgets.
- **Integration target**: Gap #4 (Self-Healing) — the dynamic feature toggling pattern is a sophisticated form of self-healing. Gap #2 (Three-Tier Interaction) — engine fallback is analogous to tier fallback.
- **Overlap**: browser-use has watchdog-based self-healing. browser-harness has session recovery. Firecrawl's approach is unique: it adapts the *scraping strategy* rather than retrying the same approach.
- **Quality**: Production-ready
- **Effort**: Medium

### 2. Self-Healing Retry Tracker

- **Pattern**: Multi-dimensional retry budget with feature toggles, feature removals, PDF/document prefetches, and engine switching.
- **Subsystem**: #4 (Retry Tracker)
- **Intrinsic score**: 4.20
- **Source file**: `scraper/scrapeURL/retryTracker.ts`
- **Evidence**: Verified in code
- **What it does**: `ScrapeRetryTracker` manages a complex retry budget: max attempts, feature toggles used, features removed, PDF/document prefetches. Each retry can change strategy: add stealth proxy, remove PDF support, switch engines, or prefetch PDFs. The tracker prevents infinite retry loops while allowing comprehensive strategy exploration.
- **Integration target**: Gap #4 (Self-Healing) — the retry strategy pattern.
- **Overlap**: browser-use's loop detector is action-level. Firecrawl's retry tracker is engine-level. Complementary approaches.
- **Quality**: Production-ready
- **Effort**: Low

### 3. Stealth & Anti-Bot Infrastructure

- **Pattern**: Multi-layer stealth: TLS client engine (HTTP/2 fingerprinting), stealth proxy mode, auto-detection of proxy inadequacy, ATSV anti-bot solver, user-agent rotation, ad blocking.
- **Subsystem**: #11 (Stealth)
- **Intrinsic score**: 3.45
- **Source file**: Engine stealth flags, `fire-engine/index.ts`, `playwright-service-ts/api.ts`
- **Evidence**: Verified in code
- **What it does**: The stealth infrastructure operates at multiple levels: (1) TLS client engine (`fire-engine;tlsclient`) provides HTTP/2 fingerprinting, (2) stealth proxy mode activates on 401/403/429 detection, (3) ATSV feature flag enables anti-bot solving, (4) Playwright service rotates user agents, blocks ads/media, (5) domain-specific engine forcing uses known-good engines for specific sites.
- **Integration target**: Gap #8 (Stealth & Anti-Bot) — the multi-layer stealth approach.
- **Overlap**: Hermes Agent has Camofox + Browserbase stealth. browser-use has security watchdog. Firecrawl's approach is scraping-focused but the patterns are applicable.
- **Quality**: Production-ready
- **Effort**: Medium

### 4. NuQ Custom Job Queue

- **Pattern**: Postgres-backed job queue with RabbitMQ prefetch acceleration, distributed locking, LISTEN/NOTIFY dual transport, backlog promotion.
- **Subsystem**: #2 (NuQ)
- **Intrinsic score**: 4.25
- **Source file**: `services/worker/nuq.ts` (1700 lines)
- **Evidence**: Verified in code
- **What it does**: Custom job queue combining Postgres durability with RabbitMQ speed. Jobs are stored in Postgres with `SELECT FOR UPDATE SKIP LOCKED` for atomic dequeue. RabbitMQ prefetch layer accelerates worker pickup. Backlog promotion (`CTAS` with `ON CONFLICT DO NOTHING`) efficiently migrates pending jobs. LISTEN/NOTIFY and RabbitMQ fanout for dual-mode completion notification. Prometheus metrics for queue depth, processing time, and throughput.
- **Integration target**: Gap #7 (Agent Orchestration) — the job queue pattern for task scheduling.
- **Overlap**: browser-harness has no queue. browser-use has no queue. Firecrawl has the most sophisticated job queue among reference projects.
- **Quality**: Production-ready
- **Effort**: High — 1700 lines, Postgres + RabbitMQ infrastructure

## Unguided Findings

### Multi-Entity Schema Splitting in Extract (composite: 3.70)

- **What it does**: The extract pipeline detects whether a schema contains a large array (multi-entity) and splits it into two sub-schemas: one for scalar fields (single-answer across all documents) and one for array fields (batch per-document extraction). Results are merged with `mixSchemaObjects()`.
- **Why it matters**: This is a clever optimization for structured data extraction — instead of making one expensive LLM call with all documents, it makes cheap per-document calls for array fields and one cross-document call for scalar fields.
- **Architecture**: `analyzeSchemaAndPrompt()` detects multi-entity. `spreadSchemas()` splits. `batchExtract()` handles arrays. `singleAnswer()` handles scalars. `mixSchemaObjects()` merges.
- **Key files**: `lib/extract/completions/analyzeSchemaAndPrompt.ts`, `batchExtract.ts`, `singleAnswer.ts`
- **Adoption feasibility**: Medium — specific to data extraction but the pattern is generalizable.

### SSRF Protection in Playwright Service (composite: 2.90)

- **What it does**: DNS resolution caching with private IP validation prevents DNS rebinding attacks. All target URLs are validated before navigation.
- **Why it matters**: SSRF via browser automation is a real attack vector. This is the most complete SSRF protection among the browser automation reference projects.
- **Architecture**: `assertSafeTargetUrl()` resolves hostname via cached DNS lookup, checks each address against private IP ranges.
- **Key files**: `apps/playwright-service-ts/api.ts`
- **Adoption feasibility**: High

### Transformer Pipeline (16+ Stages) (composite: 3.35)

- **What it does**: Ordered transformer pipeline: rawHtml → HTML → markdown → links → images → metadata → screenshot upload → LLM extract → summary → query → agent → diff → audio → field coercion. Each stage is independently configurable.
- **Why it matters**: This is a production-proven pipeline architecture for web content processing. The ordered, configurable pipeline pattern is directly applicable to Super Browser's action result processing.
- **Architecture**: Array of transformer functions executed in sequence. Each receives and returns a `Document` object. Feature flags control which transformers run.
- **Key files**: `scraper/scrapeURL/transformers/index.ts`
- **Adoption feasibility**: High

## Notable Code

Dynamic feature toggling on proxy error:

```typescript
// scraper/scrapeURL/index.ts (pattern)
if (isLikelyProxyError && meta.options.proxy === "auto" && !meta.featureFlags.has("stealthProxy")) {
    throw new AddFeatureError(["stealthProxy"]);
}
```

Engine waterfall racing:

```typescript
// scraper/scrapeURL/index.ts (pattern)
while (remainingEngines.length > 0) {
    const { engine } = remainingEngines.shift()!;
    enginePromises.push({ engine, promise: engineExecute(engine) });
    result = await Promise.race([
        ...enginePromises.map(x => x.promise),
        new Promise((_, reject) =>
            setTimeout(() => reject(new WaterfallNextEngineSignal()), waitUntilWaterfall)),
    ]);
}
```

NuQ dual-transport completion:

```typescript
// services/worker/nuq.ts (pattern)
if (this.nuqWaitMode === "listen" && !config.NUQ_RABBITMQ_URL) {
    await nuqPool.query(`SELECT pg_notify('${this.queueName}', $1);`, [job.id + "|completed"]);
} else if (config.NUQ_RABBITMQ_URL && job.listen_channel_id) {
    await this.sendJobEnd(job.id, "completed", job.listen_channel_id);
}
```

Browser agent tool-calling with action log:

```typescript
// lib/scrape-interact/browser-agent.ts (pattern)
prepareStep: async ({ stepNumber, messages }) => {
    if (actionLog.length === 0) return {};
    return {
        messages: [...messages, {
            role: "user",
            content: [{ type: "text", text: `ACTION LOG (your commands so far):\n${actionLog.join("\n")}` }]
        }],
    };
},
```

## Thin Project Disposition

Not applicable — Firecrawl has 4 Tier 1 and 8 Tier 2 subsystems. The most production-hardened web scraping platform in the reference corpus.

**Unique contribution**: The engine waterfall with dynamic feature toggling (4.50) and NuQ custom job queue (4.25) are patterns not found in other reference projects. Firecrawl is primarily a scraping/extract service rather than a browser automation agent, but its infrastructure patterns (retry, queue, stealth) are directly applicable.
