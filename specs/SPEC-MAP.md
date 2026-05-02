# Spec Map — Super Browser

> Index of all gap specifications with build order and status.
> Generated: 2026-04-22
> Analysis Sources: 15 reference projects
> Total Spec Lines: ~12,800

## Gap Registry

| # | Gap | Phase | Status | Depends On | Enables | Best Source | Effort | Spec File |
|---|-----|-------|--------|------------|---------|-------------|--------|-----------|
| 1 | Browser Session & CDP | P0 | draft | — | 02, 08, 11 | Stagehand CDP (4.80) | Medium | GAP-01.md |
| 2 | Three-Tier Interaction Engine | P1 | draft | 01, 12 | 03, 04, 05, 06, 07 | UI-TARS-Desktop Browser (4.49) | Medium | GAP-02.md |
| 3 | Visual Verification | P2 | draft | 01, 02 | 04, 07, 11 | Agent-S bBoN (3.91) | Low | GAP-03.md |
| 4 | Self-Healing & Session Recovery | P3 | draft | 01, 02 | 05, 07, 11 | browser-use Watchdog (4.45) | Medium | GAP-04.md |
| 5 | Domain Skill Registry | P4 | draft | 02 | 04, 07, 09 | browser-harness skills (3.90) | Low | GAP-05.md |
| 6 | Vision-Based Element Location | P5 | draft | 02, 09 | 03, 04, 08 | UI-TARS-Desktop Parser (4.74) | High | GAP-06.md |
| 7 | Agent Orchestration & Facade | P1 | draft | 01, 02, 12 | 04, 09, 10, 11 | Hermes Registry (4.80) | Medium | GAP-07.md |
| 8 | Stealth & Anti-Bot Layer | P5 | draft | 01 | 04, 07 | Patchright (4.55) | Medium | GAP-08.md |
| 9 | Token Budget & Cost Control | P3 | draft | 07, 12 | 06 | Hermes Compressor (4.50) | Medium | GAP-09.md |
| 10 | Security Envelope | P4 | draft | 07 | — | OpenClaw Audit (4.20) | Medium | GAP-10.md |
| 11 | Tracing & Observability | P2 | draft | 01, 12 | 04, 07, 09 | Stagehand FlowLogger (4.75) | Medium | GAP-11.md |
| 12 | Structured Action Results | P0 | draft | — | 02, 07, 09, 11 | Hermes Results (4.20) | Low | GAP-12.md |

## Dependency Graph

```
GAP-12 ──────┐
             │
GAP-01 ──┬───┼──────┐
         │   │      │
         │   ▼      ▼
         │ GAP-02 ──┼──► GAP-03 (visual verification)
         │   │      ├──► GAP-04 (self-healing)
         │   │      ├──► GAP-05 (domain skills)
         │   │      │
         │   ├──► GAP-07 ◄──┘
         │   │      │
         │   │      ├──► GAP-09 (token budget) ──► GAP-06 (vision)
         │   │      └──► GAP-10 (security)
         │   │
         ├──► GAP-08 (stealth)
         └──► GAP-11 (tracing)
```

## Build Order (topological)

| Batch | Gaps | Rationale |
|-------|------|-----------|
| 1 | GAP-12, GAP-01 | No dependencies — foundation layer |
| 2 | GAP-02 | Depends on GAP-01 (CDP) and GAP-12 (ActionResult) |
| 3 | GAP-07 | Depends on GAP-01, GAP-02, GAP-12 — the orchestration layer |
| 4 | GAP-03, GAP-04, GAP-05, GAP-08, GAP-11 | All depend on GAP-01 or GAP-02 — can be built in parallel |
| 5 | GAP-09, GAP-10 | Depend on GAP-07 — budget and security policies |
| 6 | GAP-06 | Depends on GAP-02 and GAP-09 — vision is last |

## Novel Work Summary

Three capabilities have no reference source and must be built from scratch:

| Gap | Novel Capability | Risk | Est. Effort |
|-----|-----------------|------|-------------|
| GAP-02 | Three-tier cascade with domain-level tier preference cache (automatic tier selection) | Medium | 3-4 days |
| GAP-03 | Perceptual hashing (dHash + pHash) for visual change detection | Low | 2-3 days |
| GAP-05 | ACT-R activation scoring for domain skill relevance | Low | 1-2 days |

Everything else is adopted from reference sources (Patchright, httpmorph, Hermes, Stagehand, browser-use, browser-harness, Agent-S, OpenClaw, Firecrawl, Skyvern, agent-browser, LaVague, UI-TARS-Desktop, UI-TARS).

## Key Dependencies (External)

| Package | Role | Used By |
|---------|------|---------|
| patchright | Stealth browser (Playwright fork) | GAP-01, GAP-08 |
| httpmorph | TLS fingerprinting HTTP client | GAP-08 |
| Pillow | Image processing, perceptual hashing | GAP-03, GAP-06 |
| pytesseract | OCR text grounding | GAP-06 |
| prometheus_client | Metrics export | GAP-11 |
| pyyaml | Config files | GAP-10 |

## Phase-to-Week Mapping

| Phase | Weeks | Gaps | Milestone |
|-------|-------|------|-----------|
| P0 | 1 | GAP-01, GAP-12 | Patchright session + CDP bridge + result envelope |
| P1 | 2-4 | GAP-02, GAP-07 | Three-tier engine + agent loop + tool registry |
| P2 | 5 | GAP-03, GAP-11 | Visual verification + tracing |
| P3 | 6-7 | GAP-04, GAP-09 | Self-healing + token budget |
| P4 | 7-8 | GAP-05, GAP-10 | Domain skills + security envelope |
| P5 | 8-10 | GAP-06, GAP-08 | Vision + stealth layer |

## Status Key

- **draft**: Spec written, implementation not started
- **in-progress**: Implementation underway
- **review**: Code complete, needs review
- **done**: Merged and tested
