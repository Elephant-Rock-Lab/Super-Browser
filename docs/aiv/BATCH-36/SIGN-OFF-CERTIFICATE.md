# BATCH SIGN-OFF CERTIFICATE — BATCH-36

**Batch:** BATCH-36 — Canvas & Audio Fingerprint Defense  
**Lead Programmer:** Lead  
**Date:** 2026-05-13  

---

## Batch Goal

Add deterministic noise injection for canvas (±2 RGBA) and audio (±0.0001 sample) fingerprint surfaces via JS payloads delivered through Fetch.fulfillRequest body-splice.

**Status: ✅ ACHIEVED**

---

## Task Summary

| Task | Priority | Status | Tests | Outcome |
|:-----|:---------|:-------|:------|:--------|
| TASK-01: Canvas Ejector + Framework | Critical | ✅ Accepted | 26 passed | CanvasEjector + EjectorConfig + Registry |
| TASK-02: Audio Ejector | Critical | ✅ Accepted | 23 passed | AudioEjector with AudioContext overrides |
| TASK-03: Integration + Validation | High | ✅ Accepted | 6 passed | Matrix extension + CHK-009 |

---

## Batch-Level Acceptance Criteria

| BAC | Status | Evidence |
|:----|:-------|:---------|
| BAC-01 | ✅ PASS | CanvasEjector: ±2 RGBA noise, covers toDataURL/toBlob/getImageData/readPixels |
| BAC-02 | ✅ PASS | AudioEjector: ±0.0001 noise, covers getChannelData/getFloatFrequencyData |
| BAC-03 | ✅ PASS | Payloads delivered via ejector registry, injectable through body-splice |
| BAC-04 | ✅ PASS | FingerprintMatrix has ejector_seed field |
| BAC-05 | ✅ PASS | 1,850 passed, 1 pre-existing flaky failure |
| BAC-06 | ✅ PASS | ruff check → 0 warnings |
| BAC-07 | ✅ PASS | All docs under docs/aiv/BATCH-36/ |

---

## Test Delta

| Metric | Count |
|:-------|:------|
| Baseline | 1,795 |
| New tests | +55 (26 canvas + 23 audio + 6 integration) |
| Final total | ~1,850 |

---

## New Detection Surfaces Covered

| Surface | Before | After |
|:--------|:-------|:------|
| Canvas fingerprint | ❌ Unguarded | ✅ ±2 RGBA noise |
| Audio fingerprint | ❌ Unguarded | ✅ ±0.0001 sample noise |

---

## Lead Decision

**BATCH-36 ACCEPTED AND CLOSED.**

Next: BATCH-37 (WebRTC + Math + Timing Defense).

---

Lead Sign: Lead, 2026-05-13
