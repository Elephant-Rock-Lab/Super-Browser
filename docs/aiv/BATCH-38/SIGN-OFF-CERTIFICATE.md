# BATCH SIGN-OFF CERTIFICATE — BATCH-38

**Batch:** BATCH-38 — Browser API Surface Coverage
**Lead Programmer:** Lead
**Date:** 2026-05-13

---

## Batch Goal

Cover 5 remaining low-weight browser API detection surfaces with deterministic noise injection.

**Status: ✅ ACHIEVED**

---

## Task Summary

| Task | Priority | Status | Tests | Outcome |
|:-----|:---------|:-------|:------|:--------|
| TASK-01: Browser API Ejector | High | ✅ Accepted | 21 passed | Battery, Permissions, Speech, CSS :visited, ClientRect |
| TASK-02: Integration | High | ✅ Accepted | 6 passed | CHK-012, 12-check suite, 5-ejector pipeline |

---

## New Detection Surfaces Covered

| Surface | Before | After |
|:--------|:-------|:------|
| navigator.getBattery | ❌ Unguarded | ✅ Blocked (promise reject) |
| navigator.permissions | ❌ Unguarded | ✅ Returns denied |
| speechSynthesis.getVoices | ❌ Unguarded | ✅ Seed-derived mock voices |
| CSS :visited | ❌ Unguarded | ✅ getComputedStyle override |
| getBoundingClientRect | ❌ Unguarded | ✅ ±0.5px seed-derived jitter |

---

## Test Delta: +28 (running total 1,915)

---

**BATCH-38 ACCEPTED AND CLOSED.**

Lead Sign: Lead, 2026-05-13
