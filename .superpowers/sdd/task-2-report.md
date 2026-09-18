# Task 2 Report: Lua params + MAVLink RX state

## Status
DONE_WITH_CONCERNS

## Commits
- `85f2c9f` feat: receive fold NAMED_VALUE_FLOAT state in TW Lua

## Changes
- Expanded `TW_` param table 29→33; added `FB_EN`, `FB_REQ`, `FB_STALE`, `THETA_MAX`.
- Added MAVLink RX state (`fold_pct`, `fold_cnt`, `fold_flt`, `fold_pwm_fb`, `fold_hld`, `fold_have_pct`, `fold_last_rx_ms`), `poll_fold_mavlink()`, `compute_fb_ok()`, `fold_pct_to_theta()`.
- Source assertion test for FB params + NAMED_VALUE_FLOAT registration; updated staged-mix test table size 29→33.

## Test summary
New assertion `lua declares FB params and registers NAMED_VALUE_FLOAT` passes; 15 transition-model tests fail pre-existing `asGuard` TDZ in `transwing_lua_mix_model.mjs`; staged-mix test still fails unrelated `set_output_pwm(32+i,blended)` pattern.

## Self-review
- `fold_pct_to_theta` placed after `clamp` (Lua scope); rest per brief verbatim.
- `poll_fold_mavlink` / `compute_fb_ok` not wired into main loop — deferred to Task 3.
- `FB_REQ` / `warned_fb_req` declared but unused — reserved for Task 3 gating.

## Concerns
- Pre-existing suite failures unrelated to this task; full green requires fixing `asGuard` initialization order in JS model.
- RX plumbing is receive-only until Task 3 integrates dual-track `theta_est`.
