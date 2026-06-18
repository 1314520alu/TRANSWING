export const BODY_FRAME = Object.freeze({
  origin: "CG",
  axes: Object.freeze({
    x: "forward",
    y: "right wing",
    z: "up",
  }),
});

export const AXES = Object.freeze([
  Object.freeze({
    name: "left_wing_hinge_axis",
    label: "Left hinge",
    point: Object.freeze([0, -0.126, 0.416]),
    direction: Object.freeze([-0.457, 0.771, 0.486]),
  }),
  Object.freeze({
    name: "right_wing_hinge_axis",
    label: "Right hinge",
    point: Object.freeze([0, 0.126, 0.416]),
    direction: Object.freeze([-0.457, -0.771, 0.486]),
  }),
]);

export const MOTORS = Object.freeze([
  Object.freeze({
    id: "M1",
    testLetter: "A",
    position: "right_front",
    label: "M1 / A / RF",
    spin: "CCW",
    side: "right",
    unfolded: Object.freeze([0.525, 0.32, -0.045]),
    folded: Object.freeze([0.155, 0.49, -0.46]),
  }),
  Object.freeze({
    id: "M2",
    testLetter: "C",
    position: "left_rear",
    label: "M2 / C / LR",
    spin: "CCW",
    side: "left",
    unfolded: Object.freeze([0.52, -0.98, -0.06]),
    folded: Object.freeze([-0.48, -0.46, -0.355]),
  }),
  Object.freeze({
    id: "M3",
    testLetter: "D",
    position: "left_front",
    label: "M3 / D / LF",
    spin: "CW",
    side: "left",
    unfolded: Object.freeze([0.525, -0.32, -0.045]),
    folded: Object.freeze([0.155, -0.49, -0.46]),
  }),
  Object.freeze({
    id: "M4",
    testLetter: "B",
    position: "right_rear",
    label: "M4 / B / RR",
    spin: "CW",
    side: "right",
    unfolded: Object.freeze([0.52, 0.98, -0.06]),
    folded: Object.freeze([-0.48, 0.46, -0.355]),
  }),
]);

export function smoothstep(value) {
  const x = Math.max(0, Math.min(1, value));
  return x * x * (3 - 2 * x);
}

export function interpolateMotorPosition(motor, thetaDeg) {
  const s = smoothstep(thetaDeg / 90);
  return motor.unfolded.map((value, index) =>
    round6(value * (1 - s) + motor.folded[index] * s),
  );
}

export function motorRowsAt(thetaDeg) {
  return MOTORS.map((motor) => ({
    ...motor,
    current: interpolateMotorPosition(motor, thetaDeg),
  }));
}

function round6(value) {
  return Math.round(value * 1_000_000) / 1_000_000;
}
