## Tier 1: DOM Resilience (Tests Selector → Coordinate Fallback)

| Scenario | What It Tests | Expected Failure Mode |
|----------|-------------|----------------------|
| **Dynamic ID soup** | Page where every element has a random `id="x7k9m2"` regenerated on each load | Selector matching fails; must fall back to coordinate or vision |
| **CSS-in-JS chaos** | React/Vue app with hashed class names (`.css-1a2b3c`) and no semantic attributes | `data-testid` missing; must use text content or visual position |
| **Shadow DOM login form** | Authentication inside closed shadow roots (e.g., some bank portals) | Standard selectors cannot pierce; CDP coordinate click required |
| **Nested iframes** | Payment form buried 3 levels deep in cross-origin iframes | `page.frame_locator()` chain breaks; coordinate click at compositor level bypasses |
| **Hydration race** | Next.js page where buttons exist in DOM but are non-interactive until JS hydrates | `page.click()` times out; need wait-for-stable or retry with visual verification |
| **Infinite scroll trap** | Content loads as you scroll, but "Load More" button disappears and reappears | Stale element reference; need scroll-then-relocate loop |

**Test URL candidates**: `https://www.threads.net` (shadow DOM), `https://www.behance.net` (dynamic grids), any React-admin dashboard.

---

## Tier 2: Anti-Bot Evasion (Tests Patchright + Stealth)

| Scenario | What It Tests | Expected Failure Mode |
|----------|-------------|----------------------|
| **Cloudflare Turnstile** | "Verify you are human" challenge with invisible CAPTCHA | `navigator.webdriver` leak; Patchright must patch CDP `Runtime.enable` |
| **DataDome slider CAPTCHA** | Drag-the-piece puzzle with behavioral tracking | Coordinate click lacks human-like mouse curve; needs path interpolation |
| **Akamai Bot Manager** | Fingerprinting + behavioral ML on mouse movements | Raw CDP dispatch detected; needs real mouse or Browser Use cloud |
| **PerimeterX (HUMAN)** | Challenge page with honeypot fields and timing analysis | Fast form fill flagged as bot; needs randomized delays between actions |
| **Fingerprint.com** | 300+ signal collection including WebGL, Canvas, AudioContext | Patchright handles most; AudioContext clock skew may remain |
| **TLS fingerprint mismatch** | Site blocks based on JA3/JA4 hash of cipher suites | Requires proxy with matching TLS fingerprint |

**Test URL candidates**: `https://nowsecure.nl` (Cloudflare test), `https://datadome.co` (demo), `https://www.footlocker.com` (PerimeterX), `https://fingerprint.com/demo` (fingerprinting test).

---

## Tier 3: Vision & Cognitive (Tests Visual Fallback + Domain Skills)

| Scenario | What It Tests | Expected Failure Mode |
|----------|-------------|----------------------|
| **Canvas-based UI** | Drawing app, game, or data visualization where no DOM elements exist | Selector and coordinate both fail; vision must identify interactive regions |
| **SVG icon buttons** | Toolbar with `<svg>` icons and no text labels | Text-based selector fails; vision must recognize icon semantics |
| **Image map navigation** | Old-school `<map>`/`<area>` or interactive infographic | Standard click hits wrong coordinates; vision must parse image structure |
| **CAPTCHA image grid** | "Select all traffic lights" — requires visual understanding | LLM vision accuracy; needs specific prompting |
| **Broken responsive layout** | Mobile viewport where elements overlap or are off-screen | Coordinate click hits wrong element; needs viewport-aware vision |
| **Dark mode toggle flips colors** | Site changes theme, invalidating cached selectors | Domain skill must store both themes; visual verification catches mismatch |

**Test URL candidates**: `https://excalidraw.com` (canvas), `https://www.figma.com` (canvas + complex DOM), `https://www.google.com/recaptcha/api2/demo` (CAPTCHA).

---

## Tier 4: Session & State Recovery (Tests Self-Healing)

| Scenario | What It Tests | Expected Failure Mode |
|----------|-------------|----------------------|
| **Auth token expiry mid-task** | JWT expires after 15 minutes during long workflow | Session recovery must detect 401, refresh token, replay action |
| **Browser crash during upload** | Chrome renderer process dies on large file | Daemon must detect WebSocket disconnect, respawn, resume task |
| **Popup blocker intercepts OAuth** | Google login opens popup that gets blocked | Recovery must detect blocked popup, retry with `popup=1` |
| **Rate limit → CAPTCHA → success** | Site throttles, serves CAPTCHA, then resumes | Three-state recovery: wait → solve → continue |
| **A/B test variant** | Site shows different layout to 50% of users | Domain skill must store both variants; selector fallback to vision |
| **Geolocation block** | Content varies by IP/geo; selectors valid only for one region | Recovery must detect mismatch, switch proxy, reload skills |

**Test URL candidates**: Any OAuth flow (Google, GitHub), `https://www.linkedin.com` (rate limits, A/B tests), `https://www.netflix.com` (geo-blocks).

---

## Tier 5: Adversarial & Deception (Tests Full Stack)

| Scenario | What It Tests | Expected Failure Mode |
|----------|-------------|----------------------|
| **Honeypot form fields** | Hidden fields that bots fill but humans ignore | `display:none` detection; must skip invisible elements |
| **Fake buttons** | "Download" buttons that are actually ads; real button is subtle | Vision must distinguish semantic intent from visual prominence |
| **Clickjacking overlay** | Transparent iframe overlays steal clicks | Coordinate click hits wrong target; need frame-aware hit testing |
| **Slowloris-style page** | Page loads forever, never fires `load` event | Navigation timeout; need custom wait condition |
| **Memory exhaustion** | Single-page app that leaks memory over 100+ actions | Browser crash; session recovery must respawn with clean profile |
| **CSP blocking inline scripts** | `eval()` and inline JS blocked by Content Security Policy | `Runtime.evaluate` fails; need script injection via allowed sources |

**Test URL candidates**: Ad-heavy sites (`https://www.download.com`), SPAs with memory leaks (large React tables), sites with strict CSP (`https://github.com`).

---

## Tier 6: Multi-Modal Integration (Tests Predator's Cognitive Stack)

| Scenario | What It Tests | Expected Failure Mode |
|----------|-------------|----------------------|
| **"Book me a flight" end-to-end** | Navigate Kayak → search → select → fill passenger → pay | 50+ actions; domain skill must learn and generalize across airlines |
| **Compare prices across 5 sites** | Amazon, Walmart, Target, Best Buy, eBay for same product | Each site has different selectors; skills must auto-discover |
| **File upload + verification** | Upload PDF to portal, verify success message appears | File chooser dialog handling; post-upload visual verification |
| **Two-factor auth workflow** | Login → SMS code → enter code → dashboard | External event (SMS) coordination; session must stay alive |
| **Social media cross-post** | Draft post on Buffer → publish to Twitter, LinkedIn, Mastodon | Each platform has different auth flows and rate limits |

---

## Recommended Test Matrix

```python
# Pseudocode for a comprehensive test suite
CHALLENGES = [
    # Tier 1: DOM Resilience
    ("shadow_dom_login", "https://bank.example.com/login", ["selector", "coordinate"]),
    ("dynamic_ids", "https://threads.net", ["selector", "coordinate", "vision"]),
    ("nested_iframes", "https://payment.example.com/checkout", ["coordinate"]),
    
    # Tier 2: Anti-Bot
    ("cloudflare_turnstile", "https://nowsecure.nl", ["stealth", "cloud"]),
    ("datadome_slider", "https://datadome.co/demo", ["stealth", "human_curve"]),
    ("fingerprint_test", "https://fingerprint.com/demo", ["stealth"]),
    
    # Tier 3: Vision
    ("canvas_drawing", "https://excalidraw.com", ["vision"]),
    ("captcha_grid", "https://google.com/recaptcha/demo", ["vision", "captcha_solver"]),
    ("svg_icons", "https://figma.com", ["vision"]),
    
    # Tier 4: Recovery
    ("auth_expiry", "https://app.example.com/long-task", ["session_recovery"]),
    ("browser_crash", "https://upload.example.com/large-file", ["daemon_restart"]),
    ("ab_test_variant", "https://linkedin.com/feed", ["skill_variants"]),
    
    # Tier 5: Adversarial
    ("honeypot_form", "https://registration.example.com", ["visibility_check"]),
    ("clickjacking", "https://vulnerable.example.com", ["frame_aware"]),
    ("memory_leak", "https://spa.example.com/big-table", ["health_monitor"]),
    
    # Tier 6: Integration
    ("book_flight", "https://kayak.com", ["domain_skills", "end_to_end"]),
    ("price_comparison", ["amazon.com", "walmart.com", "target.com"], ["multi_domain"]),
    ("2fa_workflow", "https://secure.example.com", ["external_events"]),
]
```
