# RFCs

Design and planning documents for Super Browser.

| Document | Status | Description |
|:---------|:-------|:------------|
| [v2-decomposition.md](v2-decomposition.md) | Draft | Decomposes the closed v2.0 PR (#112) into five reviewable tracks with acceptance criteria, rollback plans, and sequencing. |
| [v2-track-a-api-simplification.md](v2-track-a-api-simplification.md) | Implemented (v2.0.0a1) | Defines the exact breaking API removals and migrations for v2.0-alpha.1 (Track A). Covers `SuperBrowserConfig`, `_legacy_core`, `Config.from_legacy()`, and `raw_page` policy. |
| [v2-track-b-network-stealth.md](v2-track-b-network-stealth.md) | Draft | Defines the network-stealth layer for v2.0-alpha.2 (Track B). Covers `ProxyPool`, IP reputation, JA4/TLS fingerprint reporting, and aggregate `NetworkStealthReport`. Diagnostic and routing-first — no TLS spoofing claims. |
