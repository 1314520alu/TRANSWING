# Task 1 Report: Host-side fbOk / selectThetaEst (TDD)

## Summary

Implemented three pure JS helpers in `transwing_lua_mix_model.mjs` for MAVLink fold-angle feedback theta selection, with TDD tests in `transwing_lua_mix_model.test.mjs`. No Lua changes.

## Deliverables

| Export | Signature | Purpose |
|--------|-----------|---------|
| `fbOk` | `({ en, havePct, lastRxMs, nowMs, staleMs, flt, hld }) → boolean` | True when feedback is enabled, has pct, fresh, and not fault/hold |
| `foldPctToTheta` | `(foldPct, thetaMax) → number` | Maps 0–100 pct (clamped) to degrees |
| `selectThetaEst` | `({ fbOk, foldPct, thetaMax, thetaOl }) → { thetaEst, thetaOl }` | Uses feedback angle when ok; aligns open-loop to feedback |

## TDD Evidence

### Step 1–2: RED — failing tests before implementation

**Command:**
```bash
node --test transwing_lua_mix_model.test.mjs
```

**Output (excerpt):**
```
SyntaxError: The requested module './transwing_lua_mix_model.mjs' does not provide an export named 'fbOk'
    at transwing_lua_mix_model.test.mjs:8

ℹ tests 1
ℹ pass 0
ℹ fail 1
```

Module failed to load because `fbOk`, `foldPctToTheta`, and `selectThetaEst` were not yet exported.

### Step 3–4: GREEN — implementation + passing new tests

**Command (focused):**
```bash
node --test --test-name-pattern="fbOk|foldPctToTheta|selectThetaEst" transwing_lua_mix_model.test.mjs
```

**Output:**
```
✔ fbOk requires enable, havePct, fresh rx, and clear flt/hld (1.219ms)
✔ foldPctToTheta maps 0-100 onto thetaMax (0.1691ms)
✔ selectThetaEst uses feedback and aligns open-loop when fbOk (1.0144ms)
ℹ tests 3
ℹ pass 3
ℹ fail 0
```

### Full suite (pre-commit)

**Command:**
```bash
node --test transwing_lua_mix_model.test.mjs
```

**Result:** 34 tests — **18 pass, 16 fail**. All 3 new tests pass. Remaining failures are **pre-existing** on this branch (not introduced by Task 1):

- 15× `evaluateTransition`: `ReferenceError: Cannot access 'asGuard' before initialization` (uses `asGuard` at line 238 before declaration at line 327)
- 1× Lua script test: missing `SRV_Channels:set_output_pwm(32 + i, blended)` pattern

Task scope was helpers + tests only; these regressions were not fixed.

## Commit

```
44bcd2c test: add fold MAVLink feedback theta selection helpers
```

Files: `transwing_lua_mix_model.mjs`, `transwing_lua_mix_model.test.mjs` (+54 lines)

## Self-Review

### Correctness

- `fbOk`: All six guard conditions match brief — enable, havePct, null timestamps, stale window `(nowMs - lastRxMs) > staleMs`, flt/hld as `Number(x) === 1`.
- `foldPctToTheta`: Reuses existing module-level `clamp`; maps 0/50/100 and clamps out-of-range pct.
- `selectThetaEst`: When `fbOk` false, returns open-loop unchanged; when true, sets both `thetaEst` and `thetaOl` to feedback-derived angle (open-loop alignment for downstream slew).

### Scope

- No Lua edits.
- No unrelated refactors.
- Placed exports before `mixThetaForAssist` per brief snippet location (after `evaluateTransition`).

### Test coverage

- Happy path + each `fbOk` rejection branch.
- `foldPctToTheta` endpoints and clamp.
- `selectThetaEst` with and without feedback.

### Concerns

1. Full test file has 16 pre-existing failures unrelated to this task; CI may fail until `asGuard` TDZ bug and Lua motor-blend assertion are addressed separately.
2. `fbOk` stale check is strict `>` (2501 ms with 1000 ms stale fails; 2500 ms would pass) — matches brief exactly.

## Next Steps (Task 2+)

Wire these helpers into Lua mix loop / host viewer once MAVLink fold feedback plumbing is added.
