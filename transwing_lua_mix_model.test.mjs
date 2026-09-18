import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  FACTOR_TABLE,
  evaluateTransition,
  fbOk,
  foldPctToTheta,
  foldSlewStep,
  inferApFoldTarget,
  interpolateFactors,
  mixThetaForAssist,
  mixToScriptOutputs,
  pwmToThetaTarget,
  readControlInputs,
  selectThetaEst,
  stepThetaEstimate,
  thetaToPwm,
  updateApFoldTarget,
} from "./transwing_lua_mix_model.mjs";

test("maps fold actuator PWM to target angle with fixed-wing at 0 deg and hover at 90 deg", () => {
  assert.equal(pwmToThetaTarget(1100, 1100, 1900), 0);
  assert.equal(pwmToThetaTarget(1900, 1100, 1900), 90);
  assert.equal(pwmToThetaTarget(1500, 1100, 1900), 45);
  assert.equal(pwmToThetaTarget(900, 1100, 1900), 0);
  assert.equal(pwmToThetaTarget(2100, 1100, 1900), 90);
});

test("maps reversed fold actuator PWM ranges", () => {
  assert.equal(pwmToThetaTarget(1900, 1900, 1100), 0);
  assert.equal(pwmToThetaTarget(1100, 1900, 1100), 90);
  assert.equal(pwmToThetaTarget(1500, 1900, 1100), 45);
});

test("slews estimated angle toward target using open-loop actuator rates", () => {
  assert.equal(stepThetaEstimate(0, 90, 1, 4.5, 4.5), 4.5);
  assert.equal(stepThetaEstimate(0, 90, 10, 4.5, 4.5), 45);
  assert.equal(stepThetaEstimate(88, 90, 10, 4.5, 4.5), 90);
  assert.equal(stepThetaEstimate(90, 0, 2, 4.5, 9), 72);
  assert.equal(stepThetaEstimate(2, 0, 2, 4.5, 9), 0);
});

test("infers AP fold target from VTOL mode or fixed-wing airspeed gate", () => {
  assert.equal(inferApFoldTarget(17, 5), 90);
  assert.equal(inferApFoldTarget(6, 0.6), 0);
  assert.equal(inferApFoldTarget(5, 0.4), 0);
  assert.equal(inferApFoldTarget(6, 19), 0);
  assert.equal(inferApFoldTarget(3, 18), null);
});

test("tracks AP fold target from PWM until fixed-wing airspeed forces 0 deg", () => {
  const pwmFw = 2000;
  const pwmQ = 1000;
  const tracking = updateApFoldTarget({
    rawPwm: 1389,
    pwmFw,
    pwmQ,
    flightMode: 6,
    airspeed: 15,
    thetaCmd: 55,
    prevTarget: 55,
    dt: 0.1,
  });
  assert.equal(tracking, 0);

  const jumped = updateApFoldTarget({
    rawPwm: 2000,
    pwmFw,
    pwmQ,
    flightMode: 6,
    airspeed: 20,
    thetaCmd: 55,
    prevTarget: 55,
    dt: 0.1,
  });
  assert.equal(jumped, 0);
});

test("fold slew steps command angle instead of jumping PWM endpoint", () => {
  const pwmFw = 2000;
  const pwmQ = 1000;
  let thetaCmd = 55;
  const target = 0;
  const pwmSeries = [thetaToPwm(thetaCmd, pwmFw, pwmQ)];

  for (let i = 0; i < 20; i += 1) {
    thetaCmd = foldSlewStep(thetaCmd, target, 0.1, 4.5, 4.5);
    pwmSeries.push(thetaToPwm(thetaCmd, pwmFw, pwmQ));
  }

  assert.ok(pwmSeries[1] > pwmSeries[0]);
  assert.ok(pwmSeries.at(-1) > pwmSeries[0]);
  assert.ok(pwmSeries.at(-1) < pwmFw);
  assert.notEqual(pwmSeries[1], pwmFw);
});

test("interpolates motor factors between table rows", () => {
  const factors = interpolateFactors(37.5);
  assert.equal(factors.length, 4);
  assert.deepEqual(
    factors.map((row) => row.motor),
    ["M1", "M2", "M3", "M4"],
  );
  assert.equal(factors[0].throttle, 1);
  assert.equal(Number(factors[0].roll.toFixed(6)), -0.496631);
  assert.equal(Number(factors[0].pitch.toFixed(6)), 1);
  assert.equal(Number(factors[2].yawForce.toFixed(6)), 0.496631);
  assert.equal(factors[3].yawDrag, -1);
});

test("factor table is generated from simulation-corrected hover geometry", () => {
  const hover = FACTOR_TABLE.find((row) => row.theta === 90);
  assert.ok(hover);
  assert.deepEqual(
    hover.motors.map((motor) => [motor.motor, motor.pitch]),
    [
      ["M1", 1],
      ["M2", -1],
      ["M3", 1],
      ["M4", -1],
    ],
  );
});

test("clamps factor interpolation to endpoints", () => {
  assert.deepEqual(interpolateFactors(-10), FACTOR_TABLE[0].motors);
  assert.deepEqual(interpolateFactors(100), FACTOR_TABLE.at(-1).motors);
});

test("reads RC stick inputs when TW_INPUT_SRC uses RC", () => {
  const controls = readControlInputs({
    inputSrc: 1,
    throttle: 0,
    roll: 0,
    pitch: 0,
    yaw: 0,
    rcThrottle: 1500,
    rcRoll: 1700,
    rcPitch: 1300,
    rcYaw: 1500,
    pwmMin: 1000,
    pwmMax: 2000,
  });

  assert.equal(controls.throttle, 0.5);
  assert.equal(controls.roll, 0.4);
  assert.equal(controls.pitch, -0.4);
  assert.equal(controls.yaw, 0);
});

test("falls back to TW_THR/ROLL/PITCH/YAW when input source is parameters", () => {
  const controls = readControlInputs({
    inputSrc: 0,
    throttle: 0.7,
    roll: -0.2,
    pitch: 0.3,
    yaw: 0.1,
    rcThrottle: 2000,
    rcRoll: 2000,
  });

  assert.equal(controls.throttle, 0.7);
  assert.equal(controls.roll, -0.2);
  assert.equal(controls.pitch, 0.3);
  assert.equal(controls.yaw, 0.1);
});

test("transition model holds FBWA low-speed attitude instead of aborting", () => {
  const state = evaluateTransition({
    thetaDeg: 65,
    targetThetaDeg: 60,
    airspeed: 0.7,
    rollDeg: 5,
    pitchDeg: 22,
    climbRate: 0,
    motorPwm: [1400, 1400, 1400, 1400],
    flightMode: 5,
  }, {
    blendAirspeedMin: 12,
    attitudeAbortDeg: 20,
  });

  assert.equal(state.risk, "DANGER");
  assert.equal(state.action, "HOLD_THETA");
  assert.notEqual(state.allowedThetaDeg, 90);
});

test("mixes controls into scripting PWM outputs with correction gain", () => {
  const factors = interpolateFactors(90);
  const outputs = mixToScriptOutputs(factors, {
    throttle: 0.55,
    roll: 0.1,
    pitch: -0.2,
    yaw: 0.05,
  }, {
    minPwm: 1100,
    maxPwm: 1900,
    hoverPwm: 1500,
    gain: 0.2,
  });

  assert.deepEqual(
    outputs.map((output) => output.channel),
    [94, 95, 96, 97],
  );
  assert.deepEqual(
    outputs.map((output) => output.motor),
    ["M1", "M2", "M3", "M4"],
  );
  assert.deepEqual(
    outputs.map((output) => output.pwm),
    [1700, 1748, 1708, 1724],
  );
});

test("transition model allows stable low-speed acceleration down to 70 degrees", () => {
  const state = evaluateTransition({
    thetaDeg: 75,
    targetThetaDeg: 70,
    airspeed: 8,
    rollDeg: 8,
    pitchDeg: 10,
    climbRate: 0,
    motorPwm: [1600, 1600, 1600, 1600],
    elevatorNorm: 0.2,
  });

  assert.equal(state.phase, "ACCEL");
  assert.equal(state.risk, "WARN");
  assert.equal(state.action, "ALLOW");
  assert.equal(state.allowedThetaDeg, 70);
  assert.match(state.reason, /accel/);
});

test("low ground airspeed does not trigger fixed-wing airspeed guard", () => {
  const state = evaluateTransition({
    thetaDeg: 10,
    targetThetaDeg: 10,
    airspeed: 0.6,
    rollDeg: 0,
    pitchDeg: 0,
    climbRate: 0,
    motorPwm: [1500, 1500, 1500, 1500],
    elevatorNorm: 0,
    asGuard: false,
  });

  assert.equal(state.risk, "OK");
  assert.equal(state.action, "ALLOW");
  assert.equal(state.reason, "nominal");
});

test("transition model blocks blend fold angles until blend airspeed", () => {
  const state = evaluateTransition({
    thetaDeg: 50,
    targetThetaDeg: 50,
    airspeed: 12,
    rollDeg: 8,
    pitchDeg: 10,
    climbRate: 0,
    motorPwm: [1600, 1600, 1600, 1600],
    elevatorNorm: 0.2,
  });

  assert.equal(state.phase, "BLEND");
  assert.equal(state.risk, "DANGER");
  assert.equal(state.action, "HOLD_THETA");
  assert.equal(state.allowedThetaDeg, 55);
  assert.match(state.reason, /blend airspeed/);
});

test("transition model blocks fixed-wing fold angles until fixed-wing airspeed", () => {
  const state = evaluateTransition({
    thetaDeg: 35,
    targetThetaDeg: 20,
    airspeed: 12,
    rollDeg: 8,
    pitchDeg: 10,
    climbRate: 0,
    motorPwm: [1600, 1600, 1600, 1600],
    elevatorNorm: 0.2,
  });

  assert.equal(state.phase, "BLEND");
  assert.equal(state.risk, "DANGER");
  assert.equal(state.action, "HOLD_THETA");
  assert.equal(state.allowedThetaDeg, 30);
  assert.match(state.reason, /fixed-wing airspeed/);
});

test("assist link holds fold at safe minimum when below blend airspeed", () => {
  const state = evaluateTransition({
    thetaDeg: 15,
    targetThetaDeg: 0,
    airspeed: 10,
    rollDeg: 5,
    pitchDeg: 5,
    climbRate: 0,
    motorPwm: [1600, 1600, 1600, 1600],
    elevatorNorm: 0.2,
    assistActive: true,
    flightMode: 6,
  });

  assert.equal(state.action, "HOLD_THETA");
  assert.equal(state.allowedThetaDeg, 55);
  assert.match(state.reason, /assist active hold 55/);
  assert.equal(mixThetaForAssist(15, true, { airspeed: 10 }), 55);
  assert.equal(mixThetaForAssist(60, true, { airspeed: 10 }), 60);
});

test("assist link releases past safe minimum above blend airspeed", () => {
  const state = evaluateTransition({
    thetaDeg: 55,
    targetThetaDeg: 0,
    airspeed: 15,
    rollDeg: 5,
    pitchDeg: 5,
    climbRate: 0,
    motorPwm: [1600, 1600, 1600, 1600],
    elevatorNorm: 0.2,
    assistActive: true,
    flightMode: 6,
  });

  assert.equal(state.allowedThetaDeg, 30);
  assert.doesNotMatch(state.reason, /assist active hold 55/);
  assert.equal(mixThetaForAssist(55, true, { airspeed: 15 }), 55);
  assert.equal(mixThetaForAssist(30, true, { airspeed: 15 }), 30);
});

test("assist link does not override abort-to-Q", () => {
  const state = evaluateTransition({
    thetaDeg: 20,
    targetThetaDeg: 20,
    airspeed: 15,
    rollDeg: 40,
    pitchDeg: 5,
    climbRate: 0,
    motorPwm: [1600, 1600, 1600, 1600],
    elevatorNorm: 0.2,
    assistActive: true,
    flightMode: 6,
  });

  assert.equal(state.action, "ABORT_TO_Q");
  assert.equal(state.allowedThetaDeg, 90);
});

test("transition model aborts early when attitude diverges in accel", () => {
  const state = evaluateTransition({
    thetaDeg: 65.6,
    targetThetaDeg: 65.6,
    airspeed: 12.4,
    rollDeg: 43,
    pitchDeg: 1.5,
    climbRate: 0,
    motorPwm: [1300, 1472, 1551, 1373],
    elevatorNorm: 0.1,
  });

  assert.equal(state.phase, "ACCEL");
  assert.equal(state.risk, "DANGER");
  assert.equal(state.action, "ABORT_TO_Q");
  assert.equal(state.allowedThetaDeg, 90);
  assert.match(state.reason, /attitude/);
});

test("transition model allows fixed-wing fold angle only after fixed-wing airspeed gate", () => {
  const state = evaluateTransition({
    thetaDeg: 30,
    targetThetaDeg: 30,
    airspeed: 26,
    rollDeg: 5,
    pitchDeg: 4,
    climbRate: 1,
    motorPwm: [1550, 1560, 1545, 1555],
    elevatorNorm: 0.1,
  });

  assert.equal(state.phase, "FIXED_WING");
  assert.equal(state.risk, "OK");
  assert.equal(state.action, "ALLOW");
  assert.equal(state.allowedThetaDeg, 30);
});

test("transition model does not flag Q_PWM_MIN idle as motor saturation", () => {
  const state = evaluateTransition({
    thetaDeg: 55,
    targetThetaDeg: 55,
    airspeed: 8,
    motorPwm: [1000, 1000, 1000, 1000],
  });

  assert.equal(state.risk, "DANGER");
  assert.doesNotMatch(state.reason, /saturation/);
});

test("transition model does not abort fixed-wing trim sink with adequate airspeed", () => {
  const state = evaluateTransition({
    thetaDeg: 0,
    targetThetaDeg: 0,
    airspeed: 25.4,
    rollDeg: 0.1,
    pitchDeg: -16.1,
    climbRate: -5.4,
    descentSustained: false,
    motorPwm: [1550, 1560, 1545, 1555],
    elevatorNorm: 0.1,
  });

  assert.equal(state.phase, "FIXED_WING");
  assert.equal(state.action, "ALLOW");
  assert.equal(state.allowedThetaDeg, 0);
});

test("transition model aborts sustained fixed-wing sink combined with attitude danger", () => {
  const state = evaluateTransition({
    thetaDeg: 0,
    targetThetaDeg: 0,
    airspeed: 25.4,
    rollDeg: 2,
    pitchDeg: -40,
    climbRate: -6.5,
    descentSustained: true,
    motorPwm: [1550, 1560, 1545, 1555],
    elevatorNorm: 0.1,
  }, {
    attitudeAbortDeg: 30,
    attitudeDangerDeg: 35,
    fixedWingAirspeedMin: 16,
  });

  assert.equal(state.action, "ABORT_TO_Q");
  assert.equal(state.allowedThetaDeg, 90);
});

test("transition model aborts severe descent during transition even without attitude fault", () => {
  const state = evaluateTransition({
    thetaDeg: 55,
    targetThetaDeg: 50,
    airspeed: 20,
    rollDeg: 5,
    pitchDeg: 8,
    climbRate: -13,
    descentSustained: false,
    motorPwm: [1600, 1600, 1600, 1600],
    elevatorNorm: 0.1,
  });

  assert.equal(state.action, "ABORT_TO_Q");
  assert.equal(state.allowedThetaDeg, 90);
  assert.match(state.reason, /descent/);
});

test("transition model flags attitude and output saturation during conversion", () => {
  const state = evaluateTransition({
    thetaDeg: 55,
    targetThetaDeg: 50,
    airspeed: 20,
    rollDeg: 43,
    pitchDeg: 12,
    climbRate: -6,
    motorPwm: [1990, 1600, 1590, 1580],
    elevatorNorm: 0.96,
  });

  assert.equal(state.phase, "BLEND");
  assert.equal(state.risk, "DANGER");
  assert.equal(state.action, "ABORT_TO_Q");
  assert.equal(state.allowedThetaDeg, 90);
  assert.match(state.reason, /attitude/);
  assert.match(state.reason, /descent/);
  assert.match(state.reason, /saturation/);
});

test("Lua script defaults to log-only mode and writes isolated scripting functions", () => {
  const lua = readFileSync(new URL("./scripts/transwing_dynamic_mix.lua", import.meta.url), "utf8");

  assert.match(lua, /add_param\(TABLE_KEY,\s*2,\s*"LOG_ONLY",\s*1\)/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*4,\s*"PWM_FW",\s*2000\)/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*5,\s*"PWM_Q",\s*1000\)/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*24,\s*"INPUT_SRC",\s*1\)/);
  assert.match(lua, /logger:write\(/);
  assert.match(lua, /TWNG/);
  assert.match(lua, /A1,A2,A3,A4/);
  assert.match(lua, /TWTR/);
  assert.match(lua, /PHASE/);
  assert.match(lua, /SAFE_MIN/);
  assert.match(lua, /ACCEL_MIN/);
  assert.match(lua, /BLEND_MIN/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*22,\s*"ATT_ABORT",\s*42\)/);
  assert.match(lua, /TW_GUARD/);
  assert.match(lua, /read_control_inputs/);
  assert.match(lua, /set_output_pwm_chan_timeout\(fold_chan,\s*safe_pwm,\s*guard_ms\)/);
  assert.match(lua, /apply_fold_servo_output/);
  assert.match(lua, /infer_ap_fold_target/);
  assert.match(lua, /update_ap_fold_target/);
  assert.match(lua, /fold_slew_active/);
  assert.match(lua, /SRV_Channels:set_output_pwm\(93 \+ i, pwm\[i\]\)/);
});

test("Lua script exposes staged mix modes before direct motor control", () => {
  const lua = readFileSync(new URL("./scripts/transwing_dynamic_mix.lua", import.meta.url), "utf8");

  assert.match(lua, /add_table\(TABLE_KEY,\s*"TW_",\s*33\)/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*29,\s*"ASST_EN",\s*1\)/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*23,\s*"MIX_MODE",\s*0\)/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*26,\s*"MIX_BLEND",\s*0\)/);
  assert.match(lua, /local MIX_MODE_OBSERVE = 0/);
  assert.match(lua, /local MIX_MODE_MIRROR = 1/);
  assert.match(lua, /local MIX_MODE_CONTROL = 2/);
  assert.match(lua, /local function effective_mix_mode\(/);
  assert.match(lua, /local function can_takeover_motors\(/);
  assert.match(lua, /if P\.LOG_ONLY:get\(\) < 0\.5 and mode == MIX_MODE_OBSERVE then/);
  assert.match(lua, /if mix_mode == MIX_MODE_MIRROR then/);
  assert.match(lua, /SRV_Channels:set_output_pwm\(93 \+ i, pwm\[i\]\)/);
  assert.match(lua, /if can_takeover_motors\(/);
  assert.match(lua, /SRV_Channels:set_output_pwm\(32 \+ i, blended\)/);
});

test("Lua guard warning includes the trigger reason", () => {
  const lua = readFileSync(new URL("./scripts/transwing_dynamic_mix.lua", import.meta.url), "utf8");

  assert.match(lua, /local function build_guard_reason\(/);
  assert.match(lua, /read_assist_active/);
  assert.match(lua, /quadplane:in_assisted_flight/);
  assert.match(lua, /apply_assist_link/);
  assert.match(lua, /mix_theta_for_assist/);
  assert.match(lua, /assist active hold/);
  assert.match(lua, /TWAS/);
  assert.match(lua, /blend airspeed/);
  assert.match(lua, /fixed-wing airspeed/);
  assert.match(lua, /attitude roll=/);
  assert.match(lua, /descent /);
  assert.match(lua, /saturation/);
  assert.match(lua, /guard reason=%s/);
});

test("default SITL parameter files enable real motor takeover with diagnostic mirror", () => {
  const luaParams = readFileSync(new URL("./transwing_lua_sitl.params", import.meta.url), "utf8");
  const mpParams = readFileSync(new URL("./transwing_sitl_mp.params", import.meta.url), "utf8");

  for (const text of [luaParams, mpParams]) {
    assert.match(text, /^TW_LOG_ONLY,0$/m);
    assert.match(text, /^TW_MIX_MODE,2$/m);
    assert.match(text, /^TW_INPUT_SRC,1$/m);
    assert.match(text, /^TW_SAFE_MIN,55$/m);
    assert.match(text, /^TW_ACCEL_MIN,55$/m);
    assert.match(text, /^TW_BLEND_MIN,30$/m);
    assert.match(text, /^TW_BLEND_AS,13$/m);
    assert.match(text, /^TW_FW_AS,19$/m);
    assert.match(text, /^TW_ATT_ABORT,42$/m);
    assert.match(text, /^TW_SAT_PWM,1980$/m);
    assert.match(text, /^TW_GUARD_FBWA,1$/m);
    assert.match(text, /^TW_GUARD_MS,1000$/m);
    assert.match(text, /^TW_ASST_EN,1$/m);
  }

  assert.match(luaParams, /^SERVO13_FUNCTION,94$/m);
  assert.match(luaParams, /^SERVO14_FUNCTION,95$/m);
  assert.match(luaParams, /^SERVO15_FUNCTION,96$/m);
  assert.match(luaParams, /^SERVO16_FUNCTION,97$/m);
});

test("fbOk requires enable, havePct, fresh rx, and clear flt/hld", () => {
  const base = { en: true, havePct: true, lastRxMs: 1000, nowMs: 1500, staleMs: 1000, flt: 0, hld: 0 };
  assert.equal(fbOk(base), true);
  assert.equal(fbOk({ ...base, en: false }), false);
  assert.equal(fbOk({ ...base, havePct: false }), false);
  assert.equal(fbOk({ ...base, nowMs: 2501 }), false);
  assert.equal(fbOk({ ...base, flt: 0.49 }), true);
  assert.equal(fbOk({ ...base, flt: 0.5 }), false);
  assert.equal(fbOk({ ...base, flt: 1 }), false);
  assert.equal(fbOk({ ...base, flt: 2 }), false);
  assert.equal(fbOk({ ...base, hld: 0.5 }), false);
  assert.equal(fbOk({ ...base, hld: 1 }), false);
});

test("foldPctToTheta maps 0-100 onto thetaMax", () => {
  assert.equal(foldPctToTheta(0, 90), 0);
  assert.equal(foldPctToTheta(50, 90), 45);
  assert.equal(foldPctToTheta(100, 90), 90);
  assert.equal(foldPctToTheta(-10, 90), 0);
  assert.equal(foldPctToTheta(120, 90), 90);
});

test("selectThetaEst uses feedback and aligns open-loop when fbOk", () => {
  const withFb = selectThetaEst({ fbOk: true, foldPct: 50, thetaMax: 90, thetaOl: 10 });
  assert.equal(withFb.thetaEst, 45);
  assert.equal(withFb.thetaOl, 45);

  const ol = selectThetaEst({ fbOk: false, foldPct: 50, thetaMax: 90, thetaOl: 12 });
  assert.equal(ol.thetaEst, 12);
  assert.equal(ol.thetaOl, 12);
});

test("lua declares FB params and registers NAMED_VALUE_FLOAT", () => {
  const lua = readFileSync(new URL("./scripts/transwing_dynamic_mix.lua", import.meta.url), "utf8");
  const module = readFileSync(
    new URL("./scripts/modules/MAVLink/mavlink_msg_NAMED_VALUE_FLOAT.lua", import.meta.url),
    "utf8",
  );
  assert.match(lua, /add_param\(TABLE_KEY,\s*30,\s*"FB_EN"/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*31,\s*"FB_REQ"/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*32,\s*"FB_STALE"/);
  assert.match(lua, /add_param\(TABLE_KEY,\s*33,\s*"THETA_MAX"/);
  assert.match(lua, /msg_id\s*=\s*251/);
  assert.match(lua, /msg_map\s*=\s*\{\s*\[251\]\s*=\s*"NAMED_VALUE_FLOAT"\s*\}/);
  assert.match(lua, /mavlink:init\(\s*32\s*,\s*1\s*\)/);
  assert.match(lua, /pcall\(FB\.msgs\.decode,\s*msg,\s*FB\.msg_map\)/);
  assert.match(lua, /register_rx_msgid/);
  assert.match(lua, /NAMED_VALUE_FLOAT|msgid.*251|MSG_ID/);
  assert.match(lua, /fold_pct/);
  assert.match(module, /NAMED_VALUE_FLOAT\.id = 251/);
  assert.match(module, /NAMED_VALUE_FLOAT\.crc_extra = 170/);
  assert.match(module, /\{\s*"value",\s*"<f"\s*\}/);
  assert.match(module, /"value"[\s\S]*"name"/);
});

test("lua selects theta from feedback and gates CONTROL on FB_REQ", () => {
  const lua = readFileSync(new URL("./scripts/transwing_dynamic_mix.lua", import.meta.url), "utf8");
  assert.match(lua, /ST\.theta_ol/);
  assert.match(lua, /theta_cmd\s*=\s*0/);
  assert.match(lua, /ST\.theta_cmd\s*=\s*step_theta_estimate\(ST\.theta_cmd,\s*slew_target/);
  assert.doesNotMatch(lua, /ST\.theta_cmd\s*=\s*ST\.theta_est/);
  assert.match(lua, /update_ap_fold_target\([\s\S]*?ST\.theta_cmd,\s*ST\.theta_ap_target/);
  assert.match(lua, /compute_fb_ok/);
  assert.match(lua, /logger:write\("TWFB"/);
  assert.match(lua, /FB_REQ/);
  assert.match(lua, /fold estimate timeout|TW_DEG/);
});
