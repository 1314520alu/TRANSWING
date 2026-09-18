# Task 4 Report: Docs sync

**Branch:** `feature/lua-fold-mavlink-feedback`  
**Date:** 2026-09-18  
**Status:** Complete

## Summary

Synchronized documentation with the implemented Lua fold MAVLink feedback path in `scripts/transwing_dynamic_mix.lua` (`TW_FB_EN/REQ/STALE/THETA_MAX`, dual-track `theta_est`, `FB_REQ` CONTROL gate, `TWFB` log).

## Files changed

| File | Change |
|------|--------|
| `Transwing_折叠执行器_MAVLink回传说明.md` | New/updated: §4 reflects Lua integration; §6 split into bench (manual), script (checked), integration (manual) |
| `Transwing_Lua_动态混控仿真说明.md` | Param count 33; added `TW_FB_*` table + §4.2 detail; `TWFB` log §6.3; updated flowchart, limits, config block |
| `knowledge-base/README.md` | Added MAVLink fold feedback doc links (quick lookup + full index) |
| `knowledge-base/index.yaml` | Added `Transwing_折叠执行器_MAVLink回传说明.md` entry under `sitl_lua` |

## Commit

```
docs: document Lua fold MAVLink feedback path
```

## Documentation highlights

### MAVLink 回传说明

- Header and §4 now state feedback is **implemented** in `transwing_dynamic_mix.lua`.
- §4 table covers: `fold_pct` → `theta_est`, stale/fault fallback, `FB_REQ` CONTROL block, `TWFB` logging.
- §6 acceptance: script-side items marked `[x]`; wiring and field trials remain manual `[ ]`.

### Lua 动态混控说明

- **`TW_FB_EN`** (1): enable MAVLink fold feedback receive.
- **`TW_FB_REQ`** (1): block `MIX_MODE=2` without valid feedback.
- **`TW_FB_STALE`** (1000 ms): feedback timeout.
- **`TW_THETA_MAX`** (90): pct → degrees full travel.
- **`theta_est`**: feedback path preferred; open-loop `TW_RATE_*` fallback; CONTROL fold PWM still uses command slew angle.
- New **`TWFB`** DataFlash message documented.

## Knowledge base

Links to the MAVLink fold doc were missing from `README.md` and `index.yaml`; added per task brief. No other index changes required.

## Verification

- [x] §4/§6 updated in MAVLink doc
- [x] FB params and `theta_est` source documented in Lua doc
- [x] Knowledge-base links present
- [x] No Lua/JS code modified
- [x] Commit on `feature/lua-fold-mavlink-feedback`

## Concerns / follow-ups

1. **Hardware validation pending**: Script-side checklist is checked in docs only; bench items (SERIAL wiring, `fold_pct` vs visual angle) still need real flight-controller + actuator testing.
2. **`Transwing_折叠执行器_MAVLink回传说明.md` was untracked**: First commit of this file in this branch; ensure prior tasks’ Lua implementation is on the same branch before merge.
3. **SITL without F103**: SITL runs will continue to use open-loop `theta_est` unless a MAVLink fold source is injected; document readers should not expect `TWFB.Ok=1` in pure SITL without mock.

## Out of scope (per brief)

- No changes to `scripts/transwing_dynamic_mix.lua` or JS mix model.
- No push to remote.
