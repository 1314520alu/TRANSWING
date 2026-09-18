import {
  MOTORS,
  interpolateMotorDirection,
  interpolateMotorPosition,
} from "./transwing_scene_data.mjs";

export const FACTOR_THETAS = Object.freeze([0, 15, 30, 45, 60, 75, 90]);
export const TRANSITION_DEFAULTS = Object.freeze({
  blendAirspeedMin: 13,
  fixedWingAirspeedMin: 19,
  safeMinThetaDeg: 55,
  accelMinThetaDeg: 55,
  blendMinThetaDeg: 30,
  attitudeAbortDeg: 42,
  attitudeWarnDeg: 20,
  attitudeDangerDeg: 35,
  descentDangerMps: -8,
  motorPwmMin: 1100,
  motorPwmMax: 1900,
  motorPwmSat: 1980,
  elevatorSaturationNorm: 0.9,
});

export const FACTOR_TABLE = generateFactorTable();

const clamp = (value, min, max) => Math.min(Math.max(value, min), max);
const lerp = (from, to, ratio) => from + (to - from) * ratio;

export function generateFactorTable(thetas = FACTOR_THETAS) {
  return thetas.map((theta) => {
    const rows = MOTORS.map((motor) => {
      const position = interpolateMotorPosition(motor, theta);
      const force = interpolateMotorDirection(motor, theta);
      const moment = cross(position, force);
      return {
        motor: motor.id,
        spin: motor.spin,
        throttle: theta <= 0 ? 0 : 1,
        rollMoment: moment[0],
        pitchMoment: moment[1],
        yawMoment: moment[2],
      };
    });

    const rollMax = maxAbs(rows.map((row) => row.rollMoment));
    const pitchMax = maxAbs(rows.map((row) => row.pitchMoment));
    const yawMax = maxAbs(rows.map((row) => row.yawMoment));

    return {
      theta,
      motors: rows.map((row) => ({
        motor: row.motor,
        throttle: row.throttle,
        roll: normalize(row.rollMoment, rollMax),
        pitch: normalize(row.pitchMoment, pitchMax),
        yawForce: normalize(row.yawMoment, yawMax),
        yawDrag: row.spin === "CCW" ? 1 : -1,
      })),
    };
  });
}

export function pwmToThetaTarget(pwm, pwmFw, pwmQ) {
  if (pwmFw === pwmQ) {
    throw new Error("pwmFw and pwmQ must be different");
  }

  const ratio = clamp((pwm - pwmFw) / (pwmQ - pwmFw), 0, 1);
  return ratio * 90;
}

export function stepThetaEstimate(theta, target, dt, rateUp, rateDn) {
  const delta = target - theta;
  if (delta === 0 || dt <= 0) {
    return theta;
  }

  const rate = delta > 0 ? rateUp : rateDn;
  const maxStep = Math.abs(rate * dt);
  if (Math.abs(delta) <= maxStep) {
    return target;
  }
  return theta + Math.sign(delta) * maxStep;
}

export function inferApFoldTarget(flightMode, airspeed, options = {}) {
  const cfg = { ...TRANSITION_DEFAULTS, ...options };
  if (flightMode >= 17 && flightMode <= 23) {
    return 90;
  }
  if (flightMode === 5 || flightMode === 6) {
    return 0;
  }
  if (airspeed >= cfg.fixedWingAirspeedMin) {
    return 0;
  }
  return null;
}

export function updateApFoldTarget(input, options = {}) {
  const cfg = { ...TRANSITION_DEFAULTS, ...options };
  const rateUp = options.rateUp ?? 4.5;
  const rateDn = options.rateDn ?? 4.5;
  const dt = Math.max(input.dt ?? 0.1, 0.05);
  const inferred = inferApFoldTarget(input.flightMode ?? -1, input.airspeed ?? 0, cfg);
  if (inferred != null) {
    return inferred;
  }

  const fromPwm = pwmToThetaTarget(input.rawPwm, input.pwmFw, input.pwmQ);
  const maxStep = Math.max(rateUp, rateDn) * dt * 2 + 2;
  const prevTarget = input.prevTarget;
  const thetaCmd = input.thetaCmd ?? fromPwm;

  if (prevTarget == null) {
    return fromPwm;
  }

  if (Math.abs(fromPwm - thetaCmd) <= maxStep + 1) {
    return fromPwm;
  }
  if (Math.abs(fromPwm - prevTarget) > maxStep + 1) {
    return fromPwm;
  }
  return prevTarget;
}

export function thetaToPwm(theta, pwmFw, pwmQ) {
  return Math.round(pwmFw + clamp(theta, 0, 90) / 90 * (pwmQ - pwmFw));
}

export function foldSlewStep(thetaCmd, slewTarget, dt, rateUp, rateDn) {
  return stepThetaEstimate(thetaCmd, slewTarget, dt, rateUp, rateDn);
}

export function interpolateFactors(theta) {
  if (theta <= FACTOR_TABLE[0].theta) {
    return FACTOR_TABLE[0].motors;
  }
  if (theta >= FACTOR_TABLE.at(-1).theta) {
    return FACTOR_TABLE.at(-1).motors;
  }

  const upperIndex = FACTOR_TABLE.findIndex((row) => row.theta >= theta);
  const lower = FACTOR_TABLE[upperIndex - 1];
  const upper = FACTOR_TABLE[upperIndex];
  const ratio = (theta - lower.theta) / (upper.theta - lower.theta);

  return lower.motors.map((lowerMotor, index) => {
    const upperMotor = upper.motors[index];
    return {
      motor: lowerMotor.motor,
      throttle: lerp(lowerMotor.throttle, upperMotor.throttle, ratio),
      roll: lerp(lowerMotor.roll, upperMotor.roll, ratio),
      pitch: lerp(lowerMotor.pitch, upperMotor.pitch, ratio),
      yawForce: lerp(lowerMotor.yawForce, upperMotor.yawForce, ratio),
      yawDrag: lerp(lowerMotor.yawDrag, upperMotor.yawDrag, ratio),
    };
  });
}

export function mixToScriptOutputs(factors, controls, options = {}) {
  const minPwm = options.minPwm ?? 1100;
  const maxPwm = options.maxPwm ?? 1900;
  const hoverPwm = options.hoverPwm ?? 1500;
  const gain = options.gain ?? 0.2;
  const pwmSpan = maxPwm - hoverPwm;

  return factors.map((factor, index) => {
    const normalized =
      controls.throttle * factor.throttle +
      gain * (
        controls.roll * factor.roll +
        controls.pitch * factor.pitch +
        controls.yaw * (factor.yawForce + factor.yawDrag)
      );
    const pwm = Math.round(clamp(hoverPwm + normalized * pwmSpan, minPwm, maxPwm));

    return {
      channel: 94 + index,
      motor: factor.motor,
      pwm,
    };
  });
}

export function readControlInputs(options = {}) {
  const src = options.inputSrc ?? 1;
  const controls = {
    throttle: clamp(options.throttle ?? 0, 0, 1),
    roll: clamp(options.roll ?? 0, -1, 1),
    pitch: clamp(options.pitch ?? 0, -1, 1),
    yaw: clamp(options.yaw ?? 0, -1, 1),
  };

  if (src !== 1) {
    return controls;
  }

  const pwmMin = options.pwmMin ?? 1000;
  const pwmMax = options.pwmMax ?? 2000;
  const stickCenter = options.stickCenter ?? 1500;
  const stickHalf = options.stickHalf ?? 500;

  if (options.rcThrottle != null) {
    const normalized = (options.rcThrottle - pwmMin) / (pwmMax - pwmMin);
    controls.throttle = clamp(normalized, 0, 1);
  }
  if (options.rcRoll != null) {
    controls.roll = clamp((options.rcRoll - stickCenter) / stickHalf, -1, 1);
  }
  if (options.rcPitch != null) {
    controls.pitch = clamp((options.rcPitch - stickCenter) / stickHalf, -1, 1);
  }
  if (options.rcYaw != null) {
    controls.yaw = clamp((options.rcYaw - stickCenter) / stickHalf, -1, 1);
  }

  return controls;
}

export function evaluateTransition(input, options = {}) {
  const cfg = { ...TRANSITION_DEFAULTS, ...options };
  const thetaDeg = clamp(input.thetaDeg ?? 90, 0, 90);
  const targetThetaDeg = clamp(input.targetThetaDeg ?? thetaDeg, 0, 90);
  const airspeed = Math.max(0, input.airspeed ?? 0);
  const rollDeg = Math.abs(input.rollDeg ?? 0);
  const pitchDeg = Math.abs(input.pitchDeg ?? 0);
  const climbRate = input.climbRate ?? 0;
  const motorPwm = input.motorPwm ?? [];
  const elevatorNorm = Math.abs(input.elevatorNorm ?? 0);

  const phase = phaseForTheta(thetaDeg, cfg.accelMinThetaDeg, cfg.blendMinThetaDeg);
  const reasons = [];
  let risk = "OK";
  let allowedThetaDeg = targetThetaDeg;

  const stableAccel = asGuard && targetThetaDeg >= cfg.accelMinThetaDeg &&
    targetThetaDeg < 90 &&
    airspeed < cfg.blendAirspeedMin;
  const lowBlendAirspeed = asGuard && targetThetaDeg < cfg.accelMinThetaDeg &&
    targetThetaDeg >= cfg.blendMinThetaDeg &&
    airspeed < cfg.blendAirspeedMin;
  const lowFixedWingAirspeed = asGuard && targetThetaDeg < cfg.blendMinThetaDeg &&
    airspeed < cfg.fixedWingAirspeedMin;
  const attitudeAbort = rollDeg > cfg.attitudeAbortDeg || pitchDeg > cfg.attitudeAbortDeg;
  const attitudeDanger = rollDeg > cfg.attitudeDangerDeg || pitchDeg > cfg.attitudeDangerDeg;
  const attitudeWarn = rollDeg > cfg.attitudeWarnDeg || pitchDeg > cfg.attitudeWarnDeg;
  const descentDanger = climbRate < cfg.descentDangerMps;
  const descentSustained = input.descentSustained === true;
  const descentSevere = climbRate < cfg.descentDangerMps * 1.5;
  const inFixedWing = targetThetaDeg < cfg.blendMinThetaDeg &&
    airspeed >= cfg.fixedWingAirspeedMin;
  const descentAbort = inFixedWing
    ? (descentSevere || (descentSustained && (attitudeAbort || attitudeDanger)))
    : (descentSevere || descentSustained);
  const motorPwmSat = options.motorPwmSat ?? cfg.motorPwmSat;
  const flightMode = input.flightMode ?? -1;
  const guardFbwa = options.guardFbwa ?? true;
  const modeFbwa = 5;
  const maxMotorPwm = motorPwm.length ? Math.max(...motorPwm) : 0;
  const motorSaturation = motorPwm.some((pwm) => pwm >= motorPwmSat) ||
    motorPwm.some((pwm) => pwm <= 1050 && maxMotorPwm >= motorPwmSat - 50);
  const saturation = motorSaturation ||
    elevatorNorm >= cfg.elevatorSaturationNorm;

  if (stableAccel && risk === "OK") {
    reasons.push(`accel at airspeed ${airspeed.toFixed(1)}`);
    risk = "WARN";
  }
  if (lowBlendAirspeed) {
    reasons.push(`blend airspeed ${airspeed.toFixed(1)} below gate`);
    risk = "DANGER";
  }
  if (lowFixedWingAirspeed && targetThetaDeg < cfg.blendMinThetaDeg) {
    reasons.push(`fixed-wing airspeed ${airspeed.toFixed(1)} below gate`);
    risk = "DANGER";
  }
  if (attitudeAbort) {
    reasons.push(`attitude roll=${rollDeg.toFixed(1)} pitch=${pitchDeg.toFixed(1)}`);
    risk = "DANGER";
  } else if (attitudeDanger) {
    reasons.push(`attitude roll=${rollDeg.toFixed(1)} pitch=${pitchDeg.toFixed(1)}`);
    risk = "DANGER";
  } else if (attitudeWarn && risk === "OK") {
    reasons.push(`attitude roll=${rollDeg.toFixed(1)} pitch=${pitchDeg.toFixed(1)}`);
    risk = "WARN";
  }
  if (descentDanger) {
    reasons.push(`descent ${climbRate.toFixed(1)} m/s`);
    risk = "DANGER";
  }
  if (descentSustained && descentDanger) {
    reasons.push(`descent sustained`);
  }
  if (saturation) {
    reasons.push("saturation");
    risk = "DANGER";
  }

  if (risk === "DANGER" && lowBlendAirspeed) {
    allowedThetaDeg = cfg.accelMinThetaDeg;
  }
  if (risk === "DANGER" && targetThetaDeg < cfg.blendMinThetaDeg) {
    allowedThetaDeg = cfg.blendMinThetaDeg;
  }

  const abortTrigger = attitudeAbort || descentAbort || saturation;
  const fbwaLowSpeed = guardFbwa && flightMode === modeFbwa && airspeed < cfg.blendAirspeedMin;
  if (risk === "DANGER" && abortTrigger && targetThetaDeg < 90) {
    if (fbwaLowSpeed && attitudeAbort && !descentAbort && !saturation) {
      allowedThetaDeg = Math.max(
        targetThetaDeg,
        targetThetaDeg < cfg.blendMinThetaDeg
          ? cfg.blendMinThetaDeg
          : targetThetaDeg < cfg.accelMinThetaDeg
            ? cfg.accelMinThetaDeg
            : targetThetaDeg,
      );
    } else {
      allowedThetaDeg = 90;
    }
  }

  const assistActive = input.assistActive === true;
  const assistEnable = options.assistEnable ?? true;
  const asGuard = input.asGuard !== false && airspeed >= (options.groundAirspeedMax ?? 3);
  if (assistActive && assistEnable && targetThetaDeg < cfg.safeMinThetaDeg) {
    const allowPastSafeMin = airspeed >= cfg.blendAirspeedMin;
    if (!allowPastSafeMin && allowedThetaDeg !== 90) {
      const nextAllowed = Math.max(allowedThetaDeg, cfg.safeMinThetaDeg);
      if (nextAllowed > allowedThetaDeg) {
        reasons.push(`assist active hold ${cfg.safeMinThetaDeg.toFixed(0)}`);
      }
      allowedThetaDeg = nextAllowed;
      if (risk === "OK") {
        risk = "WARN";
      }
    }
  }

  return {
    phase,
    risk,
    action: allowedThetaDeg === 90 && targetThetaDeg < 90
      ? "ABORT_TO_Q"
      : allowedThetaDeg > targetThetaDeg ? "HOLD_THETA" : "ALLOW",
    allowedThetaDeg,
    reason: reasons.join("; ") || "nominal",
    assistActive,
  };
}

export function fbOk({ en, havePct, lastRxMs, nowMs, staleMs, flt, hld }) {
  if (!en) return false;
  if (!havePct) return false;
  if (lastRxMs == null || nowMs == null) return false;
  if ((nowMs - lastRxMs) > staleMs) return false;
  if (Number(flt) === 1) return false;
  if (Number(hld) === 1) return false;
  return true;
}

export function foldPctToTheta(foldPct, thetaMax) {
  const pct = clamp(Number(foldPct), 0, 100);
  return (pct / 100) * thetaMax;
}

export function selectThetaEst({ fbOk: ok, foldPct, thetaMax, thetaOl }) {
  if (!ok) {
    return { thetaEst: thetaOl, thetaOl };
  }
  const thetaEst = foldPctToTheta(foldPct, thetaMax);
  return { thetaEst, thetaOl: thetaEst };
}

export function mixThetaForAssist(thetaDeg, assistActive, options = {}) {
  const cfg = { ...TRANSITION_DEFAULTS, ...options };
  const assistEnable = options.assistEnable ?? true;
  const airspeed = options.airspeed ?? 0;
  if (!assistActive || !assistEnable) {
    return thetaDeg;
  }
  if (airspeed >= cfg.blendAirspeedMin && thetaDeg <= cfg.safeMinThetaDeg + 1) {
    return thetaDeg;
  }
  return Math.max(thetaDeg, cfg.safeMinThetaDeg);
}

function phaseForTheta(thetaDeg, accelMin = TRANSITION_DEFAULTS.accelMinThetaDeg, blendMin = TRANSITION_DEFAULTS.blendMinThetaDeg) {
  if (thetaDeg > 75) return "HOVER";
  if (thetaDeg >= accelMin) return "ACCEL";
  if (thetaDeg >= blendMin) return "BLEND";
  return "FIXED_WING";
}

function cross(a, b) {
  return [
    a[1] * b[2] - a[2] * b[1],
    a[2] * b[0] - a[0] * b[2],
    a[0] * b[1] - a[1] * b[0],
  ];
}

function maxAbs(values) {
  return Math.max(...values.map((value) => Math.abs(value)), 0);
}

function normalize(value, maxValue) {
  if (maxValue <= 1e-9) {
    return 0;
  }
  return round6(value / maxValue);
}

function round6(value) {
  return Math.round(value * 1_000_000) / 1_000_000;
}
