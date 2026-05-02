# Patchright

> Playwright fork with 30 AST-level anti-detection patches, eliminating Runtime.enable and replacing it with manual execution context creation, network-level init script injection, and CLI switch sanitization
> Source ID: SRC-PATCHRIGHT
> Language: TypeScript (ts-morph AST patching)
> Scale: ~35 source files, ~30 driver patches, ~150KB patch code
> Last Verified: 2026-04-22
> Verification Status: Fully Re-analyzed
> Domain Pack: ai-agents v1.0
> Pillar Schema Version: v1.0
> Analysis Version: v2 (two-pass)
> Quality Gate Status: PASS

## Subsystem Inventory

| # | Subsystem | Category | Key Files | D1: Prod | D2: Novel | D3: Compose | D4: Depth | Composite | Tier | Gap Mapping |
|---|-----------|----------|-----------|----------|-----------|-------------|-----------|-----------|------|-------------|
| 1 | Runtime.enable Elimination | Processing & Logic | `crPagePatch.ts`, `crDevToolsPatch.ts`, `crServiceWorkerPatch.ts` | 5 | 5 | 3 | 5 | 4.55 | 1 | Primary #8 |
| 2 | Execution Context Management | Processing & Logic | `framesPatch.ts` (42KB), `frameSelectorsPatch.ts` (13KB) | 4 | 5 | 2 | 5 | 3.95 | 1 | Primary #1, #8 |
| 3 | Network-Level Init Script Injection | Integration & Extension | `crNetworkManagerPatch.ts` (20KB) | 4 | 5 | 3 | 5 | 4.20 | 1 | Primary #8 |
| 4 | Chrome Switch Sanitizer | Governance & Quality | `chromiumSwitchesPatch.ts`, `chromiumPatch.ts` | 5 | 3 | 4 | 3 | 3.70 | 1 | Primary #8 |
| 5 | Closed Shadow Root Traversal | Perception & Input | `framesPatch.ts:868-1012`, `XPathSelectorEnginePatch.ts` | 4 | 4 | 3 | 4 | 3.70 | 2 | Partial #2, #6 |
| 6 | Page Binding Rewrite | Integration & Extension | `pageBindingPatch.ts`, `utilityScriptSerializersPatch.ts` | 4 | 4 | 2 | 5 | 3.70 | 2 | Partial #8 |
| 7 | CSP Fixing Engine | Processing & Logic | `crNetworkManagerPatch.ts:173-268` | 4 | 3 | 3 | 4 | 3.35 | 2 | Partial #8 |
| 8 | Trace/Snapshot Compatibility | Governance & Quality | `snapshotterPatch.ts`, `tracingPatch.ts` | 3 | 2 | 3 | 3 | 2.70 | 3 | Partial #11 |
| 9 | AST Patching Architecture | Integration & Extension | `patchright_driver_patch.ts`, all patches in `driver_patches/` | 5 | 4 | 5 | 4 | 4.40 | 1 | Partial #8 (DevOps) |
| 10 | Automated Patch Impact Analysis | Governance & Quality | `utils/check_patch_impact.ts`, `utils/extract_patched_symbols.ts` | 4 | 3 | 4 | 4 | 3.65 | 2 | No mapping (DevOps) |

Tier 1 count: 5 | Tier 2 count: 4 | Tier 3 count: 1

## Pillar Coverage

| Pillar | Coverage | Depth | Key Files | Super Browser Status |
|--------|----------|-------|-----------|----------------------|
| 1. Memory | ○ None | — | — | N/A |
| 2. Reasoning | ○ None | — | — | N/A |
| 3. Multi-Agent Coordination | ○ None | — | — | N/A |
| 4. Perception | ◐ Partial | Production | `framesPatch.ts` (DOM traversal, CSR), `XPathSelectorEnginePatch.ts` | Gap — Closed Shadow Root support is valuable |
| 5. Goal Management | ○ None | — | — | N/A |
| 6. Autonomy | ○ None | — | — | N/A |
| 7. Knowledge Representation | ○ None | — | — | N/A |
| 8. Self-Improvement | ◐ Partial | Research | `utils/check_patch_impact.ts` | Gap — automated version tracking only |
| 9. Metacognition | ○ None | — | — | N/A |
| 10. World Modeling | ○ None | — | — | N/A |
| 11. Plugin & Extension | ◐ Partial | Production | Drop-in Playwright replacement, Python/NodeJS/.NET bindings | Gap — compatible with existing Playwright ecosystem |
| 12. Runtime & Execution | ● Full | Production | `crPagePatch.ts`, `framesPatch.ts`, `crNetworkManagerPatch.ts` | Better than Super Browser — complete CDP execution rewrite |
| 13. Provider & Model Management | ○ None | — | — | N/A |
| 14. Value Alignment | ○ None | — | — | N/A |

## What to Adopt

### 1. Runtime.enable Elimination Pattern

- **Pattern**: Remove all `Runtime.enable` CDP calls from the browser session. Create execution contexts manually via `Runtime.evaluate("globalThis")` + objectId parsing. Listen for contexts via `contextPayload.name` field instead of `Runtime.executionContextCreated` events.
- **Subsystem**: #1 (Runtime.enable Elimination)
- **Intrinsic score**: 4.55
- **Source file**: `crPagePatch.ts`, `crDevToolsPatch.ts`, `crServiceWorkerPatch.ts`
- **Evidence**: Verified in code
- **What it does**: The primary detection vector for bot detectors is `Runtime.enable` — it tells Chrome to start sending execution context events, which detectors check for. Patchright systematically removes every `Runtime.enable` call and replaces the entire execution context lifecycle with manual CDP calls. Contexts are created via `Runtime.evaluate("globalThis", { serializationOptions: { serialization: "idOnly" } })` and the contextId is parsed from the objectId string (`globalThis.result.objectId.split('.')[1]`).
- **Integration target**: Gap #8 (Stealth & Anti-Bot Layer) — the single most important stealth technique. Super Browser's roadmap specifies Patchright as the stealth browser — this analysis confirms it's the right choice.
- **Overlap**: Camofox (from Hermes Agent) uses Firefox fingerprint spoofing instead. Patchright is Chromium-based and operates at the CDP protocol level. Complementary approaches.
- **Quality**: Production-ready
- **Effort**: Medium — adopt Patchright as a dependency rather than reimplementing

### 2. Network-Level Init Script Injection

- **Pattern**: Replace `Page.addScriptToEvaluateOnNewDocument` (detectable) with `Fetch.requestPaused` → modify HTML response body → inject self-removing `<script>` tags → fix CSP headers.
- **Subsystem**: #3 (Init Script Injection)
- **Intrinsic score**: 4.20
- **Source file**: `crNetworkManagerPatch.ts` (20KB)
- **Evidence**: Verified in code
- **What it does**: When init scripts need to run on every page, Patchright intercepts HTML document responses via the Fetch CDP domain, modifies the response body to inject `<script>` tags with random class names and IDs (using `crypto.randomBytes(22).toString("hex")`), adds CSP fixes to allow execution, and fulfills the modified response. Scripts self-remove via `document.getElementById(scriptId)?.remove()`. After page load, CDP `DOM.querySelectorAll` + `DOM.removeNode` cleans up remaining tag elements.
- **Integration target**: Gap #8 (Stealth & Anti-Bot) — the init script injection mechanism.
- **Overlap**: This is unique to Patchright — no other reference project implements network-level script injection as a stealth technique.
- **Quality**: Production-ready
- **Effort**: Low — use Patchright directly

### 3. Chrome Switch Sanitization

- **Pattern**: Remove 13 fingerprint-able CLI switches, add `--disable-blink-features=AutomationControlled`, force `--headless=new`.
- **Subsystem**: #4 (Switch Sanitizer)
- **Intrinsic score**: 3.70
- **Source file**: `chromiumSwitchesPatch.ts`
- **Evidence**: Verified in code
- **What it does**: Removes: `--enable-automation`, `--disable-popup-blocking`, `--disable-component-update`, `--disable-default-apps`, `--disable-extensions`, `--disable-client-side-phishing-detection`, `--disable-component-extensions-with-background-pages`, `--allow-pre-commit-input`, `--disable-ipc-flooding-protection`, `--metrics-recording-only`, `--unsafely-disable-devtools-self-xss-warnings`, `--disable-back-forward-cache`, and specific `--disable-features` entries. Adds `--disable-blink-features=AutomationControlled`. Forces `--headless=new` (not legacy headless).
- **Integration target**: Gap #8 (Stealth & Anti-Bot) — browser launch configuration.
- **Overlap**: browser-harness connects to existing Chrome (avoids the problem). Patchright provides the complete solution for new browser instances.
- **Quality**: Production-ready
- **Effort**: Low — direct adoption

### 4. Closed Shadow Root Traversal

- **Pattern**: Use `DOM.describeNode` with `pierce: true` to discover closed shadow roots, then resolve elements within them. XPath support via DOMParser to parse CSR innerHTML and map results back to DOM elements.
- **Subsystem**: #5 (Closed Shadow Root)
- **Intrinsic score**: 3.70
- **Source file**: `framesPatch.ts:868-1012`, `XPathSelectorEnginePatch.ts`
- **Evidence**: Verified in code
- **What it does**: Recursive `findClosedShadowRoots` walks the DOM tree, finds nodes with `shadowRootType: "closed"`, and collects their `backendNodeId`s. Elements inside closed shadow roots can then be resolved via CDP's `DOM.describeNode` with the `pierce: true` option. The XPath engine patch uses DOMParser to parse CSR innerHTML and map XPath results back to original DOM nodes.
- **Integration target**: Gap #2 (Three-Tier Interaction Engine) — closed shadow root support for the selector tier. Gap #6 (Vision Element Location) — structural element discovery.
- **Overlap**: browser-use handles shadow DOM with `pierce: true` in its DOM extraction. Patchright's implementation is more complete (XPath support, recursive traversal).
- **Quality**: Production-ready
- **Effort**: Low — use Patchright directly

### 5. AST-Level Patching Architecture

- **Pattern**: Use `ts-morph` to apply patches as structured AST transformations rather than raw text diffs. Each patch clearly names the target class, method, and transformation. Automated CI tracks upstream Playwright changes.
- **Subsystem**: #9 (AST Patching)
- **Intrinsic score**: 4.40
- **Source file**: `patchright_driver_patch.ts`, all files in `driver_patches/`
- **Evidence**: Verified in code
- **What it does**: The master orchestrator applies 30 patches in sequence to a checked-out Playwright source tree. Each patch file uses `ts-morph` to find specific classes/methods by name, then applies transformations (add statements, replace methods, insert imports). This approach survives formatting changes, is self-documenting, and enables automated impact analysis when Playwright updates.
- **Integration target**: DevOps — maintaining the Patchright fork as Super Browser's stealth browser. The automated `check_patch_impact.ts` and `extract_patched_symbols.ts` utilities enable tracking upstream changes.
- **Overlap**: No other reference project uses AST patching for browser customization.
- **Quality**: Production-ready
- **Effort**: Low — adopt Patchright as dependency, use its CI tooling for maintenance

## Unguided Findings

### CSP Fixing Engine (composite: 3.35)

- **What it does**: When injecting init scripts into HTML responses, parses and modifies Content-Security-Policy headers and `<meta>` tags to allow script execution. Adds `'unsafe-eval'`, `'unsafe-inline'`, wildcard sources to `script-src`, relaxes `style-src`, `img-src`, `connect-src` directives. Handles nonce-based CSP by extracting nonces from existing script tags.
- **Why it matters**: CSP fixing is essential for init script injection to work on sites with strict CSP policies. Without it, injected stealth scripts would be blocked by the site's security policy.
- **Architecture**: `_fixCSP()` method parses CSP header string into directives, modifies each directive type, and reconstructs the header.
- **Key files**: `crNetworkManagerPatch.ts:173-268`
- **Adoption feasibility**: High — directly available via Patchright

### Service Worker Neutralization (composite: 3.35)

- **What it does**: Replaces `navigator.serviceWorker.register` with a no-op function via init script injection. This prevents service workers from interfering with page automation (caching, offline behavior, push notifications).
- **Why it matters**: Service workers can intercept and modify requests, serve cached content, and generally interfere with browser automation. Neutralizing them ensures consistent page behavior.
- **Key files**: `browserContextPatch.ts`
- **Adoption feasibility**: High

## Notable Code

Execution context creation without Runtime.enable:

```typescript
// framesPatch.ts (pattern)
const globalThis = await client._sendMayFail('Runtime.evaluate', {
    expression: "globalThis",
    serializationOptions: { serialization: "idOnly" },
});
const executionContextId = parseInt(globalThis.result.objectId.split('.')[1], 10);
this._mainWorld = registerContext(executionContextId, world);
```

Self-removing init script injection:

```typescript
// crNetworkManagerPatch.ts (pattern)
let scriptId = crypto.randomBytes(22).toString("hex");
injectionHTML += `<script class="${initScriptTag}" ${nonceAttr} id="${scriptId}" 
    type="text/javascript">document.getElementById("${scriptId}")?.remove();${scriptSource}</script>`;
```

Closed shadow root discovery:

```typescript
// framesPatch.ts (pattern)
let findClosedShadowRoots = function(node, results = []) {
    if (node.shadowRoots) {
        for (const shadowRoot of node.shadowRoots) {
            if (shadowRoot.shadowRootType === "closed" && shadowRoot.backendNodeId)
                results.push(shadowRoot.backendNodeId);
            findClosedShadowRoots(shadowRoot, results);
        }
    }
    return results;
};
```

CSP fixing for script injection:

```typescript
// crNetworkManagerPatch.ts (pattern)
case 'script-src':
    addIfMissing(directiveValues, "'unsafe-eval'");
    if (!scriptNonce) addIfMissing(directiveValues, "'unsafe-inline'");
    if (!directiveValues.includes("*")) directiveValues.push("*");
    break;
```

## Thin Project Disposition

Not applicable — Patchright has 5 Tier 1 and 4 Tier 2 subsystems despite being a focused fork. Its value is concentrated but deep.

**Unique contribution**: The best-in-class open-source anti-detection implementation for Chromium. Passes Cloudflare, Kasada, Akamai, Datadome, Fingerprint.com, and CreepJS. Super Browser's roadmap correctly identifies Patchright as the stealth browser — this analysis confirms it should be adopted as a direct dependency rather than reimplemented.
