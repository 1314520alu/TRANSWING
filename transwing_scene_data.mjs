export const BODY_FRAME = Object.freeze({
  origin: "CG",
  axes: Object.freeze({
    x: "forward",
    y: "right wing",
    z: "down",
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

export const SIM_CG_X_SHIFT_M = 0.1625;

export const RAW_MOTORS = freezeMotorRows([
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

export const SIM_MOTORS = freezeMotorRows(
  RAW_MOTORS.map((motor) => shiftMotorX(motor, SIM_CG_X_SHIFT_M)),
);

export const MOTORS = SIM_MOTORS;

export function centroidOf(points) {
  const sum = points.reduce(
    (acc, point) => acc.map((value, index) => value + point[index]),
    [0, 0, 0],
  );
  return sum.map((value) => round6(value / points.length));
}

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

export function interpolateMotorDirection(_motor, thetaDeg) {
  const s = smoothstep(thetaDeg / 90);
  return unit([
    1 * (1 - s) + 0 * s,
    0,
    0 * (1 - s) + -1 * s,
  ]);
}

export function motorRowsAt(thetaDeg) {
  return MOTORS.map((motor) => ({
    ...motor,
    current: interpolateMotorPosition(motor, thetaDeg),
  }));
}

export function axisSegment(axis, halfLength = 0.5) {
  return {
    start: axis.point.map((value, index) =>
      round6(value - axis.direction[index] * halfLength),
    ),
    end: axis.point.map((value, index) =>
      round6(value + axis.direction[index] * halfLength),
    ),
  };
}

export function bodyToScene(point) {
  return [point[0], -point[1], -point[2]];
}

function round6(value) {
  return Math.round(value * 1_000_000) / 1_000_000;
}

function freezeMotorRows(rows) {
  return Object.freeze(
    rows.map((motor) =>
      Object.freeze({
        ...motor,
        unfolded: Object.freeze([...motor.unfolded]),
        folded: Object.freeze([...motor.folded]),
      }),
    ),
  );
}

function shiftMotorX(motor, dx) {
  return {
    ...motor,
    unfolded: shiftPointX(motor.unfolded, dx),
    folded: shiftPointX(motor.folded, dx),
  };
}

function shiftPointX(point, dx) {
  return [round6(point[0] + dx), point[1], point[2]];
}

function unit(vector) {
  const length = Math.hypot(...vector);
  return vector.map((value) => round6(value / length));
}
