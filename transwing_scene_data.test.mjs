import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

import {
  AXES,
  BODY_FRAME,
  MOTORS,
  RAW_MOTORS,
  SIM_CG_X_SHIFT_M,
  SIM_MOTORS,
  axisSegment,
  bodyToScene,
  centroidOf,
  interpolateMotorDirection,
  interpolateMotorPosition,
} from "./transwing_scene_data.mjs";

test("uses CG body frame with X forward, Y right, Z down", () => {
  assert.deepEqual(BODY_FRAME.origin, "CG");
  assert.deepEqual(BODY_FRAME.axes, {
    x: "forward",
    y: "right wing",
    z: "down",
  });
});

test("contains the recomputed left and right hinge axes", () => {
  assert.equal(AXES.length, 2);
  assert.deepEqual(AXES.map((axis) => axis.name), [
    "left_wing_hinge_axis",
    "right_wing_hinge_axis",
  ]);
  assert.deepEqual(AXES[0].point, [0, -0.126, 0.416]);
  assert.deepEqual(AXES[0].direction, [-0.457, 0.771, 0.486]);
  assert.deepEqual(AXES[1].point, [0, 0.126, 0.416]);
  assert.deepEqual(AXES[1].direction, [-0.457, -0.771, 0.486]);
});

test("contains four motors with correct unfolded and folded positions", () => {
  assert.equal(MOTORS.length, 4);
  assert.deepEqual(
    MOTORS.map((motor) => [motor.id, motor.testLetter, motor.position, motor.spin]),
    [
      ["M1", "A", "right_front", "CCW"],
      ["M2", "C", "left_rear", "CCW"],
      ["M3", "D", "left_front", "CW"],
      ["M4", "B", "right_rear", "CW"],
    ],
  );
  assert.deepEqual(MOTORS[0].unfolded, [0.6875, 0.32, -0.045]);
  assert.deepEqual(MOTORS[0].folded, [0.3175, 0.49, -0.46]);
  assert.deepEqual(MOTORS[3].unfolded, [0.6825, 0.98, -0.06]);
  assert.deepEqual(MOTORS[3].folded, [-0.3175, 0.46, -0.355]);
});

test("keeps raw real-airframe coordinates separate from simulation CG-shifted coordinates", () => {
  assert.equal(SIM_CG_X_SHIFT_M, 0.1625);
  assert.equal(RAW_MOTORS.length, 4);
  assert.equal(SIM_MOTORS.length, 4);
  assert.notEqual(RAW_MOTORS, SIM_MOTORS);

  assert.deepEqual(RAW_MOTORS[0].folded, [0.155, 0.49, -0.46]);
  assert.deepEqual(RAW_MOTORS[1].folded, [-0.48, -0.46, -0.355]);
  assert.deepEqual(SIM_MOTORS[0].folded, [0.3175, 0.49, -0.46]);
  assert.deepEqual(SIM_MOTORS[1].folded, [-0.3175, -0.46, -0.355]);
});

test("raw hover thrust center is aft of CG while simulation hover center is on CG", () => {
  assert.deepEqual(centroidOf(RAW_MOTORS.map((motor) => motor.folded)), [-0.1625, 0, -0.4075]);
  assert.deepEqual(centroidOf(SIM_MOTORS.map((motor) => motor.folded)), [0, 0, -0.4075]);
});

test("interpolation preserves exact endpoints", () => {
  for (const motor of MOTORS) {
    assert.deepEqual(interpolateMotorPosition(motor, 0), motor.unfolded);
    assert.deepEqual(interpolateMotorPosition(motor, 90), motor.folded);
  }
});

test("maps body frame to scene frame with Y right and Z down in the viewer", () => {
  assert.deepEqual(bodyToScene([0, 1, 1]), [0, -1, -1]);
  assert.deepEqual(bodyToScene([0.6875, 0.32, -0.045]), [0.6875, -0.32, 0.045]);
});

test("points motors forward when wings are horizontal", () => {
  for (const motor of MOTORS) {
    assert.deepEqual(interpolateMotorDirection(motor, 0), [1, 0, 0]);
  }
});

test("points motors upward in the folded hover state", () => {
  for (const motor of MOTORS) {
    assert.deepEqual(interpolateMotorDirection(motor, 90), [0, 0, -1]);
  }
});

test("folded hover geometry has no net torque with equal motor thrust", () => {
  const torque = MOTORS.reduce(
    (sum, motor) => {
      const [x, y, z] = motor.folded;
      const [fx, fy, fz] = [0, 0, -1];
      return [
        sum[0] + y * fz - z * fy,
        sum[1] + z * fx - x * fz,
        sum[2] + x * fy - y * fx,
      ];
    },
    [0, 0, 0],
  );

  assert.ok(Math.abs(torque[0]) < 1e-9, `roll torque ${torque[0]}`);
  assert.ok(Math.abs(torque[1]) < 1e-9, `pitch torque ${torque[1]}`);
  assert.ok(Math.abs(torque[2]) < 1e-9, `yaw torque ${torque[2]}`);
});

test("computes hinge axis display segment endpoints from point and vector", () => {
  assert.deepEqual(axisSegment(AXES[0], 0.5), {
    start: [0.2285, -0.5115, 0.173],
    end: [-0.2285, 0.2595, 0.659],
  });
  assert.deepEqual(axisSegment(AXES[1], 0.5), {
    start: [0.2285, 0.5115, 0.173],
    end: [-0.2285, -0.2595, 0.659],
  });
});

test("viewer uses manual slider control without autoplay", () => {
  const html = readFileSync(new URL("./transwing_kinematic_viewer.html", import.meta.url), "utf8");
  assert.equal(html.includes('id="play"'), false);
  assert.equal(html.includes("dataset.playing"), false);
  assert.equal(html.includes("播放"), false);
});
