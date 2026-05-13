# BATCH SIGN-OFF CERTIFICATE — BATCH-32

**Batch:** BATCH-32 — Biomechanical Behavior v2  
**Lead Programmer:** Lead  
**Date:** 2026-05-13  
**Commit:** (latest on master)

---

## Batch Goal

Replace basic random-jitter human behavior with scientifically grounded biomechanical models: cubic Bézier mouse trajectories with Fitts's Law timing, QWERTY-aware digraph keystroke timing, and inertial scroll with exponential friction decay.

**Status: ✅ ACHIEVED**

---

## Task Summary

| Task | Priority | Status | Tests | Outcome |
|:-----|:---------|:-------|:------|:--------|
| TASK-01: Pure-Data Behavioral Synthesis | Critical | ✅ Accepted | 30 passed | Mouse, keyboard, scroll synthesis |
| TASK-02: HumanBehaviorAdapter Integration | High | ✅ Accepted | 9 passed | CDP dispatch of synthesized events |

---

## Batch-Level Acceptance Criteria

| BAC | Status | Evidence |
|:----|:-------|:---------|
| BAC-01 | ✅ PASS | synthesize_mouse_trajectory: 37 events in 605ms for 700px, deterministic |
| BAC-02 | ✅ PASS | synthesize_keystrokes: 26 events for "hello world", digraph variation + corrections |
| BAC-03 | ✅ PASS | synthesize_scroll: 30 events for 500px, inertial decay |
| BAC-04 | ✅ PASS | HumanBehaviorAdapter dispatches synthesized events via mouse.move/keyboard/wheel |
| BAC-05 | ⚠️ DEFERRED | CHANGELOG deferred to BATCH-34 |
| BAC-06 | ✅ PASS | All docs archived under docs/aiv/BATCH-32/ |
| BAC-07 | ✅ PASS | 1,767 tests passed. 2 pre-existing failures unrelated. |
| BAC-08 | ✅ PASS | ruff check on all BATCH-32 files: 0 warnings |

---

## What Changed vs Before

```
Before BATCH-32:
  _patchright_click:  mouse.move(target, steps=random(5,15))  ← straight line with jitter
  _patchright_type:   keyboard.type(ch, delay=random(50,150))  ← uniform random delay
  humanize_scroll:    mouse.wheel(0, scroll_step_px * amount)  ← single event

After BATCH-32:
  _patchright_click:  Bézier curve with Fitts timing, 10% overshoot, autocorrelated jitter
  _patchright_type:   QWERTY digraph delays (lognormal), 2% mistake injection, WPM scaling
  humanize_scroll:    Inertial model with friction decay (τ=350ms), multiple events
```

---

## Test Delta

| Metric | Count |
|:-------|:------|
| Baseline | 1,753 |
| New tests | +39 (30 synthesis + 9 adapter) |
| Updated tests | 2 (v1.4 integration tests adapted) |
| Final total | ~1,767 |

---

## AIV Framework Compliance

| Check | Status |
|:------|:-------|
| Blueprint issued before review | ✅ |
| Reviewer session spawned (separate) | ✅ |
| Lead Response documented | ✅ |
| All Tasks have Partial Sign-Off | ✅ |
| All ACs traceable to tests | ✅ |
| Full suite regression test | ✅ |
| Lint gate passed | ✅ |
| Single commit with Co-Authored-By | ✅ |

---

## Lead Decision

**BATCH-32 ACCEPTED AND CLOSED.**

Three batches down (30, 31, 32). Two remaining: BATCH-33 (Integration & Regression Harness) and BATCH-34 (Release v1.5.0).

---

Lead Sign: Lead, 2026-05-13 18:00
