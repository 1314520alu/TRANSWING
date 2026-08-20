# Transwing Lua Dynamic Mix SITL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a first complete SITL-oriented Lua dynamic-mix observer/controller for the open-loop Transwing fold actuator.

**Architecture:** Keep ArduPilot native QuadPlane/Tilt-Rotor as the primary controller. Add a Lua script that estimates fold angle from open-loop PWM plus slew-rate timing, interpolates the existing motor factor table, logs state, and optionally emits simulated motor outputs to Lua Scripting output functions. Mirror the math in a Node module so it can be tested locally before running in SITL.

**Tech Stack:** ArduPilot Lua scripting, Node.js `node:test`, existing Transwing CSV factor table.

---

### Task 1: Test Open-Loop Estimator And Factor Interpolation

**Files:**
- Create: `transwing_lua_mix_model.mjs`
- Create: `transwing_lua_mix_model.test.mjs`

- [ ] **Step 1: Write failing tests**

Test PWM-to-target-angle mapping, open-loop slew estimation, factor interpolation at 37.5 deg, and simulated scripting output scaling.

- [ ] **Step 2: Verify tests fail**

Run: `node --test transwing_lua_mix_model.test.mjs`

Expected: FAIL because `transwing_lua_mix_model.mjs` does not exist yet.

- [ ] **Step 3: Implement model**

Implement pure functions:
- `pwmToThetaTarget(pwm, pwmFw, pwmQ)`
- `stepThetaEstimate(theta, target, dt, rateUp, rateDn)`
- `interpolateFactors(theta)`
- `mixToScriptOutputs(factors, controls, options)`

- [ ] **Step 4: Verify tests pass**

Run: `node --test transwing_lua_mix_model.test.mjs`

Expected: PASS.

### Task 2: Add SITL Lua Script

**Files:**
- Create: `scripts/transwing_dynamic_mix.lua`

- [ ] **Step 1: Implement Lua script**

Add ArduPilot Lua script with:
- user parameter table prefix `TW_`
- open-loop fold angle estimator
- embedded 0/15/30/45/60/75/90 deg factor table
- logger output `TWNG`
- optional Scripting output functions 94-97 when `TW_LOG_ONLY = 0`

- [ ] **Step 2: Keep real-motor outputs untouched by default**

Default `TW_LOG_ONLY = 1`. With that setting the script only logs and sends GCS messages.

### Task 3: Document SITL Setup

**Files:**
- Create: `Transwing_Lua_动态混控仿真说明.md`
- Modify: `ArduPilot_QuadPlane_TiltRotor_参数配置.md`

- [ ] **Step 1: Add setup doc**

Document script placement, parameters, expected output functions, and how to run in SITL.

- [ ] **Step 2: Link from parameter doc**

Add a short reference to the new Lua simulation document.

### Task 4: Verify

**Files:**
- Test: `transwing_lua_mix_model.test.mjs`
- Test: `transwing_scene_data.test.mjs`

- [ ] **Step 1: Run local tests**

Run: `node --test transwing_lua_mix_model.test.mjs transwing_scene_data.test.mjs`

Expected: PASS.

- [ ] **Step 2: Static inspect Lua**

Run a text check for required API calls and defaults:
- `TW_LOG_ONLY`
- `SRV_Channels`
- `logger:write`
- `param:add_table`
