# Skales Competitive Analysis

**Date:** 2026-05-13  
**Repos studied:** [skalesapp/skales](https://github.com/skalesapp/skales) (v10.2.9, 930★), [skalesapp/wordpress](https://github.com/skalesapp/wordpress) (v1.3.0)  
**Analyst:** Lead  

---

## What Is Skales?

Skales is a **local-first AI desktop agent** built with Electron + Next.js 14. Single-click install (EXE/DMG/AppImage), no Docker, no terminal. Solo developer (Mario Simic, Vienna), 930 stars, 154 forks, 34 releases. BSL 1.1 license (Apache 2.0 after 2030-04-19).

**Positioning:** "AI companion" — not just a chatbot. Desktop-native, privacy-first, multi-modal.

---

## Architecture

```
┌─────────────────────────────────────────────────┐
│                    Electron Shell                │
│  ┌────────────────────────────────────────────┐  │
│  │           Next.js 14 (App Router)          │  │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────┐  │  │
│  │  │  /chat   │ │/codework │ │ /studio    │  │  │
│  │  └──────────┘ └──────────┘ └────────────┘  │  │
│  │  ┌──────────┐ ┌──────────┐ ┌────────────┐  │  │
│  │  │/browser  │ │/planner  │ │/discover   │  │  │
│  │  └──────────┘ └──────────┘ └────────────┘  │  │
│  │              src/lib/ (core)                 │  │
│  │              src/actions/ (139+ tools)       │  │
│  └────────────────────────────────────────────┘  │
│              electron/main.js                     │
│              ~/.skales-data/ (JSON + SQLite)      │
└─────────────────────────────────────────────────┘
         │                    │
    15+ AI Providers     Mobile Relay
    (BYOK, local Ollama)  (E2E encrypted)
```

**Stack:** TypeScript (85.5%), HTML (8.1%), JS (6.1%)  
**Frontend:** Next.js 14 App Router, Tailwind CSS, Framer Motion  
**Storage:** `~/.skales-data/` (JSON + SQLite)  
**AI loop:** ReAct agent, 139+ tools, multi-agent delegation  
**Mobile:** React Native Android app, QR-pairing via E2E encrypted relay

---

## Feature Map (v10.2.9)

| Category | Features | Relevance to Super Browser |
|:---------|:---------|:---------------------------|
| **Chat** | Multi-provider, streaming, voice TTS/STT | ✅ We have multi-provider LLM |
| **Codework** | File read/write, live diffs, session history, undo | ❌ We don't have this |
| **Browser Agent** | Playwright, cookie bypass, element detection, workspaces, playbooks | ✅ Core overlap — our primary competitor |
| **Studio** | Image/video/audio gen, templates, brand kit, HF Spaces | ❌ Not our space |
| **Lio AI** | Code builder, multi-AI architect, live preview | ❌ Not our space |
| **Computer Use** | Screenshot, mouse, keyboard, safety mode | ❌ Desktop control (v2.0 for us) |
| **Organization** | Multi-agent teams, CEO routing, advisor strategy | ⚠️ Partial — our delegator |
| **WordPress** | REST API plugin, Elementor, WooCommerce, SEO, media | ❌ Niche integration |
| **Calendar/Email** | Google/Apple/Outlook + Gmail/IMAP | ❌ Productivity features |
| **Memory** | Short/long-term, dreaming consolidation | ⚠️ Our MemoryStore (v1.3.0) |
| **Spotlight** | Hotkey, vision, command palette | ❌ Desktop-native feature |
| **Discover Feed** | Social network for AI agents, skill sharing | ❌ Not our space |
| **Agent Skills** | SKILL.md import, 1000+ community skills | ⚠️ Our skills system |
| **Playground** | Personalized AI workspace, glassmorphism UI | ❌ UI innovation |
| **Mobile** | Android, QR pairing, 139 tools via relay | ❌ Future consideration |
| **Voice** | TTS (6 providers), STT, voice chat mode | ❌ Not our space |
| **Desktop Buddy** | Animated mascot, tool approval | ❌ UI feature |

---

## WordPress Plugin — Deep Analysis

A single 700-line PHP file (`skales-connector.php`). MIT licensed.

### Architecture
```
Skales Desktop → HTTPS + Bearer Token → WordPress REST API (/wp-json/skales/v1/*)
```

### REST API Surface (13 endpoints)

| Endpoint | Method | Purpose |
|:---------|:-------|:--------|
| `/connect` | GET | Test connection, auto-detect plugins |
| `/pages` | GET/POST | List/create pages |
| `/pages/{id}` | PUT | Update page |
| `/posts` | POST | Create post |
| `/posts/{id}` | PUT | Update post |
| `/media` | POST | Upload media (base64) |
| `/elementor/page` | POST | Create Elementor page |
| `/elementor/page/{id}` | PUT | Update Elementor page |
| `/woo/products` | GET | List products |
| `/woo/products/bulk-price` | PUT | Bulk price update |
| `/seo/{id}` | PUT | Update SEO meta |
| `/cache/clear` | POST | Clear all caches |

### Key Technical Details

1. **Auth:** SHA-256 hashed token stored in `wp_options`. Raw token shown once, never persisted. Bearer header on every request.

2. **Elementor Integration:** Builds Flexbox Container format (Elementor 3.6+). Handles multi-column layouts via nested containers with `flex_basis`. Creates proper `_elementor_data` JSON, sets canvas template, triggers CSS regeneration.

3. **Plugin Detection:** Auto-detects 10 plugins (Elementor, WooCommerce, RankMath, Yoast, caches, forms). Reports capabilities via `/connect` endpoint.

4. **Security:** `kses_remove_filters()` for HTML passthrough (only for authenticated API calls). Token never stored raw. No external data transmission.

5. **Full-width CSS:** Injects theme-specific CSS overrides (Astra, GeneratePress, Twenty Twenty-Four, Kadence, OceanWP, Elementor) via `wp_head` for Skales-created pages.

### Code Quality Assessment

| Aspect | Grade | Notes |
|:-------|:------|:------|
| Functionality | A- | Covers all major WP operations |
| Security | B+ | SHA-256 tokens, bearer auth, no raw storage |
| Code style | B | Single 700-line file, procedural, well-commented |
| Error handling | B | WP_Error returns, but no rate limiting |
| Testability | D | No tests, no DI, tightly coupled to WP functions |

---

## Skales vs Super Browser — Feature Comparison

| Dimension | Skales | Super Browser | Verdict |
|:----------|:-------|:--------------|:--------|
| **Stealth** | None | Full stack (ejectors, profiles, consistency engine) | **We win** |
| **Browser control** | Playwright | Patchright (CDP) | Comparable |
| **Anti-detection** | None | 5 ejectors, 12 validation checks | **We win** |
| **Desktop app** | Electron (native) | Python library (no GUI) | **They win** |
| **Install friction** | 1-click EXE/DMG | `pip install` + setup | **They win** |
| **AI providers** | 15+ (BYOK) | Multi-provider | Comparable |
| **Code editing** | Full Codework (3-panel) | None | **They win** |
| **Memory** | Dreaming consolidation | MemoryStore | Comparable |
| **Mobile** | Android + relay | None | **They win** |
| **Social** | Discover Feed | None | **They win** |
| **WordPress** | Full plugin | None | **They win** |
| **API surface** | 139+ tools | ~50 API methods | **They win** |
| **Fingerprint defense** | Zero | 5 ejectors, 12 surfaces | **We win** |
| **Consistency engine** | None | 38 rules, xoshiro256** PRNG | **We win** |
| **Behavioral synthesis** | None | Bézier/Fitts/QWERTY/scroll | **We win** |
| **License** | BSL 1.1 (restrictive) | MIT | **We win** |
| **Language** | TypeScript | Python | Different audiences |
| **RAM** | ~300MB | Library (no overhead) | Different model |

---

## Takeaways for Super Browser

### What Skales Does Well (Study)
1. **1-click install** — EXE/DMG/AppImage with auto-updater. Our `pip install` is higher friction.
2. **139+ tools** — Massive tool surface. Their ReAct loop has enormous breadth.
3. **WordPress integration** — The connector plugin is a masterclass in niche integration. 700 lines, covers 90% of WordPress management via natural language.
4. **Social layer** — Discover Feed creates network effects. Agent skills ecosystem.
5. **Multi-modal** — Voice, vision, desktop control, code building, image/video generation.

### What They Lack (Our Moat)
1. **Zero stealth** — No fingerprint defense, no consistency engine, no behavioral synthesis. Skales is trivially detectable as automation.
2. **No anti-detection** — No canvas/audio/WebRTC/timing/Browser API hardening. A fingerprint scanner would flag them immediately.
3. **No deterministic profiles** — No profile system, no seed-based consistency.

### Strategic Implications

1. **Skales is NOT a stealth competitor.** They're a general-purpose AI agent. Our niche (anti-detection browser automation) is orthogonal to their "AI companion" positioning.

2. **They validate the market.** 930 stars, 34 releases, mobile app, social feed — the desktop AI agent space is real and growing.

3. **WordPress connector is a pattern worth studying.** Single PHP file, REST API, plugin auto-detection, Elementor Flexbox Container format. If we ever do WordPress integration, this is the blueprint.

4. **Tool breadth matters.** 139 tools vs our ~50. Our tools are deeper (stealth-specific), but breadth attracts users.

5. **No conflict with our roadmap.** Skales targets "AI companion" users. We target "undetectable browser automation" users. Different buyers, different value props.

---

## Summary

```
Skales:  Breadth champion — 139 tools, desktop app, mobile, social, WordPress
Us:      Depth champion — anti-detection, fingerprint defense, behavioral synthesis

Overlap: Browser automation (our core, their feature)
Moat:    Stealth (our monopoly, their gap)
Gap:     Desktop app + install experience (their advantage)
```

**Threat level: LOW.** Different market. Our stealth moat is unassailable from their direction. But their install UX and tool breadth are worth emulating in our v2.0 desktop plans.

---

Lead Sign: Lead, 2026-05-13
